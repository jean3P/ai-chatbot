# apps/adapters/repositories/inmemory_repos.py
"""
In-Memory Repository Adapters for testing
"""
from typing import Optional, List, Dict
from uuid import UUID
from copy import deepcopy

from apps.domain.models import Message, Conversation


class InMemoryMessageRepository:
    """
    In-memory message repository for testing
    """

    def __init__(self):
        self._messages: Dict[UUID, Message] = {}

    def save(self, message: Message) -> Message:
        """Save message to memory"""
        self._messages[message.id] = deepcopy(message)
        return message

    def get(self, message_id: UUID) -> Optional[Message]:
        """Get message by ID"""
        return deepcopy(self._messages.get(message_id))

    def list_by_conversation(
            self,
            conversation_id: UUID,
            limit: Optional[int] = None
    ) -> List[Message]:
        """List messages in conversation"""
        messages = [
            msg for msg in self._messages.values()
            if msg.conversation_id == conversation_id
        ]
        messages.sort(key=lambda m: m.created_at)

        if limit:
            messages = messages[:limit]

        return [deepcopy(msg) for msg in messages]

    def delete(self, message_id: UUID) -> bool:
        """Delete message"""
        if message_id in self._messages:
            del self._messages[message_id]
            return True
        return False

    def clear(self):
        """Clear all messages"""
        self._messages.clear()


class InMemoryConversationRepository:
    """
    In-memory conversation repository for testing
    """

    def __init__(self):
        self._conversations: Dict[UUID, Conversation] = {}

    def save(self, conversation: Conversation) -> Conversation:
        """Save conversation to memory"""
        self._conversations[conversation.id] = deepcopy(conversation)
        return conversation

    def get(self, conversation_id: UUID) -> Optional[Conversation]:
        """Get conversation by ID"""
        return deepcopy(self._conversations.get(conversation_id))

    def list_by_session(
            self,
            session_id: str,
            limit: Optional[int] = None
    ) -> List[Conversation]:
        """List conversations by session"""
        conversations = [
            conv for conv in self._conversations.values()
            if conv.session_id == session_id
        ]
        conversations.sort(key=lambda c: c.updated_at, reverse=True)

        if limit:
            conversations = conversations[:limit]

        return [deepcopy(conv) for conv in conversations]

    def list_by_user(
            self,
            user_id: UUID,
            limit: Optional[int] = None
    ) -> List[Conversation]:
        """List conversations by user"""
        conversations = [
            conv for conv in self._conversations.values()
            if conv.user_id == user_id
        ]
        conversations.sort(key=lambda c: c.updated_at, reverse=True)

        if limit:
            conversations = conversations[:limit]

        return [deepcopy(conv) for conv in conversations]

    def delete(self, conversation_id: UUID) -> bool:
        """Delete conversation"""
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            return True
        return False

    def clear(self):
        """Clear all conversations"""
        self._conversations.clear()
