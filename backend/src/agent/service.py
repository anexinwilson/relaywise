import time
from typing import Any

from composio import Composio
from composio_langchain import LangchainProvider
from langchain.agents import create_agent
from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from langchain.agents.middleware import SummarizationMiddleware
from langchain_core.messages.utils import count_tokens_approximately

from agent.client import get_redis_client
from agent.event_streaming import stream_event
from agent.intent import detect_personality_intent
from agent.app_router import Resolution, display_name, resolve
from agent.personality import PersonalityHandler
from agent.sync import (
    connected_slugs,
    get_recent_app,
    preferred_app,
    set_recent_app,
)
from config import settings
from credits import (
    CreditCalculator,
    CreditChecker,
    extract_token_counts,
    next_reset_label,
)
from memory import ChatMemory, UserMemoryStore, build_memory_block, extract_memories
from utils import get_logger

from .prompts import (
    APP_NOT_CONNECTED_MESSAGE,
    ASSUMED_APP_HINT,
    CONNECTED_APPS_HINT,
    EXECUTION_SYSTEM_PROMPT,
    GENERIC_ERROR_MESSAGE,
    NO_APPS_CONNECTED_MESSAGE,
    OUT_OF_CREDITS_MESSAGE,
    WHICH_APP_MESSAGE,
)

logger = get_logger(__name__)

# The checkpointer replays a thread's entire history on every turn, which grows
# without bound and would eventually exceed the model's context window.
#
# LangChain's own middleware handles this: once history passes the trigger, the
# older half is replaced by a generated summary and recent turns are kept
# verbatim. Summarising rather than discarding means a follow-up like "send
# that to the team" still resolves — a hard reset would lose what "that" was.
# It happens silently; the user is never told.
MAX_HISTORY_TOKENS = 24_000
KEEP_RECENT_MESSAGES = 20

# A run is not capped by call count.
#
# There was a six-call ceiling here, sized for a flow where tools were loaded
# up front and a run was search, execute, reply. The Tool Router changed that
# shape: COMPOSIO_SEARCH_TOOLS and COMPOSIO_GET_TOOL_SCHEMAS are themselves
# model calls, so discovery alone can spend the whole budget and the run ends
# with "Model call limits exceeded" instead of an answer. Meta-tools trade
# fewer tokens per call for more calls, and the old ceiling did not account
# for it.
#
# Spend is bounded by credits instead: the balance is checked before a run and
# debited after, and the Bedrock budget in terraform/api/monitoring.tf is the
# backstop.


class BroadcastCallbackHandler(AsyncCallbackHandler):
    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id

    async def on_tool_start(
        self, serialized: dict, input_str: str, **kwargs: Any
    ) -> Any:
        tool_name = serialized.get("name", "tool")
        stream_event(
            self.conversation_id, "execute", f"Executing action: {tool_name}..."
        )

    async def on_tool_end(self, output: str, **kwargs: Any) -> Any:
        stream_event(self.conversation_id, "execute", "Tool execution completed.")


class ExecutionAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            api_key=settings.BEDROCK_MANTLE_API_KEY,
            base_url=settings.BEDROCK_MANTLE_BASE_URL,
            model=settings.BEDROCK_MODEL_ID,
            temperature=0,
            max_tokens=4096,
        )

    async def execute(
        self,
        user_message: str,
        tools: list[Any],
        user_id: str,
        conversation_id: str,
        memory_context: str = "",
    ) -> tuple[str, dict]:
        """Return the reply text *and* the raw graph result.

        The result carries `usage_metadata` on each AI message, which is the
        only source of real token counts. Returning just the string — as this
        did before — silently made credit metering impossible.
        """
        async with AsyncPostgresSaver.from_conn_string(settings.DATABASE_URL) as checkpointer:
            await checkpointer.setup()
            agent = create_agent(
                model=self.llm,
                tools=tools,
                checkpointer=checkpointer,
                system_prompt=EXECUTION_SYSTEM_PROMPT.format(memory_context=memory_context),
                # Applied to the replayed thread on every turn, so history
                # cannot grow past the context window. Full history stays in
                # the checkpoint; only what the model sees is bounded.
                middleware=[
                    # trigger/keep are ("kind", value) tuples, not mappings.
                    SummarizationMiddleware(
                        model=self.llm,
                        trigger=("tokens", MAX_HISTORY_TOKENS),
                        keep=("messages", KEEP_RECENT_MESSAGES),
                        token_counter=count_tokens_approximately,
                    ),
                ],
            )

            result = await agent.ainvoke(
                {"messages": [HumanMessage(content=user_message)]},
                config={
                    "configurable": {"thread_id": conversation_id},
                    "callbacks": [BroadcastCallbackHandler(conversation_id)],
                    "metadata": {
                        "user_id": user_id,
                        "conversation_id": conversation_id,
                    },
                },
            )

        final = result["messages"][-1].content
        if isinstance(final, list):
            final = "".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in final
            )

        return final, result


