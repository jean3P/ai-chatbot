# AI Chatbot - Backend

Enterprise-grade Django backend for RAG-powered chatbot with pgvector semantic search, OpenRouter LLM integration, cost tracking, and rate limiting.

---

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Database Architecture](#database-architecture)
- [Configuration](#configuration)
- [Admin Access](#admin-access)
- [Running Migrations](#running-migrations)
- [Document Processing](#document-processing)
- [Data Management](#data-management)
- [Cost Management](#cost-management)
- [Rate Limiting](#rate-limiting)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Management Commands](#management-commands)
- [Scripts Reference](#scripts-reference)
- [API Endpoints](#api-endpoints)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [Project Structure](#project-structure)
- [License](#license)

---

## Overview

The Swisson AI Chatbot backend provides:

- **RAG Pipeline**: Document processing with semantic search using pgvector
- **LLM Integration**: OpenRouter API for multiple AI models
- **Citation System**: Structured citations with document metadata in responses
- **Cost Tracking**: Automatic logging of token usage and costs per request
- **Budget Enforcement**: Daily spending limits with automated alerts
- **Rate Limiting**: Configurable per-environment request throttling
- **Observability**: A/B testing, answer logging, and user feedback collection
- **WebSocket Support**: Real-time chat via Django Channels
- **Security**: Multi-user database architecture with principle of least privilege
- **Scalability**: Redis-backed task queue and caching

**Technology Stack:**
- Python 3.12+
- Django 5.2
- PostgreSQL 15 with pgvector extension
- Redis 7
- Docker & Docker Compose

---

## Prerequisites

### Required

- **Python 3.12+**
- **Docker & Docker Compose**
- **uv** (Python package manager)
  ```bash
  # Unix/Mac/Linux
  curl -LsSf https://astral.sh/uv/install.sh | sh
  
  # Windows (PowerShell)
  powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```

### Optional

- **psql** (PostgreSQL client) - For database management
- **curl** or **httpie** - For API testing
- **git** - Version control

---

## Quick Start

```bash
# 1. Clone repository
git clone <your-repo-url>
cd ai-chatbot/backend

# 2. Install dependencies
uv sync

# 3. Start services (PostgreSQL + Redis)
docker-compose up -d

# 4. Setup database users
psql -h localhost -U chatbot_user -d chatbot_dev -f scripts/create-app-user.sql
# Password: dev_password_123

# 5. Configure environment
cp .env.example .env.local
# Edit .env.local: Add SECRET_KEY, OPENROUTER_API_KEY, and budget settings

# 6. Run migrations
./scripts/run-migrations.sh  # Unix/Mac/Linux
scripts\run-migrations.bat   # Windows

# 7. Load documents (choose one):
# Option A: Load real PDFs
./scripts/load-real-pdfs.sh
# Option B: Generate test data
uv run python manage.py seed_database --size small

# 8. Start development server
uv run python manage.py runserver

# 9. Verify
curl http://localhost:8000/api/health/db
```

**Access Points:**
- API: http://localhost:8000/api/
- Admin: http://localhost:8000/admin/
- Health: http://localhost:8000/api/health/db

---

## Installation

### 1. Install uv Package Manager

```bash
# Verify installation
uv --version

# Should output: uv 0.x.x
```

### 2. Install Python Dependencies

```bash
cd backend

# Install all dependencies (including dev)
uv sync

# Production install (no dev dependencies)
uv sync --no-dev

# Activate virtual environment (optional - uv run does this automatically)
source .venv/bin/activate  # Unix/Mac/Linux
.venv\Scripts\activate     # Windows
```

### 3. Start Docker Services

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# Expected output:
# NAME                      STATUS    PORTS
# chatbot-postgres-dev      Up        0.0.0.0:5432->5432/tcp
# chatbot-postgres-test     Up        0.0.0.0:5433->5432/tcp
# chatbot-redis             Up        0.0.0.0:6379->6379/tcp

# View logs
docker-compose logs -f postgres-dev

# Stop services
docker-compose down
```

**Services:**
- **postgres-dev**: Development database (port 5432)
- **postgres-test**: Test database (port 5433, ephemeral)
- **redis**: Cache and message broker (port 6379)

---

## Database Architecture

### User Roles

The application uses **two database users** for security:

| User | Type | Used For | Permissions |
|------|------|----------|-------------|
| `chatbot_user` | Superuser | Migrations, schema changes | Full database access |
| `chatbot_app` | Restricted | Application runtime | CRUD only on app tables |

### Security Benefits

- **Principle of Least Privilege**: Application runs with minimal necessary permissions
- **Attack Surface Reduction**: Cannot drop tables, create users, or modify schema
- **SQL Injection Protection**: Limits damage from potential vulnerabilities
- **Audit Trail**: Separate users for different operations
- **Production-Ready**: Same pattern used in production environments

### Database Schema

```sql
-- Core Tables
documents_document           -- Document metadata
documents_documentchunk      -- Text chunks with vector embeddings
chat_conversation            -- User conversation history
chat_message                -- Messages with LLM responses and citations
chat_messagefeedback        -- User feedback on responses
chat_answerlog              -- Cost and performance tracking per request
core_experiment             -- A/B testing configurations

-- Auth & System
auth_user                   -- Django users (read-only for app)
django_migrations           -- Migration history
django_session             -- User sessions
```

### Connection Flow

```
┌─────────────────────┐
│ Django Application  │
└──────────┬──────────┘
           │
    ┌──────▼──────┐
    │ chatbot_app │ (Restricted)
    │ CRUD only   │
    └─────────────┘
           │
    ┌──────▼────────────┐
    │   PostgreSQL      │
    │   + pgvector      │
    └───────────────────┘
           ▲
    ┌──────┴──────┐
    │ chatbot_user│ (Superuser)
    │ Migrations  │
    └─────────────┘
```

### Setup Database Users

```bash
# Connect as superuser
psql -h localhost -U chatbot_user -d chatbot_dev
# Password: dev_password_123

# Run setup script (idempotent - safe to run multiple times)
\i scripts/create-app-user.sql

# Verify users
\du

# Expected output:
#                      List of roles
#   Role name   |            Attributes
# --------------+----------------------------------
#  chatbot_app  | Connection limit: 50
#  chatbot_user | Superuser, Create role, Create DB
#  postgres     | Superuser, Create role, Create DB

\q
```

**What the script does:**
- Creates `chatbot_app` user with password
- Grants CONNECT and USAGE on database and schema
- Grants SELECT, INSERT, UPDATE, DELETE on application tables
- Grants USAGE on sequences (for auto-increment IDs)
- Sets connection limit to 50
- DENIES: DROP, CREATE TABLE, ALTER, CREATE USER

**Verify permissions:**

```bash
psql -h localhost -U chatbot_app -d chatbot_dev -f scripts/test-app-user-permissions.sql
```

This runs comprehensive tests:
- ✓ INSERT, SELECT, UPDATE, DELETE work
- ✓ DROP TABLE denied
- ✓ CREATE TABLE denied
- ✓ ALTER TABLE denied
- ✓ CREATE USER denied

---

## Configuration

### Environment Files

- `.env.example` - Template with all variables (commit to git)
- `.env.local` - Your personal config (NEVER commit - in .gitignore)

### Setup Environment

```bash
# Copy template
cp .env.example .env.local

# Generate SECRET_KEY
uv run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Required Variables

Edit `.env.local`:

```bash
# Environment
ENVIRONMENT=development

# Database (application runtime)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=chatbot_dev
DB_USER=chatbot_app  # Restricted user
DB_PASSWORD=app_secure_password_change_in_production

# Django
DEBUG=True
SECRET_KEY=<your-generated-secret-key>

# Redis
REDIS_URL=redis://localhost:6379/0

# OpenRouter API (get from https://openrouter.ai/keys)
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxx
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# AI Models
DEFAULT_EMBEDDING_MODEL=text-embedding-3-small
DEFAULT_LLM_MODEL=gpt-4o-mini
MULTILINGUAL_LLM_MODEL=mistralai/mistral-7b-instruct

# Vector Database
PGVECTOR_ENABLED=true
EMBEDDING_DIMENSION=384  # Must match embedding model

# RAG Settings
MAX_CHUNK_SIZE=1200
CHUNK_OVERLAP=200
MAX_RETRIEVAL_CHUNKS=10
SIMILARITY_THRESHOLD=0.3

# Cost Management
DAILY_COST_BUDGET_USD=50.0
BUDGET_ALERT_THRESHOLD=0.8
BUDGET_ALERT_EMAIL=your-email@example.com

# CORS (for frontend)
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### Embedding Model Dimensions

| Model | Dimension | Use Case |
|-------|-----------|----------|
| `text-embedding-3-small` | 1536 | Balanced performance/cost |
| `text-embedding-3-large` | 3072 | Highest accuracy |
| `sentence-transformers/all-MiniLM-L6-v2` | 384 | Local/offline, no API costs |

**Important:** `EMBEDDING_DIMENSION` must match your chosen model.

---

## Admin Access

### Creating Admin User

The Django admin interface requires a superuser account:

```bash
# Create superuser
uv run python manage.py createsuperuser

# Follow prompts:
# Username: admin
# Email: admin@localhost
# Password: [choose secure password]
# Password (again): [confirm]
```

**Password Requirements:**
- Minimum 8 characters
- Cannot be too similar to username
- Cannot be entirely numeric
- Cannot be too common (e.g., "password123")

### Accessing Admin

```bash
# Start server
uv run python manage.py runserver

# Access admin panel
# http://localhost:8000/admin/
```

**Log in with your credentials**

The admin interface provides:
- **User management** (Authentication and Authorization)
- **Chat history** (Conversations, Messages, Message Feedback)
- **Document management** (Documents, Document chunks)
- **Observability** (Answer Logs, Experiments)
- Full database CRUD operations

### Resetting Forgotten Password

**Method 1: Change password in shell**

```bash
uv run python manage.py shell
```

```python
from django.contrib.auth.models import User

# Find user
user = User.objects.get(username='admin')

# Set new password
user.set_password('your-new-password')
user.save()

print(f"Password updated for {user.username}")
exit()
```

**Method 2: Use changepassword command**

```bash
uv run python manage.py changepassword admin
```

**Method 3: Delete and recreate superuser**

```bash
uv run python manage.py shell
```

```python
from django.contrib.auth.models import User

# Delete old user
User.objects.filter(username='admin').delete()
exit()
```

```bash
# Create new superuser
uv run python manage.py createsuperuser
```

### Security Best Practices

For development:
- Username: `admin` or your name
- Password: At least 12 characters, mixed case, numbers
- Email: Use real email if testing email features

For production:
- **Never use default credentials**
- Use strong unique passwords (20+ characters)
- Enable two-factor authentication
- Limit admin access to necessary users only
- Use separate admin accounts per person
- Monitor admin access logs

---

## Running Migrations

### Why Use Migration Scripts?

Migrations require **schema modification privileges** (CREATE TABLE, ALTER TABLE) which the restricted `chatbot_app` user doesn't have. The scripts handle this automatically.

### Running Migrations

**Unix/Mac/Linux:**

```bash
./scripts/run-migrations.sh
```

**Windows:**

```batch
scripts\run-migrations.bat
```

**What the script does:**

1. Backs up current `.env.local`
2. Temporarily switches to `chatbot_user` (superuser)
3. Runs `python manage.py migrate`
4. Restores `chatbot_app` user in `.env.local`

### Manual Migration (Advanced)

Only if scripts don't work:

```bash
# 1. Edit .env.local
DB_USER=chatbot_user
DB_PASSWORD=dev_password_123

# 2. Run migrations
uv run python manage.py migrate

# 3. Restore .env.local
DB_USER=chatbot_app
DB_PASSWORD=app_secure_password_change_in_production

# 4. Restart application
```

### Creating New Migrations

```bash
# 1. Make model changes
code apps/your_app/models.py

# 2. Generate migration
uv run python manage.py makemigrations

# 3. Review generated file
cat apps/your_app/migrations/0XXX_description.py

# 4. Check SQL that will run
uv run python manage.py sqlmigrate your_app 0XXX

# 5. Apply migration
./scripts/run-migrations.sh
```

### Migration Best Practices

✓ **Always review** migrations before applying  
✓ **Test locally** before staging/production  
✓ **Backup database** before production migrations  
✓ **Use migration scripts** for automatic user switching  
✓ **Check SQL** with `sqlmigrate` command  
✗ Don't manually edit migration files after creation  
✗ Don't skip migrations or run them out of order  

See [docs/database-migrations.md](docs/database-migrations.md) for comprehensive migration guide.

---

## Document Processing

### RAG Pipeline Overview

```
PDF Upload → Text Extraction → Chunking → Embedding → Vector Storage
    ↓            ↓                ↓           ↓            ↓
Document    Plain Text      512-1200     384/1536D    pgvector
Metadata    (PyMuPDF)       char chunks   vectors      similarity
```

### Processing Stages

1. **Upload**: Store PDF file and metadata in database
2. **Extract**: Parse PDF to extract text using PyMuPDF
3. **Chunk**: Split text into semantic chunks with overlap
4. **Embed**: Generate vector embeddings via OpenRouter API
5. **Store**: Save chunks with embeddings to pgvector for similarity search

### Management Commands

#### `batch_upload_documents` - Upload Multiple PDFs

Upload and optionally process all PDFs from a directory.

**Basic Usage:**

```bash
# Upload and process PDFs
uv run python manage.py batch_upload_documents \
    backend/media/documents \
    --process \
    --language en \
    --verbosity 2
```

**Options:**

```bash
--process              # Process immediately (extract, chunk, embed)
--language LANGUAGE    # Document language (en, de, fr, etc.)
--dry-run             # Preview without uploading
--overwrite           # Replace existing documents with same name
--verbosity {0,1,2,3} # Output detail level
```

**Examples:**

```bash
# Preview what would be uploaded
uv run python manage.py batch_upload_documents \
    /path/to/pdfs \
    --dry-run \
    --verbosity 2

# Upload without processing (process later)
uv run python manage.py batch_upload_documents \
    /path/to/pdfs \
    --language en

# Upload and process with overwrite
uv run python manage.py batch_upload_documents \
    /path/to/pdfs \
    --process \
    --overwrite \
    --language en \
    --verbosity 2
```

**Output:**

```
Processing directory: /path/to/pdfs
Found 5 PDF files

Uploading: Installation_Guide_v2.pdf
✓ Uploaded: Installation Guide v2 (ID: 123)
  Creating chunks and embeddings...
  ✓ Processed 45 chunks in 3.2s

Uploading: User_Manual.pdf
✓ Uploaded: User Manual (ID: 124)
  Creating chunks and embeddings...
  ✓ Processed 67 chunks in 4.8s

Summary:
  Uploaded: 5 documents
  Processed: 5 documents
  Total chunks: 234
  Total time: 18.4s
```

#### `process_documents` - Process Uploaded Documents

Process documents that have been uploaded but not yet processed.

**Basic Usage:**

```bash
# Process all unprocessed documents
uv run python manage.py process_documents --verbosity 2
```

**Options:**

```bash
--document-id ID      # Process specific document only
--reprocess          # Reprocess already processed documents
--batch-size N       # Number of documents to process at once
--verbosity {0,1,2,3}
```

**Examples:**

```bash
# Process specific document
uv run python manage.py process_documents \
    --document-id 42 \
    --verbosity 2

# Reprocess all documents (regenerate embeddings)
uv run python manage.py process_documents \
    --reprocess \
    --verbosity 2

# Process in batches of 10
uv run python manage.py process_documents \
    --batch-size 10 \
    --verbosity 2
```

**Output:**

```
Processing documents...

Processing: Installation Guide (ID: 42)
  Extracting text from PDF...
  ✓ Extracted 12,450 characters from 15 pages
  Creating chunks...
  ✓ Created 48 chunks
  Generating embeddings...
  ✓ Generated embeddings for 48 chunks
  Document processed successfully in 5.2s

Summary:
  Processed: 1 document
  Total chunks: 48
  Total time: 5.2s
```

### Typical Workflows

**Workflow 1: Upload and Process Together**

```bash
# One command - upload and process
uv run python manage.py batch_upload_documents \
    backend/media/documents \
    --process \
    --language en \
    --verbosity 2
```

**Workflow 2: Upload First, Process Later**

```bash
# Step 1: Upload only
uv run python manage.py batch_upload_documents \
    backend/media/documents \
    --language en

# Step 2: Review uploaded documents
uv run python manage.py shell
>>> from apps.documents.models import Document
>>> Document.objects.filter(processed=False)
>>> exit()

# Step 3: Process them
uv run python manage.py process_documents --verbosity 2
```

**Workflow 3: Selective Processing**

```bash
# Process specific document
uv run python manage.py process_documents \
    --document-id 42 \
    --verbosity 2
```

### Verifying Processing

```bash
uv run python manage.py shell
```

```python
from apps.documents.models import Document, DocumentChunk

# Check all documents
docs = Document.objects.all()
print(f"Total documents: {docs.count()}\n")

for doc in docs:
    chunks = DocumentChunk.objects.filter(document=doc)
    print(f"{doc.title}:")
    print(f"  Processed: {doc.processed}")
    print(f"  Chunks: {chunks.count()}")
    
    if chunks.exists():
        chunk = chunks.first()
        print(f"  Has embedding: {chunk.embedding is not None}")
        print(f"  Embedding dimension: {len(chunk.embedding) if chunk.embedding else 0}")
        print(f"  Sample text: {chunk.content[:80]}...")
        print(f"  Metadata: {chunk.metadata}")
    print()
```

### Troubleshooting Document Processing

**Issue: Documents not processing**

```bash
# Check for unprocessed documents
uv run python manage.py shell
>>> from apps.documents.models import Document
>>> Document.objects.filter(processed=False).count()
>>> exit()

# Process with verbose output
uv run python manage.py process_documents --verbosity 3
```

**Issue: Missing embeddings**

```python
from apps.documents.models import DocumentChunk

# Check for chunks without embeddings
missing = DocumentChunk.objects.filter(embedding__isnull=True)
print(f"Missing embeddings: {missing.count()}")

# Get document IDs
doc_ids = missing.values_list('document_id', flat=True).distinct()
print(f"Affected documents: {list(doc_ids)}")
```

Then reprocess:

```bash
uv run python manage.py process_documents \
    --document-id 42 \
    --verbosity 2
```

---

## Data Management

### Loading Real Documents

**Replace test data with real PDFs:**

```bash
# Unix/Mac/Linux
./scripts/load-real-pdfs.sh

# Windows
scripts\load-real-pdfs.bat
```

**What this does:**

1. Removes all seeded test data (identified by `[SEED]` prefix)
2. Uploads all PDFs from `backend/media/documents/`
3. Extracts text from PDFs
4. Creates semantic chunks
5. Generates embeddings
6. Stores in pgvector for similarity search

**Requirements:**
- Place PDF files in `backend/media/documents/`
- Ensure OpenRouter API key is configured
- Development server not required (offline script)

**Output:**

```
Clearing seeded data...
Deleted 5 seeded documents
Deleted 20 seeded conversations

Processing real PDFs from backend/media/documents...
Found 3 PDF files

Uploading: DMX_Splitter_Manual.pdf
✓ Processed: 67 chunks

Uploading: Installation_Guide.pdf
✓ Processed: 45 chunks

Uploading: Troubleshooting.pdf
✓ Processed: 38 chunks

Done! Real PDFs loaded and processed.
Total: 3 documents, 150 chunks
```

### Seeding Test Data

**For development and testing only** - generates realistic fake data.

**Basic Usage:**

```bash
# Small dataset (fast)
uv run python manage.py seed_database --size small

# Medium dataset
uv run python manage.py seed_database --size medium

# Large dataset
uv run python manage.py seed_database --size large
```

**Dataset Sizes:**

| Size | Documents | Chunks | Conversations | Messages | Time |
|------|-----------|--------|---------------|----------|------|
| Small | 5 | 250 | 20 | ~140-200 | <1s |
| Medium | 20 | 2,000 | 100 | ~800-1,200 | ~3s |
| Large | 50 | 10,000 | 500 | ~3,500-7,500 | ~15s |

**Options:**

```bash
--size {small,medium,large}  # Dataset size
--clear                      # Remove existing seed data first
--documents-only            # Seed only documents (no conversations)
--conversations-only        # Seed only conversations (no documents)
--environment {development,staging}  # Target environment
```

**Examples:**

```bash
# Clear existing seeds and create new small dataset
uv run python manage.py seed_database --size small --clear

# Seed only documents
uv run python manage.py seed_database --size medium --documents-only

# Seed only conversations
uv run python manage.py seed_database --size small --conversations-only

# Production prevention (will fail)
ENVIRONMENT=production uv run python manage.py seed_database
# ERROR: Cannot seed database in production environment
```

**Seeded Data Characteristics:**

**Documents:**
- Realistic titles: "DMX Splitter XPD-42 User Manual"
- Product lines: DMX Equipment, Ethernet DMX Node, DIN Rail
- Document types: manual, datasheet, quick_start, firmware_notes
- Prefixed with `[SEED]` for easy identification
- Random 384-dimension normalized embeddings

**Conversations:**
- Realistic titles: "How to configure DMX XPD-42?"
- Alternating user/assistant messages
- Assistant responses include citations to document chunks
- Metadata includes relevance scores

**Use Cases:**
- Local development without real PDFs
- UI/UX testing with data
- Performance testing
- Integration testing
- Demo environments

**Removing Seeded Data:**

```bash
# Method 1: Use --clear flag
uv run python manage.py seed_database --size small --clear

# Method 2: Use load-real-pdfs script (removes seeds automatically)
./scripts/load-real-pdfs.sh

# Method 3: Manual removal via shell
uv run python manage.py shell
>>> from apps.documents.models import Document
>>> from apps.chat.models import Conversation
>>> Document.objects.filter(description__startswith='[SEED]').delete()
>>> Conversation.objects.filter(title__startswith='[SEED]').delete()
```

### Cleaning Databases

**Clean development database:**

```bash
# Unix/Mac/Linux
./scripts/clean-database.sh dev

# Windows
scripts\clean-database.bat dev
```

**Confirmation prompt:**

```
WARNING: This will delete ALL data from development database
Are you sure? (yes/no): yes

Cleaning chatbot_dev...
TRUNCATE TABLE chat_message CASCADE;
TRUNCATE TABLE chat_conversation CASCADE;
TRUNCATE TABLE documents_documentchunk CASCADE;
TRUNCATE TABLE documents_document CASCADE;

✓ Cleaned chatbot_dev

Database cleaning complete!
```

**Clean test database:**

```bash
./scripts/clean-database.sh test
```

**Clean both databases:**

```bash
./scripts/clean-database.sh both
```

**What it does:**
- Removes all data from application tables
- Preserves schema (tables, columns, constraints)
- Resets auto-increment sequences
- Does NOT remove migrations or users
- Requires confirmation for development database

**When to use:**
- Start fresh development
- Reset after testing
- Clear corrupted data
- Prepare for real data load

---

## Cost Management

The system automatically tracks LLM usage costs and enforces daily budget limits.

### Configuration

Set budget in `.env.local`:

```bash
# Cost Management
DAILY_COST_BUDGET_USD=50.0           # Daily spending limit
BUDGET_ALERT_THRESHOLD=0.8            # Alert at 80% of budget
BUDGET_ALERT_EMAIL=admin@example.com  # Email for alerts
```

### Automatic Cost Tracking

Every LLM request is automatically logged to the `AnswerLog` table with:

- **Token counts**: prompt_tokens, completion_tokens, total_tokens
- **Model used**: LLM model and embedding model
- **Cost calculation**: Estimated USD cost based on model pricing
- **Performance**: Total latency, retrieval time, generation time
- **Quality metrics**: Chunks retrieved, citations count, similarity scores
- **Error tracking**: Had error, error type, error message

### Budget Enforcement

Budget is checked **before each request**:

1. **Normal** (< 80%): Requests proceed normally
2. **Warning** (80-99%): Warning logged, requests continue
3. **Critical** (≥ 100%): Requests **blocked** with error message

**When budget exceeded:**

```json
{
  "error": "Daily cost budget exceeded. Please try again tomorrow or contact support.",
  "budget_status": {
    "total_cost": 52.45,
    "daily_budget": 50.0,
    "budget_used_pct": 104.9
  }
}
```

### Cost Reports

Generate cost reports with the `cost_report` management command:

**Basic Usage:**

```bash
# Today's costs
uv run python manage.py cost_report

# Last 7 days
uv run python manage.py cost_report --days 7

# Breakdown by model
uv run python manage.py cost_report --days 7 --by-model

# Breakdown by RAG method
uv run python manage.py cost_report --days 7 --by-method

# Export to CSV
uv run python manage.py cost_report --days 30 --export-csv costs.csv
```

**Example Output:**

```
======================================================================
Cost Report: 2025-01-01 to 2025-01-07
======================================================================

Total Requests: 1,234
Total Cost: $12.45
Total Tokens: 1,456,789
Average Latency: 850ms
Cost per Request: $0.0101

----------------------------------------------------------------------
Breakdown by Model:
----------------------------------------------------------------------

gpt-4o-mini:
  Requests: 1,100
  Cost: $10.20
  Tokens: 1,200,000
  Avg Cost/Request: $0.0093

mistralai/mistral-7b-instruct:
  Requests: 134
  Cost: $2.25
  Tokens: 256,789
  Avg Cost/Request: $0.0168

----------------------------------------------------------------------
Daily Breakdown:
----------------------------------------------------------------------
2025-01-01: 180 requests, $1.85
2025-01-02: 165 requests, $1.62
2025-01-03: 190 requests, $1.98
2025-01-04: 175 requests, $1.75
2025-01-05: 210 requests, $2.15
2025-01-06: 158 requests, $1.55
2025-01-07: 156 requests, $1.55

======================================================================
Today's Budget: $3.42 / $50.00
✓ Budget usage: 6.8%
======================================================================
```

### Monitoring via Django Admin

Access cost tracking in Django Admin:

1. Navigate to **http://localhost:8000/admin/**
2. Go to **CHAT > Answer logs**
3. Filter by date, method, model, or error status
4. View detailed metrics for each request

**Admin Features:**
- Filter by date range, model, method, language
- Search by query text or error messages
- Sort by cost, latency, or tokens
- Export selected records to CSV
- View aggregate statistics

### Model Pricing

The system tracks costs for common models:

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|------------------------|
| `gpt-4o-mini` | $0.150 | $0.600 |
| `gpt-4o` | $2.50 | $10.00 |
| `claude-3-5-sonnet` | $3.00 | $15.00 |
| `mistralai/mistral-7b-instruct` | $0.20 | $0.20 |
| `text-embedding-3-small` | $0.020 | $0.00 |

**Update pricing**: Edit `apps/infrastructure/pricing.py`

### Budget Alerts

When budget threshold is reached, the system:

1. **Logs warning** to application logs
2. **Sends email** to configured address (if set)
3. **Continues serving** requests (warning level)
4. **Blocks requests** when 100% exceeded (critical level)

**Email Alert Example:**

```
Subject: 🚨 Budget Alert: WARNING

Budget Alert for 2025-01-15

Current Status:
- Total Cost: $42.50
- Daily Budget: $50.00
- Budget Used: 85.0%
- Requests: 1,456

Alert Level: WARNING

View detailed report:
python manage.py cost_report --days 1 --by-model
```

### Best Practices

**Development:**
- Set reasonable daily budgets ($10-50)
- Monitor costs weekly with reports
- Review expensive queries in admin

**Production:**
- Set strict budgets based on expected traffic
- Configure email alerts for team notification
- Export daily reports for accounting
- Monitor cost per request trends
- Implement user-level cost tracking (future enhancement)

### Cost Optimization Tips

1. **Use cheaper models**: `gpt-4o-mini` vs `gpt-4o` saves ~90%
2. **Reduce chunk retrieval**: Lower `MAX_RETRIEVAL_CHUNKS` setting
3. **Limit max tokens**: Set lower `max_tokens` for responses
4. **Cache common queries**: Implement result caching (future)
5. **Monitor expensive queries**: Review high-cost requests in admin

---

## Rate Limiting

The system enforces request rate limits to prevent abuse and control costs.

### Configuration

Rate limits are configured per environment in `apps/infrastructure/rate_limit.py`:

| Environment | Anonymous | Authenticated | Chat Endpoint | Uploads |
|-------------|-----------|---------------|---------------|---------|
| **Development** | 100/min | 1,000/hour | 50/min | 10/hour |
| **Staging** | 100/min | 1,000/hour | 50/min | 10/hour |
| **Production** | 100/min | 1,000/hour | 50/min | 10/hour |
| **Test** | 1,000/min | 10,000/hour | - | - |

### Rate Limit Types

**1. Anonymous Rate Limit**
- Based on IP address
- Applies to unauthenticated requests
- Default: 100 requests per minute

**2. User Rate Limit**
- Based on authenticated user ID
- Higher limits for logged-in users
- Default: 1,000 requests per hour

**3. Endpoint-Specific Limits**
- **Chat endpoints** (`/api/chat/`): 50/min (expensive LLM calls)
- **Upload endpoints** (`/api/documents/upload/`): 10/hour (prevents storage abuse)
- **Burst protection**: 20 requests/min across all endpoints

### Rate Limit Response

When limit exceeded, API returns `429 Too Many Requests`:

```json
{
  "error": "Rate limit exceeded",
  "message": "Too many requests. Please try again in 42 seconds.",
  "retry_after": 42
}
```

**Response Headers:**

```
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 60
Retry-After: 42
```

### Rate Limit Headers

All responses include rate limit information:

- **X-RateLimit-Limit**: Total requests allowed in period
- **X-RateLimit-Remaining**: Requests remaining in current period
- **X-RateLimit-Reset**: Seconds until limit resets
- **Retry-After**: Seconds to wait (only on 429 responses)

### Testing Rate Limits

```bash
# Test anonymous rate limit
for i in {1..110}; do
  curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/
done

# Expected: 100x 200 OK, then 10x 429

# Check headers
curl -I http://localhost:8000/api/
```

### Bypassing Rate Limits (Development)

Temporarily disable in `.env.local`:

```bash
# This doesn't exist yet but shows intent
RATE_LIMIT_ENABLED=False
```

Or clear rate limit cache:

```bash
uv run python manage.py clear_rate_limits
```

### Managing Rate Limits

**View rate limit usage:**

```bash
# In Django shell
uv run python manage.py shell
```

```python
from django.core.cache import cache

# Check specific IP
ip = "192.168.1.1"
count = cache.get(f"rate_limit:ip:{ip}:min")
print(f"Requests this minute: {count}")
```

**Clear rate limits:**

```bash
# Clear all rate limits
uv run python manage.py clear_rate_limits

# Clear specific identifier
uv run python manage.py clear_rate_limits --identifier ip:192.168.1.1
```

### Production Considerations

**Adjust limits for production:**

1. Monitor actual traffic patterns
2. Set conservative initial limits
3. Gradually increase based on usage
4. Consider user tiers (free/paid)
5. Implement IP whitelisting for trusted sources

**Example production config:**

```python
# apps/infrastructure/rate_limit.py
RATE_LIMIT_CONFIGS = {
    "production": {
        "enabled": True,
        "anon_rate": "60/min",        # Stricter
        "user_rate": "500/hour",      # Adjusted for avg user
        "chat_rate": "30/min",        # Limit expensive operations
        "upload_rate": "5/hour",      # Prevent storage abuse
        "burst_rate": "10/min",       # Tighter burst control
    }
}
```

---

## Development Workflow

### Daily Development

```bash
# 1. Start services
docker-compose up -d

# 2. Activate virtual environment (optional)
source .venv/bin/activate  # Unix/Mac
.venv\Scripts\activate     # Windows

# 3. Start Django development server
uv run python manage.py runserver

# 4. Make code changes
# Edit files...

# 5. If models changed, create migration
uv run python manage.py makemigrations
./scripts/run-migrations.sh

# 6. Run tests
uv run pytest apps/ -v

# 7. Format code
uv run black .
uv run isort .
```

### Code Quality

```bash
# Format code automatically
uv run black .
uv run isort .

# Check formatting without changes
uv run black --check .
uv run isort --check-only .

# Run linters (if configured)
uv run flake8 apps/
uv run pylint apps/
```

### Django Management Commands

```bash
# Interactive Python shell
uv run python manage.py shell

# Database shell (PostgreSQL)
uv run python manage.py dbshell

# Create admin superuser
uv run python manage.py createsuperuser

# Collect static files
uv run python manage.py collectstatic

# Show installed apps
uv run python manage.py showmigrations

# Check for issues
uv run python manage.py check
```

### Inspecting Database

```bash
# Connect to database
psql -h localhost -U chatbot_app -d chatbot_dev
# Password: app_secure_password_change_in_production
```

```sql
-- List tables
\dt

-- Describe table structure
\d documents_document

-- List all users
\du

-- List installed extensions
\dx

-- Check data counts
SELECT 
  'documents' as table_name, 
  COUNT(*) as count 
FROM documents_document
UNION ALL
SELECT 'chunks', COUNT(*) FROM documents_documentchunk
UNION ALL
SELECT 'conversations', COUNT(*) FROM chat_conversation
UNION ALL
SELECT 'messages', COUNT(*) FROM chat_message;

-- Check embedding dimensions
SELECT 
  array_length(embedding, 1) as dimension,
  COUNT(*) as count
FROM documents_documentchunk
WHERE embedding IS NOT NULL
GROUP BY array_length(embedding, 1);

-- Exit
\q
```

---

## Testing

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with output
uv run pytest -v

# Run specific app
uv run pytest apps/core/tests/ -v

# Run specific test file
uv run pytest apps/core/tests/test_health_check.py -v

# Run specific test
uv run pytest apps/core/tests/test_health_check.py::TestDatabaseHealthCheck::test_health_check_success -v

# Run with coverage
uv run pytest --cov=apps --cov-report=html

# Open coverage report
open htmlcov/index.html  # Mac
xdg-open htmlcov/index.html  # Linux
start htmlcov\index.html  # Windows
```
**Note:** Test database migrations run automatically via pytest fixtures.

### Manual Test Database Setup (if needed)
```bash
uv run python manage.py migrate --settings=config.settings.test
```

### Test Database

Tests automatically use ephemeral test database on port 5433:

```bash
# Start test database
docker-compose up -d postgres-test

# Run tests (automatically use test database)
uv run pytest

# Tests configuration
# - Settings: config/settings/test.py
# - Database: test_chatbot (port 5433)
# - Data: tmpfs (in-memory, wiped on restart)
```

### Writing Tests

```python
# apps/your_app/tests/test_example.py
import pytest
from django.urls import reverse
from apps.documents.models import Document

@pytest.mark.django_db
class TestDocumentFeature:
    """Test document functionality"""
    
    def test_create_document(self):
        """Test document creation"""
        doc = Document.objects.create(
            title="Test Document",
            document_type="manual",
            language="en"
        )
        assert doc.id is not None
        assert doc.title == "Test Document"
    
    def test_api_endpoint(self, client):
        """Test API endpoint"""
        response = client.get(reverse('documents:list'))
        assert response.status_code == 200
```

### Test Configuration

- **Pytest config**: `pytest.ini`
- **Django settings**: `config/settings/test.py`
- **Fixtures**: `conftest.py`
- **Markers**: Use `@pytest.mark.django_db` for database tests

---

## Management Commands

### Document Management

| Command | Purpose | Example |
|---------|---------|---------|
| `batch_upload_documents` | Upload multiple PDFs | `uv run python manage.py batch_upload_documents /path --process` |
| `process_documents` | Process uploaded PDFs | `uv run python manage.py process_documents --verbosity 2` |
| `regenerate_embeddings` | Regenerate embeddings | `uv run python manage.py regenerate_embeddings` |

### Data Management

| Command | Purpose | Example |
|---------|---------|---------|
| `seed_database` | Generate test data | `uv run python manage.py seed_database --size small --clear` |

### Cost & Monitoring

| Command | Purpose | Example |
|---------|---------|---------|
| `cost_report` | Generate cost report | `uv run python manage.py cost_report --days 7 --by-model` |
| `clear_rate_limits` | Clear rate limit cache | `uv run python manage.py clear_rate_limits` |

### Django Built-in

| Command | Purpose | Example |
|---------|---------|---------|
| `runserver` | Start development server | `uv run python manage.py runserver 8080` |
| `migrate` | Apply migrations | Use `./scripts/run-migrations.sh` instead |
| `makemigrations` | Create migrations | `uv run python manage.py makemigrations` |
| `createsuperuser` | Create admin user | `uv run python manage.py createsuperuser` |
| `shell` | Python shell | `uv run python manage.py shell` |
| `dbshell` | Database shell | `uv run python manage.py dbshell` |
| `showmigrations` | List migrations | `uv run python manage.py showmigrations` |
| `check` | Check for issues | `uv run python manage.py check` |
| `collectstatic` | Collect static files | `uv run python manage.py collectstatic` |

### Getting Command Help

```bash
# List all commands
uv run python manage.py --help

# Get help for specific command
uv run python manage.py batch_upload_documents --help
uv run python manage.py process_documents --help
uv run python manage.py cost_report --help
```

---

## Scripts Reference

### Database Setup Scripts (SQL)

| Script | Purpose | Usage |
|--------|---------|-------|
| `create-app-user.sql` | Create restricted `chatbot_app` user | `psql -U chatbot_user -d chatbot_dev -f scripts/create-app-user.sql` |
| `test-app-user-permissions.sql` | Verify user permissions work correctly | `psql -U chatbot_app -d chatbot_dev -f scripts/test-app-user-permissions.sql` |
| `init-db.sql` | Initialize extensions (auto-run on container start) | Automatic via Docker entrypoint |

### Migration Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `run-migrations.sh` | Run migrations with superuser (Unix/Mac/Linux) | `./scripts/run-migrations.sh` |
| `run-migrations.bat` | Run migrations with superuser (Windows) | `scripts\run-migrations.bat` |

### Data Management Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `clean-database.sh` | Clean dev/test databases (Unix/Mac/Linux) | `./scripts/clean-database.sh [dev\|test\|both]` |
| `clean-database.bat` | Clean dev/test databases (Windows) | `scripts\clean-database.bat [dev\|test\|both]` |
| `load-real-pdfs.sh` | Load real PDFs, remove seed data (Unix/Mac/Linux) | `./scripts/load-real-pdfs.sh` |
| `load-real-pdfs.bat` | Load real PDFs, remove seed data (Windows) | `scripts\load-real-pdfs.bat` |

### Script Examples

**Initial Setup:**

```bash
# Create database user
psql -h localhost -U chatbot_user -d chatbot_dev -f scripts/create-app-user.sql

# Run migrations
./scripts/run-migrations.sh

# Load documents
./scripts/load-real-pdfs.sh
```

**Clean and Reload:**

```bash
# Clean database
./scripts/clean-database.sh dev

# Load fresh data
./scripts/load-real-pdfs.sh
```

**Verify Security:**

```bash
# Test that restricted user cannot perform admin operations
psql -h localhost -U chatbot_app -d chatbot_dev -f scripts/test-app-user-permissions.sql
```

---

## API Endpoints

### Health Check

**Endpoint:** `GET /api/health/db`

**Purpose:** Database connectivity check for load balancers and monitoring

**Response (Healthy):**

```json
{
  "status": "healthy",
  "latency_ms": 12.34,
  "database": "chatbot_dev"
}
```

**Response (Unhealthy):**

```json
{
  "status": "unhealthy",
  "error": "connection timeout",
  "latency_ms": 5000.0
}
```

**Status Codes:**
- `200` - Database healthy
- `503` - Database unreachable

**Features:**
- 5-second timeout
- Logs warning if latency > 100ms
- No-cache headers (for load balancers)

**Usage:**

```bash
curl http://localhost:8000/api/health/db

# With timeout
curl --max-time 6 http://localhost:8000/api/health/db

# Monitor in loop
while true; do curl -s http://localhost:8000/api/health/db | jq; sleep 5; done
```

### Chat API

| Endpoint | Method | Purpose | Notes |
|----------|--------|---------|-------|
| `/api/chat/conversations/` | GET | List conversations | Filter by session_id |
| `/api/chat/conversations/` | POST | Create conversation | Auto-creates on first message |
| `/api/chat/conversations/{id}/` | GET | Get conversation details | Includes all messages |
| `/api/chat/conversations/{id}/` | DELETE | **Delete conversation** | ** Cascade deletes messages** |
| `/api/chat/conversations/{id}/messages/` | POST | Send message | Returns AI response with citations |
| `/api/chat/feedback/` | POST | Submit feedback | User feedback on responses |

### Delete Conversation Endpoint 

**Endpoint:** `DELETE /api/chat/conversations/{id}/`

**Purpose:** Delete a conversation and all its messages

**Headers:**
```
X-Session-ID: your-session-id  (optional but recommended)
```

**Success Response (204):**
```
No content - conversation deleted successfully
```

**Error Responses:**

```json
// 404 Not Found - Conversation doesn't exist
{
  "error": "Conversation not found"
}

// 403 Forbidden - Wrong session ID
{
  "error": "You do not have permission to delete this conversation"
}
```

**Usage Examples:**

```bash
# Delete with session validation
curl -X DELETE \
  -H "X-Session-ID: abc123" \
  http://localhost:8000/api/chat/conversations/550e8400-e29b-41d4-a716-446655440000/

# Delete without session validation (works if no session set)
curl -X DELETE \
  http://localhost:8000/api/chat/conversations/550e8400-e29b-41d4-a716-446655440000/
```

**Features:**
- Cascade deletes all related messages automatically
- Optional session validation for security
- Returns 204 No Content on success
- Returns 404 if conversation doesn't exist
- Returns 403 if session ID mismatch

### Citation Data in Responses 

Chat responses now include structured citation metadata:

**Response Format:**

```json
{
  "success": true,
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "role": "assistant",
    "content": "According to the XPD-42 Manual, Page 15...",
    "citations": [
      {
        "document_title": "XPD-42 User Manual",
        "page_number": 15,
        "chunk_text": "Connect the DMX input cable to port 1...",
        "chunk_id": "770e8400-e29b-41d4-a716-446655440002",
        "document_id": "880e8400-e29b-41d4-a716-446655440003",
        "relevance_score": 0.89,
        "section_title": "Installation"
      }
    ],
    "created_at": "2025-01-15T10:30:00Z"
  }
}
```

**Citation Fields:**
- `document_title`: Human-readable document name
- `page_number`: Page where information was found
- `chunk_text`: Preview of cited content (max 500 chars)
- `chunk_id`: UUID for retrieving full chunk
- `document_id`: UUID for retrieving full document
- `relevance_score`: Similarity score (0.0-1.0)
- `section_title`: Section within document (if available)

### Documents API

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/documents/` | GET | List documents |
| `/api/documents/upload/` | POST | Upload document |
| `/api/documents/{id}/` | GET | Get document details |
| `/api/documents/{id}/` | DELETE | Delete document |

---

## Deployment

### Environment-Specific Settings

**Development:**
```bash
ENVIRONMENT=development
DEBUG=True
DB_USER=chatbot_app
ALLOWED_HOSTS=localhost,127.0.0.1
DAILY_COST_BUDGET_USD=50.0
```

**Staging:**
```bash
ENVIRONMENT=staging
DEBUG=False
DB_USER=chatbot_app
DB_HOST=<rds-endpoint>
ALLOWED_HOSTS=staging.yourdomain.com
DAILY_COST_BUDGET_USD=200.0
```

**Production:**
```bash
ENVIRONMENT=production
DEBUG=False
DB_USER=chatbot_app
DB_HOST=<rds-endpoint>
ALLOWED_HOSTS=yourdomain.com
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
DAILY_COST_BUDGET_USD=500.0
BUDGET_ALERT_EMAIL=alerts@yourdomain.com
```

### Pre-Deployment Checklist

- [ ] Set `DEBUG=False`
- [ ] Generate new `SECRET_KEY`
- [ ] Use strong database passwords
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Enable SSL/HTTPS
- [ ] Set production budget limits
- [ ] Configure email alerts
- [ ] Setup error monitoring (Sentry)
- [ ] Configure S3 for media files
- [ ] Setup automated backups
- [ ] Review security settings
- [ ] Test migrations in staging
- [ ] Test rate limits
- [ ] Document rollback procedure

### Deployment Commands

```bash
# Check deployment readiness
python manage.py check --deploy

# Collect static files
python manage.py collectstatic --noinput

# Run migrations (use superuser temporarily)
python manage.py migrate

# Verify health
curl https://api.yourdomain.com/api/health/db

# Generate initial cost report
python manage.py cost_report --days 1
```

### Additional Resources

- [Database Migrations Guide](docs/database-migrations.md)
- [Backup & Restore Procedures](docs/database-backup-restore.md)

---

## Troubleshooting

### Permission Denied on Migrations

**Error:**
```
django.db.utils.ProgrammingError: permission denied for schema public
```

**Cause:** Running migrations with restricted `chatbot_app` user

**Solution:**
```bash
# Use migration script (automatically switches to superuser)
./scripts/run-migrations.sh
```

### Database Connection Failed

**Error:**
```
psycopg2.OperationalError: connection to server at "localhost", port 5432 failed
```

**Solutions:**

```bash
# Check if database is running
docker-compose ps

# Start database
docker-compose up -d postgres-dev

# Check logs
docker-compose logs postgres-dev

# Verify connection manually
psql -h localhost -p 5432 -U chatbot_user -d chatbot_dev
```

### Password Authentication Failed

**Error:**
```
FATAL: password authentication failed for user "chatbot_app"
```

**Solutions:**

```bash
# Verify user exists
psql -h localhost -U chatbot_user -d chatbot_dev -c "\du chatbot_app"

# Recreate user if missing
psql -h localhost -U chatbot_user -d chatbot_dev -f scripts/create-app-user.sql

# Check .env.local has correct password
grep DB_PASSWORD .env.local
```

### Port Already in Use

**Error:**
```
Error: That port is already in use
```

**Solutions:**

```bash
# Find process using port (Unix/Mac)
lsof -i :8000

# Find process using port (Windows)
netstat -ano | findstr :8000

# Kill process or use different port
uv run python manage.py runserver 8080
```

### pgvector Extension Not Found

**Error:**
```
psycopg2.errors.UndefinedObject: type "vector" does not exist
```

**Solution:**

```bash
# Install extension (as superuser)
psql -h localhost -U chatbot_user -d chatbot_dev -c "CREATE EXTENSION vector;"

# Verify
psql -h localhost -U chatbot_user -d chatbot_dev -c "\dx"
```

### Documents Not Processing

**Check unprocessed documents:**

```python
from apps.documents.models import Document

unprocessed = Document.objects.filter(processed=False)
print(f"Unprocessed: {unprocessed.count()}")

for doc in unprocessed:
    print(f"- {doc.title} (ID: {doc.id})")
```

**Process them:**

```bash
uv run python manage.py process_documents --verbosity 2
```

### Missing Embeddings

**Check for missing embeddings:**

```python
from apps.documents.models import DocumentChunk

missing = DocumentChunk.objects.filter(embedding__isnull=True)
print(f"Missing embeddings: {missing.count()}")

# Get affected documents
doc_ids = missing.values_list('document_id', flat=True).distinct()
print(f"Affected documents: {list(doc_ids)}")
```

**Regenerate:**

```bash
# Reprocess specific document
uv run python manage.py process_documents --document-id 42 --verbosity 2

# Or reprocess all
uv run python manage.py process_documents --reprocess
```

### Redis Connection Failed

**Error:**
```
redis.exceptions.ConnectionError: Error connecting to Redis
```

**Solution:**

```bash
# Start Redis
docker-compose up -d redis

# Check logs
docker-compose logs redis

# Verify manually
redis-cli ping
# Should return: PONG
```

### Import Errors

**Error:**
```
ModuleNotFoundError: No module named 'apps'
```

**Solutions:**

```bash
# Use uv run (recommended)
uv run python manage.py runserver

# Or activate virtual environment
source .venv/bin/activate  # Unix/Mac
.venv\Scripts\activate     # Windows
python manage.py runserver
```

### Rate Limit Issues

**Error:**
```
429 Too Many Requests
```

**Check rate limit status:**

```bash
# View headers
curl -I http://localhost:8000/api/

# Output shows:
# X-RateLimit-Limit: 100
# X-RateLimit-Remaining: 0
# Retry-After: 42
```

**Solutions:**

```bash
# Wait for the time specified in Retry-After header
# Or clear rate limits (development only)
uv run python manage.py clear_rate_limits

# Or for specific IP
uv run python manage.py clear_rate_limits --identifier ip:192.168.1.1
```

### Budget Exceeded Errors

**Error:**
```json
{
  "error": "Daily cost budget exceeded. Please try again tomorrow or contact support."
}
```

**Check budget status:**

```bash
# Run cost report
uv run python manage.py cost_report

# View in Django admin
# http://localhost:8000/admin/ -> CHAT -> Answer logs
```

**Solutions:**

```bash
# Option 1: Increase budget in .env.local
DAILY_COST_BUDGET_USD=100.0

# Option 2: Wait until next day (resets at midnight UTC)

# Option 3: Clear cost tracking (development only - loses data)
./scripts/clean-database.sh dev
```

---

## Project Structure

```
backend/
├── apps/                           # Django applications
│   ├── adapters/                   # External service integrations
│   │   ├── embeddings/            # Embedding model adapters
│   │   ├── llm/                   # LLM provider adapters
│   │   ├── parsing/               # Document parsing
│   │   ├── repositories/          # Data access layer
│   │   └── retrieval/             # Vector store implementations
│   ├── chat/                      # Chat functionality
│   │   ├── migrations/
│   │   ├── __init__.py
│   │   ├── admin.py               # Admin for conversations, messages, feedback, answer logs
│   │   ├── apps.py
│   │   ├── consumers.py           # WebSocket consumers
│   │   ├── models.py              # Conversation, Message, MessageFeedback, AnswerLog
│   │   ├── routing.py
│   │   ├── serializers.py         # Enhanced with citation data
│   │   ├── urls.py
│   │   └── views.py               # DELETE conversation endpoint, citation support
│   ├── core/                      # Core utilities
│   │   ├── management/
│   │   │   └── commands/
│   │   │       ├── seed_database.py
│   │   │       ├── cost_report.py     #  Generate cost reports
│   │   │       └── clear_rate_limits.py #  Clear rate limit cache
│   │   ├── tests/
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── budget_monitor.py      #  Budget enforcement
│   │   ├── exceptions.py
│   │   ├── middleware.py          #  Rate limiting middleware
│   │   ├── models.py              #  Experiment model
│   │   ├── throttling.py          #  DRF throttle classes
│   │   ├── urls.py
│   │   ├── utils.py
│   │   └── views.py               # Health checks
│   ├── documents/                 # Document management
│   │   ├── migrations/
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py              # Document, DocumentChunk
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   └── views.py
│   ├── domain/                    # Business logic (DDD)
│   │   ├── ports/                 # Interface definitions
│   │   ├── prompts/
│   │   ├── services/
│   │   │   └── chat_service.py    # Enhanced with cost tracking
│   │   ├── strategies/
│   │   ├── __init__.py
│   │   └── models.py              # Domain entities
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── container.py           # Dependency injection
│   │   ├── pricing.py             #  Model pricing configuration
│   │   └── rate_limit.py          #  Rate limit configuration
│   └── rag/                       # RAG pipeline
│       ├── management/
│       │   └── commands/
│       │       ├── batch_upload_documents.py
│       │       ├── process_documents.py
│       │       └── regenerate_embeddings.py
│       ├── __init__.py
│       ├── apps.py
│       ├── pipeline.py
│       ├── processors.py
│       └── utils.py
├── config/                        # Django configuration
│   ├── settings/                  # Environment-specific settings
│   │   ├── __init__.py
│   │   ├── base.py               # Enhanced with cost/rate limit settings
│   │   ├── databases.py          # Database configuration
│   │   ├── development.py        # Development overrides
│   │   └── test.py               # Test settings
│   ├── __init__.py
│   ├── asgi.py                   # ASGI entry point
│   ├── urls.py                   # URL routing
│   └── wsgi.py                   # WSGI entry point
├── docs/                          # Documentation
│   ├── database-migrations.md
│   └── database-backup-restore.md
├── media/                         # User uploads
│   └── documents/                # PDF files
├── scripts/                       # Utility scripts
│   ├── create-app-user.sql       # Create restricted DB user
│   ├── test-app-user-permissions.sql
│   ├── init-db.sql
│   ├── run-migrations.sh
│   ├── run-migrations.bat
│   ├── clean-database.sh
│   ├── clean-database.bat
│   ├── load-real-pdfs.sh
│   ├── load-real-pdfs.bat
│   └── README.md
├── static/                        # Static files
├── .env.example                   # Enhanced with budget/rate limit vars
├── .env.local                     # Local config (gitignored)
├── .gitignore
├── conftest.py                    # Pytest fixtures
├── docker-compose.yaml            # Local services
├── manage.py                      # Django management
├── pytest.ini                     # Pytest configuration
├── pyproject.toml                 # Python dependencies (uv)
├── uv.lock                        # Locked dependencies
└── README.md                      # This file
```

**Key Files Updated (✨):**
- `apps/chat/models.py` - Added `AnswerLog` and `MessageFeedback` models
- `apps/chat/views.py` - Added DELETE conversation endpoint, citation support
- `apps/chat/serializers.py` - Enhanced with structured citation data
- `apps/core/models.py` - Added `Experiment` model for A/B testing
- `apps/core/budget_monitor.py` -  Budget enforcement system
- `apps/core/middleware.py` -  Rate limiting middleware
- `apps/core/throttling.py` -  DRF throttle classes
- `apps/infrastructure/pricing.py` -  Model pricing configuration
- `apps/infrastructure/rate_limit.py` -  Rate limit rules per environment
- `apps/domain/services/chat_service.py` - Enhanced with cost tracking
- `config/settings/base.py` - Added budget and rate limit settings

---

## License

MIT © 2025 Jean Pool Pereyra Príncipe  
See [LICENSE](./LICENSE) for details.

---

**Questions?** Contact jeanpool@swisson.com