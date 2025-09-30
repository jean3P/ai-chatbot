# AI Chatbot - Backend

Django-based backend for RAG-powered chatbot with pgvector for semantic search.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Detailed Setup](#detailed-setup)
- [Database Architecture](#database-architecture)
- [Running Migrations](#running-migrations)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Seeding Data](#seeding-data)
- [API Documentation](#api-documentation)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

- **Python 3.12+**
- **Docker & Docker Compose** (for PostgreSQL and Redis)
- **uv** (Python package manager) - Install: `pip install uv`
- **Git**

### Optional
- **psql** (PostgreSQL client) - for database management
- **curl** or **Postman** - for API testing

---

## Quick Start

```bash
# 1. Clone repository
git clone <your-repo-url>
cd ai-chatbot/backend

# 2. Install dependencies
uv sync

# 3. Start services
docker-compose up -d

# 4. Create database user
psql -h localhost -U chatbot_user -d chatbot_dev -f scripts/create-app-user.sql
# Password: dev_password_123

# 5. Setup environment
cp .env.example .env.local
# Edit .env.local (see Configuration section)

# 6. Run migrations
./scripts/run-migrations.sh  # Unix/Mac/Linux
# OR
scripts\run-migrations.bat   # Windows

# 7. Start development server
uv run python manage.py runserver

# 8. Test
curl http://localhost:8000/api/health/db
```

---

## Detailed Setup

### 1. Install uv (Python Package Manager)

```bash
# Unix/Mac/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Verify installation
uv --version
```

### 2. Install Python Dependencies

```bash
cd backend

# Install all dependencies (including dev dependencies)
uv sync

# Install without dev dependencies (production)
uv sync --no-dev

# Activate virtual environment (optional - uv run does this automatically)
source .venv/bin/activate  # Unix/Mac/Linux
.venv\Scripts\activate     # Windows
```

### 3. Start Docker Services

```bash
# Start all services (PostgreSQL dev, PostgreSQL test, Redis)
docker-compose up -d

# Start specific services
docker-compose up -d postgres-dev redis

# Check service status
docker-compose ps

# View logs
docker-compose logs -f postgres-dev

# Stop services
docker-compose down
```

**Services:**
- **postgres-dev**: Port 5432 (development database)
- **postgres-test**: Port 5433 (test database, ephemeral)
- **redis**: Port 6379 (Celery & Channels)

### 4. Configure Environment

```bash
# Copy example to create local config
cp .env.example .env.local

# Generate SECRET_KEY
uv run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Edit .env.local with your settings
```

**Required variables in `.env.local`:**

```bash
ENVIRONMENT=development

# Database (runtime uses chatbot_app)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=chatbot_dev
DB_USER=chatbot_app
DB_PASSWORD=app_secure_password_change_in_production

# Django
DEBUG=True
SECRET_KEY=<your-generated-key>

# Redis
REDIS_URL=redis://localhost:6379/0

# OpenRouter API (get from https://openrouter.ai/keys)
OPENROUTER_API_KEY=your-api-key-here

# Models
DEFAULT_EMBEDDING_MODEL=text-embedding-3-small
DEFAULT_LLM_MODEL=gpt-4o-mini

# Vector Database
PGVECTOR_ENABLED=true
EMBEDDING_DIMENSION=384
```

### 5. Create Database Users

Our setup uses **two database users** for security:

1. **chatbot_user** (superuser) - For migrations and schema changes
2. **chatbot_app** (restricted) - For normal application runtime

```bash
# Connect to database as superuser
psql -h localhost -U chatbot_user -d chatbot_dev
# Password: dev_password_123

# Run inside psql:
\i scripts/create-app-user.sql
\q
```

**What this does:**
- Creates `chatbot_app` user with minimal privileges
- Grants CRUD on application tables
- Denies schema modification (DROP, CREATE, ALTER)
- Sets connection limit to 50

**Verify users exist:**

```bash
psql -h localhost -U chatbot_user -d chatbot_dev -c "\du"
```

### 6. Run Database Migrations

**Always use the migration script** (it handles user switching automatically):

```bash
# Unix/Mac/Linux
./scripts/run-migrations.sh

# Windows
scripts\run-migrations.bat
```

**What the script does:**
1. Temporarily switches to `chatbot_user` (superuser)
2. Runs `python manage.py migrate`
3. Restores `chatbot_app` user in .env.local

**Manual migration (if needed):**

```bash
# 1. Edit .env.local temporarily
DB_USER=chatbot_user
DB_PASSWORD=dev_password_123

# 2. Run migrations
uv run python manage.py migrate

# 3. Restore .env.local
DB_USER=chatbot_app
DB_PASSWORD=app_secure_password_change_in_production
```

### 7. Create Superuser (Admin Access)

```bash
uv run python manage.py createsuperuser
```

### 8. Start Development Server

```bash
uv run python manage.py runserver

# Or specify port
uv run python manage.py runserver 8080

# Or bind to all interfaces
uv run python manage.py runserver 0.0.0.0:8000
```

**Access:**
- API: http://localhost:8000/api/
- Admin: http://localhost:8000/admin/
- Health check: http://localhost:8000/api/health/db

---

## Database Architecture

### User Roles

| User | Role | Used For | Permissions |
|------|------|----------|-------------|
| `chatbot_user` | Superuser | Migrations, schema changes | Full database access |
| `chatbot_app` | Restricted | Application runtime | CRUD only on app tables |

### Why Two Users?

**Security Benefits:**
- Application cannot accidentally drop tables
- Cannot create malicious tables or users
- Follows principle of least privilege
- Limits damage from SQL injection
- Compliance with security best practices

**Tables:**
```
documents_document         - Document metadata
documents_documentchunk    - Text chunks with embeddings (pgvector)
chat_conversation          - User conversation history
chat_message              - Individual messages
auth_user                 - Django users (read-only for app)
django_migrations         - Migration history
```

### Connection Flow

```
Development Server → chatbot_app (restricted) → PostgreSQL
Migration Script  → chatbot_user (superuser) → PostgreSQL
```

---

## Running Migrations

### Creating New Migrations

```bash
# Make model changes first
code apps/your_app/models.py

# Generate migration
uv run python manage.py makemigrations

# Review generated migration
cat apps/your_app/migrations/0XXX_description.py

# Apply migration (use script)
./scripts/run-migrations.sh
```

### Migration Best Practices

1. **Always review** generated migrations before applying
2. **Test locally** before deploying
3. **Use migration script** (handles user switching)
4. **Check SQL** with `python manage.py sqlmigrate app_name 0XXX`
5. **Backup database** before production migrations

### Testing Migrations

```bash
# Check for unapplied migrations
uv run python manage.py showmigrations

# Test rollback
uv run python manage.py migrate your_app 0XXX_previous

# Re-apply
uv run python manage.py migrate
```

See [docs/database-migrations.md](docs/database-migrations.md) for detailed migration procedures.

---

## Development Workflow

### Daily Development

```bash
# 1. Start services
docker-compose up -d

# 2. Start Django
uv run python manage.py runserver

# 3. Make changes
# Edit code...

# 4. If models changed, create migration
uv run python manage.py makemigrations
./scripts/run-migrations.sh

# 5. Test changes
uv run pytest apps/ -v
```

### Code Quality

```bash
# Format code
uv run black .
uv run isort .

# Check formatting
uv run black --check .
uv run isort --check-only .

# Run linters
uv run flake8
```

### Running Django Management Commands

```bash
# Django shell
uv run python manage.py shell

# Database shell
uv run python manage.py dbshell

# Create superuser
uv run python manage.py createsuperuser

# Collect static files
uv run python manage.py collectstatic
```

---

## Testing

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific app tests
uv run pytest apps/core/tests/ -v

# Run specific test file
uv run pytest apps/core/tests/test_health_check.py -v

# Run with coverage
uv run pytest --cov=apps --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Test Database

Tests use **postgres-test** on port 5433 (ephemeral, tmpfs storage):

```bash
# Start test database
docker-compose up -d postgres-test

# Run tests
uv run pytest

# Tests automatically:
# - Use test settings (config.settings.test)
# - Connect to port 5433
# - Clean database after each test
```

### Writing Tests

```python
# apps/your_app/tests/test_example.py
import pytest
from django.urls import reverse

@pytest.mark.django_db
class TestYourFeature:
    def test_something(self):
        # Your test here
        assert True
```

### Test Configuration

- **Settings**: `config/settings/test.py`
- **Pytest config**: `pytest.ini`
- **Fixtures**: `conftest.py`

---

## Seeding Data

### Seed Command

Generate test data for development:

```bash
# Small: 5 docs × 50 chunks + 20 conversations
uv run python manage.py seed_database --size small

# Medium: 20 docs × 100 chunks + 100 conversations
uv run python manage.py seed_database --size medium

# Large: 50 docs × 200 chunks + 500 conversations
uv run python manage.py seed_database --size large

# Clear existing seed data first
uv run python manage.py seed_database --size small --clear

# Seed only documents
uv run python manage.py seed_database --size small --documents-only

# Seed only conversations
uv run python manage.py seed_database --size small --conversations-only
```

### Seed Data Features

- **Realistic content**: DMX equipment manuals and troubleshooting
- **Random embeddings**: 384-dimension normalized vectors
- **Citations**: Assistant messages include chunk references
- **Fast**: Small dataset in <1 second

### Production Warning

```bash
# Seed command is blocked in production
ENVIRONMENT=production python manage.py seed_database
# ERROR: Cannot seed database in production environment
```

---

## API Documentation

### Health Check

**Endpoint:** `GET /api/health/db`

**Response:**
```json
{
  "status": "healthy",
  "latency_ms": 12.34,
  "database": "chatbot_dev"
}
```

**Status Codes:**
- `200` - Database healthy
- `503` - Database unreachable

**Usage:**
```bash
curl http://localhost:8000/api/health/db
```

**Monitoring:**
- Logs warning if latency > 100ms
- 5-second timeout
- No-cache headers (for load balancers)

### Chat Endpoints

**Create conversation:** `POST /api/chat/conversations/`

**Send message:** `POST /api/chat/conversations/{id}/messages/`

**List conversations:** `GET /api/chat/conversations/`

### Document Endpoints

**Upload document:** `POST /api/documents/upload/`

**List documents:** `GET /api/documents/`

**Document details:** `GET /api/documents/{id}/`

---

## Deployment

### Environment Setup

**Staging:**
```bash
ENVIRONMENT=staging
DEBUG=False
DB_USER=chatbot_app
DB_HOST=<rds-endpoint>
```

**Production:**
```bash
ENVIRONMENT=production
DEBUG=False
DB_USER=chatbot_app
DB_HOST=<rds-endpoint>
ALLOWED_HOSTS=yourdomain.com
SECURE_SSL_REDIRECT=True
```

### Deployment Checklist

- [ ] Set `DEBUG=False`
- [ ] Generate new `SECRET_KEY`
- [ ] Use strong database passwords
- [ ] Enable SSL/HTTPS
- [ ] Configure ALLOWED_HOSTS
- [ ] Setup error monitoring (Sentry)
- [ ] Configure S3 for media files
- [ ] Setup automated backups
- [ ] Review security settings
- [ ] Run migrations in maintenance window

### Deployment Commands

```bash
# Collect static files
python manage.py collectstatic --noinput

# Run migrations (use superuser temporarily)
python manage.py migrate --settings=config.settings.production

# Check deployment
python manage.py check --deploy
```

See deployment guides:
- [docs/database-migrations.md](docs/database-migrations.md)
- [docs/database-backup-restore.md](docs/database-backup-restore.md)

---

## Troubleshooting

### Common Issues

#### 1. Permission Denied on Migrations

**Error:**
```
django.db.utils.ProgrammingError: permission denied for schema public
```

**Solution:** Use migration script (switches to superuser):
```bash
./scripts/run-migrations.sh
```

#### 2. Database Connection Failed

**Error:**
```
psycopg2.OperationalError: connection refused
```

**Solution:** Ensure database is running:
```bash
docker-compose up -d postgres-dev
docker-compose ps
```

#### 3. Password Authentication Failed

**Error:**
```
FATAL: password authentication failed for user "chatbot_app"
```

**Solution:** Verify user exists:
```bash
psql -h localhost -U chatbot_user -d chatbot_dev -c "\du chatbot_app"

# If missing, create user:
psql -h localhost -U chatbot_user -d chatbot_dev -f scripts/create-app-user.sql
```

#### 4. Import Errors

**Error:**
```
ModuleNotFoundError: No module named 'apps'
```

**Solution:** Use `uv run` or activate venv:
```bash
uv run python manage.py runserver
# OR
source .venv/bin/activate
python manage.py runserver
```

#### 5. Port Already in Use

**Error:**
```
Error: That port is already in use
```

**Solution:**
```bash
# Find process using port
lsof -i :8000  # Unix/Mac
netstat -ano | findstr :8000  # Windows

# Kill process or use different port
python manage.py runserver 8080
```

#### 6. pgvector Extension Not Found

**Error:**
```
psycopg2.errors.UndefinedObject: type "vector" does not exist
```

**Solution:** Install extension (as superuser):
```bash
psql -h localhost -U chatbot_user -d chatbot_dev -c "CREATE EXTENSION vector;"
```

#### 7. Redis Connection Failed

**Error:**
```
redis.exceptions.ConnectionError: Error connecting to Redis
```

**Solution:** Start Redis:
```bash
docker-compose up -d redis
docker-compose logs redis
```

### Debug Mode

Enable verbose logging:

```bash
# In .env.local
DEBUG=True
LOG_LEVEL=DEBUG

# Then check logs
tail -f /var/log/django/debug.log
```

### Database Inspection

```bash
# Connect to database
psql -h localhost -U chatbot_app -d chatbot_dev

# Inside psql:
\dt                          # List tables
\d documents_document        # Describe table
\du                          # List users
\l                           # List databases
\dx                          # List extensions

# Check row counts
SELECT 
  'documents' as table, COUNT(*) FROM documents_document
UNION ALL
SELECT 'chunks', COUNT(*) FROM documents_documentchunk
UNION ALL  
SELECT 'conversations', COUNT(*) FROM chat_conversation
UNION ALL
SELECT 'messages', COUNT(*) FROM chat_message;
```

### Getting Help

1. Check [docs/](docs/) directory for detailed guides
2. Review error logs: `docker-compose logs -f`
3. Search issues on GitHub
4. Contact team on Slack: #engineering-support

---

## Project Structure

```
backend/
├── apps/                       # Django applications
│   ├── adapters/              # External integrations
│   │   ├── embeddings/        # Embedding models
│   │   ├── llm/               # LLM providers
│   │   ├── parsing/           # Document parsers
│   │   └── retrieval/         # Vector stores
│   ├── chat/                  # Chat functionality
│   │   ├── models.py          # Conversation, Message
│   │   ├── views.py           # API endpoints
│   │   └── consumers.py       # WebSocket handlers
│   ├── core/                  # Core utilities
│   │   ├── management/        # Management commands
│   │   │   └── commands/
│   │   │       └── seed_database.py
│   │   ├── views.py           # Health checks
│   │   └── tests/             # Core tests
│   ├── documents/             # Document management
│   │   ├── models.py          # Document, DocumentChunk
│   │   └── views.py           # Upload, search
│   └── domain/                # Business logic
│       ├── models.py          # Domain entities
│       ├── ports/             # Interface definitions
│       └── services/          # Application services
├── config/                    # Django configuration
│   ├── settings/              # Environment-specific settings
│   │   ├── base.py           # Common settings
│   │   ├── development.py    # Development overrides
│   │   ├── test.py           # Test settings
│   │   └── databases.py      # Database configuration
│   ├── urls.py               # URL routing
│   └── wsgi.py               # WSGI entry point
├── docs/                      # Documentation
│   ├── database-migrations.md
│   └── database-backup-restore.md
├── scripts/                   # Utility scripts
│   ├── create-app-user.sql   # Create restricted user
│   ├── run-migrations.sh     # Migration helper (Unix)
│   └── run-migrations.bat    # Migration helper (Windows)
├── .env.example              # Environment template
├── .env.local                # Local config (gitignored)
├── docker-compose.yaml       # Local services
├── manage.py                 # Django management
├── pytest.ini                # Pytest configuration
├── pyproject.toml            # Python dependencies
└── README.md                 # This file
```

---

## Additional Resources

### Documentation

- [Database Migrations Guide](docs/database-migrations.md)
- [Backup & Restore Procedures](docs/database-backup-restore.md)
- [Django Documentation](https://docs.djangoproject.com/)
- [pgvector Documentation](https://github.com/pgvector/pgvector)

### Scripts

- `scripts/create-app-user.sql` - Setup restricted database user
- `scripts/test-app-user-permissions.sql` - Verify user permissions
- `scripts/run-migrations.sh` - Run migrations with superuser
- `scripts/init-db.sql` - Initialize database extensions

### Management Commands

```bash
# Seed database
python manage.py seed_database --help

# Process documents
python manage.py process_documents --help

# Batch upload
python manage.py batch_upload_documents --help

# Regenerate embeddings
python manage.py regenerate_embeddings --help
```

---

## License

MIT © 2025 Jean Pool Pereyra Príncipe  
See [LICENSE](./LICENSE) for details.


---

**Questions?** Contact the team at jeanpool@swisson.com
