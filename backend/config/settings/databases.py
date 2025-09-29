"""
Database Configuration Module

Provides environment-specific database configurations for Django.
This module can be imported and tested independently of Django.

Supported environments:
- test: Ephemeral PostgreSQL for automated tests
- development: Local PostgreSQL with Docker Compose
- staging: AWS RDS PostgreSQL for pre-production testing
- production: AWS RDS PostgreSQL with high availability

Usage:
    from config.settings.databases import get_database_config

    db_config = get_database_config('development')
    DATABASES = {'default': db_config}
"""

import os
from pathlib import Path

# Base directory (backend root)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ============================================================================
# COMMON DATABASE SETTINGS
# ============================================================================

COMMON_DB_SETTINGS = {
    'ENGINE': 'django.db.backends.postgresql',
    'CONN_MAX_AGE': 60,  # Connection pooling: keep connections for 60 seconds
    'ATOMIC_REQUESTS': True,  # Wrap each request in a transaction
    'OPTIONS': {
        'connect_timeout': 10,  # Connection timeout in seconds
        'application_name': 'swisson-chatbot',  # Appears in pg_stat_activity
    },
}


# ============================================================================
# ENVIRONMENT-SPECIFIC CONFIGURATIONS
# ============================================================================

def get_database_config(environment: str) -> dict:
    """
    Get database configuration for specified environment.

    Args:
        environment: One of 'test', 'development', 'staging', 'production'

    Returns:
        Dictionary with Django database configuration

    Raises:
        ValueError: If environment is not recognized

    Examples:
        >>> config = get_database_config('development')
        >>> config['ENGINE']
        'django.db.backends.postgresql'
        >>> config['HOST']
        'localhost'
    """
    # Map environment names to their config functions (don't call them yet!)
    config_functions = {
        'test': _get_test_config,
        'development': _get_development_config,
        'staging': _get_staging_config,
        'production': _get_production_config,
    }

    if environment not in config_functions:
        valid_envs = ', '.join(config_functions.keys())
        raise ValueError(
            f"Invalid environment '{environment}'. "
            f"Must be one of: {valid_envs}"
        )

    # Now call the specific config function for the requested environment
    return config_functions[environment]()


def _get_test_config() -> dict:
    """
    Test environment configuration.

    Uses ephemeral PostgreSQL container (port 5433) with tmpfs.
    Data is wiped on every container restart.
    Optimized for speed over durability.
    """
    return {
        **COMMON_DB_SETTINGS,
        'NAME': 'test_chatbot',
        'USER': 'postgres',
        'PASSWORD': 'postgres',
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5433'),
        'OPTIONS': {
            **COMMON_DB_SETTINGS['OPTIONS'],
            'options': '-c search_path=public',
        },
        'TEST': {
            'NAME': 'test_chatbot',  # Don't create separate test database
        },
    }


def _get_development_config() -> dict:
    """
    Development environment configuration.

    Uses local PostgreSQL container (port 5432) with persistent volume.
    Data persists between container restarts.
    Allows developers to keep local data.
    """
    return {
        **COMMON_DB_SETTINGS,
        'NAME': os.getenv('DB_NAME', 'chatbot_dev'),
        'USER': os.getenv('DB_USER', 'chatbot_user'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'dev_password_123'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
        'OPTIONS': {
            **COMMON_DB_SETTINGS['OPTIONS'],
            'sslmode': 'disable',  # Local development, no SSL needed
        },
    }


def _get_staging_config() -> dict:
    """
    Staging environment configuration.

    Uses AWS RDS PostgreSQL instance for pre-production testing.
    SSL required for security.
    Credentials from environment variables (populated by AWS Secrets Manager).
    """
    # Verify required environment variables
    required_vars = ['DB_NAME', 'DB_USER', 'DB_PASSWORD', 'DB_HOST']
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        raise ValueError(
            f"Missing required environment variables for staging: {', '.join(missing_vars)}"
        )

    return {
        **COMMON_DB_SETTINGS,
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT', '5432'),
        'CONN_MAX_AGE': 300,  # Longer connection pooling for staging (5 minutes)
        'OPTIONS': {
            **COMMON_DB_SETTINGS['OPTIONS'],
            'sslmode': 'require',  # Require SSL but don't verify certificate
            'sslrootcert': str(BASE_DIR / 'certs' / 'rds-ca-bundle.pem'),
        },
    }


def _get_production_config() -> dict:
    """
    Production environment configuration.

    Uses AWS RDS PostgreSQL instance with Multi-AZ deployment.
    SSL with full certificate verification.
    Credentials from environment variables (populated by AWS Secrets Manager).
    Longest connection pooling for performance.
    """
    # Verify required environment variables
    required_vars = ['DB_NAME', 'DB_USER', 'DB_PASSWORD', 'DB_HOST']
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        raise ValueError(
            f"Missing required environment variables for production: {', '.join(missing_vars)}"
        )

    return {
        **COMMON_DB_SETTINGS,
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT', '5432'),
        'CONN_MAX_AGE': 600,  # Longest connection pooling for production (10 minutes)
        'OPTIONS': {
            **COMMON_DB_SETTINGS['OPTIONS'],
            'sslmode': 'verify-full',  # Strongest SSL mode - verify certificate
            'sslrootcert': str(BASE_DIR / 'certs' / 'rds-ca-bundle.pem'),
        },
    }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_all_environments() -> list:
    """
    Get list of supported environment names.

    Returns:
        List of environment name strings

    Example:
        get_all_environments()
        ['test', 'development', 'staging', 'production']
    """
    return ['test', 'development', 'staging', 'production']


def validate_environment(environment: str) -> bool:
    """
    Check if environment name is valid.

    Args:
        environment: Environment name to validate

    Returns:
        True if valid, False otherwise

    Example:
        validate_environment('development')
        True
        validate_environment('invalid')
        False
    """
    return environment in get_all_environments()


def get_connection_info(environment: str) -> dict:
    """
    Get human-readable connection information for an environment.

    Args:
        environment: Environment name

    Returns:
        Dictionary with connection details (passwords masked)

    Example:
        info = get_connection_info('development')
        info['host']
        'localhost'
        info['password']
        '***'
    """
    config = get_database_config(environment)

    return {
        'environment': environment,
        'host': config['HOST'],
        'port': config['PORT'],
        'database': config['NAME'],
        'user': config['USER'],
        'password': '***',  # Never expose passwords
        'ssl_mode': config['OPTIONS'].get('sslmode', 'N/A'),
    }
