## Local Development Setup

### 1. Environment Configuration

Copy the development environment template:
```bash
cd backend
cp .env.development .env.local
```

Generate a new SECRET_KEY:
```bash
uv run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Edit `.env.local` and update:
- `SECRET_KEY` with the generated value
- `OPENROUTER_API_KEY` with your API key from https://openrouter.ai/keys

### 2. Start Database
```bash
docker-compose up -d
```

### 3. Run Migrations
```bash
uv run python manage.py migrate
```

### 4. Start Server
```bash
uv run python manage.py runserver
```

### Environment Files

- `.env.example` - Template with all variables (commit this)
- `.env.development` - Development defaults (commit this)
- `.env.local` - Your personal config (never commit)

See `.env.example` for full documentation of all variables.