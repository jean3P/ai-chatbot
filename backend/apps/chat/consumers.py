# backend/apps/chat/consumers.py
import json
import asyncio
import logging
from urllib.parse import urlparse, parse_qs

from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async

from apps.chat.models import Conversation, Message
from apps.chat.views import get_system_prompt
from apps.core.openrouter import openrouter_client

logger = logging.getLogger(__name__)

HISTORY_WINDOW = 12  # how many recent messages to include as context


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

        # Parse query params (e.g. ws://.../ws/chat/ROOM/?session_id=abc&conversation_id=uuid&lang=de)
        query = parse_qs(urlparse(self.scope['query_string'].decode()).query)
        self.session_id = (query.get('session_id', [None])[0]) or self.room_name  # fallback to room as session
        self.conversation_id = query.get('conversation_id', [None])[0]
        self.language = query.get('lang', ['en'])[0]

        # Get or create Conversation
        self.conversation = await self._get_or_create_conversation()

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        await self.send(text_data=json.dumps({
            'type': 'connection',
            'message': 'Connected to chat',
            'conversation_id': str(self.conversation.id),
            'session_id': self.session_id,
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

        # typing on
        await self.channel_layer.group_send(self.room_group_name, {'type': 'typing_indicator', 'typing': True})

        # 1) persist user message
        user_msg = await self._save_message(role='user', content=message_text)

        # 2) build LLM messages with history
        messages = await self._build_llm_messages()

        # 3) call LLM
        try:
            ai_text = await self._call_llm(messages)
        except Exception as e:
            logger.error(f"LLM error: {e}")
            ai_text = "Sorry, I ran into a problem answering that."

        # 4) persist assistant message
        ai_msg = await self._save_message(role='assistant', content=ai_text,
                                          extra_meta={'model': openrouter_client.llm_model})

        # typing off
        await self.channel_layer.group_send(self.room_group_name, {'type': 'typing_indicator', 'typing': False})

        # 5) broadcast the assistant message (with ids so UI can render history consistently)
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'chat_message',
            'message': {
                'id': str(ai_msg.id),
                'role': 'assistant',
                'content': ai_msg.content,
                'created_at': ai_msg.created_at.isoformat(),
                'conversation_id': str(self.conversation.id),
            },
            'sender': 'assistant'
        })

    async def handle_typing(self, data):
        await self.channel_layer.group_send(self.room_group_name,
                                            {'type': 'typing_indicator', 'typing': bool(data.get('typing'))})

    async def chat_message(self, event):
        # pass through
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message'],
            'sender': event.get('sender', 'user'),
        }))

    async def typing_indicator(self, event):
        await self.send(text_data=json.dumps({'type': 'typing', 'typing': event['typing']}))

    # ---------- helpers (thread-safe DB + LLM) ----------

    async def _get_or_create_conversation(self):
        if self.conversation_id:
            conv = await sync_to_async(Conversation.objects.get)(id=self.conversation_id)
            return conv

        # else find by session_id (reuse most recent) or create
        def _get_or_create():
            conv = Conversation.objects.filter(session_id=self.session_id).order_by('-updated_at').first()
            if conv:
                return conv
            title = "New chat"
            return Conversation.objects.create(session_id=self.session_id, language=self.language, title=title)

        return await sync_to_async(_get_or_create)()

    async def _save_message(self, role: str, content: str, extra_meta: dict | None = None):
        def _save():
            msg = Message.objects.create(
                conversation=self.conversation,
                role=role,
                content=content,
                metadata=extra_meta or {}
            )
            # bump conversation timestamp
            self.conversation.save(update_fields=['updated_at'])
            return msg

        return await sync_to_async(_save)()

    async def _build_llm_messages(self):
        def _load():
            # newest first, then reversed for chronological order
            recent = list(self.conversation.messages.order_by('-created_at')[:HISTORY_WINDOW])
            recent.reverse()
            return recent

        recent_messages = await sync_to_async(_load)()

        msgs = [{"role": "system", "content": get_system_prompt(self.conversation.language or 'en')}]
        for m in recent_messages:
            msgs.append({"role": m.role, "content": m.content})
        return msgs

    async def _call_llm(self, messages):
        # openrouter client is sync; run in thread
        return await sync_to_async(openrouter_client.generate_answer)(messages, model=None, stream=False,
                                                                      max_tokens=800)
