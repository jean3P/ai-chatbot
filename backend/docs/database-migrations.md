# Database Migration Runbook

This guide provides step-by-step procedures for safely creating, testing, and deploying database schema changes across
all environments.

**Environments:**

- **Local Development**: Port 5432 (postgres-dev)
- **Test**: Port 5433 (postgres-test)
- **Staging**: Remote PostgreSQL instance
- **Production**: Remote PostgreSQL instance

---

## 1. Creating Migrations Locally

### Prerequisites

- Development database running: `docker-compose up -d postgres-dev`
- Virtual environment activated: `source .venv/bin/activate` (Unix) or `.venv\Scripts\activate` (Windows)
- On feature branch: `git checkout -b feature/your-migration-name`

### Steps

**1.1 Make model changes**

```bash
# Edit your model file
code apps/your_app/models.py
```

**1.2 Generate migration**

```bash
python manage.py makemigrations
```

**1.3 Review generated migration**

```bash
# Check the generated file
cat apps/your_app/migrations/0XXX_description.py

# Verify SQL that will be executed
python manage.py sqlmigrate your_app 0XXX
```

**1.4 Test migration locally**

```bash
# Apply migration
python manage.py migrate

# Verify in database
python manage.py dbshell
# Run: \dt to list tables, \d table_name to describe table
```

**1.5 Test rollback**

```bash
# Roll back to previous migration
python manage.py migrate your_app 0XXX_previous

# Re-apply
python manage.py migrate
```

**1.6 Commit migration**

```bash
git add apps/your_app/migrations/0XXX_description.py
git commit -m "Add migration: brief description of changes"
git push origin feature/your-migration-name
```

---

## 2. Testing in Development

### Automated Testing

**2.1 Run migration tests**

```bash
# Test migrations apply cleanly
python manage.py migrate --settings=config.settings.test

# Run all tests
pytest apps/ -v

# Run migration-specific tests if any
pytest apps/your_app/tests/test_migrations.py -v
```

**2.2 Test with seed data**

```bash
# Start fresh
python manage.py migrate
python manage.py seed_database --size medium --clear

# Verify data integrity
python manage.py shell
>>> from apps.your_app.models import YourModel
>>> YourModel.objects.count()
>>> # Verify changes work as expected
```

### Manual Testing

**2.3 Test common operations**

- Create records
- Update records
- Delete records
- Query with new fields/indexes
- Test any custom migrations (data migrations)

**2.4 Performance testing**

```bash
# Check migration execution time
time python manage.py migrate your_app 0XXX

# For large tables, test with production-like data volume
python manage.py seed_database --size large
```

---

## 3. Deploying to Staging

### Prerequisites

- All tests passing in CI
- PR approved and merged to `develop` branch
- Staging database backup created

### Steps

**3.1 Create backup**

```bash
# SSH to staging server or use remote backup tool
pg_dump -h staging-db-host -U postgres -d chatbot_staging > backup_$(date +%Y%m%d_%H%M%S).sql
```

**3.2 Deploy code to staging**

```bash
# Pull latest develop branch on staging server
cd /app/backend
git pull origin develop
```

**3.3 Apply migrations**

```bash
# Activate venv
source .venv/bin/activate

# Check migration status
python manage.py showmigrations

# Apply migrations
python manage.py migrate --settings=config.settings.staging

# Verify
python manage.py showmigrations
```

**3.4 Smoke test**

```bash
# Test critical endpoints
curl https://staging.yourapp.com/api/health
curl https://staging.yourapp.com/api/documents

# Check logs
tail -f /var/log/app/django.log
```

**3.5 Monitor for issues**

- Check error logs for 24 hours
- Monitor database performance metrics
- Test all affected features manually

---

## 4. Deploying to Production

### Prerequisites

- Production backup created
- Maintenance window scheduled (if needed)
- Rollback plan prepared

### Pre-Deployment Checklist

**4.1 Risk assessment**

- [ ] Migration is backward compatible
- [ ] No data loss risk
- [ ] Estimated execution time < 5 seconds (or maintenance window scheduled)
- [ ] Rollback procedure tested
- [ ] Team members on standby

**4.2 Notifications**

```bash
# Notify team in Slack/email
# Subject: Production Migration - [DATE] [TIME]
# Body: 
# - Migration: 0XXX_description
# - Estimated downtime: X minutes (if any)
# - Rollback procedure: attached
```

### Deployment Steps

**4.3 Create production backup**

```bash
# Full database backup
pg_dump -h prod-db-host -U postgres -d chatbot_production > prod_backup_$(date +%Y%m%d_%H%M%S).sql

# Verify backup integrity
pg_restore --list prod_backup_*.sql | head -20
```

**4.4 Enable maintenance mode** (if needed)

```bash
# Set maintenance flag
echo "MAINTENANCE_MODE=true" >> /app/.env
sudo systemctl reload nginx
```

**4.5 Apply migration**

```bash
cd /app/backend
source .venv/bin/activate

# Double-check environment
python manage.py diffsettings | grep DATABASE

# Apply migration
python manage.py migrate --settings=config.settings.production

# Check status
python manage.py showmigrations
```

**4.6 Verify and monitor**

```bash
# Disable maintenance mode
sed -i '/MAINTENANCE_MODE/d' /app/.env
sudo systemctl reload nginx

# Smoke tests
curl https://api.yourapp.com/health
curl https://api.yourapp.com/api/documents

# Monitor logs in real-time
tail -f /var/log/app/django.log
tail -f /var/log/postgresql/postgresql.log
```

