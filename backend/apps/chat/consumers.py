# backend/apps/chat/consumers.py
"""
WebSocket consumers for real-time chat
"""
import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
import logging

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time chat"""

    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection',
            'message': 'Connected to chat'
        }))

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type', 'chat_message')

            if message_type == 'chat_message':
                await self.handle_chat_message(text_data_json)
            elif message_type == 'typing':
                await self.handle_typing(text_data_json)

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
        except Exception as e:
            logger.error(f"Error in WebSocket receive: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Server error'
            }))

    async def handle_chat_message(self, data):
        """Handle incoming chat message"""
        message = data.get('message', '').strip()

        if not message:
            return

        # Send typing indicator to other clients
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'typing': True
            }
        )

        # Simulate processing delay
        await asyncio.sleep(1)

        # Generate response (this is a simplified version)
        response = await self.generate_response(message)

        # Stop typing indicator
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'typing': False
            }
        )

        # Send response to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': response,
                'sender': 'assistant'
            }
        )

    async def handle_typing(self, data):
        """Handle typing indicator"""
        is_typing = data.get('typing', False)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'typing': is_typing
            }
        )

    async def generate_response(self, message):
        """Generate AI response (simplified)"""
        # This is a placeholder - in production, integrate with RAG pipeline
        return f"I received your message: '{message}'. This is a WebSocket demo response!"

    # Receive message from room group
    async def chat_message(self, event):
        message = event['message']
        sender = event.get('sender', 'user')

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': message,
            'sender': sender,
            'timestamp': str(asyncio.get_event_loop().time())
        }))

    async def typing_indicator(self, event):
        typing = event['typing']

        # Send typing indicator to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'typing': typing
        }))
