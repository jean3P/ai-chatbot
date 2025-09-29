# apps/adapters/repositories/django_repos.py
"""
Django ORM Repository Adapters

Implements repository ports using Django models.
"""
from typing import Optional, List
from uuid import UUID
import logging

from apps.domain.models import Message, Conversation, MessageRole

logger = logging.getLogger(__name__)


class DjangoMessageRepository:
    """
    Message repository using Django ORM

    Wraps Django Message model with domain interface.
    """

    def save(self, message: Message) -> Message:
        """
        Save message to database

        Args:
            message: Domain Message object

        Returns:
            Saved message with database fields populated
        """
        from apps.chat.models import Message as ORMMessage

        try:
            # Check if exists
            try:
                orm_message = ORMMessage.objects.get(id=message.id)
                # Update existing
                orm_message.content = message.content
                orm_message.metadata = message.metadata
                orm_message.save(update_fields=['content', 'metadata'])

            except ORMMessage.DoesNotExist:
                # Create new
                orm_message = ORMMessage.objects.create(
                    id=message.id,
                    conversation_id=message.conversation_id,
                    role=message.role.value,
                    content=message.content,
                    metadata=message.metadata
                )

            # Convert back to domain model
            return self._to_domain(orm_message)

        except Exception as e:
            logger.error(f"Error saving message: {e}")
            raise

    def get(self, message_id: UUID) -> Optional[Message]:
        """
        Get message by ID

        Args:
            message_id: Message UUID

        Returns:
            Message or None if not found
        """
        from apps.chat.models import Message as ORMMessage

        try:
            orm_message = ORMMessage.objects.get(id=message_id)
            return self._to_domain(orm_message)

        except ORMMessage.DoesNotExist:
            return None

    def list_by_conversation(
            self,
            conversation_id: UUID,
            limit: Optional[int] = None
    ) -> List[Message]:
        """
        List messages in a conversation

        Args:
            conversation_id: Conversation UUID
            limit: Optional limit

        Returns:
            List of Message objects ordered by created_at
        """
        from apps.chat.models import Message as ORMMessage

        queryset = ORMMessage.objects.filter(
            conversation_id=conversation_id
        ).order_by('created_at')

        if limit:
            queryset = queryset[:limit]

        return [self._to_domain(msg) for msg in queryset]

    def delete(self, message_id: UUID) -> bool:
        """
        Delete message

        Args:
            message_id: Message UUID

        Returns:
            True if deleted, False if not found
        """
        from apps.chat.models import Message as ORMMessage

        deleted, _ = ORMMessage.objects.filter(id=message_id).delete()
        return deleted > 0

    def _to_domain(self, orm_message) -> Message:
        """Convert ORM model to domain model"""
        return Message(
            id=orm_message.id,
            conversation_id=orm_message.conversation_id,
            role=MessageRole(orm_message.role),
            content=orm_message.content,
            metadata=orm_message.metadata or {},
            created_at=orm_message.created_at
        )


class DjangoConversationRepository:
    """
    Conversation repository using Django ORM

    Wraps Django Conversation model with domain interface.
    """

    def save(self, conversation: Conversation) -> Conversation:
        """
        Save conversation to database

        Args:
            conversation: Domain Conversation object

        Returns:
            Saved conversation
        """
        from apps.chat.models import Conversation as ORMConversation

        try:
            # Check if exists
            try:
                orm_conv = ORMConversation.objects.get(id=conversation.id)
                # Update existing
                orm_conv.title = conversation.title
                orm_conv.language = conversation.language
                orm_conv.updated_at = conversation.updated_at
                orm_conv.save(update_fields=['title', 'language', 'updated_at'])

            except ORMConversation.DoesNotExist:
                # Create new
                orm_conv = ORMConversation.objects.create(
                    id=conversation.id,
                    session_id=conversation.session_id,
                    user_id=conversation.user_id,
                    title=conversation.title,
                    language=conversation.language
                )

            # Convert back to domain
            return self._to_domain(orm_conv)

        except Exception as e:
            logger.error(f"Error saving conversation: {e}")
            raise

    def get(self, conversation_id: UUID) -> Optional[Conversation]:
        """
        Get conversation by ID

        Args:
            conversation_id: Conversation UUID

        Returns:
            Conversation or None
        """
        from apps.chat.models import Conversation as ORMConversation

        try:
            orm_conv = ORMConversation.objects.get(id=conversation_id)
            return self._to_domain(orm_conv)

        except ORMConversation.DoesNotExist:
            return None

    def list_by_session(
            self,
            session_id: str,
            limit: Optional[int] = None
    ) -> List[Conversation]:
        """
        List conversations by session

        Args:
            session_id: Session identifier
            limit: Optional limit

        Returns:
            List of Conversation objects
        """
        from apps.chat.models import Conversation as ORMConversation

        queryset = ORMConversation.objects.filter(
            session_id=session_id
        ).order_by('-updated_at')

        if limit:
            queryset = queryset[:limit]

        return [self._to_domain(conv) for conv in queryset]

    def list_by_user(
            self,
            user_id: UUID,
            limit: Optional[int] = None
    ) -> List[Conversation]:
        """
        List conversations by user

        Args:
            user_id: User UUID
            limit: Optional limit

        Returns:
            List of Conversation objects
        """
        from apps.chat.models import Conversation as ORMConversation

        queryset = ORMConversation.objects.filter(
            user_id=user_id
        ).order_by('-updated_at')

        if limit:
            queryset = queryset[:limit]

        return [self._to_domain(conv) for conv in queryset]

    def delete(self, conversation_id: UUID) -> bool:
        """
        Delete conversation

        Args:
            conversation_id: Conversation UUID

        Returns:
            True if deleted
        """
        from apps.chat.models import Conversation as ORMConversation

        deleted, _ = ORMConversation.objects.filter(id=conversation_id).delete()
        return deleted > 0

    def _to_domain(self, orm_conv) -> Conversation:
        """Convert ORM model to domain model"""
        return Conversation(
            id=orm_conv.id,
            title=orm_conv.title,
            language=orm_conv.language,
            session_id=orm_conv.session_id,
            user_id=orm_conv.user_id,
            messages=[],  # Don't load messages automatically
            created_at=orm_conv.created_at,
            updated_at=orm_conv.updated_at
        )
