# Database Backup and Restore Procedures

This document outlines backup and restore procedures for all database environments.

**Service Level Objectives:**
- **RTO (Recovery Time Objective):** < 4 hours
- **RPO (Recovery Point Objective):** < 1 hour

**Backup Schedule:**
- **Production:** Automated daily full backups, 5-minute continuous WAL archiving
- **Staging:** Automated daily full backups
- **Development:** Manual backups as needed

---

## 1. Manual Backup (pg_dump)

### 1.1 Full Database Backup

**Backup entire database:**
```bash
# Development database
pg_dump -h localhost -p 5432 -U chatbot_user -d chatbot_dev \
  --format=custom \
  --file=backup_dev_$(date +%Y%m%d_%H%M%S).dump

# With compression
pg_dump -h localhost -p 5432 -U chatbot_user -d chatbot_dev \
  --format=custom \
  --compress=9 \
  --file=backup_dev_$(date +%Y%m%d_%H%M%S).dump
```

**Backup with SQL format (human-readable):**
```bash
pg_dump -h localhost -p 5432 -U chatbot_user -d chatbot_dev \
  --format=plain \
  --file=backup_dev_$(date +%Y%m%d_%H%M%S).sql
```

### 1.2 Schema-Only Backup

**Backup structure without data:**
```bash
pg_dump -h localhost -p 5432 -U chatbot_user -d chatbot_dev \
  --schema-only \
  --file=schema_$(date +%Y%m%d_%H%M%S).sql
```

### 1.3 Data-Only Backup

**Backup data without schema:**
```bash
pg_dump -h localhost -p 5432 -U chatbot_user -d chatbot_dev \
  --data-only \
  --file=data_$(date +%Y%m%d_%H%M%S).sql
```

### 1.4 Table-Specific Backup

**Backup specific tables:**
```bash
pg_dump -h localhost -p 5432 -U chatbot_user -d chatbot_dev \
  --table=documents_document \
  --table=documents_documentchunk \
  --file=backup_documents_$(date +%Y%m%d_%H%M%S).dump
```

### 1.5 Exclude Large Tables

**Backup excluding specific tables:**
```bash
pg_dump -h localhost -p 5432 -U chatbot_user -d chatbot_dev \
  --exclude-table=documents_documentchunk \
  --file=backup_no_chunks_$(date +%Y%m%d_%H%M%S).dump
```

---

## 2. Automated Backups (AWS RDS)

### 2.1 RDS Automated Backup Configuration

**Enable automated backups in RDS:**
```bash
# AWS CLI
aws rds modify-db-instance \
  --db-instance-identifier chatbot-production \
  --backup-retention-period 30 \
  --preferred-backup-window "03:00-04:00" \
  --apply-immediately

# Verify configuration
aws rds describe-db-instances \
  --db-instance-identifier chatbot-production \
  --query 'DBInstances[0].{BackupRetention:BackupRetentionPeriod,Window:PreferredBackupWindow}'
```

**Terraform configuration:**
```hcl
resource "aws_db_instance" "chatbot_production" {
  identifier = "chatbot-production"
  
  # Automated backups
  backup_retention_period = 30
  backup_window          = "03:00-04:00"
  
  # Point-in-time recovery
  enabled_cloudwatch_logs_exports = ["postgresql"]
  
  # Snapshot before deletion
  skip_final_snapshot       = false
  final_snapshot_identifier = "chatbot-production-final-${timestamp()}"
  
  # Copy tags to snapshots
  copy_tags_to_snapshot = true
}
```

### 2.2 Manual RDS Snapshot

**Create manual snapshot:**
```bash
aws rds create-db-snapshot \
  --db-instance-identifier chatbot-production \
  --db-snapshot-identifier chatbot-manual-$(date +%Y%m%d-%H%M%S)

# Check snapshot status
aws rds describe-db-snapshots \
  --db-snapshot-identifier chatbot-manual-YYYYMMDD-HHMMSS
```

### 2.3 Snapshot Lifecycle Management

