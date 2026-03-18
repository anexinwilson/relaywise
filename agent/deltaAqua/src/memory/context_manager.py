import asyncio
import json
import re
from typing import List
from config import settings
from utils import get_logger
from agent.client import get_executor

logger = get_logger(__name__)

_executor = get_executor()


class ContextManager:
    """Manages memory context retrieval from AgentCore memory strategies"""
    
    def __init__(self, memory_client, toolkits_catalog: List[dict]):
        self.memory_client = memory_client
        self.toolkits_catalog = toolkits_catalog
    
    async def build_memory_context(self, user_id: str, conversation_id: str) -> str:
        """Fetch all 4 memory strategy namespaces and build a [MEMORY] block for the system prompt."""
        EPISODIC_ID  = settings.EPISODIC_STRATEGY_ID
        SUMMARY_ID   = settings.SUMMARY_STRATEGY_ID
        SEMANTIC_ID  = settings.SEMANTIC_STRATEGY_ID
        PREFERENCE_ID = settings.PREFERENCE_STRATEGY_ID

        loop = asyncio.get_event_loop()

        async def _retrieve(namespace: str, query: str, strategy_id: str) -> List[str]:
            try:
                resp = await loop.run_in_executor(
                    _executor,
                    lambda: self.memory_client.retrieve_memory_records(
                        memoryId=settings.AGENTCORE_MEMORY_ID,
                        namespace=namespace,
                        searchCriteria={
                            'searchQuery': query,
                            'memoryStrategyId': strategy_id,
                        },
                        maxResults=5,
                    )
                )
                texts = []
                for rec in resp.get('memoryRecordSummaries', []):
                    text = rec.get('content', {}).get('text', '').strip()
                    if text:
                        texts.append(text)
                return texts
            except Exception as e:
                logger.debug(f"Memory retrieve skipped ({namespace}): {e}")
                return []

        # Fetch all 4 strategies in parallel
        semantic_ns   = f"/strategies/{SEMANTIC_ID}/actors/{user_id}/"
        preference_ns = f"/strategies/{PREFERENCE_ID}/actors/{user_id}/"
        episodic_ns   = f"/strategies/{EPISODIC_ID}/actors/{user_id}/sessions/{conversation_id}/"
        summary_ns    = f"/strategies/{SUMMARY_ID}/actors/{user_id}/sessions/{conversation_id}/"

        semantic_facts, preferences, episodic, summary = await asyncio.gather(
            _retrieve(semantic_ns,   "user facts and personal information", SEMANTIC_ID),
            _retrieve(preference_ns, "user preferences and working style",  PREFERENCE_ID),
            _retrieve(episodic_ns,   "conversation events and actions",      EPISODIC_ID),
            _retrieve(summary_ns,    "conversation summary",                 SUMMARY_ID),
        )

        parts = []
        if semantic_facts:
            parts.append("Facts about the user: " + " ".join(semantic_facts))
        if preferences:
            parts.append("User preferences: " + " ".join(preferences))
        if summary:
            parts.append("This conversation so far: " + " ".join(summary))
        elif episodic:
            parts.append("Recent conversation events: " + " ".join(episodic))

        if not parts:
            return ""

        memory_block = "[MEMORY]\n" + "\n".join(parts) + "\n[/MEMORY]\n"
        logger.info(f"Memory context built ({len(parts)} sections, {sum(len(p) for p in parts)} chars)")
        return memory_block

    async def get_conversation_summary(self, user_id: str, conversation_id: str) -> str:
        """Get episodic conversation summary"""
        try:
            episodic_strategy_id = settings.EPISODIC_STRATEGY_ID
            episodic_namespace = f"/strategies/{episodic_strategy_id}/actors/{user_id}/sessions/{conversation_id}/"
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                _executor,
                lambda: self.memory_client.retrieve_memory_records(
                    memoryId=settings.AGENTCORE_MEMORY_ID,
                    namespace=episodic_namespace,
                    searchCriteria={
                        'searchQuery': 'recent conversation context',
                        'memoryStrategyId': episodic_strategy_id
                    },
                    maxResults=5
                )
            )
            
            memory_records = response.get('memoryRecordSummaries', [])
            if memory_records:
                context_parts = []
                for record in memory_records:
                    content = record.get('content', {})
                    text = content.get('text', '')
                    if text:
                        context_parts.append(text)
                
                if context_parts:
                    context_text = " ".join(context_parts)
                    logger.info(f"Retrieved episodic context: {context_text[:200]}...")
                    return context_text
            
            return ""
        except Exception as e:
            logger.error(f"Error getting episodic context: {e}")
            return ""
    
    async def get_app_from_context(self, user_id: str, conversation_id: str) -> List[str]:
        """Extract app mentions from conversation context"""
        try:
            episodic_context = await self.get_conversation_summary(user_id, conversation_id)
            
            app_mentions = []
            
            if episodic_context:
                # Try to parse as JSON first (episodic strategy returns JSON)
                try:
                    # Try to parse as JSON
                    parsed = json.loads(episodic_context)
                    # Extract text from common JSON structures
                    if isinstance(parsed, dict):
                        # Try common JSON structures from episodic memory
                        text_parts = []
                        for key, value in parsed.items():
                            if isinstance(value, str):
                                text_parts.append(value)
                        context_text = ' '.join(text_parts).lower()
                    else:
                        context_text = episodic_context.lower()
                except (json.JSONDecodeError, AttributeError):
                    # Not JSON, use as-is
                    context_text = episodic_context.lower()
                
                # Clean the text - remove JSON artifacts
                context_text = re.sub(r'[{}":,]', ' ', context_text)
                
                for app in self.toolkits_catalog:
                    app_name = app.get('name', '').lower()
                    app_slug = app.get('slug', '').lower()
                    
                    # Only match whole words or common substrings
                    app_name_words = re.split(r'\W+', app_name)
                    app_slug_words = re.split(r'\W+', app_slug)
                    
                    # Check for app name or slug as whole words
                    app_name_pattern = r'\b' + re.escape(app_name) + r'\b'
                    app_slug_pattern = r'\b' + re.escape(app_slug) + r'\b'
                    
                    if (re.search(app_name_pattern, context_text) or 
                        re.search(app_slug_pattern, context_text)):
                        if app_slug not in app_mentions:
                            app_mentions.append(app_slug)
                
                if app_mentions:
                    logger.info(f"Found apps in episodic context: {app_mentions}")
                    return app_mentions
            
            try:
                events_response = self.memory_client.list_events(
                    memoryId=settings.AGENTCORE_MEMORY_ID,
                    actorId=user_id,
                    sessionId=conversation_id,
                    maxResults=3,
                    includePayloads=True
                )
                
                events = events_response.get('events', [])
                if events:
                    for event in events:
                        payload = event.get('payload', [])
                        if payload and isinstance(payload, list):
                            for item in payload:
                                if isinstance(item, dict) and 'conversational' in item:
                                    content = item['conversational'].get('content', {})
                                    if isinstance(content, dict):
                                        text = content.get('text', '').lower()
                                        
                                        for app in self.toolkits_catalog:
                                            app_name = app.get('name', '').lower()
                                            app_slug = app.get('slug', '').lower()
                                            
                                            if app_name in text or app_slug in text:
                                                if app_slug not in app_mentions:
                                                    app_mentions.append(app_slug)
                    
                    if app_mentions:
                        logger.info(f"Found apps in recent events: {app_mentions}")
                        return app_mentions
            except Exception as e:
                logger.warning(f"Could not fetch recent events: {e}")
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting app from context: {e}")
            return []
    
    def expand_toolkit_names(self, toolkits: List[str]) -> List[str]:
        """Expand toolkit names to include related app slugs"""
        expanded = set(toolkits)
        for tk in toolkits:
            tk_lower = tk.lower()
            for app in self.toolkits_catalog:
                app_slug = app.get('slug', '').lower()
                if tk_lower in app_slug or app_slug in tk_lower:
                    expanded.add(app['slug'])
        return list(expanded)
