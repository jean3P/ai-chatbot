# /backend/setup_rag.py

"""
RAG System Setup Script
Initializes the RAG system, processes documents, and sets up the vector store
"""
import os
import sys
import django
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.core.management import call_command
from django.conf import settings
from apps.documents.models import Document, DocumentChunk
from apps.rag.pipeline import rag_pipeline
from apps.rag.utils import validate_embeddings, get_vector_store
import logging

# Setup logging with Windows-compatible formatting
import sys

if sys.platform == "win32":
    # Windows-compatible logging without emojis
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
else:
    logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def create_directories():
    """Create necessary directories"""
    directories = [
        'media/documents',
        'logs',
        'staticfiles'
    ]

    for directory in directories:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        logger.info(f"[OK] Created directory: {directory}")


def run_migrations():
    """Run database migrations"""
    logger.info("Running database migrations...")
    try:
        call_command('migrate', verbosity=0)
        logger.info("[OK] Database migrations completed")
    except Exception as e:
        logger.error(f"[ERROR] Migration failed: {e}")
        return False
    return True


def create_superuser():
    """Create superuser if needed"""
    try:
        from django.contrib.auth.models import User
        if not User.objects.filter(is_superuser=True).exists():
            logger.info("Creating superuser...")
            call_command('createsuperuser', interactive=True)
        else:
            logger.info("✓ Superuser already exists")
    except Exception as e:
        logger.info(f"Superuser creation skipped: {e}")


def validate_environment():
    """Validate environment variables and configuration"""
    logger.info("Validating environment configuration...")

    required_vars = [
        'OPENROUTER_API_KEY',
        'SECRET_KEY'
    ]

    missing_vars = []
    for var in required_vars:
        if not getattr(settings, var, None):
            missing_vars.append(var)

    if missing_vars:
        logger.error(f"[ERROR] Missing required environment variables: {missing_vars}")
        logger.error("Please check your .env file")
        return False

    logger.info("[OK] Environment configuration valid")
    return True


def process_existing_documents():
    """Process any existing documents"""
    logger.info("Processing existing documents...")

    unprocessed_docs = Document.objects.filter(processed=False)
    count = unprocessed_docs.count()

    if count == 0:
        logger.info("[OK] No unprocessed documents found")
        return True

    logger.info(f"Found {count} unprocessed documents")

    try:
        call_command('process_documents', verbosity=1)
        logger.info("[OK] Document processing completed")
        return True
    except Exception as e:
        logger.error(f"[ERROR] Document processing failed: {e}")
        return False


def validate_rag_system():
    """Validate RAG system setup"""
    logger.info("Validating RAG system...")

    # Check embeddings
    validation_results = validate_embeddings()
    logger.info(f"[OK] Embedding validation: {validation_results}")

    # Test vector store
    try:
        vector_store = get_vector_store()
        logger.info(f"[OK] Vector store loaded: {vector_store.size()} embeddings")
    except Exception as e:
        logger.error(f"[ERROR] Vector store error: {e}")
        return False

    # Get system stats
    stats = rag_pipeline.get_document_stats()
    logger.info("[STATS] System Statistics:")
    for key, value in stats.items():
        logger.info(f"   {key}: {value}")

    return True


def setup_sample_documents():
    """Setup sample documents if none exist"""
    if Document.objects.exists():
        logger.info("[OK] Documents already exist")
        return

    logger.info("No documents found. You can add documents using:")
    logger.info("  python manage.py upload_document /path/to/your/document.pdf")
    logger.info("  Or use the Django admin at http://localhost:8000/admin/")


def main():
    """Main setup function"""
    logger.info(" Setting up RAG system...")
    logger.info("=" * 50)

    steps = [
        ("Creating directories", create_directories),
        ("Validating environment", validate_environment),
        ("Running migrations", run_migrations),
        ("Processing documents", process_existing_documents),
        ("Validating RAG system", validate_rag_system),
        ("Checking sample documents", setup_sample_documents),
    ]

    for step_name, step_func in steps:
        logger.info(f"\n {step_name}...")
        try:
            if callable(step_func):
                success = step_func()
                if success is False:
                    logger.error(f"✗ Failed: {step_name}")
                    sys.exit(1)
            else:
                step_func
        except Exception as e:
            logger.error(f"✗ Error in {step_name}: {e}")
            sys.exit(1)

    logger.info("\n" + "=" * 50)
    logger.info(" RAG system setup completed successfully!")
    logger.info("\nNext steps:")
    logger.info("1. Start the development server:")
    logger.info("   python manage.py runserver")
    logger.info("\n2. Upload documents:")
    logger.info("   python manage.py upload_document /path/to/document.pdf")
    logger.info("\n3. Test the chat interface:")
    logger.info("   http://localhost:8000/admin/ (admin interface)")
    logger.info("   http://localhost:3000/ (frontend)")
    logger.info("\n4. Monitor logs:")
    logger.info("   tail -f logs/chatbot.log")


if __name__ == "__main__":
    main()