**Tag snapshots for lifecycle policies:**
```bash
aws rds add-tags-to-resource \
  --resource-name arn:aws:rds:region:account:snapshot:snapshot-name \
  --tags Key=Retention,Value=30days Key=Environment,Value=production
```

### 2.4 Cross-Region Backup Replication

**Copy snapshot to another region:**
```bash
aws rds copy-db-snapshot \
  --source-db-snapshot-identifier arn:aws:rds:us-east-1:account:snapshot:snapshot-name \
  --target-db-snapshot-identifier chatbot-dr-backup-$(date +%Y%m%d) \
  --region us-west-2 \
  --copy-tags
```

---

## 3. Restore Procedures

### 3.1 Restore from pg_dump Backup

**Restore to existing database:**
```bash
# Drop existing database (CAUTION!)
dropdb -h localhost -p 5432 -U postgres chatbot_dev

# Create fresh database
createdb -h localhost -p 5432 -U postgres chatbot_dev

# Restore from custom format
pg_restore -h localhost -p 5432 -U chatbot_user -d chatbot_dev \
  --verbose \
  --no-owner \
  --no-privileges \
  backup_dev_20240101_120000.dump

# Restore from SQL format
psql -h localhost -p 5432 -U chatbot_user -d chatbot_dev \
  < backup_dev_20240101_120000.sql
```

**Restore to new database:**
```bash
# Create new database
createdb -h localhost -p 5432 -U postgres chatbot_restored

# Restore
pg_restore -h localhost -p 5432 -U chatbot_user -d chatbot_restored \
  backup_dev_20240101_120000.dump
```

### 3.2 Restore Specific Tables

**Restore only certain tables:**
```bash
pg_restore -h localhost -p 5432 -U chatbot_user -d chatbot_dev \
  --table=documents_document \
  --table=documents_documentchunk \
  backup_dev_20240101_120000.dump
```

### 3.3 Restore from RDS Snapshot

**Restore RDS snapshot to new instance:**
```bash
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier chatbot-restored \
  --db-snapshot-identifier chatbot-manual-20240101-120000 \
  --db-instance-class db.t3.medium \
  --vpc-security-group-ids sg-xxxxxxxxx \
  --db-subnet-group-name default

# Monitor restore progress
aws rds describe-db-instances \
  --db-instance-identifier chatbot-restored \
  --query 'DBInstances[0].{Status:DBInstanceStatus,Progress:BackupRestoreProgress}'
```

**Update DNS/connection after restore:**
```bash
# Get new endpoint
aws rds describe-db-instances \
  --db-instance-identifier chatbot-restored \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text

# Update application configuration
# Update Route53 CNAME or update .env file
```

### 3.4 Restore to Docker Container (Testing)

**Test restore to fresh container:**
```bash
# Start new PostgreSQL container
docker run -d \
  --name postgres-restore-test \
  -e POSTGRES_DB=chatbot_test \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5434:5432 \
  pgvector/pgvector:pg15

# Wait for PostgreSQL to start
sleep 10

# Restore backup
pg_restore -h localhost -p 5434 -U postgres -d chatbot_test \
  backup_dev_20240101_120000.dump

# Verify restoration
psql -h localhost -p 5434 -U postgres -d chatbot_test -c "\dt"
psql -h localhost -p 5434 -U postgres -d chatbot_test -c "SELECT COUNT(*) FROM documents_document;"

# Cleanup when done
docker stop postgres-restore-test
docker rm postgres-restore-test
```

---

## 4. Point-in-Time Recovery (PITR)

### 4.1 RDS Point-in-Time Recovery

**Restore to specific timestamp:**
```bash
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier chatbot-production \
  --target-db-instance-identifier chatbot-pitr-20240101-1030 \
  --restore-time 2024-01-01T10:30:00Z \
  --db-instance-class db.t3.medium \
  --vpc-security-group-ids sg-xxxxxxxxx

# Or restore to latest restorable time
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier chatbot-production \
  --target-db-instance-identifier chatbot-pitr-latest \
  --use-latest-restorable-time \
  --db-instance-class db.t3.medium
```

