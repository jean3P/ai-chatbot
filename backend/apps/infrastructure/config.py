# apps/infrastructure/config.py

"""
Configuration Management

Environment-specific configurations for different deployment contexts.
"""

import os
from typing import Any, Dict


def get_environment() -> str:
    """
    Get current environment from environment variable

    Returns:
        Environment name: 'test', 'development', 'staging', or 'production'
    """
    return os.getenv("ENVIRONMENT", "development")


def get_config() -> Dict[str, Any]:
    """
    Get configuration for current environment

    Returns:
        Configuration dictionary for active environment
    """
    env = get_environment()

    configs = {
        "test": TEST_CONFIG,
        "development": DEVELOPMENT_CONFIG,
        "staging": STAGING_CONFIG,
        "production": PRODUCTION_CONFIG,
    }

    config = configs.get(env, DEVELOPMENT_CONFIG)
    config["environment"] = env  # Add environment name to config

    return config


# ============================================================
# TEST CONFIGURATION
# ============================================================

TEST_CONFIG = {
    "llm": {"type": "fake", "response": "Test response from fake LLM"},
    "embedding": {"type": "fake", "dimension": 384},
    "retriever": {"type": "fake"},
    "prompt_version": "v1.0",
    "strategy_method": "baseline",
    "chunking": {"type": "fixed_size", "size": 500, "overlap": 50},
    "retrieval": {
        "type": "cosine",
        "threshold": 0.0,  # Accept all for testing
        "top_k": 10,
    },
}

# ============================================================
# DEVELOPMENT CONFIGURATION
# ============================================================

DEVELOPMENT_CONFIG = {
    "llm": {
        "type": "openrouter",
        "api_key": os.getenv("OPENROUTER_API_KEY", ""),
        "base_url": "https://openrouter.ai/api/v1",
        "model": "gpt-4o-mini",
        "temperature": 0.1,
        "max_tokens": 1000,
    },
    "embedding": {
        "type": "sentence_transformers",
        "model": "all-MiniLM-L6-v2",
        "device": "cpu",
        "dimension": 384,
    },
    "retriever": {"type": "numpy"},
    "prompt_version": "v1.0",
    "strategy_method": "baseline",
    "chunking": {"type": "fixed_size", "size": 1200, "overlap": 200},
    "retrieval": {"type": "cosine", "threshold": 0.3, "top_k": 10},
}

# ============================================================
# STAGING CONFIGURATION
# ============================================================

STAGING_CONFIG = {
    "llm": {
        "type": "openrouter",
        "api_key": os.getenv("OPENROUTER_API_KEY"),
        "base_url": "https://openrouter.ai/api/v1",
        "model": "gpt-4o-mini",
        "temperature": 0.1,
        "max_tokens": 1000,
    },
    "embedding": {
        "type": "sentence_transformers",
        "model": "all-MiniLM-L6-v2",
        "device": "cpu",
        "dimension": 384,
    },
    "retriever": {"type": "pgvector", "dimension": 384},  # Test pgvector in staging
    "prompt_version": "v1.0",
    "strategy_method": "baseline",
    "chunking": {"type": "fixed_size", "size": 1200, "overlap": 200},
    "retrieval": {"type": "cosine", "threshold": 0.3, "top_k": 10},
}

# ============================================================
# PRODUCTION CONFIGURATION
# ============================================================

PRODUCTION_CONFIG = {
    "llm": {
        "type": "openrouter",
        "api_key": os.getenv("OPENROUTER_API_KEY"),
        "base_url": "https://openrouter.ai/api/v1",
        "model": "gpt-4o-mini",
        "temperature": 0.1,
        "max_tokens": 1000,
    },
    "embedding": {
        "type": "sentence_transformers",
        "model": "all-MiniLM-L6-v2",
        "device": "cpu",
        "dimension": 384,
    },
    "retriever": {"type": "pgvector", "dimension": 384},
    "prompt_version": "v1.0",
    "strategy_method": "baseline",
    "chunking": {"type": "fixed_size", "size": 1200, "overlap": 200},
    "retrieval": {"type": "cosine", "threshold": 0.3, "top_k": 10},
    "rate_limits": {"per_ip": 100, "per_user": 1000, "per_session": 20},
    "monitoring": {
        "enabled": True,
        "metrics_backend": "cloudwatch",
        "tracing_backend": "datadog",
    },
    "cost_limits": {"daily_budget_usd": 500, "alert_threshold_pct": 80},
}


# ============================================================
# CONFIGURATION HELPERS
# ============================================================


def get_llm_config() -> Dict[str, Any]:
    """Get LLM configuration for current environment"""
    return get_config()["llm"]


def get_embedding_config() -> Dict[str, Any]:
    """Get embedding configuration for current environment"""
    return get_config()["embedding"]


def get_retriever_config() -> Dict[str, Any]:
    """Get retriever configuration for current environment"""
    return get_config()["retriever"]


def is_production() -> bool:
    """Check if running in production environment"""
    return get_environment() == "production"


def is_test() -> bool:
    """Check if running in test environment"""
    return get_environment() == "test"


def is_development() -> bool:
    """Check if running in development environment"""
    return get_environment() == "development"


def is_staging() -> bool:
    """Check if running in staging environment"""
    return get_environment() == "staging"
