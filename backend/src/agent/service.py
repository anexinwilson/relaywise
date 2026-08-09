import time
from typing import Any

from composio import Composio
from composio_langchain import LangchainProvider
from langchain.agents import create_agent
from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from agent.event_streaming import stream_event
from agent.intent import detect_personality_intent
from agent.personality import PersonalityHandler
from config import settings
from memory import ChatMemory
from utils import get_logger

from .prompts import EXECUTION_SYSTEM_PROMPT, GENERIC_ERROR_MESSAGE

logger = get_logger(__name__)


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
    ) -> str:
        async with AsyncPostgresSaver.from_conn_string(settings.DATABASE_URL) as checkpointer:
            await checkpointer.setup()
            agent = create_agent(
                model=self.llm,
                tools=tools,
                checkpointer=checkpointer,
                system_prompt=EXECUTION_SYSTEM_PROMPT.format(memory_context=memory_context),
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

        return final


class AgentService:
    def __init__(self):
        self.sdk = Composio(
            api_key=settings.COMPOSIO_API_KEY,
            provider=LangchainProvider(),
        )
        self.execution_agent = ExecutionAgent()
        self.chat_memory = ChatMemory()
        self.personality_handler = PersonalityHandler(
            self.execution_agent.llm,
            self.chat_memory,
        )

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
            self.chat_memory.save_chat_name(user_id, conversation_id, chat_name)
            self.chat_memory.append_message(user_id, conversation_id, "user", user_message)
            try:
                chat_name = self.chat_memory.get_chat_name(user_id, conversation_id) or chat_name
            except Exception as exc:
                logger.error("Failed to retrieve chat name from STM: %s", exc)

            personality_intent = detect_personality_intent(user_message)
            if personality_intent:
                result = await self._handle_personality(
                    personality_intent,
                    user_message,
                    user_id,
                    conversation_id,
                    chat_name,
                )
                self.chat_memory.append_message(
                    user_id, conversation_id, "assistant", str(result.get("response", ""))
                )
                return result

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

            final = await self.execution_agent.execute(
                user_message,
                tools,
                user_id,
                conversation_id,
            )

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
