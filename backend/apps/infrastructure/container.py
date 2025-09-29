# apps/infrastructure/container.py

"""
Dependency Injection Container

Simple factory functions for creating fully-wired services.
No magic, no framework - just explicit construction.
"""

from typing import Dict, Any, Optional
import logging

from apps.domain.models import DomainException
from apps.infrastructure.config import get_config

logger = logging.getLogger(__name__)


# ============================================================
# ADAPTER FACTORIES
# ============================================================

def create_llm_provider(config: Dict[str, Any]):
    """
    Factory for LLM provider based on configuration

    Args:
        config: LLM configuration dict with 'type' key

    Returns:
        Implementation of ILLMProvider

    Raises:
        ValueError: If provider type is unknown
    """
    provider_type = config.get('type', 'fake')

    if provider_type == 'fake':
        from apps.adapters.llm.fake import FakeLLM
        return FakeLLM(response=config.get('response', 'Test response'))

    elif provider_type == 'openrouter':
        from apps.adapters.llm.openrouter import OpenRouterLLM

        api_key = config.get('api_key')
        if not api_key:
            raise ValueError("OpenRouter API key is required")

        return OpenRouterLLM(
            api_key=api_key,
            base_url=config.get('base_url', 'https://openrouter.ai/api/v1'),
            model=config.get('model', 'gpt-4o-mini'),
            temperature=config.get('temperature', 0.1),
            max_tokens=config.get('max_tokens', 1000)
        )

    else:
        raise ValueError(f"Unknown LLM provider type: {provider_type}")


def create_embedding_provider(config: Dict[str, Any]):
    """
    Factory for embedding provider based on configuration

    Args:
        config: Embedding configuration dict with 'type' key

    Returns:
        Implementation of IEmbeddingProvider

    Raises:
        ValueError: If provider type is unknown
    """
    provider_type = config.get('type', 'fake')

    if provider_type == 'fake':
        from apps.adapters.embeddings.fake import FakeEmbedding
        return FakeEmbedding(dimension=config.get('dimension', 384))

    elif provider_type == 'sentence_transformers':
        from apps.adapters.embeddings.sentence_transformers import SentenceTransformersEmbedding
        return SentenceTransformersEmbedding(
            model_name=config.get('model', 'all-MiniLM-L6-v2'),
            device=config.get('device', 'cpu')
        )

    else:
        raise ValueError(f"Unknown embedding provider type: {provider_type}")


def create_vector_store(config: Dict[str, Any]):
    """
    Factory for vector store based on configuration
    """
    store_type = config.get('type', 'numpy')

    if store_type == 'numpy':
        from apps.adapters.retrieval.numpy_db_store import NumPyDBVectorStore
        return NumPyDBVectorStore(auto_load=True)  # Auto-load from database

    elif store_type == 'pgvector':
        from apps.adapters.retrieval.pgvector_store import PgVectorStore
        return PgVectorStore(dimension=config.get('dimension', 384))

    elif store_type == 'fake':
        from apps.adapters.retrieval.fake import FakeVectorStore
        return FakeVectorStore()

    else:
        raise ValueError(f"Unknown vector store type: {store_type}")


def create_document_parser(file_type: str = 'pdf'):
    """
    Factory for document parser based on file type

    Args:
        file_type: File extension (e.g., 'pdf', 'txt')

    Returns:
        Implementation of IDocumentParser

    Raises:
        ValueError: If file type is not supported
    """
    if file_type == 'pdf':
        from apps.adapters.parsing.pymupdf_parser import PyMuPDFParser
        return PyMuPDFParser()

    elif file_type == 'fake':
        from apps.adapters.parsing.fake import FakeParser
        return FakeParser()

    else:
        raise ValueError(f"Unsupported file type: {file_type}")


def create_message_repository(use_inmemory: bool = False):
    """
    Factory for message repository

    Args:
        use_inmemory: If True, use in-memory repo (for testing)

    Returns:
        Implementation of IMessageRepository
    """
    if use_inmemory:
        from apps.adapters.repositories.inmemory_repos import InMemoryMessageRepository
        return InMemoryMessageRepository()
    else:
        from apps.adapters.repositories.django_repos import DjangoMessageRepository
        return DjangoMessageRepository()


def create_conversation_repository(use_inmemory: bool = False):
    """
    Factory for conversation repository

    Args:
        use_inmemory: If True, use in-memory repo (for testing)

    Returns:
        Implementation of IConversationRepository
    """
    if use_inmemory:
        from apps.adapters.repositories.inmemory_repos import InMemoryConversationRepository
        return InMemoryConversationRepository()
    else:
        from apps.adapters.repositories.django_repos import DjangoConversationRepository
        return DjangoConversationRepository()


# ============================================================
# STRATEGY FACTORIES
# ============================================================

def create_rag_strategy(config: Dict[str, Any], method: str = 'baseline'):
    """
    Factory for RAG strategy

    Args:
        config: Full configuration dict
        method: Strategy method ('baseline', 'hybrid', 'rerank')

    Returns:
        Implementation of IRagStrategy

    Raises:
        ValueError: If method is unknown
    """
    if method == 'baseline':
        from apps.domain.strategies.baseline import BaselineStrategy
        from apps.domain.prompts.template import PromptTemplate

        # Create dependencies
        llm = create_llm_provider(config['llm'])
        embedder = create_embedding_provider(config['embedding'])
        retriever = create_vector_store(config['retriever'])

        # Create prompt template
        prompt_template = PromptTemplate(
            version=config.get('prompt_version', 'v1.0')
        )

        # Create strategy with configuration
        retrieval_config = config.get('retrieval', {})

        return BaselineStrategy(
            retriever=retriever,
            llm=llm,
            embedder=embedder,
            prompt_template=prompt_template,
            top_k=retrieval_config.get('top_k', 10),
            similarity_threshold=retrieval_config.get('threshold', 0.3)
        )

    # Future strategies
    # elif method == 'hybrid':
    #     from apps.domain.strategies.hybrid import HybridStrategy
    #     return HybridStrategy(...)

    else:
        raise ValueError(f"Unknown RAG strategy method: {method}")


