# Migration Guide: Local to Snowflake

This guide helps you migrate from the local file-based version to the Snowflake-hosted version.

## Overview

The Snowflake version moves all storage and state from local files to Snowflake:

| Component | Local Version | Snowflake Version |
|-----------|---------------|-------------------|
| User Auth | `storage/users.json` | `users` table |
| Video Storage | `storage/uploads/` | `@auto_captions_uploads` stage |
| Output Videos | `storage/outputs/` | `@auto_captions_outputs` stage |
| Job Queue | In-memory session state | `processing_queue` table |

## Step 1: Backup Local Data

```bash
# Create backups of local storage
cp -r storage storage.backup
```

## Step 2: Set Up Snowflake

Follow the setup instructions in `SNOWFLAKE_SETUP.md`:

1. Create database and schema
2. Set environment variables
3. Install dependencies
4. Test connection

## Step 3: Migrate User Accounts

If you have existing users in `storage/users.json`:

```bash
python scripts/migrate_users.py
```

This script:
- Reads `storage/users.json`
- Creates accounts in Snowflake `users` table
- Preserves password hashes and salts

### Manual Migration (if script not available)

```python
import json
from app.snowflake_config import SnowflakeConnection
from pathlib import Path

# Read local users
users_file = Path("storage/users.json")
with open(users_file) as f:
    users = json.load(f)

# Insert into Snowflake
sf = SnowflakeConnection()
for username, data in users.items():
    sf.execute_update(
        "INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)",
        (username, data["password"], data["salt"])
    )
print(f"Migrated {len(users)} users")
```

## Step 4: Migrate Video Files (Optional)

If you have processed videos to preserve:

```bash
python scripts/migrate_videos.py --source storage/outputs/ --stage @auto_captions_outputs
```

This uploads all video files from local storage to Snowflake stages.

### Manual Video Upload

```python
from app.snowflake_storage import SnowflakeStageStorage
from pathlib import Path

outputs_dir = Path("storage/outputs")
for video_file in outputs_dir.glob("*.mp4"):
    stage_path = SnowflakeStageStorage.upload_file(
        video_file,
        SnowflakeStageStorage.OUTPUTS_STAGE,
        video_file.name
    )
    print(f"Uploaded {video_file.name} to {stage_path}")
```

## Step 5: Test with New Version

```bash
# Install updated dependencies
pip install -r requirements.txt

# Run Streamlit app
streamlit run interfaces/streamlit_app.py

# Or start FastAPI server
uvicorn interfaces.fastapi_app:app --reload
```

## Verification Checklist

- [ ] Snowflake connection successful
- [ ] Database tables created (`users`, `processing_queue`, `temp_audio_files`)
- [ ] Stages created (`@auto_captions_uploads`, `@auto_captions_outputs`)
- [ ] Can login with migrated user account
- [ ] Can upload new videos
- [ ] Can process videos successfully
- [ ] Output videos appear in `@auto_captions_outputs` stage

## Troubleshooting Migration

### Users Not Migrating

```sql
-- Check if users were created
SELECT COUNT(*) FROM users;

-- Check specific user
SELECT * FROM users WHERE username = 'test_user';
```

### Stages Not Found

```sql
-- List all stages
SELECT * FROM INFORMATION_SCHEMA.STAGES;

-- Create manually if needed
CREATE STAGE @auto_captions_uploads;
CREATE STAGE @auto_captions_outputs;
```

### Connection Issues

- Verify `SNOWFLAKE_ACCOUNT` format
- Check credentials with Snowflake Web UI login
- Confirm warehouse is active

## Post-Migration Cleanup

### Keep Local Backup (Recommended)

```bash
# Archive the old local version
tar -czf autocaptions-local-backup-$(date +%Y%m%d).tar.gz storage/ interfaces/ app/
```

### Remove Local Secrets (Production)

```bash
# Remove files containing sensitive data
rm -f storage/users.json
rm -f .env  # Don't keep plain-text credentials

# Use secure credential management instead:
# - AWS Secrets Manager
# - Azure Key Vault
# - HashiCorp Vault
# - Snowflake Native App Store
```

## Rollback to Local Version

If you need to revert:

```bash
# Switch back to local branch/tag
git checkout local-version

# Or restore from backup
rm -rf storage
cp -r storage.backup storage

# Install original dependencies
pip install -r requirements.txt

# Run original apps
streamlit run interfaces/streamlit_app.py
```

## Data Retention

### In Snowflake
- User accounts persist indefinitely
- Processed videos stored in stages (configurable retention)
- Job history in `processing_queue` table

### Cleanup Options

```sql
-- Delete jobs older than 30 days
DELETE FROM processing_queue 
WHERE updated_at < CURRENT_TIMESTAMP - INTERVAL '30 days'
  AND status = 'done';

-- Archive to cold storage (Snowflake Time Travel)
-- Automatically kept for 90 days (default)
```

## Performance Comparisons

| Metric | Local | Snowflake |
|--------|-------|-----------|
| Video Upload | Filesystem | Network (faster for large) |
| Video Download | Filesystem | Network (network-bound) |
| Job Persistence | Lost on restart | Always persisted |
| Multi-user Support | Session-isolated | Shared across users |
| Storage Scaling | Limited by disk | Unlimited |

## Best Practices

1. **Regular Backups**: Schedule Snowflake backups
2. **Monitor Costs**: Track warehouse usage
3. **Cleanup Old Jobs**: Archive/delete after retention period
4. **Use Roles**: Don't use SYSADMIN for app user
5. **Encrypt Stages**: Consider using encryption for sensitive videos

## Support

For issues:
1. Check `SNOWFLAKE_SETUP.md` troubleshooting section
2. Review Snowflake documentation: https://docs.snowflake.com
3. Check application logs for error messages
4. Verify environment variables are set correctly

## FAQ

**Q: Can I run both versions simultaneously?**
A: No, they share the same database. Choose one version.

**Q: Will my local videos disappear?**
A: No, they remain in `storage/` directory until you delete them.

**Q: How do I download videos from stages?**
A: Use Snowflake Web UI or the `download_file()` method in the app.

**Q: What happens if Snowflake goes down?**
A: The app will fail to start. Set up alerts for warehouse downtime.

**Q: How do I scale to multiple workers?**
A: All workers read from same `processing_queue` table in Snowflake.
