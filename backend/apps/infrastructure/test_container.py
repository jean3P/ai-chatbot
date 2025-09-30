# apps/infrastructure/test_container.py
"""
Script to test container configuration

Run with: python manage.py shell < apps/infrastructure/test_container.py
"""
import os

os.environ["ENVIRONMENT"] = "test"

from apps.infrastructure.config import get_config, get_environment
from apps.infrastructure.container import (create_chat_service,
                                           print_service_info)


def test_container():
    """Test container can create services"""
    print("=" * 60)
    print("TESTING DEPENDENCY INJECTION CONTAINER")
    print("=" * 60)

    # Show current environment
    env = get_environment()
    print(f"\nCurrent environment: {env}")

    # Get config
    config = get_config()
    print(f"\nConfiguration loaded: {list(config.keys())}")

    # Print service info
    print("\n")
    print_service_info(config)

    # Test creating chat service
    print("\nCreating ChatService...")
    try:
        service = create_chat_service(config, use_inmemory_repos=True)
        print(f"✓ ChatService created: {type(service).__name__}")
        print(f"✓ RAG Strategy: {type(service._rag_strategy).__name__}")
        print(f"✓ Message Repository: {type(service._message_repo).__name__}")
        print(f"✓ Conversation Repository: {type(service._conversation_repo).__name__}")

    except Exception as e:
        print(f"✗ Failed to create service: {e}")
        import traceback

        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("CONTAINER TEST PASSED")
    print("=" * 60)
    return True


if __name__ == "__main__":
    test_container()
