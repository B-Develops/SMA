# Database Backup and Recovery Strategy

## Overview

SarkinMota uses automated database backups to prevent data loss and enable disaster recovery. This document describes the backup strategy, retention policies, and recovery procedures.

## Backup Strategy

### Automated Backups

Backups are created using `scripts/backup_db.py`. **PostgreSQL is the only
supported database**, so the script is PostgreSQL-only.

- Uses `pg_dump` in custom format (`-Fc`) for compressed backups
- Taken inside a single transaction, so an archive is never a torn snapshot
- Dumped with `--no-owner --no-acl`, so an archive can be restored as a
  different role
- Backup file format: `<dbname>_YYYYMMDD_HHMMSS.dump`
- Requires the PostgreSQL client tools (`pg_dump`) on `PATH`

See [`POSTGRES.md`](POSTGRES.md) for installation and connection setup.

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
# Inspect the archive first
python scripts/restore_db.py backups/sarkinmota_20260927_120000.dump --list

# Restore into the database named by DATABASE_URL
python scripts/restore_db.py backups/sarkinmota_20260927_120000.dump
```

A restore over a database that already has tables is **refused** unless you pass
`--force`, because `pg_restore --clean` drops the existing objects. To restore
into a scratch database instead:

```bash
python scripts/restore_db.py backups/sarkinmota_20260927_120000.dump \
    --db-url postgresql://temp_user:pass@localhost/temp_restore
```

### Point-in-Time Recovery

Use WAL (Write-Ahead Logging) archiving for point-in-time recovery:

```sql
-- Enable WAL archiving in postgresql.conf
wal_level = replica
archive_mode = on
archive_command = 'cp %p /path/to/wal_archive/%f'
```

### Partial Restore

To restore a single table or subset of data from a dump:

```bash
# List contents of dump
pg_restore -l backups/sarkinmota.dump

# Restore specific table only
pg_restore -d sarkinmota -t users backups/sarkinmota.dump
```

## Verification

### Verify Backup Integrity

```bash
# Validate the archive can be read and list its contents
python scripts/restore_db.py backups/sarkinmota.dump --list

# Or with the client tool directly
pg_restore --list backups/sarkinmota.dump
```

`backup_db.py` also fails if `pg_dump` produced a zero-byte file, so an empty
archive can never be reported as a successful backup.

### Test Restore Procedure

Run a restore to a temporary database monthly to verify backups are usable:

```bash
python scripts/restore_db.py backups/latest.dump \
    --db-url postgresql://temp_user:pass@localhost/temp_restore
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
2. Check server-side state: `SELECT * FROM pg_stat_database;` and
   `SELECT * FROM pg_locks WHERE NOT granted;`
3. If the data is unreadable, restore from the most recent valid backup
4. If only some tables are affected, restore those individually with
   `pg_restore -t <table>`

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
│   ├── backup_db.py      # PostgreSQL backup script (pg_dump)
│   ├── restore_db.py     # PostgreSQL restore script (pg_restore)
│   └── schedule_backup.py # Windows Task Scheduler wrapper
├── backups/              # Backup storage (gitignored)
├── docs/
│   ├── BACKUP.md         # This document
│   └── POSTGRES.md       # PostgreSQL setup and operations
└── logs/
    └── backup.log        # Backup execution logs
```

## Security

- Backup files contain all application data — treat them as sensitive
- Use encryption at rest for off-site backups (e.g., GPG, AES-256)
- Restrict backup directory permissions to the application user only
- Never commit backup files to version control
- Rotate backup encryption keys annually
