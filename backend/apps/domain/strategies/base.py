# apps/domain/strategies/base.py
"""
Base RAG Strategy Interface

Defines the interface that all RAG strategies must implement.
"""
from typing import Dict, List, Optional, Protocol

from apps.domain.models import Answer, Chunk, Citation, Message


class IRagStrategy(Protocol):
    """
    Interface for RAG (Retrieval-Augmented Generation) strategies

    All RAG implementations must provide these methods.
    This enables swapping strategies via configuration without code changes.
    """

    def retrieve(
        self, query: str, history: List[Message], filters: Optional[Dict] = None
    ) -> List[Chunk]:
        """
        Retrieve relevant document chunks for a query

        Args:
            query: User's question
            history: Conversation history for context
            filters: Optional metadata filters (document_type, language, etc.)

        Returns:
            List of relevant Chunk objects sorted by relevance
        """
        ...

    def build_prompt(
        self,
        query: str,
        chunks: List[Chunk],
        history: List[Message],
        language: str = "en",
    ) -> List[Dict[str, str]]:
        """
        Build LLM prompt messages from context

        Args:
            query: User's question
            chunks: Retrieved document chunks
            history: Conversation history
            language: Response language code

        Returns:
            List of message dicts for LLM
            Format: [{"role": "system", "content": "..."}, ...]
        """
        ...

    def extract_citations(self, response: str, chunks: List[Chunk]) -> List[Citation]:
        """
        Extract citations from LLM response

        Args:
            response: Generated answer text
            chunks: Source chunks that were provided as context

        Returns:
            List of Citation objects found in response
        """
        ...

    def generate_answer(
        self,
        query: str,
        history: List[Message],
        language: str = "en",
        filters: Optional[Dict] = None,
    ) -> Answer:
        """
        End-to-end answer generation

        Orchestrates: retrieve → build_prompt → generate → extract_citations

        Args:
            query: User's question
            history: Conversation history
            language: Response language
            filters: Optional metadata filters

        Returns:
            Answer object with content, citations, and metadata
        """
        ...
