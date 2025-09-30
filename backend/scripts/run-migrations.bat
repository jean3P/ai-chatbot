@echo off
REM scripts/run-migrations.bat
REM Helper script to run migrations with superuser privileges (Windows)

echo ==========================================
echo Running Django Migrations
echo ==========================================
echo.
echo WARNING: This script temporarily uses postgres superuser
echo          for schema modifications (migrations).
echo.

REM Check if .env.local exists
if not exist .env.local (
    echo ERROR: .env.local not found
    echo        Copy .env.example to .env.local first
    exit /b 1
)

REM Backup .env.local
copy .env.local .env.local.bak > nul

REM Update to postgres user
powershell -Command "(gc .env.local) -replace '^DB_USER=.*', 'DB_USER=chatbot_user' | Out-File -encoding ASCII .env.local"
powershell -Command "(gc .env.local) -replace '^DB_PASSWORD=.*', 'DB_PASSWORD=dev_password_123' | Out-File -encoding ASCII .env.local"

echo Running migrations...
python manage.py migrate

REM Restore original
move /Y .env.local.bak .env.local > nul

echo.
echo ==========================================
echo Migrations complete!
echo ==========================================
