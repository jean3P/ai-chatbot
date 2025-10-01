# apps/domain/services/chat_service.py

"""
Chat Service - Orchestrates conversation flow

This service coordinates between RAG strategies and repositories
to handle the complete chat use case.
"""

import logging
import time
from typing import Optional
from uuid import UUID

from apps.chat.models import AnswerLog
from apps.core.budget_monitor import budget_monitor
from apps.domain.models import (
    Answer,
    Conversation,
    InsufficientContextError,
    Message,
    MessageRole,
    NotFoundError,
    ValidationError,
)
from apps.domain.ports.repositories import IConversationRepository, IMessageRepository
from apps.domain.strategies.base import IRagStrategy
from apps.infrastructure.pricing import calculate_cost

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
        conversation_repo: IConversationRepository,
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

    # apps/domain/services/chat_service.py

    def answer_question(
            self, conversation_id: UUID, query: str, language: str = "en"
    ) -> Answer:
        """
        Generate answer to user's question with cost tracking and budget enforcement

        Steps:
        1. Validate input
        2. Check daily budget (NEW)
        3. Load conversation
        4. Save user message
        5. Get conversation history
        6. Generate answer using RAG
        7. Save assistant message
        8. Log costs (NEW)
        9. Return answer

        Args:
            conversation_id: UUID of the conversation
            query: User's question
            language: Response language (en, de, fr, es)

        Returns:
            Answer object with response and metadata

        Raises:
            NotFoundError: If conversation doesn't exist
            ValidationError: If query is empty, invalid, or budget exceeded
            InsufficientContextError: If no relevant info found
        """
        start_time = time.time()

        # 1. Validate input
        if not query or not query.strip():
            raise ValidationError("Query cannot be empty")

        if language not in ["en", "de", "fr", "es"]:
            logger.warning(f"Invalid language '{language}', defaulting to 'en'")
            language = "en"

        # 2. Check budget before processing (NEW)
        budget_status = budget_monitor.check_budget()

        if budget_status["alert_level"] == "critical":
            logger.error(
                f"Daily budget exceeded: ${budget_status['total_cost']:.2f} / "
                f"${budget_status['daily_budget']:.2f}"
            )
            raise ValidationError(
                "Daily cost budget exceeded. Please try again tomorrow or contact support."
            )

        # Log warning if approaching limit
        if budget_status["alert_level"] == "warning":
            logger.warning(
                f"Budget warning: {budget_status['budget_used_pct']:.1f}% used"
            )

        # 3. Load conversation
        conversation = self._conversation_repo.get(conversation_id)
        if not conversation:
            raise NotFoundError(f"Conversation {conversation_id} not found")

        logger.info(f"Processing query for conversation {conversation_id}")

        try:
            # 4. Save user message
            user_message = Message(
                conversation_id=conversation_id, role=MessageRole.USER, content=query
            )
            user_message = self._message_repo.save(user_message)

            # 5. Get conversation history
            history = self._message_repo.list_by_conversation(
                conversation_id, limit=10
            )

            # 6. Generate answer using RAG
            answer = self._rag_strategy.generate_answer(
                query=query, history=history, language=language
            )

            # 7. Save assistant message
            assistant_message = Message(
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT,
                content=answer.content,
                metadata={
                    "citations": [
                        {
                            "document": c.document,
                            "page": c.page,
                            "section": c.section,
                            "score": c.score,
                        }
                        for c in answer.citations
                    ],
                    "sources_count": len(answer.sources),
                    "method": answer.method,
                    **answer.metadata,
                },
            )
            assistant_message = self._message_repo.save(assistant_message)

            # Update conversation (touch updated_at)
            conversation.updated_at = assistant_message.created_at
            self._conversation_repo.save(conversation)

            logger.info(
                f"Successfully generated answer with {len(answer.citations)} citations"
            )

            # 8. Log costs (NEW)
            self._log_answer(answer, assistant_message, query, language, start_time)

            return answer

        except InsufficientContextError:
            # Handle no context found
            logger.warning(f"No context found for query: {query[:50]}...")

            fallback_answer = self._generate_fallback_answer(language)

            assistant_message = Message(
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT,
                content=fallback_answer,
                metadata={"fallback": True, "error": "insufficient_context"},
            )
            self._message_repo.save(assistant_message)

            return Answer(
                content=fallback_answer,
                citations=[],
                sources=[],
                method="fallback",
                context_used=False,
                metadata={"error": "insufficient_context"},
            )

        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            raise

    def create_conversation(
        self, session_id: str, language: str = "en", title: str = ""
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
            session_id=session_id, language=language, title=title or "New conversation"
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
        self, user_id: UUID, limit: int = 20
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
        self, session_id: str, limit: int = 20
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
            "en": "I couldn't find relevant information in the knowledge base to answer your question. Could you rephrase or ask something else?",
            "de": "Ich konnte keine relevanten Informationen in der Wissensdatenbank finden, um Ihre Frage zu beantworten. Könnten Sie umformulieren oder etwas anderes fragen?",
            "fr": "Je n'ai pas trouvé d'informations pertinentes dans la base de connaissances pour répondre à votre question. Pourriez-vous reformuler ou poser une autre question?",
            "es": "No pude encontrar información relevante en la base de conocimientos para responder tu pregunta. ¿Podrías reformular o preguntar algo más?",
        }

        return fallbacks.get(language, fallbacks["en"])

    def _log_answer(
        self,
        answer: Answer,
        message: Message,
        query: str,
        language: str,
        start_time: float,
    ):
        """
        Log answer generation metrics

        Args:
            answer: Generated answer object
            message: Saved message
            query: User's original query
            language: Response language
            start_time: Start timestamp
        """
        try:
            total_latency = (time.time() - start_time) * 1000  # Convert to ms

            # Get token usage from metadata
            prompt_tokens = answer.metadata.get("prompt_tokens", 0)
            completion_tokens = answer.metadata.get("completion_tokens", 0)
            total_tokens = answer.metadata.get("total_tokens", 0)
            llm_model = answer.metadata.get("llm_model", "unknown")

            # Calculate cost
            estimated_cost = calculate_cost(
                prompt_tokens,
                completion_tokens,
                llm_model
            )

            AnswerLog.objects.create(
                message_id=message.id,
                query=query,
                language=language,
                method=answer.method,
                strategy_config=answer.metadata.get("strategy_config", {}),
                chunks_retrieved=answer.metadata.get("chunks_retrieved", 0),
                chunks_used=answer.source_count,
                top_similarity_score=answer.metadata.get("top_similarity_score", 0.0),
                context_used=answer.context_used,
                llm_model=answer.metadata.get("llm_model", "unknown"),
                embedding_model=answer.metadata.get("embedding_model", "unknown"),
                total_tokens=answer.metadata.get("total_tokens", 0),
                prompt_tokens=answer.metadata.get("prompt_tokens", 0),
                completion_tokens=answer.metadata.get("completion_tokens", 0),
                total_latency_ms=total_latency,
                estimated_cost_usd=estimated_cost,
                citations_count=len(answer.citations),
                sources_count=answer.source_count,
                had_error=False,
            )

            logger.info(
                f"Cost: ${estimated_cost:.4f} | "
                f"Tokens: {total_tokens} | "
                f"Model: {llm_model}"
            )

        except Exception as e:
            logger.error(f"Failed to log answer: {e}")
