# Database Scripts

## create-app-user.sql

Creates the `chatbot_app` application user with minimal required privileges.

### Usage

```bash
# As postgres superuser
psql -h localhost -U postgres -d chatbot_dev -f scripts/create-app-user.sql

# For production (update password in script first!)
psql -h prod-host -U postgres -d chatbot_production -f scripts/create-app-user.sql
```

### What it does

- Creates `chatbot_app` user (idempotent)
- Grants CRUD on: documents, conversations, messages
- Grants READ on: auth tables, django system tables
- DENIES: DROP, CREATE, ALTER operations
- Sets connection limit to 50

### Testing

```bash
# Run permission tests
psql -h localhost -U chatbot_app -d chatbot_dev -f scripts/test-app-user-permissions.sql

# Or test manually
psql -h localhost -U chatbot_app -d chatbot_dev

# Try allowed operations
SELECT * FROM documents_document LIMIT 5;
INSERT INTO documents_document (...) VALUES (...);

# Try denied operations (should fail)
DROP TABLE documents_document;
CREATE TABLE test (id INT);
```

### Security Notes

- **CHANGE PASSWORD in production!** The default password is for development only
- User cannot create/drop tables or users
- User cannot modify schema
- User has connection limit of 50
- Consider enabling Row Level Security (RLS) for multi-tenant setups
```

**Test the script:**

```bash
cd backend

# 1. Run the creation script
psql -h localhost -p 5432 -U postgres -d chatbot_dev -f scripts/create-app-user.sql

# 2. Run the test script
psql -h localhost -p 5432 -U chatbot_app -d chatbot_dev -f scripts/test-app-user-permissions.sql

# 3. Verify manually
psql -h localhost -p 5432 -U chatbot_app -d chatbot_dev

# Inside psql, test:
# SELECT * FROM documents_document LIMIT 1;  -- Should work
# DROP TABLE documents_document;              -- Should fail
# CREATE TABLE test (id INT);                 -- Should fail
```