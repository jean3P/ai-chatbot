@echo off
REM backend/scripts/clean-database.bat
REM Clean development or test database (Windows)

if "%1"=="" (
    echo Usage: clean-database.bat [dev^|test^|both]
    echo.
    echo Clean database by removing all data
    echo.
    echo Options:
    echo   dev   - Clean development database
    echo   test  - Clean test database
    echo   both  - Clean both databases
    exit /b 1
)

if "%1"=="dev" goto clean_dev
if "%1"=="test" goto clean_test
if "%1"=="both" goto clean_both

echo Invalid argument: %1
exit /b 1

:clean_dev
echo WARNING: This will delete ALL data from development database
set /p confirm="Are you sure? (yes/no): "
if not "%confirm%"=="yes" (
    echo Cancelled
    exit /b 0
)
set PGPASSWORD=dev_password_123
psql -h localhost -p 5432 -U chatbot_user -d chatbot_dev -c "TRUNCATE TABLE chat_message, chat_conversation, documents_documentchunk, documents_document CASCADE;"
echo Development database cleaned
goto end

:clean_test
set PGPASSWORD=postgres
psql -h localhost -p 5433 -U postgres -d test_chatbot -c "TRUNCATE TABLE chat_message, chat_conversation, documents_documentchunk, documents_document CASCADE;"
echo Test database cleaned
goto end

:clean_both
echo WARNING: This will delete ALL data from BOTH databases
set /p confirm="Are you sure? (yes/no): "
if not "%confirm%"=="yes" (
    echo Cancelled
    exit /b 0
)
call %0 dev
call %0 test
goto end

:end
echo.
echo Database cleaning complete!