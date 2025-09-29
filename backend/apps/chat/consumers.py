# apps/chat/consumers.py

"""
WebSocket consumers with dual RAG architecture support
"""

import json
import logging
from urllib.parse import urlparse, parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from django.conf import settings

from apps.chat.models import Conversation, Message
from apps.chat.views import get_system_prompt

# Old architecture
from apps.core.openrouter import openrouter_client

# New architecture
from apps.infrastructure.container import create_chat_service

logger = logging.getLogger(__name__)

HISTORY_WINDOW = 12
USE_NEW_ARCHITECTURE = getattr(settings, 'USE_NEW_RAG_ARCHITECTURE', False)


class ChatConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.conversation = None
        self.language = None
        self.conversation_id = None
        self.session_id = None
        self.room_group_name = None
        self.room_name = None

    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'

        # Parse query params
        query = parse_qs(urlparse(self.scope['query_string'].decode()).query)
        self.session_id = (query.get('session_id', [None])[0]) or self.room_name
        self.conversation_id = query.get('conversation_id', [None])[0]
        self.language = query.get('lang', ['en'])[0]

        # Validate language
        if self.language not in ['en', 'de', 'fr', 'es']:
            logger.info(f"Invalid WebSocket language '{self.language}', defaulting to English")
            self.language = 'en'

        logger.info(f"WebSocket connected with language: {self.language}, architecture: {'NEW' if USE_NEW_ARCHITECTURE else 'OLD'}")

        # Get or create Conversation
        self.conversation = await self._get_or_create_conversation()

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        await self.send(text_data=json.dumps({
            'type': 'connection',
            'message': 'Connected to chat',
            'conversation_id': str(self.conversation.id),
            'session_id': self.session_id,
            'architecture': 'new_hexagonal' if USE_NEW_ARCHITECTURE else 'old_rag'
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            payload = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({'type': 'error', 'message': 'Invalid JSON format'}))
            return

        msg_type = payload.get('type', 'chat_message')
        if msg_type == 'chat_message':
            await self.handle_chat_message(payload)
        elif msg_type == 'typing':
            await self.handle_typing(payload)

    async def handle_chat_message(self, data):
        message_text = (data.get('message') or '').strip()
        if not message_text:
            return

        # Typing indicator on
        await self.channel_layer.group_send(
            self.room_group_name,
            {'type': 'typing_indicator', 'typing': True}
        )

        # Route to appropriate architecture
        if USE_NEW_ARCHITECTURE:
            await self._handle_message_new_architecture(message_text)
        else:
            await self._handle_message_old_architecture(message_text)

        # Typing indicator off
        await self.channel_layer.group_send(
            self.room_group_name,
            {'type': 'typing_indicator', 'typing': False}
        )

    async def _handle_message_new_architecture(self, message_text):
        """Handle message using new hexagonal architecture"""
        try:
            # Save user message
            user_msg = await self._save_message(role='user', content=message_text)

            # Create service and generate answer
            try:
                service = await sync_to_async(create_chat_service)()
                answer = await sync_to_async(service.answer_question)(
                    conversation_id=self.conversation.id,
                    query=message_text,
                    language=self.language
                )

                # Get the AI message that was saved
                ai_msg = await self._get_latest_assistant_message()

                if ai_msg:
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'chat_message',
                            'message': {
                                'id': str(ai_msg.id),
                                'role': 'assistant',
                                'content': ai_msg.content,
                                'created_at': ai_msg.created_at.isoformat(),
                                'conversation_id': str(self.conversation.id),
                                'architecture': 'new_hexagonal',
                                'citations_count': len(answer.citations) if hasattr(answer, 'citations') else 0
                            },
                            'sender': 'assistant'
                        }
                    )
                else:
                    raise Exception("AI message not found after generation")

            except Exception as e:
                logger.error(f"Error in new architecture: {e}")
                # Fallback response
                fallback_text = self._get_fallback_text(self.language)
                ai_msg = await self._save_message(
                    role='assistant',
                    content=fallback_text,
                    extra_meta={'error': True, 'architecture': 'new_hexagonal'}
                )

                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': {
                            'id': str(ai_msg.id),
                            'role': 'assistant',
                            'content': ai_msg.content,
                            'created_at': ai_msg.created_at.isoformat(),
                            'conversation_id': str(self.conversation.id),
                            'architecture': 'new_hexagonal',
                            'error': True
                        },
                        'sender': 'assistant'
                    }
                )

        except Exception as e:
            logger.error(f"Fatal error in new architecture handler: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'An error occurred processing your message'
            }))

    async def _handle_message_old_architecture(self, message_text):
        """Handle message using old RAG architecture"""
        try:
            # Save user message
            user_msg = await self._save_message(role='user', content=message_text)

            # Build LLM messages with history
            messages = await self._build_llm_messages()

            # Call LLM (old architecture)
            try:
                ai_text = await self._call_llm_old(messages)
            except Exception as e:
                logger.error(f"LLM error (old architecture): {e}")
                ai_text = "Sorry, I ran into a problem answering that."

            # Save assistant message
            ai_msg = await self._save_message(
                role='assistant',
                content=ai_text,
                extra_meta={
                    'model': openrouter_client.llm_model,
                    'architecture': 'old_rag'
                }
            )

            # Broadcast
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': {
                        'id': str(ai_msg.id),
                        'role': 'assistant',
                        'content': ai_msg.content,
                        'created_at': ai_msg.created_at.isoformat(),
                        'conversation_id': str(self.conversation.id),
                        'architecture': 'old_rag'
                    },
                    'sender': 'assistant'
                }
            )

        except Exception as e:
            logger.error(f"Fatal error in old architecture handler: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'An error occurred processing your message'
            }))

    async def handle_typing(self, data):
        await self.channel_layer.group_send(
            self.room_group_name,
            {'type': 'typing_indicator', 'typing': bool(data.get('typing'))}
        )

    async def chat_message(self, event):
        """Handle chat message from group"""
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message'],
            'sender': event.get('sender', 'user'),
        }))

    async def typing_indicator(self, event):
        """Handle typing indicator from group"""
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'typing': event['typing']
        }))

    # Helper methods
    async def _get_or_create_conversation(self):
        """Get or create conversation"""
        if self.conversation_id:
            conv = await sync_to_async(Conversation.objects.get)(id=self.conversation_id)
            return conv

        def _get_or_create():
            conv = Conversation.objects.filter(
                session_id=self.session_id
            ).order_by('-updated_at').first()
            if conv:
                return conv
            return Conversation.objects.create(
                session_id=self.session_id,
                language=self.language,
                title="New chat"
            )

        return await sync_to_async(_get_or_create)()

    async def _save_message(self, role: str, content: str, extra_meta: dict | None = None):
        """Save message to database"""
        def _save():
            msg = Message.objects.create(
                conversation=self.conversation,
                role=role,
                content=content,
                metadata=extra_meta or {}
            )
            self.conversation.save(update_fields=['updated_at'])
            return msg

        return await sync_to_async(_save)()

    async def _get_latest_assistant_message(self):
        """Get the most recent assistant message"""
        def _get():
            return Message.objects.filter(
                conversation=self.conversation,
                role='assistant'
            ).order_by('-created_at').first()

        return await sync_to_async(_get)()

    async def _build_llm_messages(self):
        """Build messages for LLM (old architecture)"""
        def _load():
            recent = list(
                self.conversation.messages.order_by('-created_at')[:HISTORY_WINDOW]
            )
            recent.reverse()
            return recent

        recent_messages = await sync_to_async(_load)()

        msgs = [{"role": "system", "content": get_system_prompt(self.language)}]
        for m in recent_messages:
            msgs.append({"role": m.role, "content": m.content})
        return msgs

    async def _call_llm_old(self, messages):
        """Call LLM using old architecture"""
        return await sync_to_async(openrouter_client.generate_answer)(
            messages,
            model=None,
            stream=False,
            max_tokens=800
        )

    def _get_fallback_text(self, language):
        """Get fallback text in appropriate language"""
        fallbacks = {
            'en': "I apologize, but I encountered an error. Please try again.",
            'de': "Entschuldigung, es ist ein Fehler aufgetreten.",
            'fr': "Je m'excuse, une erreur s'est produite.",
            'es': "Me disculpo, ocurrió un error."
        }
        return fallbacks.get(language, fallbacks['en'])
