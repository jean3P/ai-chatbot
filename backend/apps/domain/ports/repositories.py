# apps/domain/ports/repositories.py

"""
Repository Ports - Interfaces for data persistence

These ports define contracts for accessing stored data.
"""

from typing import Protocol, Optional, List
from uuid import UUID

from apps.domain.models import Message, Conversation


class IMessageRepository(Protocol):
    """
    Interface for message persistence

    Handles CRUD operations for messages.
    """

    def save(self, message: Message) -> Message:
        """
        Save a message (create or update)

        Args:
            message: Message domain object to save

        Returns:
            Saved message with any generated fields populated

        Raises:
            ValidationError: If message data is invalid
        """
        ...

    def get(self, message_id: UUID) -> Optional[Message]:
        """
        Retrieve a message by ID

        Args:
            message_id: UUID of the message

        Returns:
            Message object if found, None otherwise
        """
        ...

    def list_by_conversation(
            self,
            conversation_id: UUID,
            limit: Optional[int] = None
    ) -> List[Message]:
        """
        Get all messages in a conversation

        Args:
            conversation_id: UUID of the conversation
            limit: Optional maximum number of messages to return

        Returns:
            List of Message objects ordered by created_at (oldest first)
        """
        ...

    def delete(self, message_id: UUID) -> bool:
        """
        Delete a message

        Args:
            message_id: UUID of the message to delete

        Returns:
            True if deleted, False if not found
        """
        ...


class IConversationRepository(Protocol):
    """
    Interface for conversation persistence

    Handles CRUD operations for conversations.
    """

    def save(self, conversation: Conversation) -> Conversation:
        """
        Save a conversation (create or update)

        Args:
            conversation: Conversation domain object to save

        Returns:
            Saved conversation with any generated fields populated

        Raises:
            ValidationError: If conversation data is invalid
        """
        ...

    def get(self, conversation_id: UUID) -> Optional[Conversation]:
        """
        Retrieve a conversation by ID

        Args:
            conversation_id: UUID of the conversation

        Returns:
            Conversation object if found, None otherwise
        """
        ...

    def list_by_session(
            self,
            session_id: str,
            limit: Optional[int] = None
    ) -> List[Conversation]:
        """
        Get conversations for a session

        Args:
            session_id: Session identifier
            limit: Optional maximum number to return

        Returns:
            List of Conversation objects ordered by updated_at (newest first)
        """
        ...

    def list_by_user(
            self,
            user_id: UUID,
            limit: Optional[int] = None
    ) -> List[Conversation]:
        """
        Get conversations for a user

        Args:
            user_id: User UUID
            limit: Optional maximum number to return

        Returns:
            List of Conversation objects ordered by updated_at (newest first)
        """
        ...

    def delete(self, conversation_id: UUID) -> bool:
        """
        Delete a conversation and its messages

        Args:
            conversation_id: UUID of the conversation to delete

        Returns:
            True if deleted, False if not found

        Note:
            Should cascade delete all associated messages
        """
        ...
