import asyncio
from langchain_core.messages import SystemMessage, HumanMessage
from .prompts import (
    COGNIVE_IDENTITY,
    COGNIVE_INTRO,
    COGNIVE_CAPABILITIES_GENERAL,
    COGNIVE_FAQ,
    USER_IDENTITY_NO_MEMORY,
)
from utils import get_logger
from agent.client import get_executor

logger = get_logger(__name__)

_executor = get_executor()


class PersonalityHandler:
    """Handles conversational/personality responses for non-tool intents"""
    
    def __init__(self, llm, chat_memory):
        self.llm = llm
        self.chat_memory = chat_memory
    
    async def conversational_response(self, user_message: str, reference: str = "") -> str:
        system_content = COGNIVE_IDENTITY
        if reference:
            system_content += (
                "\n\nREFERENCE MATERIAL — use this to inform your answer. "
                "Respond naturally and conversationally; do not copy it verbatim.\n"
                + reference
            )
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                _executor,
                lambda: self.llm.invoke([
                    SystemMessage(content=system_content),
                    HumanMessage(content=user_message)
                ])
            )
            content = result.content
            if isinstance(content, list):
                content = ''.join([p.get('text', '') if isinstance(p, dict) else str(p) for p in content])
            return content
        except Exception as e:
            logger.error(f"conversational_response failed: {e}")
            return ""
    
    async def handle_greeting(self, user_message: str, user_id: str, conversation_id: str, chat_name: str) -> dict:
        """Handle greeting intent"""
        # LLM responds naturally — greets the user, picks up their name from context
        # Include all reference material so it can answer questions mixed with greetings
        faq_str = "\n\n".join(f"{k.upper()}:\n{v}" for k, v in COGNIVE_FAQ.items())
        reference = f"{COGNIVE_INTRO}\n\n{COGNIVE_CAPABILITIES_GENERAL}\n\nFAQ:\n{faq_str}"
        response = await self.conversational_response(user_message, reference=reference)
        if not response:
            response = "Hey! Great to have you here. What can I help you with?"
        self.chat_memory.store_message(user_id, conversation_id, user_message, 'USER')
        self.chat_memory.store_message(user_id, conversation_id, response, 'ASSISTANT')
        return {
            "response": response,
            "awaiting_user": False,
            "success": True,
            "chatName": chat_name,
            "personality_response": True
        }
    
    async def handle_identity(self, user_message: str, user_id: str, conversation_id: str, chat_name: str) -> dict:
        """Handle identity intent (who are you?)"""
        # LLM answers "who are you?" grounded in COGNIVE_INTRO + FAQ
        faq_str = "\n\n".join(f"{k.upper()}:\n{v}" for k, v in COGNIVE_FAQ.items())
        reference = f"{COGNIVE_INTRO}\n\nFAQ:\n{faq_str}"
        response = await self.conversational_response(user_message, reference=reference)
        if not response:
            response = COGNIVE_INTRO
        self.chat_memory.store_message(user_id, conversation_id, user_message, 'USER')
        self.chat_memory.store_message(user_id, conversation_id, response, 'ASSISTANT')
        return {
            "response": response,
            "awaiting_user": False,
            "success": True,
            "chatName": chat_name,
            "personality_response": True
        }
    
    async def handle_capabilities(self, user_message: str, user_id: str, conversation_id: str, chat_name: str) -> dict:
        """Handle capabilities intent (what can you do?)"""
        # LLM answers "what can you do?" grounded in COGNIVE_CAPABILITIES_GENERAL + FAQ
        faq_str = "\n\n".join(f"{k.upper()}:\n{v}" for k, v in COGNIVE_FAQ.items())
        reference = f"{COGNIVE_CAPABILITIES_GENERAL}\n\nFAQ:\n{faq_str}"
        response = await self.conversational_response(
            user_message, reference=reference
        )
        if not response:
            response = COGNIVE_CAPABILITIES_GENERAL
        self.chat_memory.store_message(user_id, conversation_id, user_message, 'USER')
        self.chat_memory.store_message(user_id, conversation_id, response, 'ASSISTANT')
        return {
            "response": response,
            "awaiting_user": False,
            "success": True,
            "chatName": chat_name,
            "personality_response": True
        }
    
    async def handle_user_identity(self, user_message: str, user_id: str, conversation_id: str, chat_name: str) -> dict:
        """Handle user_identity intent (who am I?)"""
        response = USER_IDENTITY_NO_MEMORY

        self.chat_memory.store_message(user_id, conversation_id, user_message, 'USER')
        self.chat_memory.store_message(user_id, conversation_id, response, 'ASSISTANT')
        return {
            "response": response,
            "awaiting_user": False,
            "success": True,
            "chatName": chat_name,
            "personality_response": True
        }