**Check latest restorable time:**
```bash
aws rds describe-db-instances \
  --db-instance-identifier chatbot-production \
  --query 'DBInstances[0].LatestRestorableTime'
```

### 4.2 WAL Archiving (Self-Managed)

**Configure continuous archiving:**
```sql
-- postgresql.conf
wal_level = replica
archive_mode = on
archive_command = 'test ! -f /backup/wal/%f && cp %p /backup/wal/%f'
archive_timeout = 300  -- 5 minutes
```

**Restore using WAL files:**
```bash
# Stop PostgreSQL
sudo systemctl stop postgresql

# Restore base backup
pg_restore -d chatbot_production backup_base.dump

# Create recovery.conf (PostgreSQL < 12) or recovery.signal (PostgreSQL >= 12)
cat > $PGDATA/recovery.signal << EOF
restore_command = 'cp /backup/wal/%f %p'
recovery_target_time = '2024-01-01 10:30:00'
EOF

# Start PostgreSQL (will apply WAL until target time)
sudo systemctl start postgresql

# Monitor recovery
tail -f /var/log/postgresql/postgresql-*.log
```

---

## 5. Backup Verification Checklist

### 5.1 Pre-Backup Verification

Before creating backup:
- [ ] Verify database connectivity
- [ ] Check disk space (backup size ≈ 1-2x database size)
- [ ] Confirm backup destination is accessible
- [ ] Verify user has sufficient permissions

```bash
# Check database size
psql -h localhost -U postgres -d chatbot_dev -c "
SELECT pg_database.datname,
       pg_size_pretty(pg_database_size(pg_database.datname)) AS size
FROM pg_database
WHERE datname = 'chatbot_dev';"

# Check disk space
df -h /backup

# Test permissions
touch /backup/test.txt && rm /backup/test.txt
```

### 5.2 Post-Backup Verification

After creating backup:
- [ ] Backup file exists and is non-zero size
- [ ] Backup completed without errors
- [ ] Backup file integrity check passes
- [ ] Backup metadata recorded
- [ ] Test restore to verify backup is usable

```bash
# Verify backup file
ls -lh backup_dev_*.dump
file backup_dev_*.dump

# Check for errors in backup log
grep -i error backup_log.txt

# Integrity check (for custom format)
pg_restore --list backup_dev_20240101_120000.dump | head -20

# Quick restore test to temporary database
createdb -U postgres test_restore
pg_restore -U postgres -d test_restore backup_dev_20240101_120000.dump
psql -U postgres -d test_restore -c "SELECT COUNT(*) FROM documents_document;"
dropdb -U postgres test_restore
```

### 5.3 Monthly Verification

Once per month:
- [ ] Full restore test to staging environment
- [ ] Verify data integrity post-restore
- [ ] Measure restore time (must be < RTO)
- [ ] Test point-in-time recovery (RDS)
- [ ] Review backup retention policies
- [ ] Update documentation if procedures changed

**Full restore test procedure:**
```bash
# 1. Create test instance from latest backup
# 2. Run data integrity checks
# 3. Measure total restore time
# 4. Document results
```

---

## 6. Disaster Recovery Scenarios

### Scenario 1: Accidental Data Deletion

**Response: Point-in-Time Recovery**
```bash
# 1. Identify time before deletion (e.g., 10:25 AM)
# 2. Restore to new RDS instance at 10:20 AM
# 3. Extract affected data
# 4. Import to production
```

**Timeline:** 1-2 hours

### Scenario 2: Database Corruption

**Response: Restore from Latest Backup**
```bash
# 1. Create new RDS instance from latest automated snapshot
# 2. Verify data integrity
# 3. Update application connection strings
# 4. Promote new instance to production
```

**Timeline:** 2-4 hours

### Scenario 3: Complete Infrastructure Failure

**Response: Cross-Region Recovery**
```bash
# 1. Restore from cross-region snapshot
# 2. Launch application in DR region
# 3. Update DNS to point to DR region
# 4. Verify all services operational
```

**Timeline:** 3-4 hours

### Scenario 4: Ransomware/Security Breach

