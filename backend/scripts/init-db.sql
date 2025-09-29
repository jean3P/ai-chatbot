-- ============================================================================
-- Database Initialization Script
-- ============================================================================
-- This script runs automatically when PostgreSQL container starts for the
-- first time. It enables required extensions and creates database users.
--
-- Extensions:
-- - uuid-ossp:         Generate UUIDs for primary keys
-- - vector:            pgvector for similarity search
-- - pg_stat_statements: Query performance monitoring
--
-- Users:
-- - chatbot_readonly:  Read-only access for analytics/reporting
--
-- Note: This script is idempotent (safe to run multiple times)
-- Note: Works with any database name (uses current_database())
-- ============================================================================

-- ============================================================================
-- EXTENSIONS
-- ============================================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgvector for similarity search
CREATE EXTENSION IF NOT EXISTS "vector";

-- Enable query performance monitoring
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";


-- ============================================================================
-- USERS AND PERMISSIONS
-- ============================================================================

-- Create read-only user for analytics and reporting
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = 'chatbot_readonly') THEN
        CREATE USER chatbot_readonly WITH PASSWORD 'readonly_pass';
        RAISE NOTICE 'Created user: chatbot_readonly';
    ELSE
        RAISE NOTICE 'User chatbot_readonly already exists';
    END IF;
END
$$;

-- Grant connection permission to current database (not hardcoded)
DO $$
BEGIN
    EXECUTE format('GRANT CONNECT ON DATABASE %I TO chatbot_readonly', current_database());
END
$$;

-- Grant usage on public schema
GRANT USAGE ON SCHEMA public TO chatbot_readonly;

-- Grant SELECT on all existing tables
GRANT SELECT ON ALL TABLES IN SCHEMA public TO chatbot_readonly;

-- Grant SELECT on all existing sequences (for viewing sequence values)
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO chatbot_readonly;

-- Automatically grant SELECT on future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO chatbot_readonly;

-- Automatically grant SELECT on future sequences
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON SEQUENCES TO chatbot_readonly;


-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Verify extensions are installed
DO $$
DECLARE
    ext_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO ext_count
    FROM pg_extension
    WHERE extname IN ('uuid-ossp', 'vector', 'pg_stat_statements');

    IF ext_count = 3 THEN
        RAISE NOTICE 'All required extensions installed successfully';
    ELSE
        RAISE WARNING 'Not all extensions installed. Expected 3, found %', ext_count;
    END IF;
END $$;

-- Verify readonly user has correct permissions
DO $$
DECLARE
    has_connect BOOLEAN;
    has_usage BOOLEAN;
BEGIN
    -- Check CONNECT privilege
    SELECT has_database_privilege('chatbot_readonly', current_database(), 'CONNECT') INTO has_connect;

    -- Check USAGE privilege on schema
    SELECT has_schema_privilege('chatbot_readonly', 'public', 'USAGE') INTO has_usage;

    IF has_connect AND has_usage THEN
        RAISE NOTICE 'Read-only user permissions configured successfully';
    ELSE
        RAISE WARNING 'Read-only user permissions incomplete';
    END IF;
END $$;