# ============================================================
# SERVICE FACTORIES
# ============================================================

def create_chat_service(config: Optional[Dict] = None, use_inmemory_repos: bool = False):
    """
    Create fully-wired ChatService with all dependencies

    This is the main entry point for creating chat services.

    Args:
        config: Optional configuration dict. If None, uses environment config.
        use_inmemory_repos: If True, use in-memory repos (for testing)

    Returns:
        ChatService instance with all dependencies injected

    Example:
        >>> service = create_chat_service()
        >>> answer = service.answer_question(
        ...     conversation_id=uuid4(),
        ...     query="How to install?",
        ...     language="en"
        ... )
    """
    config = config or get_config()

    try:
        # Validate configuration
        validate_config(config)

        # Create RAG strategy
        strategy = create_rag_strategy(
            config=config,
            method=config.get('strategy_method', 'baseline')
        )

        # Create repositories
        msg_repo = create_message_repository(use_inmemory=use_inmemory_repos)
        conv_repo = create_conversation_repository(use_inmemory=use_inmemory_repos)

        # Wire service
        from apps.domain.services.chat_service import ChatService
        service = ChatService(
            rag_strategy=strategy,
            message_repo=msg_repo,
            conversation_repo=conv_repo
        )

        logger.info(
            f"Created ChatService with strategy={config.get('strategy_method', 'baseline')}, "
            f"llm={config['llm']['type']}, "
            f"embedding={config['embedding']['type']}, "
            f"retriever={config['retriever']['type']}"
        )

        return service

    except Exception as e:
        logger.error(f"Failed to create chat service: {e}")
        raise DomainException(f"Service initialization failed: {e}")


def create_document_service(config: Optional[Dict] = None):
    """
    Create DocumentService for processing uploaded documents

    Args:
        config: Optional configuration dict

    Returns:
        DocumentService instance

    Note:
        To be implemented when DocumentService is created
    """
    config = config or get_config()

    # TODO: Implement DocumentService
    # from apps.domain.services.document_service import DocumentService
    # parser = create_document_parser('pdf')
    # embedder = create_embedding_provider(config['embedding'])
    # retriever = create_vector_store(config['retriever'])
    # return DocumentService(parser, embedder, retriever)

    raise NotImplementedError("DocumentService not yet implemented")


def create_evaluation_service(config: Optional[Dict] = None):
    """
    Create EvaluationService for running experiments

    Args:
        config: Optional configuration dict

    Returns:
        EvaluationService instance

    Note:
        To be implemented in Phase 2
    """
    config = config or get_config()

    # TODO: Implement EvaluationService
    raise NotImplementedError("EvaluationService not yet implemented")


# ============================================================
# VALIDATION
# ============================================================

def validate_config(config: Dict[str, Any]) -> bool:
    """
    Validate configuration structure

    Args:
        config: Configuration dictionary to validate

    Returns:
        True if valid

    Raises:
        ValueError: If configuration is invalid
    """
    required_keys = ['llm', 'embedding', 'retriever']

    for key in required_keys:
        if key not in config:
            raise ValueError(f"Missing required config key: {key}")

    # Validate LLM config
    if 'type' not in config['llm']:
        raise ValueError("LLM config missing 'type' key")

    # Validate embedding config
    if 'type' not in config['embedding']:
        raise ValueError("Embedding config missing 'type' key")

    # Validate retriever config
    if 'type' not in config['retriever']:
        raise ValueError("Retriever config missing 'type' key")

    # Validate embedding dimension consistency
    if config['retriever']['type'] == 'pgvector':
        if 'dimension' not in config['retriever']:
            raise ValueError("PgVector config requires 'dimension' key")

    return True


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_service_info(config: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Get information about configured services

    Args:
        config: Optional config dict, uses environment config if None

    Returns:
        Dict with service configuration info
    """
    config = config or get_config()

    return {
        'environment': config.get('environment', 'unknown'),
        'llm': {
            'type': config['llm'].get('type'),
            'model': config['llm'].get('model', 'N/A'),
        },
        'embedding': {
            'type': config['embedding'].get('type'),
            'model': config['embedding'].get('model', 'N/A'),
            'dimension': config['embedding'].get('dimension', 'N/A'),
        },
        'retriever': {
            'type': config['retriever'].get('type'),
        },
        'prompt_version': config.get('prompt_version', 'v1.0'),
        'strategy_method': config.get('strategy_method', 'baseline')
    }


def print_service_info(config: Optional[Dict] = None):
    """
    Print service configuration info (useful for debugging)

    Args:
        config: Optional config dict
    """
    info = get_service_info(config)

    print("=== Service Configuration ===")
    print(f"Environment: {info['environment']}")
    print(f"LLM: {info['llm']['type']} ({info['llm']['model']})")
    print(f"Embedding: {info['embedding']['type']} ({info['embedding']['model']})")
    print(f"Retriever: {info['retriever']['type']}")
    print(f"Prompt Version: {info['prompt_version']}")
    print(f"Strategy: {info['strategy_method']}")
    print("=" * 30)
