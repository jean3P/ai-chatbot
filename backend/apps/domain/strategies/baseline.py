# apps/domain/strategies/baseline.py

"""
Baseline RAG Strategy

Simple dense retrieval with basic prompt engineering.
This is the MVP implementation for Phase 1.
"""

import logging
import re
from typing import Dict, List, Optional

from apps.domain.models import (
    Answer,
    Chunk,
    Citation,
    DocumentType,
    InsufficientContextError,
    Message,
    MessageRole,
    Source,
)
from apps.domain.ports.embeddings import IEmbeddingProvider
from apps.domain.ports.llm import ILLMProvider
from apps.domain.ports.retriever import IVectorStore

logger = logging.getLogger(__name__)


class BaselineStrategy:
    """
    Baseline RAG implementation

    Strategy:
    - Dense retrieval only (cosine similarity)
    - Simple prompt template
    - Basic citation extraction
    - Target: 85% recall@10
    """

    def __init__(
        self,
        retriever: IVectorStore,
        llm: ILLMProvider,
        embedder: IEmbeddingProvider,
        prompt_template: "PromptTemplate",
        top_k: int = 10,
        similarity_threshold: float = 0.3,
    ):
        """
        Initialize baseline strategy

        Args:
            retriever: Vector store for similarity search
            llm: LLM provider for text generation
            embedder: Embedding provider for queries
            prompt_template: Template for building prompts
            top_k: Number of chunks to retrieve
            similarity_threshold: Minimum similarity score
        """
        self._retriever = retriever
        self._llm = llm
        self._embedder = embedder
        self._prompt_template = prompt_template
        self._top_k = top_k
        self._similarity_threshold = similarity_threshold

    def retrieve(
        self, query: str, history: List[Message], filters: Optional[Dict] = None
    ) -> List[Chunk]:
        """
        Retrieve relevant chunks using dense retrieval

        Args:
            query: User's question
            history: Conversation history (not used in baseline)
            filters: Optional metadata filters

        Returns:
            List of relevant Chunk objects
        """
        # Generate query embedding
        query_embedding = self._embedder.embed_query(query)

        # Search vector store
        results = self._retriever.search(
            query_embedding=query_embedding, top_k=self._top_k, filters=filters
        )

        # Convert to Chunk objects and filter by threshold
        chunks = []
        for result in results:
            if result.score >= self._similarity_threshold:
                chunk = Chunk(
                    content=result.content,
                    document=result.metadata.get("document_title", "Unknown"),
                    page=result.metadata.get("page_number", 0),
                    section=result.metadata.get("section_title", ""),
                    score=result.score,
                )
                chunks.append(chunk)

        logger.info(
            f"Retrieved {len(chunks)} chunks with score >= {self._similarity_threshold}"
        )
        return chunks

    def build_prompt(
        self,
        query: str,
        chunks: List[Chunk],
        history: List[Message],
        language: str = "en",
    ) -> List[Dict[str, str]]:
        """
        Build prompt messages for LLM

        Args:
            query: User's question
            chunks: Retrieved context chunks
            history: Conversation history
            language: Response language

        Returns:
            List of message dicts for LLM
        """
        messages = []

        # System prompt with context
        system_content = self._prompt_template.render_system(
            context=chunks, language=language
        )
        messages.append({"role": "system", "content": system_content})

        # Add recent conversation history (last 6 messages)
        for msg in history[-6:]:
            messages.append({"role": msg.role.value, "content": msg.content})

        # Add current query
        messages.append({"role": "user", "content": query})

        return messages

    def extract_citations(self, response: str, chunks: List[Chunk]) -> List[Citation]:
        """
        Extract citations from response

        Looks for patterns like:
        - [Document Name, Page X]
        - (Document Name, Page X)
        - Document Name, Page X

        Args:
            response: Generated answer text
            chunks: Source chunks used in generation

        Returns:
            List of Citation objects
        """
        citations = []
        seen_citations = set()  # Avoid duplicates

        # Pattern 1: [Document, Page X]
        pattern1 = r"\[([^\]]+),\s*Page\s*(\d+)\]"
        matches = re.finditer(pattern1, response, re.IGNORECASE)

        for match in matches:
            doc_name = match.group(1).strip()
            page_num = int(match.group(2))

            # Find matching chunk
            for chunk in chunks:
                if (
                    doc_name.lower() in chunk.document.lower()
                    and chunk.page == page_num
                ):

                    citation_key = (chunk.document, chunk.page)
                    if citation_key not in seen_citations:
                        citations.append(
                            Citation(
                                document=chunk.document,
                                page=chunk.page,
                                section=chunk.section,
                                text=chunk.content[:200],
                                score=chunk.score,
                            )
                        )
                        seen_citations.add(citation_key)
                    break

        # Pattern 2: Look for document mentions even without explicit citation
        for chunk in chunks[:3]:  # Top 3 chunks likely cited
            # If document title appears in response
            if chunk.document.lower() in response.lower():
                citation_key = (chunk.document, chunk.page)
                if citation_key not in seen_citations:
                    citations.append(
                        Citation(
                            document=chunk.document,
                            page=chunk.page,
                            section=chunk.section,
                            text=chunk.content[:200],
                            score=chunk.score,
                        )
                    )
                    seen_citations.add(citation_key)

        logger.info(f"Extracted {len(citations)} citations from response")
        return citations

    def generate_answer(
        self,
        query: str,
        history: List[Message],
        language: str = "en",
        filters: Optional[Dict] = None,
    ) -> Answer:
        """
        Generate complete answer with RAG

        Args:
            query: User's question
            history: Conversation history
            language: Response language
            filters: Optional metadata filters

        Returns:
            Answer object with content, citations, sources

        Raises:
            InsufficientContextError: If no relevant chunks found
        """
        # 1. Retrieve relevant chunks
        chunks = self.retrieve(query, history, filters)

        if not chunks:
            logger.warning(f"No relevant chunks found for query: {query[:50]}...")
            raise InsufficientContextError(
                "No relevant information found in the knowledge base"
            )

        # 2. Build prompt
        messages = self.build_prompt(query, chunks, history, language)

        # 3. Generate response
        try:
            response_text = self._llm.generate(messages)
            usage = {}
            if hasattr(self._llm, "get_last_usage"):
                usage = self._llm.get_last_usage()
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise

        # 4. Extract citations
        citations = self.extract_citations(response_text, chunks)

        # 5. Build source list
        sources = []
        for chunk in chunks:
            source = Source(
                chunk_id=chunk.document + str(chunk.page),  # Simplified for now
                document_title=chunk.document,
                document_type=DocumentType.OTHER,  # Would come from metadata
                page_number=chunk.page,
                section_title=chunk.section,
                content=chunk.content,
                similarity_score=chunk.score,
            )
            sources.append(source)

        # 6. Create answer object
        answer = Answer(
            content=response_text,
            citations=citations,
            sources=sources[:5],
            method="baseline",
            context_used=True,
            metadata={
                "chunks_retrieved": len(chunks),
                "chunks_used": len(chunks),
                "top_similarity_score": chunks[0].score if chunks else 0.0,
                "llm_model": getattr(self._llm, "model", "unknown"),
                "embedding_model": getattr(
                    self._embedder, "embedding_model", "unknown"
                ),
                "prompt_tokens": usage.get("input", 0),
                "completion_tokens": usage.get("output", 0),
                "total_tokens": usage.get("total", 0),
                "strategy_config": {
                    "top_k": self._top_k,
                    "threshold": self._similarity_threshold,
                },
            },
        )

        logger.info(
            f"Generated answer with {len(citations)} citations "
            f"from {len(chunks)} chunks"
        )

        return answer
