# Database Backup and Recovery Strategy

## Overview

SarkinMota uses automated database backups to prevent data loss and enable disaster recovery. This document describes the backup strategy, retention policies, and recovery procedures.

## Backup Strategy

### Automated Backups

Backups are created using `scripts/backup_db.py`, which supports both **SQLite** (default) and **PostgreSQL** (production) databases.

#### SQLite (Development / Default)

- Uses SQLite's native `backup()` API for consistent, non-blocking copies
- Backup file format: `sarkin_mota_YYYYMMDD_HHMMSS.bak`

#### PostgreSQL (Production)

- Uses `pg_dump` in custom format (`-F c`) for efficient, compressed backups
- Backup file format: `<dbname>_YYYYMMDD_HHMMSS.dump`

### Scheduling

| Environment | Frequency | Retention |
|---|---|---|
| Production | Every 6 hours | 30 days |
| Staging | Daily | 14 days |
| Development | On-demand | 7 days |

#### Recommended Cron (Linux/macOS)

```
0 */6 * * * cd /path/to/sarkinmota && python scripts/backup_db.py >> logs/backup.log 2>&1
```

#### Recommended Task Scheduler (Windows)

Create a scheduled task running every 6 hours:
```
Program: python
Arguments: scripts/backup_db.py
Start in: C:\path\to\sarkinmota
```

## Backup Storage

### Local Storage

- Backups are stored in `<project_root>/backups/` by default
- Old backups are automatically pruned based on the retention policy

### Off-Site Storage (Production)

For production deployments, configure additional remote storage:

#### AWS S3

```bash
# Install AWS CLI
pip install awscli

# Upload backup to S3
aws s3 cp backups/<file> s3://your-bucket/sarkinmota-backups/
```

#### SFTP / Remote Server

```bash
# Upload to remote server
scp backups/<file> user@backup-server:/path/to/backups/
```

## Recovery Procedures

### Full Database Restore

```bash
# SQLite
python scripts/restore_db.py backups/sarkin_mota_20240101_120000.bak

# PostgreSQL
python scripts/restore_db.py backups/sarkinmota_20240101_120000.dump
```

### Point-in-Time Recovery (PostgreSQL Only)

For PostgreSQL, use WAL (Write-Ahead Logging) archiving for point-in-time recovery:

```sql
-- Enable WAL archiving in postgresql.conf
wal_level = replica
archive_mode = on
archive_command = 'cp %p /path/to/wal_archive/%f'
```

### Partial Restore

To restore a single table or subset of data from a PostgreSQL dump:

```bash
# List contents of dump
pg_restore -l backups/sarkinmota.dump

# Restore specific table only
pg_restore -d sarkinmota -t users backups/sarkinmota.dump
```

## Verification

### Verify Backup Integrity

```bash
# SQLite - open and check tables
sqlite3 backups/sarkin_mota_20240101_120000.bak "SELECT count(*) FROM users;"

# PostgreSQL - validate dump
pg_restore --list backups/sarkinmota.dump
```

### Test Restore Procedure

Run a restore to a temporary database monthly to verify backups are usable:

```bash
# SQLite
python scripts/restore_db.py backups/latest.bak --force

# PostgreSQL
python scripts/restore_db.py backups/latest.dump --db-url postgresql://temp_user:pass@localhost/temp_restore
```

## Monitoring

### Backup Health Check

Add to your monitoring dashboard:

```python
# health check in app/__init__.py
def health_check():
    last_backup = get_last_backup_time()
    if datetime.utcnow() - last_backup > timedelta(hours=12):
        return {"status": "degraded", "reason": "backup overdue"}, 503
```

### Alerting

Trigger alerts when:
- No backup has been created in >12 hours
- Backup file size is <10% of expected (indicates empty/corrupt backup)
- Backup process exits with non-zero status

## Disaster Recovery Runbook

### Scenario 1: Accidental Data Deletion

1. Identify the time of the incident
2. Find the most recent backup before the incident
3. Create a fresh database from the backup
4. Export any data created after the backup (logs, audit trail)
5. Merge data if possible, or accept data loss for the window

### Scenario 2: Database Corruption

1. Stop the application
2. Attempt SQLite integrity check: `PRAGMA integrity_check;`
3. If corrupted, restore from most recent valid backup
4. If PostgreSQL, check `pg_stat_database` and `pg_locks`
5. Restore from backup

### Scenario 3: Complete Server Failure

1. Provision new server with matching environment
2. Install dependencies: `pip install -r requirements.txt`
3. Restore database from latest backup
4. Update DNS/load balancer to point to new server
5. Verify application health check passes

## File Structure

```
sarkinmota/
├── scripts/
│   ├── backup_db.py      # Database backup script
│   └── restore_db.py     # Database restore script
├── backups/              # Backup storage (gitignored)
├── docs/
│   └── BACKUP.md         # This document
└── logs/
    └── backup.log        # Backup execution logs
```

## Security

- Backup files contain all application data — treat them as sensitive
- Use encryption at rest for off-site backups (e.g., GPG, AES-256)
- Restrict backup directory permissions to the application user only
- Never commit backup files to version control
- Rotate backup encryption keys annually