class AgentService:
    def __init__(self):
        self.sdk = Composio(
            api_key=settings.COMPOSIO_API_KEY,
            provider=LangchainProvider(),
        )
        self.execution_agent = ExecutionAgent()
        self.chat_memory = ChatMemory()
        self.user_memory = UserMemoryStore()
        self.personality_handler = PersonalityHandler(
            self.execution_agent.llm,
            self.chat_memory,
            recall_memory=self._recall,
        )
        redis = get_redis_client()
        self.credit_checker = CreditChecker(redis)
        self.credit_calculator = CreditCalculator(redis)

    async def _recall(self, user_id: str) -> str:
        """Durable facts about this user, rendered for the system prompt.

        Never fatal: a memory lookup failure should degrade the reply, not
        prevent one.
        """
        try:
            return build_memory_block(await self.user_memory.recall(user_id))
        except Exception as exc:
            logger.error("Memory recall failed: %s", exc)
            return ""

    async def _learn(self, user_message: str, user_id: str, conversation_id: str) -> None:
        """Persist anything durable the user just told us."""
        try:
            entries = await extract_memories(self.execution_agent.llm, user_message)
            if entries:
                await self.user_memory.remember(user_id, entries, conversation_id)
        except Exception as exc:
            logger.error("Memory extraction failed: %s", exc)

    def _charge(self, result: dict, user_id: str, conversation_id: str) -> None:
        """Convert real token usage into credits and deduct.

        Best-effort by design: a metering failure must not lose a reply the
        user has already been given. The enforcing check happens before the
        model call, not here.
        """
        try:
            input_tokens, output_tokens = extract_token_counts(result)
            if not input_tokens and not output_tokens:
                return
            credits_used = self.credit_calculator.calculate_credits(
                input_tokens, output_tokens, user_id, conversation_id
            )
            self.credit_calculator.deduct_credits(user_id, credits_used, conversation_id)
        except Exception as exc:
            logger.error("Credit accounting failed: %s", exc)

    async def _handle_personality(
        self,
        intent: str,
        user_message: str,
        user_id: str,
        conversation_id: str,
        chat_name: str | None,
    ) -> dict:
        handlers = {
            "greeting": self.personality_handler.handle_greeting,
            "identity": self.personality_handler.handle_identity,
            "user_identity": self.personality_handler.handle_user_identity,
            "capabilities": self.personality_handler.handle_capabilities,
        }
        return await handlers[intent](
            user_message,
            user_id,
            conversation_id,
            chat_name,
        )

    async def execute_task(
        self,
        user_message: str,
        user_id: str,
        conversation_id: str,
        chat_name: str | None = None,
    ) -> dict:
        start = time.time()
        try:
            # Refuse before spending anything. The resolver checks too, but a
            # task can sit on the queue long enough for a balance to run out.
            has_credits, remaining = self.credit_checker.check_credits(
                user_id, conversation_id
            )
            if not has_credits:
                logger.warning("Refusing task for %s: no credits remaining", user_id)
                return {
                    "response": OUT_OF_CREDITS_MESSAGE.format(
                        reset_date=next_reset_label()
                    ),
                    "awaiting_user": False,
                    "success": False,
                    "chatName": chat_name,
                    "out_of_credits": True,
                    "remaining_credits": remaining,
                }

            self.chat_memory.save_chat_name(user_id, conversation_id, chat_name)
            self.chat_memory.append_message(user_id, conversation_id, "user", user_message)
            try:
                chat_name = self.chat_memory.get_chat_name(user_id, conversation_id) or chat_name
            except Exception as exc:
                logger.error("Failed to retrieve chat name from STM: %s", exc)

            # What we already know about this user, from any past conversation.
            # LangGraph resumes this session's own messages separately.
            memory_context = await self._recall(user_id)

            personality_intent = detect_personality_intent(user_message)
            if personality_intent:
                result = await self._handle_personality(
                    personality_intent,
                    user_message,
                    user_id,
                    conversation_id,
                    chat_name,
                )
                # Greetings and identity questions still cost tokens.
                self._charge(result.pop("usage", {}), user_id, conversation_id)
                self.chat_memory.append_message(
                    user_id, conversation_id, "assistant", str(result.get("response", ""))
                )
                return result

            # A user with nothing connected cannot be helped by any tool, so
            # skip discovery entirely rather than paying ~3,600 tokens of tool
            # schema to find that out. Reading Redis costs nothing.
            connected = connected_slugs(user_id)
            if connected is None:
                # Cache unavailable. Carry on into normal tool discovery rather
                # than claiming the user has connected nothing.
                logger.warning("Connected-app cache unavailable; skipping resolution")
                connected = []
            elif not connected:
                logger.info("No connected apps for %s; skipping tool discovery", user_id)
                self.chat_memory.append_message(
                    user_id, conversation_id, "assistant", NO_APPS_CONNECTED_MESSAGE
                )
                stream_event(conversation_id, "completed", "No connected apps.")
                return {
                    "response": NO_APPS_CONNECTED_MESSAGE,
                    "awaiting_user": True,
                    "success": True,
                    "chatName": chat_name,
                    "needs_connection": True,
                }

            # Resolve the target app before entering the tool loop.
            # `connected` is [] only when the cache was unreachable here;
            # resolve() treats that as "no signal" and falls through. Both
            # early exits below cost zero tokens and replace a run that would
            # have burned ~11k discovering it could not succeed.
            match = resolve(
                user_message,
                connected,
                recent_app=get_recent_app(user_id, conversation_id),
                preferred_app=preferred_app(user_id, connected),
            )

            if match.resolution is Resolution.MATCHED and match.slug:
                # Carry this app forward, and record the habit that lets a
                # future conversation start without asking.
                set_recent_app(user_id, conversation_id, match.slug)
                if match.assumed:
                    logger.info("Assuming %s from usage history", match.slug)
                    memory_context += ASSUMED_APP_HINT.format(
                        app=display_name(match.slug)
                    )

            if match.resolution is Resolution.NOT_CONNECTED:
                response = APP_NOT_CONNECTED_MESSAGE.format(
                    app=display_name(match.slug),
                    connected=", ".join(display_name(s) for s in connected),
                )
                logger.info("Requested app %s is not connected", match.slug)
                self.chat_memory.append_message(
                    user_id, conversation_id, "assistant", response
                )
                stream_event(conversation_id, "completed", "App not connected.")
                return {
                    "response": response,
                    "awaiting_user": True,
                    "success": True,
                    "chatName": chat_name,
                    "needs_connection": True,
                    "requested_app": match.slug,
                }

            if match.resolution is Resolution.AMBIGUOUS:
                response = WHICH_APP_MESSAGE.format(
                    apps=", ".join(display_name(s) for s in match.candidates)
                )
                logger.info("Ambiguous request across %s apps", len(match.candidates))
                self.chat_memory.append_message(
                    user_id, conversation_id, "assistant", response
                )
                stream_event(conversation_id, "completed", "Needs clarification.")
                return {
                    "response": response,
                    "awaiting_user": True,
                    "success": True,
                    "chatName": chat_name,
                    "needs_clarification": True,
                }

            # Telling the model what is connected costs a few dozen tokens and
            # saves it a discovery round trip guessing at what exists.
            memory_context += CONNECTED_APPS_HINT.format(slugs=", ".join(connected))

            stream_event(
                conversation_id,
                "init",
                "Preparing connected-app discovery...",
            )

            session = self.sdk.sessions.create(
                user_id=user_id,
                manage_connections={
                    "enable": True,
                    "callback_url": settings.CALLBACK_URL,
                },
                sandbox={"enable": False},
            )
            tools = list(session.tools())
            if not tools:
                raise RuntimeError("Composio Session returned no discovery tools")

            logger.info(
                "Loaded %s Composio Session meta-tools for session %s",
                len(tools),
                session.session_id,
            )
            stream_event(
                conversation_id,
                "execute",
                "Discovering the right connected-app tools...",
            )

            final, graph_result = await self.execution_agent.execute(
                user_message,
                tools,
                user_id,
                conversation_id,
                memory_context=memory_context,
            )
            self._charge(graph_result, user_id, conversation_id)
            await self._learn(user_message, user_id, conversation_id)

            stream_event(conversation_id, "completed", "Task completed.")
            logger.info("Completed in %.2fs", time.time() - start)
            result = {
                "response": final,
                "awaiting_user": False,
                "success": True,
                "chatName": chat_name,
            }
            self.chat_memory.append_message(user_id, conversation_id, "assistant", final)
            return result
        except Exception as exc:
            logger.exception("Task failed: %s", exc)
            return {
                "response": GENERIC_ERROR_MESSAGE.format(error_msg=str(exc)),
                "awaiting_user": False,
                "success": False,
                "chatName": chat_name,
            }


_agent_service = None


def get_agent_service() -> AgentService:
    global _agent_service
    if _agent_service is None:
        _agent_service = AgentService()
    return _agent_service