**Response: Restore from Pre-Incident Backup**
```bash
# 1. Isolate affected systems
# 2. Identify last known good backup
# 3. Restore to new isolated environment
# 4. Scan for threats
# 5. Validate data integrity
# 6. Promote to production after clearance
```

**Timeline:** 4-8 hours

---

## 7. Backup Storage and Retention

### 7.1 Backup Storage Locations

**Production:**
- Primary: AWS S3 (us-east-1)
- Secondary: AWS S3 (us-west-2)
- Tertiary: Off-site cold storage (Glacier)

**Retention Policy:**
- Daily backups: 30 days
- Weekly backups: 90 days
- Monthly backups: 1 year
- Annual backups: 7 years

### 7.2 S3 Lifecycle Configuration

```json
{
  "Rules": [
    {
      "Id": "TransitionToIA",
      "Status": "Enabled",
      "Transitions": [
        {
          "Days": 30,
          "StorageClass": "STANDARD_IA"
        },
        {
          "Days": 90,
          "StorageClass": "GLACIER"
        }
      ],
      "Expiration": {
        "Days": 365
      }
    }
  ]
}
```

### 7.3 Backup Encryption

**Encrypt backups at rest:**
```bash
# pg_dump with encryption
pg_dump -h localhost -U chatbot_user -d chatbot_dev \
  --format=custom \
  --file=- | \
  openssl enc -aes-256-cbc -salt -pbkdf2 -out backup_encrypted.dump.enc

# Decrypt and restore
openssl enc -d -aes-256-cbc -pbkdf2 -in backup_encrypted.dump.enc | \
  pg_restore -U chatbot_user -d chatbot_restored
```

---

## 8. Monitoring and Alerting

### 8.1 Backup Health Checks

**CloudWatch alarms (RDS):**
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name chatbot-backup-failed \
  --alarm-description "Alert when automated backup fails" \
  --metric-name BackupRetentionPeriodStorageUsed \
  --namespace AWS/RDS \
  --statistic Average \
  --period 86400 \
  --threshold 0 \
  --comparison-operator LessThanThreshold \
  --evaluation-periods 1
```

**Daily backup verification script:**
```bash
#!/bin/bash
# check_backups.sh

LATEST_BACKUP=$(aws rds describe-db-snapshots \
  --db-instance-identifier chatbot-production \
  --query 'DBSnapshots[0].{Time:SnapshotCreateTime,Status:Status}' \
  --output json)

BACKUP_AGE=$(echo $LATEST_BACKUP | jq -r '.Time' | xargs -I {} date -d {} +%s)
CURRENT_TIME=$(date +%s)
AGE_HOURS=$(( ($CURRENT_TIME - $BACKUP_AGE) / 3600 ))

if [ $AGE_HOURS -gt 25 ]; then
  echo "ALERT: Latest backup is $AGE_HOURS hours old"
  # Send alert to Slack/PagerDuty
  exit 1
fi

echo "OK: Latest backup is $AGE_HOURS hours old"
```

---

## 9. Testing and Validation

### 9.1 Quarterly Restore Drill

**Procedure:**
```bash
# 1. Select random production backup
aws rds describe-db-snapshots \
  --db-instance-identifier chatbot-production \
  | jq -r '.DBSnapshots[7].DBSnapshotIdentifier'  # 1-week-old backup

# 2. Restore to test environment
# 3. Run integrity checks
# 4. Measure restoration time
# 5. Document results and lessons learned
```

### 9.2 Data Integrity Checks

**Post-restore validation queries:**
```sql
-- Check row counts
SELECT 
  'documents_document' as table_name, COUNT(*) as rows FROM documents_document
UNION ALL
SELECT 
  'documents_documentchunk', COUNT(*) FROM documents_documentchunk
UNION ALL
SELECT 
  'chat_conversation', COUNT(*) FROM chat_conversation
UNION ALL
SELECT 
  'chat_message', COUNT(*) FROM chat_message;

-- Check for orphaned records
SELECT COUNT(*) FROM documents_documentchunk 
WHERE document_id NOT IN (SELECT id FROM documents_document);

-- Verify embeddings
SELECT COUNT(*) FROM documents_documentchunk 
WHERE embedding IS NULL OR array_length(embedding, 1) != 384;

