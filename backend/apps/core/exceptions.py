# backend/apps/core/exceptions.py
"""
Custom exceptions for the core app
"""


class OpenRouterError(Exception):
    """Base exception for OpenRouter API errors"""

    pass


class EmbeddingError(OpenRouterError):
    """Exception raised when embedding generation fails"""

    pass


class GenerationError(OpenRouterError):
    """Exception raised when text generation fails"""

    pass


class DocumentProcessingError(Exception):
    """Exception raised during document processing"""

    pass


class RAGError(Exception):
    """Exception raised during RAG pipeline execution"""

    pass
