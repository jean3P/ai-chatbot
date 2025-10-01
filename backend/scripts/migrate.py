#!/usr/bin/env python
# backend/scripts/migrate.py
"""
Professional migration runner with automatic user switching
Usage: python scripts/migrate.py
"""
import os
import subprocess
import sys
from pathlib import Path

# Project root
BASE_DIR = Path(__file__).resolve().parent.parent


def run_migrations():
    """Run migrations with migration user, then switch back to runtime user"""

    # Store original credentials
    original_user = os.environ.get("DB_USER", "chatbot_app")
    original_password = os.environ.get("DB_PASSWORD", "")

    print("=" * 70)
    print("DATABASE MIGRATION MANAGER")
    print("=" * 70)
    print(f"\nOriginal user: {original_user}")
    print("Switching to migration user: chatbot_user\n")

    # Switch to migration user
    os.environ["DB_USER"] = "chatbot_user"
    os.environ["DB_PASSWORD"] = "dev_password_123"

    try:
        # Run migrations with UV
        result = subprocess.run(
            ["uv", "run", "python", "manage.py", "migrate"],
            cwd=BASE_DIR,
            check=True,
            capture_output=False,
        )

        print("\n" + "=" * 70)
        print("MIGRATIONS COMPLETED SUCCESSFULLY")
        print("=" * 70)

    except subprocess.CalledProcessError as e:
        print("\n" + "=" * 70)
        print("MIGRATION FAILED")
        print("=" * 70)
        sys.exit(1)

    finally:
        # Restore original credentials
        os.environ["DB_USER"] = original_user
        os.environ["DB_PASSWORD"] = original_password
        print(f"\nRestored user: {original_user}")
        print("\nApplication should use: chatbot_app")


if __name__ == "__main__":
    run_migrations()
