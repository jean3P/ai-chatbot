#!/bin/bash
# scripts/run-migrations.sh
# Helper script to run migrations with superuser privileges

set -e  # Exit on error

echo "=========================================="
echo "Running Django Migrations"
echo "=========================================="
echo ""
echo "⚠️  This script temporarily uses postgres superuser"
echo "   for schema modifications (migrations)."
echo ""

# Check if .env.local exists
if [ ! -f .env.local ]; then
    echo "❌ Error: .env.local not found"
    echo "   Copy .env.example to .env.local first"
    exit 1
fi

# Backup current DB_USER
ORIGINAL_USER=$(grep "^DB_USER=" .env.local | cut -d'=' -f2)
echo "Original DB_USER: $ORIGINAL_USER"

# Temporarily change to postgres for migrations
echo "Temporarily switching to postgres user..."
sed -i.bak 's/^DB_USER=.*/DB_USER=chatbot_user/' .env.local
sed -i.bak 's/^DB_PASSWORD=.*/DB_PASSWORD=dev_password_123/' .env.local

# Run migrations
echo ""
echo "Running migrations..."
python manage.py migrate

# Restore original user
echo ""
echo "Restoring original DB_USER..."
mv .env.local.bak .env.local

echo ""
echo "=========================================="
echo "✓ Migrations complete!"
echo "=========================================="
echo "Application will now use: $ORIGINAL_USER"
