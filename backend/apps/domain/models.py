# apps/domain/models.py#

"""
Domain Models - Value Objects and Entities

Value Objects: Immutable, defined by attributes (e.g., Citation, Source)
Entities: Have identity, mutable (e.g., Message, Conversation)
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum


class MessageRole(str, Enum):
    """Message role in conversation"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class DocumentType(str, Enum):
    """Document classification"""
    MANUAL = "manual"
    DATASHEET = "datasheet"
    FIRMWARE_NOTES = "firmware_notes"
    QUICK_START = "quick_start"
    TROUBLESHOOTING = "troubleshooting"
    OTHER = "other"


# ============================================================
# VALUE OBJECTS (Immutable)
# ============================================================

@dataclass(frozen=True)
class Citation:
    """
    A reference to source material in an answer

    Immutable value object - cannot be changed after creation.
    Two citations with same attributes are considered equal.
    """
    document: str
    page: int
    section: Optional[str] = None
    text: str = ""
    score: float = 0.0

    def __str__(self) -> str:
        if self.section:
            return f"[{self.document}, Page {self.page}, {self.section}]"
        return f"[{self.document}, Page {self.page}]"


@dataclass(frozen=True)
class Source:
    """
    A document chunk used as context

    Represents a piece of retrieved content with metadata.
    """
    chunk_id: UUID
    document_title: str
    document_type: DocumentType
    page_number: Optional[int]
    section_title: str
    content: str
    similarity_score: float
    embedding_model: Optional[str] = None

    def content_preview(self, max_length: int = 150) -> str:
        """Get truncated content for display"""
        if len(self.content) <= max_length:
            return self.content
        return self.content[:max_length] + "..."


@dataclass(frozen=True)
class Chunk:
    """
    A text chunk with metadata

    Lightweight representation for retrieval results.
    """
    content: str
    document: str
    page: int
    section: str = ""
    score: float = 0.0

    @property
    def word_count(self) -> int:
        return len(self.content.split())


# ============================================================
# ENTITIES (Have Identity, Mutable)
# ============================================================

@dataclass
class Message:
    """
    A message in a conversation

    Entity with identity (id). Can be modified after creation.
    """
    id: UUID = field(default_factory=uuid4)
    conversation_id: Optional[UUID] = None
    role: MessageRole = MessageRole.USER
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def add_citation(self, citation: Citation) -> None:
        """Add a citation to message metadata"""
        if 'citations' not in self.metadata:
            self.metadata['citations'] = []
        self.metadata['citations'].append({
            'document': citation.document,
            'page': citation.page,
            'section': citation.section,
            'text': citation.text,
            'score': citation.score
        })

    @property
    def citations(self) -> List[Dict]:
        """Get citations from metadata"""
        return self.metadata.get('citations', [])


@dataclass
class Conversation:
    """
    A conversation thread

    Entity representing a chat session with messages.
    """
    id: UUID = field(default_factory=uuid4)
    title: str = ""
    language: str = "en"
    session_id: Optional[str] = None
    user_id: Optional[UUID] = None
    messages: List[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def add_message(self, role: MessageRole, content: str, metadata: Dict = None) -> Message:
        """Add a message to the conversation"""
        message = Message(
            conversation_id=self.id,
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self.messages.append(message)
        self.updated_at = datetime.utcnow()
        return message

    @property
    def message_count(self) -> int:
        return len(self.messages)

    def get_history(self, limit: int = 10) -> List[Message]:
        """Get recent message history"""
        return self.messages[-limit:]


# ============================================================
# RESULT OBJECTS (Return Types)
# ============================================================

@dataclass(frozen=True)
class Answer:
    """
    Result of RAG answer generation

    Immutable result object containing answer and metadata.
    """
    content: str
    citations: List[Citation]
    sources: List[Source]
    method: str
    context_used: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def has_citations(self) -> bool:
        return len(self.citations) > 0

    @property
    def source_count(self) -> int:
        return len(self.sources)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'content': self.content,
            'citations': [
                {
                    'document': c.document,
                    'page': c.page,
                    'section': c.section,
                    'text': c.text,
                    'score': c.score
                }
                for c in self.citations
            ],
            'sources': [
                {
                    'document': s.document_title,
                    'page': s.page_number,
                    'section': s.section_title,
                    'similarity': s.similarity_score,
                    'preview': s.content_preview()
                }
                for s in self.sources
            ],
            'method': self.method,
            'context_used': self.context_used,
            'metadata': self.metadata
        }


@dataclass(frozen=True)
class DocumentContent:
    """
    Extracted content from a document

    Result of document parsing.
    """
    pages: List[Dict[str, Any]]
    page_count: int
    total_chars: int
    extraction_method: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ChunkResult:
    """
    Result of similarity search

    Lightweight result for retrieval operations.
    """
    chunk_id: UUID
    content: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================
# DOMAIN EXCEPTIONS
# ============================================================

class DomainException(Exception):
    """Base exception for domain layer"""
    pass


class ValidationError(DomainException):
    """Raised when domain validation fails"""
    pass

class EmbeddingError(DomainException):
    """Raised when the embedding fails"""
    pass

class NotFoundError(DomainException):
    """Raised when entity not found"""
    pass


class InsufficientContextError(DomainException):
    """Raised when retrieval returns insufficient context"""
    pass


class EmbeddingDimensionMismatchError(DomainException):
    """Raised when embedding dimensions don't match expected"""
    pass


class LLMProviderError(DomainException):
    """Raised when LLM provider fails"""
    pass


class RetrieverError(DomainException):
    """Raised when retrieval fails"""
    pass