-- Check recent data
SELECT MAX(created_at) as latest_document FROM documents_document;
SELECT MAX(created_at) as latest_message FROM chat_message;
```

### 9.3 Performance Benchmarks

**Measure backup/restore times:**
```bash
# Backup benchmark
time pg_dump -h localhost -U chatbot_user -d chatbot_dev \
  --format=custom --file=benchmark_backup.dump

# Restore benchmark  
time pg_restore -U chatbot_user -d chatbot_test benchmark_backup.dump
```

**Expected times (approximate):**
- Small DB (<1GB): Backup 30s, Restore 60s
- Medium DB (1-10GB): Backup 5min, Restore 10min
- Large DB (10-100GB): Backup 30min, Restore 90min

---

## 10. Practical Test: Backup and Restore Dev Database

### Step-by-Step Test

**Test Objective:** Verify backup/restore procedures work correctly

**Prerequisites:**
- Development database running
- Docker available
- 5GB free disk space

**Steps:**

```bash
# 1. Create test data
docker-compose up -d postgres-dev
python manage.py seed_database --size small

# 2. Backup development database
pg_dump -h localhost -p 5432 -U chatbot_user -d chatbot_dev \
  --format=custom \
  --file=test_backup_$(date +%Y%m%d_%H%M%S).dump

# 3. Record row counts
psql -h localhost -p 5432 -U chatbot_user -d chatbot_dev -c \
  "SELECT COUNT(*) FROM documents_document;"

# 4. Start new container for restore test
docker run -d \
  --name postgres-restore-test \
  -e POSTGRES_DB=chatbot_restored \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5434:5432 \
  pgvector/pgvector:pg15

sleep 10

# 5. Restore to new container
pg_restore -h localhost -p 5434 -U postgres -d chatbot_restored \
  test_backup_*.dump

# 6. Verify data
psql -h localhost -p 5434 -U postgres -d chatbot_restored -c \
  "SELECT COUNT(*) FROM documents_document;"

# 7. Compare checksums (optional)
# Original DB
psql -h localhost -p 5432 -U chatbot_user -d chatbot_dev -t -c \
  "SELECT md5(array_agg(id::text ORDER BY id)::text) FROM documents_document;" \
  > original_checksum.txt

# Restored DB
psql -h localhost -p 5434 -U postgres -d chatbot_restored -t -c \
  "SELECT md5(array_agg(id::text ORDER BY id)::text) FROM documents_document;" \
  > restored_checksum.txt

diff original_checksum.txt restored_checksum.txt

# 8. Cleanup
docker stop postgres-restore-test
docker rm postgres-restore-test
rm test_backup_*.dump original_checksum.txt restored_checksum.txt
```

**Expected Result:**
- Backup completes without errors
- Restore completes without errors
- Row counts match between original and restored
- Checksums match (if compared)
- Total time < 5 minutes

---

## 11. Troubleshooting

### Common Issues

**Issue: Backup file too large**
```bash
# Solution: Use compression
pg_dump --compress=9 ...

# Or: Exclude large tables temporarily
pg_dump --exclude-table=documents_documentchunk ...
```

**Issue: Restore fails with permission errors**
```bash
# Solution: Use --no-owner --no-privileges
pg_restore --no-owner --no-privileges ...
```

**Issue: Restore is slow**
```bash
# Solution: Disable triggers during restore
pg_restore --disable-triggers ...

# Or: Increase parallel jobs
pg_restore --jobs=4 ...
```

**Issue: Out of disk space**
```bash
# Check space before backup
df -h

# Cleanup old backups
find /backup -name "*.dump" -mtime +30 -delete
```

---

## 12. Contacts and Escalation

**Backup/Restore Issues:**
- Database Admin: jeanpool@swisson.com
- DevOps Team: jeanpool@swisson.com
- On-call Engineer: jeanpool@swisson.com
- 
---

**Last Updated:** 30.09.2025 

**Version:** 1.0  

**Next Review:** Quarterly  

**Maintained By:** Jean Pool Pereyra Principe