**4.7 Post-deployment monitoring**

- Monitor error rates for 2 hours
- Check database performance metrics
- Verify critical user workflows
- Document any issues

---

## 5. Rolling Back Migrations

### When to Roll Back

- Application errors after migration
- Data corruption detected
- Performance degradation
- Unexpected behavior in production

### Rollback Procedure

**5.1 Quick rollback (safe migrations)**

```bash
# For backward-compatible migrations
python manage.py migrate your_app 0XXX_previous

# Verify
python manage.py showmigrations
```

**5.2 Full rollback (complex migrations)**

```bash
# Stop application
sudo systemctl stop gunicorn

# Restore from backup
psql -h prod-db-host -U postgres -d chatbot_production < prod_backup_YYYYMMDD_HHMMSS.sql

# Rollback code
git checkout previous-stable-tag
pip install -r requirements.txt

# Start application
sudo systemctl start gunicorn

# Verify
curl https://api.yourapp.com/health
```

**5.3 Post-rollback**

- Document what went wrong
- Create post-mortem
- Fix migration issues
- Re-test in staging before retry

---

## 6. Dangerous Migrations Checklist

### High-Risk Operations

Use this checklist for migrations that involve:

- [ ] **Dropping columns**: Ensure no code references the column
- [ ] **Dropping tables**: Verify table is completely unused
- [ ] **Renaming columns/tables**: Update all queries and ORM references
- [ ] **Changing column types**: Test data conversion on staging data dump
- [ ] **Adding NOT NULL constraints**: Ensure all existing rows have values
- [ ] **Adding UNIQUE constraints**: Verify no duplicate values exist
- [ ] **Data migrations**: Test with production-sized dataset
- [ ] **Large table alterations**: Schedule maintenance window

### Mitigation Strategies

**For dropping columns/tables:**

```python
# Step 1: Deploy code that doesn't use the column (wait 1 week)
# Step 2: Mark column as deprecated in migration
# Step 3: Wait another week
# Step 4: Drop the column in separate migration
```

**For adding NOT NULL:**

```python
# Step 1: Add column as nullable with default
class Migration(migrations.Migration):
    operations = [
        migrations.AddField(
            model_name='document',
            name='new_field',
            field=models.CharField(max_length=100, null=True, default='value'),
        ),
    ]

# Step 2: Populate data
# Step 3: Add NOT NULL constraint in separate migration
```

**For large table changes:**

```bash
# Use concurrent operations where possible
ALTER TABLE documents ADD COLUMN new_field VARCHAR(100);  -- Fast
CREATE INDEX CONCURRENTLY idx_name ON documents(field);  -- No table lock
```

---

## 7. Common Scenarios

### Scenario 1: Adding an Index

```bash
# Create migration
python manage.py makemigrations --empty your_app -n add_index_field

# Edit migration to use concurrent index creation
class Migration(migrations.Migration):
    operations = [
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY idx_documents_field ON documents_document(field);",
            "DROP INDEX IF EXISTS idx_documents_field;"
        )
    ]

# Test locally, then deploy to staging
```

### Scenario 2: Data Migration

```python
# apps/your_app/migrations/0XXX_populate_field.py
from django.db import migrations


def populate_field(apps, schema_editor):
    YourModel = apps.get_model('your_app', 'YourModel')
    for obj in YourModel.objects.filter(new_field__isnull=True):
        obj.new_field = calculate_value(obj)
        obj.save()


class Migration(migrations.Migration):
    operations = [
        migrations.RunPython(populate_field, migrations.RunPython.noop)
    ]
```

### Scenario 3: Multiple Migrations in One Release

```bash
# Apply all migrations at once
python manage.py migrate

# Or selectively
python manage.py migrate your_app 0XXX
python manage.py migrate other_app 0YYY
```

---

## 8. Emergency Contacts

**During Production Migrations:**

- Database Admin: jeanpool@swisson.com
- DevOps Lead: jeanpool@swisson.com
- Engineering Manager: jeanpool@swisson.com

---

## 9. Useful Commands

### Check migration status

```bash
python manage.py showmigrations
python manage.py showmigrations --plan
python manage.py showmigrations your_app
```

### Inspect migration SQL

```bash
python manage.py sqlmigrate your_app 0XXX
python manage.py sqlmigrate your_app 0XXX --backwards
```

### Manual migration control

```bash
# Mark migration as applied without running
python manage.py migrate your_app 0XXX --fake

# Unapply migration without running SQL
python manage.py migrate your_app 0XXX --fake-zero
```

### Database inspection

```bash
# Django shell
python manage.py dbshell

# PostgreSQL commands
\dt                          # List tables
\d table_name               # Describe table
\di                         # List indexes
SELECT * FROM django_migrations ORDER BY applied DESC LIMIT 10;
```

---

## 10. Best Practices

1. **Always create backward-compatible migrations** when possible
2. **Test rollback procedure** in staging before production
3. **Split large migrations** into multiple smaller ones
4. **Use database transactions** for data migrations
5. **Avoid mixing schema and data changes** in same migration
6. **Document complex migrations** with comments
7. **Monitor database performance** after deployment
8. **Keep backups** for at least 30 days
9. **Use feature flags** for risky changes
10. **Schedule high-risk migrations** during low-traffic periods

---

**Last Updated:** 30.09.2025

**Version:** 1.0  

**Maintained By:** Jean Pool Pereyra Principe