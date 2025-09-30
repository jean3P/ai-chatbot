-- =====================================================================
-- Database Access Control Script
-- Creates application user with minimal necessary privileges
-- =====================================================================
-- Purpose: Create chatbot_app user with CRUD access to application tables
--          while preventing schema modifications
-- Usage: psql -h localhost -U postgres -d chatbot_dev -f scripts/create-app-user.sql
-- =====================================================================

-- Enable required extensions (if not already enabled)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- =====================================================================
-- 1. Create Application User (Idempotent)
-- =====================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM pg_catalog.pg_roles WHERE rolname = 'chatbot_app'
    ) THEN
        CREATE ROLE chatbot_app WITH LOGIN PASSWORD 'app_secure_password_change_in_production';
        RAISE NOTICE 'Created user: chatbot_app';
    ELSE
        RAISE NOTICE 'User chatbot_app already exists, skipping creation';
    END IF;
END
$$;

-- Set connection limit (optional security measure)
ALTER ROLE chatbot_app CONNECTION LIMIT 50;

-- =====================================================================
-- 2. Grant Database Connection
-- =====================================================================

GRANT CONNECT ON DATABASE chatbot_dev TO chatbot_app;

-- =====================================================================
-- 3. Grant Schema Usage (Required for accessing tables)
-- =====================================================================

GRANT USAGE ON SCHEMA public TO chatbot_app;

-- =====================================================================
-- 4. Grant CRUD Privileges on Application Tables
-- =====================================================================

-- Documents tables
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE documents_document TO chatbot_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE documents_documentchunk TO chatbot_app;

-- Chat tables
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE chat_conversation TO chatbot_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE chat_message TO chatbot_app;

-- Auth tables (read-only for user lookups)
GRANT SELECT ON TABLE auth_user TO chatbot_app;
GRANT SELECT ON TABLE auth_group TO chatbot_app;
GRANT SELECT ON TABLE auth_permission TO chatbot_app;

-- Django system tables (read-only)
GRANT SELECT ON TABLE django_migrations TO chatbot_app;
GRANT SELECT ON TABLE django_content_type TO chatbot_app;
GRANT SELECT ON TABLE django_session TO chatbot_app;

-- =====================================================================
-- 5. Grant Sequence Usage (Required for AUTO INCREMENT)
-- =====================================================================

-- Grant usage on all sequences for ID generation
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO chatbot_app;

-- Make future sequences accessible
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT USAGE, SELECT ON SEQUENCES TO chatbot_app;

-- =====================================================================
-- 6. Explicitly DENY Schema Modification Privileges
-- =====================================================================

-- Revoke CREATE privilege on schema (prevents creating new tables)
REVOKE CREATE ON SCHEMA public FROM chatbot_app;

-- Note: By default, chatbot_app doesn't have these privileges, but we
-- explicitly revoke them for documentation and defense-in-depth

-- Revoke all privileges on database-level operations
REVOKE CREATE ON DATABASE chatbot_dev FROM chatbot_app;

-- =====================================================================
-- 7. Row Level Security (Optional - Example for conversations)
-- =====================================================================

-- Uncomment if you want users to only see their own conversations
-- ALTER TABLE chat_conversation ENABLE ROW LEVEL SECURITY;
--
-- CREATE POLICY conversation_isolation ON chat_conversation
--     FOR ALL
--     TO chatbot_app
--     USING (user_id = current_setting('app.user_id')::INTEGER);

-- =====================================================================
-- 8. Grant Future Table Privileges (For migrations)
-- =====================================================================

-- Ensure new tables created by migrations are accessible
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO chatbot_app;

-- =====================================================================
-- 9. Verification Queries
-- =====================================================================

-- Show granted privileges
\echo '=========================================='
\echo 'Privileges granted to chatbot_app:'
\echo '=========================================='

SELECT
    table_schema,
    table_name,
    string_agg(privilege_type, ', ' ORDER BY privilege_type) as privileges
FROM information_schema.table_privileges
WHERE grantee = 'chatbot_app'
    AND table_schema = 'public'
GROUP BY table_schema, table_name
ORDER BY table_name;

-- Show role attributes
\echo ''
\echo 'Role attributes:'
SELECT
    rolname,
    rolsuper as is_superuser,
    rolinherit as can_inherit,
    rolcreaterole as can_create_roles,
    rolcreatedb as can_create_db,
    rolcanlogin as can_login,
    rolconnlimit as connection_limit
FROM pg_roles
WHERE rolname = 'chatbot_app';

\echo ''
\echo 'Setup complete! Application user chatbot_app is ready.'
\echo 'IMPORTANT: Change the password in production!'
