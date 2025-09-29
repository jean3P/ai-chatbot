# apps/domain/ports/__init__.py
"""
Ports - Interface Definitions (Dependency Inversion)

Ports define contracts between domain and infrastructure layers.
Domain depends on these interfaces, adapters implement them.

This enables:
- Domain testability (use fake implementations)
- Flexibility (swap implementations without changing domain)
- Clear boundaries (explicit dependencies)
"""