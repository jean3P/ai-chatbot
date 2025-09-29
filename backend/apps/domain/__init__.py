# apps/domain/__init__.py
"""
Domain Layer - Pure Python Business Logic

This package contains the core business logic of the RAG chatbot system.
It has ZERO dependencies on Django, databases, or external services.

Key principles:
- Pure Python (no framework imports)
- Fully unit testable without infrastructure
- Independent of delivery mechanism (HTTP, WebSocket, CLI)
- Contains business rules and domain logic only
"""

__version__ = "1.0.0"