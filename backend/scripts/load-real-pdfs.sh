#!/bin/bash
# backend/scripts/load-real-pdfs.sh
# Clear seeded data and load real PDFs

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Clearing seeded data...${NC}"

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

echo ""
echo -e "${YELLOW}Processing real PDFs from backend/media/documents...${NC}"

uv run python manage.py batch_upload_documents \
    backend/media/documents \
    --process \
    --language en \
    --verbosity 2

echo ""
echo -e "${GREEN}Done! Real PDFs loaded and processed.${NC}"
