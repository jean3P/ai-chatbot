-- backend/scripts/init-db.sql
-- ============================================================================
-- Database Initialization Script
-- ============================================================================

\echo 'Starting database initialization...'

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

\echo 'Extensions created'

-- ============================================================================
-- APPLICATION USER (chatbot_app)
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'chatbot_app') THEN
        CREATE ROLE chatbot_app WITH LOGIN PASSWORD 'app_secure_password_change_in_production';
        RAISE NOTICE 'Created user: chatbot_app';
    ELSE
        RAISE NOTICE 'User chatbot_app already exists';
    END IF;
END
$$;

ALTER ROLE chatbot_app CONNECTION LIMIT 50;

-- Grant database connection (use \gexec instead of EXECUTE format)
SELECT format('GRANT CONNECT ON DATABASE %I TO chatbot_app', current_database()) \gexec

-- Schema privileges
GRANT ALL ON SCHEMA public TO chatbot_app;
GRANT CREATE ON SCHEMA public TO chatbot_app;
GRANT USAGE ON SCHEMA public TO chatbot_app;

-- Table and sequence privileges
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO chatbot_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO chatbot_app;

-- Default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO chatbot_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO chatbot_app;

-- ============================================================================
-- READ-ONLY USER (chatbot_readonly)
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'chatbot_readonly') THEN
        CREATE USER chatbot_readonly WITH PASSWORD 'readonly_pass';
        RAISE NOTICE 'Created user: chatbot_readonly';
    ELSE
        RAISE NOTICE 'User chatbot_readonly already exists';
    END IF;
END
$$;

SELECT format('GRANT CONNECT ON DATABASE %I TO chatbot_readonly', current_database()) \gexec

GRANT USAGE ON SCHEMA public TO chatbot_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO chatbot_readonly;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO chatbot_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO chatbot_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON SEQUENCES TO chatbot_readonly;

\echo 'Database initialization complete!'
