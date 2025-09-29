# apps/domain/services/chat_service.py

"""
Chat Service - Orchestrates conversation flow

This service coordinates between RAG strategies and repositories
to handle the complete chat use case.
"""

from typing import Optional
from uuid import UUID
import logging

from apps.domain.models import (
    Message, Conversation, MessageRole, Answer,
    NotFoundError, ValidationError, InsufficientContextError
)
from apps.domain.strategies.base import IRagStrategy
from apps.domain.ports.repositories import IMessageRepository, IConversationRepository

logger = logging.getLogger(__name__)


class ChatService:
    """
    Chat service for handling conversations

    Responsibilities:
    - Orchestrate answer generation
    - Manage conversation state
    - Persist messages
    - Handle errors gracefully
    """

    def __init__(
            self,
            rag_strategy: IRagStrategy,
            message_repo: IMessageRepository,
            conversation_repo: IConversationRepository
    ):
        """
        Initialize chat service

        Args:
            rag_strategy: RAG implementation to use
            message_repo: Repository for message persistence
            conversation_repo: Repository for conversation persistence
        """
        self._rag_strategy = rag_strategy
        self._message_repo = message_repo
        self._conversation_repo = conversation_repo

    def answer_question(
            self,
            conversation_id: UUID,
            query: str,
            language: str = "en"
    ) -> Answer:
        """
        Generate answer to user's question

        This is the main use case for the chat service.

        Steps:
        1. Load conversation
        2. Save user message
        3. Get conversation history
        4. Generate answer using RAG
        5. Save assistant message
        6. Update conversation
        7. Return answer

        Args:
            conversation_id: UUID of the conversation
            query: User's question
            language: Response language (en, de, fr, es)

        Returns:
            Answer object with response and metadata

        Raises:
            NotFoundError: If conversation doesn't exist
            ValidationError: If query is empty or invalid
            InsufficientContextError: If no relevant info found
        """
        # Validate input
        if not query or not query.strip():
            raise ValidationError("Query cannot be empty")

        if language not in ['en', 'de', 'fr', 'es']:
            logger.warning(f"Invalid language '{language}', defaulting to 'en'")
            language = 'en'

        # Load conversation
        conversation = self._conversation_repo.get(conversation_id)
        if not conversation:
            raise NotFoundError(f"Conversation {conversation_id} not found")

        logger.info(f"Processing query for conversation {conversation_id}")

        try:
            # Save user message
            user_message = Message(
                conversation_id=conversation_id,
                role=MessageRole.USER,
                content=query
            )
            user_message = self._message_repo.save(user_message)

            # Get conversation history
            history = self._message_repo.list_by_conversation(
                conversation_id,
                limit=10  # Last 10 messages
            )

            # Generate answer using RAG
            answer = self._rag_strategy.generate_answer(
                query=query,
                history=history,
                language=language
            )

            # Save assistant message
            assistant_message = Message(
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT,
                content=answer.content,
                metadata={
                    'citations': [
                        {
                            'document': c.document,
                            'page': c.page,
                            'section': c.section,
                            'score': c.score
                        }
                        for c in answer.citations
                    ],
                    'sources_count': len(answer.sources),
                    'method': answer.method,
                    **answer.metadata
                }
            )
            assistant_message = self._message_repo.save(assistant_message)

            # Update conversation (touch updated_at)
            conversation.updated_at = assistant_message.created_at
            self._conversation_repo.save(conversation)

            logger.info(
                f"Successfully generated answer with "
                f"{len(answer.citations)} citations"
            )

            return answer

        except InsufficientContextError:
            # Handle no context found
            logger.warning(f"No context found for query: {query[:50]}...")

            # Save user message anyway
            fallback_answer = self._generate_fallback_answer(language)

            assistant_message = Message(
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT,
                content=fallback_answer,
                metadata={
                    'fallback': True,
                    'error': 'insufficient_context'
                }
            )
            self._message_repo.save(assistant_message)

            # Return fallback answer
            return Answer(
                content=fallback_answer,
                citations=[],
                sources=[],
                method="fallback",
                context_used=False,
                metadata={'error': 'insufficient_context'}
            )

        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            raise

    def create_conversation(
            self,
            session_id: str,
            language: str = "en",
            title: str = ""
    ) -> Conversation:
        """
        Create a new conversation

        Args:
            session_id: Session identifier
            language: Conversation language
            title: Optional conversation title

        Returns:
            Created Conversation object
        """
        conversation = Conversation(
            session_id=session_id,
            language=language,
            title=title or "New conversation"
        )

        conversation = self._conversation_repo.save(conversation)
        logger.info(f"Created conversation {conversation.id}")

        return conversation

    def get_conversation(self, conversation_id: UUID) -> Optional[Conversation]:
        """
        Get conversation by ID

        Args:
            conversation_id: UUID of conversation

        Returns:
            Conversation object or None if not found
        """
        return self._conversation_repo.get(conversation_id)

    def list_user_conversations(
            self,
            user_id: UUID,
            limit: int = 20
    ) -> list[Conversation]:
        """
        List conversations for a user

        Args:
            user_id: User UUID
            limit: Maximum number to return

        Returns:
            List of Conversation objects
        """
        return self._conversation_repo.list_by_user(user_id, limit)

    def list_session_conversations(
            self,
            session_id: str,
            limit: int = 20
    ) -> list[Conversation]:
        """
        List conversations for a session

        Args:
            session_id: Session identifier
            limit: Maximum number to return

        Returns:
            List of Conversation objects
        """
        return self._conversation_repo.list_by_session(session_id, limit)

    def _generate_fallback_answer(self, language: str) -> str:
        """
        Generate fallback answer when no context found

        Args:
            language: Response language

        Returns:
            Fallback message in appropriate language
        """
        fallbacks = {
            'en': "I couldn't find relevant information in the knowledge base to answer your question. Could you rephrase or ask something else?",
            'de': "Ich konnte keine relevanten Informationen in der Wissensdatenbank finden, um Ihre Frage zu beantworten. Könnten Sie umformulieren oder etwas anderes fragen?",
            'fr': "Je n'ai pas trouvé d'informations pertinentes dans la base de connaissances pour répondre à votre question. Pourriez-vous reformuler ou poser une autre question?",
            'es': "No pude encontrar información relevante en la base de conocimientos para responder tu pregunta. ¿Podrías reformular o preguntar algo más?"
        }

        return fallbacks.get(language, fallbacks['en'])
