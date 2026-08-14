from langchain_core.messages import SystemMessage, HumanMessage
from .prompts import (
    RELAYWISE_IDENTITY,
    RELAYWISE_INTRO,
    RELAYWISE_CAPABILITIES_GENERAL,
    RELAYWISE_FAQ,
    USER_IDENTITY_NO_MEMORY,
)
from utils import get_logger

logger = get_logger(__name__)


class PersonalityHandler:
    """Handles conversational/personality responses for non-tool intents"""
    
    def __init__(self, llm, chat_memory, recall_memory=None):
        self.llm = llm
        self.chat_memory = chat_memory
        # Callable(user_id) -> rendered memory block. Injected rather than
        # imported so this class stays independent of the storage layer.
        self.recall_memory = recall_memory
    
    async def conversational_response(
        self, user_message: str, reference: str = ""
    ) -> tuple[str, dict]:
        """Return the reply and a graph-shaped result carrying token usage.

        Shaped like the LangGraph result so the same `extract_token_counts`
        works for both paths. Without this, greetings called the model for free.
        """
        system_content = RELAYWISE_IDENTITY
        if reference:
            system_content += (
                "\n\nREFERENCE MATERIAL — use this to inform your answer. "
                "Respond naturally and conversationally; do not copy it verbatim.\n"
                + reference
            )
        try:
            # ainvoke natively; the old run_in_executor(llm.invoke) burned a
            # thread to wait on a network call the client already does async.
            result = await self.llm.ainvoke(
                [
                    SystemMessage(content=system_content),
                    HumanMessage(content=user_message),
                ]
            )
            content = result.content
            if isinstance(content, list):
                content = ''.join([p.get('text', '') if isinstance(p, dict) else str(p) for p in content])
            return content, {"messages": [result]}
        except Exception as e:
            logger.error(f"conversational_response failed: {e}")
            return "", {"messages": []}
    
    async def handle_greeting(self, user_message: str, user_id: str, conversation_id: str, chat_name: str) -> dict:
        """Handle greeting intent"""
        # LLM responds naturally — greets the user, picks up their name from context
        # Include all reference material so it can answer questions mixed with greetings
        faq_str = "\n\n".join(f"{k.upper()}:\n{v}" for k, v in RELAYWISE_FAQ.items())
        reference = f"{RELAYWISE_INTRO}\n\n{RELAYWISE_CAPABILITIES_GENERAL}\n\nFAQ:\n{faq_str}"
        response, usage = await self.conversational_response(user_message, reference=reference)
        if not response:
            response = "Hey! Great to have you here. What can I help you with?"
        return {
            "response": response,
            "awaiting_user": False,
            "success": True,
            "chatName": chat_name,
            "personality_response": True,
            "usage": usage,
        }
    
    async def handle_identity(self, user_message: str, user_id: str, conversation_id: str, chat_name: str) -> dict:
        """Handle identity intent (who are you?)"""
        # LLM answers "who are you?" grounded in RELAYWISE_INTRO + FAQ
        faq_str = "\n\n".join(f"{k.upper()}:\n{v}" for k, v in RELAYWISE_FAQ.items())
        reference = f"{RELAYWISE_INTRO}\n\nFAQ:\n{faq_str}"
        response, usage = await self.conversational_response(user_message, reference=reference)
        if not response:
            response = RELAYWISE_INTRO
        return {
            "response": response,
            "awaiting_user": False,
            "success": True,
            "chatName": chat_name,
            "personality_response": True,
            "usage": usage,
        }
    
    async def handle_capabilities(self, user_message: str, user_id: str, conversation_id: str, chat_name: str) -> dict:
        """Handle capabilities intent (what can you do?)"""
        # LLM answers "what can you do?" grounded in RELAYWISE_CAPABILITIES_GENERAL + FAQ
        faq_str = "\n\n".join(f"{k.upper()}:\n{v}" for k, v in RELAYWISE_FAQ.items())
        reference = f"{RELAYWISE_CAPABILITIES_GENERAL}\n\nFAQ:\n{faq_str}"
        response, usage = await self.conversational_response(
            user_message, reference=reference
        )
        if not response:
            response = RELAYWISE_CAPABILITIES_GENERAL
        return {
            "response": response,
            "awaiting_user": False,
            "success": True,
            "chatName": chat_name,
            "personality_response": True,
            "usage": usage,
        }
    
    async def handle_user_identity(self, user_message: str, user_id: str, conversation_id: str, chat_name: str) -> dict:
        """Handle user_identity intent (who am I?).

        Answers from cross-session memory when there is any, so "what do you
        know about me" reflects what the user has actually said in past chats
        rather than always claiming ignorance.
        """
        memory_block = await self.recall_memory(user_id) if self.recall_memory else ""
        if memory_block:
            response, usage = await self.conversational_response(
                user_message,
                reference=(
                    "What you remember about this user:\n"
                    + memory_block
                    + "\nAnswer from this. Do not invent details it does not contain."
                ),
            )
            if not response:
                response = USER_IDENTITY_NO_MEMORY
        else:
            response = USER_IDENTITY_NO_MEMORY
            usage = {"messages": []}

        return {
            "response": response,
            "awaiting_user": False,
            "success": True,
            "chatName": chat_name,
            "personality_response": True,
            "usage": usage,
        }
