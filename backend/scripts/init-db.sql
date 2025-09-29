-- ============================================================================
-- Database Initialization Script
-- ============================================================================
-- This script runs automatically when PostgreSQL container starts for the
-- first time. It enables required extensions for the chatbot application.
--
-- Extensions:
-- - uuid-ossp:         Generate UUIDs for primary keys
-- - vector:            pgvector for similarity search
-- - pg_stat_statements: Query performance monitoring
--
-- Note: This script is idempotent (safe to run multiple times)
-- ============================================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgvector for similarity search
CREATE EXTENSION IF NOT EXISTS "vector";

-- Enable query performance monitoring
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

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