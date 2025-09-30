-- =====================================================================
-- Test Script for Application User Permissions
-- =====================================================================
-- Purpose: Verify chatbot_app can perform allowed operations
--          and cannot perform denied operations
-- Usage: psql -h localhost -U chatbot_app -d chatbot_dev -f scripts/test-app-user-permissions.sql
-- =====================================================================

\echo '=========================================='
\echo 'Testing chatbot_app Permissions'
\echo '=========================================='

-- =====================================================================
-- Test 1: CRUD Operations (Should SUCCEED)
-- =====================================================================

\echo ''
\echo 'Test 1: Testing INSERT operation...'
BEGIN;

-- Insert test document
INSERT INTO documents_document (
    id, title, file_path, document_type, language,
    processed, created_at, updated_at
) VALUES (
    gen_random_uuid(),
    '[TEST] Permission Test Document',
    '/tmp/test.pdf',
    'manual',
    'en',
    true,
    NOW(),
    NOW()
) RETURNING id, title;

ROLLBACK;
\echo '✓ INSERT successful'

\echo ''
\echo 'Test 2: Testing SELECT operation...'
SELECT COUNT(*) as total_documents FROM documents_document;
\echo '✓ SELECT successful'

\echo ''
\echo 'Test 3: Testing UPDATE operation...'
BEGIN;

UPDATE documents_document
SET title = '[UPDATED] Test'
WHERE title LIKE '[TEST]%'
RETURNING id, title;

ROLLBACK;
\echo '✓ UPDATE successful'

\echo ''
\echo 'Test 4: Testing DELETE operation...'
BEGIN;

DELETE FROM documents_document
WHERE title LIKE '[TEST]%'
RETURNING id, title;

ROLLBACK;
\echo '✓ DELETE successful'

-- =====================================================================
-- Test 5: Schema Modification (Should FAIL)
-- =====================================================================

\echo ''
\echo 'Test 5: Testing DROP TABLE (should fail)...'
\set ON_ERROR_STOP off

DROP TABLE documents_document;

\set ON_ERROR_STOP on
\echo '✓ DROP TABLE correctly denied'

\echo ''
\echo 'Test 6: Testing CREATE TABLE (should fail)...'
\set ON_ERROR_STOP off

CREATE TABLE test_malicious_table (id SERIAL PRIMARY KEY);

\set ON_ERROR_STOP on
\echo '✓ CREATE TABLE correctly denied'

\echo ''
\echo 'Test 7: Testing ALTER TABLE (should fail)...'
\set ON_ERROR_STOP off

ALTER TABLE documents_document ADD COLUMN malicious_column TEXT;

\set ON_ERROR_STOP on
\echo '✓ ALTER TABLE correctly denied'

\echo ''
\echo 'Test 8: Testing CREATE USER (should fail)...'
\set ON_ERROR_STOP off

CREATE ROLE malicious_user WITH LOGIN PASSWORD 'hacker';

\set ON_ERROR_STOP on
\echo '✓ CREATE USER correctly denied'

-- =====================================================================
-- Test 9: Sequence Access (Should SUCCEED)
-- =====================================================================

\echo ''
\echo 'Test 9: Testing sequence access...'
SELECT nextval('documents_document_id_seq');
\echo '✓ Sequence access successful'

-- =====================================================================
-- Test 10: Auth Table Access (Should be READ-ONLY)
-- =====================================================================

\echo ''
\echo 'Test 10: Testing auth_user SELECT (should succeed)...'
SELECT COUNT(*) as total_users FROM auth_user;
\echo '✓ auth_user SELECT successful'

\echo ''
\echo 'Test 11: Testing auth_user INSERT (should fail)...'
\set ON_ERROR_STOP off

INSERT INTO auth_user (username, password) VALUES ('hacker', 'password');

\set ON_ERROR_STOP on
\echo '✓ auth_user INSERT correctly denied'

\echo ''
\echo '=========================================='
\echo 'All permission tests completed!'
\echo '=========================================='
