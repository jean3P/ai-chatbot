@echo off
REM backend/scripts/load-real-pdfs.bat
REM Clear seeded data and load real PDFs (Windows)

echo Clearing seeded data...
echo.

uv run python manage.py shell << EOF
from apps.documents.models import Document
from apps.chat.models import Conversation

doc_count = Document.objects.filter(description__startswith='[SEED]').count()
conv_count = Conversation.objects.filter(title__startswith='[SEED]').count()

Document.objects.filter(description__startswith='[SEED]').delete()
Conversation.objects.filter(title__startswith='[SEED]').delete()

print(f'Deleted {doc_count} seeded documents')
print(f'Deleted {conv_count} seeded conversations')
EOF

echo.
echo Processing real PDFs from backend\media\documents...
echo.

uv run python manage.py batch_upload_documents .\media\documents --process --language en --verbosity 2

echo.
echo Done! Real PDFs loaded and processed.
pause
