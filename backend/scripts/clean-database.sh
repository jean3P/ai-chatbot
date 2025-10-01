#!/bin/bash
# backend/scripts/clean-database.sh
# Clean development or test database

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to display usage
usage() {
    echo "Usage: $0 [dev|test|both]"
    echo ""
    echo "Clean database by removing all data"
    echo ""
    echo "Options:"
    echo "  dev   - Clean development database (port 5432)"
    echo "  test  - Clean test database (port 5433)"
    echo "  both  - Clean both databases"
    echo ""
    exit 1
}

# Function to clean database
clean_db() {
    local db_name=$1
    local db_user=$2
    local db_port=$3
    local db_pass=$4

    echo -e "${YELLOW}Cleaning $db_name...${NC}"

    PGPASSWORD=$db_pass psql -h localhost -p $db_port -U $db_user -d $db_name << EOF
-- Drop all data from application tables
TRUNCATE TABLE chat_message CASCADE;
TRUNCATE TABLE chat_conversation CASCADE;
TRUNCATE TABLE documents_documentchunk CASCADE;
TRUNCATE TABLE documents_document CASCADE;
TRUNCATE TABLE django_session CASCADE;

-- Reset sequences
SELECT setval('documents_document_id_seq', 1, false);
SELECT setval('chat_conversation_id_seq', 1, false);
SELECT setval('chat_message_id_seq', 1, false);

-- Verify
SELECT 'Documents' as table_name, COUNT(*) as count FROM documents_document
UNION ALL
SELECT 'Chunks', COUNT(*) FROM documents_documentchunk
UNION ALL
SELECT 'Conversations', COUNT(*) FROM chat_conversation
UNION ALL
SELECT 'Messages', COUNT(*) FROM chat_message;
EOF

    echo -e "${GREEN}✓ Cleaned $db_name${NC}"
}

# Check argument
if [ $# -eq 0 ]; then
    usage
fi

case "$1" in
    dev)
        echo -e "${RED}WARNING: This will delete ALL data from development database${NC}"
        read -p "Are you sure? (yes/no): " confirm
        if [ "$confirm" = "yes" ]; then
            clean_db "chatbot_dev" "chatbot_user" "5432" "dev_password_123"
        else
            echo "Cancelled"
            exit 0
        fi
        ;;
    test)
        clean_db "test_chatbot" "postgres" "5433" "postgres"
        ;;
    both)
        echo -e "${RED}WARNING: This will delete ALL data from BOTH databases${NC}"
        read -p "Are you sure? (yes/no): " confirm
        if [ "$confirm" = "yes" ]; then
            clean_db "chatbot_dev" "chatbot_user" "5432" "dev_password_123"
            clean_db "test_chatbot" "postgres" "5433" "postgres"
        else
            echo "Cancelled"
            exit 0
        fi
        ;;
    *)
        usage
        ;;
esac

echo ""
echo -e "${GREEN}Database cleaning complete!${NC}"