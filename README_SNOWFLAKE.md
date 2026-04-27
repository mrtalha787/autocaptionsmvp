# Auto Captions MVP - Snowflake Version

This is the Snowflake-hosted version of the Auto Captions application. It replaces local file storage with Snowflake stages and uses Snowflake for persistent state management.

## Quick Start

### 1. Set Environment Variables
```bash
export SNOWFLAKE_USER=your_username
export SNOWFLAKE_PASSWORD=your_password
export SNOWFLAKE_ACCOUNT=xy12345.us-east-1
export SNOWFLAKE_WAREHOUSE=COMPUTE_WH
export SNOWFLAKE_DATABASE=AUTO_CAPTIONS
export SNOWFLAKE_SCHEMA=PUBLIC
```

Or create a `.env` file from `.env.example`:
```bash
cp .env.example .env
# Edit .env with your Snowflake credentials
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Pre-deployment Checks
```bash
python deploy_check.py
```

### 4. Run the Application

**Streamlit Web UI:**
```bash
streamlit run interfaces/streamlit_app.py
```

**FastAPI Server:**
```bash
uvicorn interfaces.fastapi_app:app --reload
```

## Architecture

### Core Components

```
app/
├── audio.py                 # Audio extraction (FFmpeg)
├── transcribe.py           # Speech-to-text (Whisper)
├── captions.py             # Caption processing
├── ass_renderer.py         # ASS subtitle generation
├── burner.py               # Caption rendering
├── snowflake_config.py     # Snowflake connection
├── snowflake_storage.py    # Stage file operations
├── snowflake_auth.py       # User authentication
└── snowflake_state.py      # Queue management
```

### Workflow

1. **Upload**: Video uploaded → Stored in `@auto_captions_uploads` stage
2. **Queue**: Job created in Snowflake `processing_queue` table
3. **Process**: Video downloaded → Audio extracted → Transcribed → Captions applied
4. **Output**: Processed video uploaded to `@auto_captions_outputs` stage
5. **Status**: Job marked as "done" in queue table

### Data Storage

| Data | Location | Purpose |
|------|----------|---------|
| User Credentials | `users` table | Authentication |
| Job Queue | `processing_queue` table | Track processing status |
| Input Videos | `@auto_captions_uploads` stage | Raw video files |
| Output Videos | `@auto_captions_outputs` stage | Processed videos |

## Configuration

### Required Snowflake Setup

```sql
-- Create database and schema
CREATE DATABASE AUTO_CAPTIONS;
CREATE SCHEMA AUTO_CAPTIONS.PUBLIC;

-- App will auto-create stages:
-- CREATE STAGE @auto_captions_uploads;
-- CREATE STAGE @auto_captions_outputs;
```

### Optional: Create Role

```sql
CREATE ROLE AUTO_CAPTIONS_APP;
GRANT ALL ON SCHEMA AUTO_CAPTIONS.PUBLIC TO ROLE AUTO_CAPTIONS_APP;
GRANT USAGE ON WAREHOUSE COMPUTE_WH TO ROLE AUTO_CAPTIONS_APP;
GRANT ROLE AUTO_CAPTIONS_APP TO USER your_username;
```

For detailed setup, see [SNOWFLAKE_SETUP.md](SNOWFLAKE_SETUP.md)

## API Endpoints (FastAPI)

### `/process` (POST)
Queue a single video for processing.

**Parameters:**
- `file`: Video file (mp4, mov, mkv)
- `username`: User identifier
- `style`: Caption style (hormozi, elegant, cinematic)
- `emphasized`: Comma-separated words to emphasize
- `pos_x`, `pos_y`: Caption position (0-1)
- `fast`: Use fast rendering
- `auto_emphasis`: Auto-detect emphasis words

**Response:**
```json
{
  "job_id": "uuid",
  "filename": "video.mp4",
  "status": "queued",
  "message": "Video queued for processing"
}
```

### `/job/{job_id}` (GET)
Get job status and details.

### `/process-batch` (POST)
Queue multiple videos (up to 30).

For more details, see [SNOWFLAKE_SETUP.md](SNOWFLAKE_SETUP.md#snowflake-environment-configuration)

## Web UI (Streamlit)

- **Login/Registration**: User accounts stored in Snowflake
- **Upload**: Add videos to your queue
- **Process**: Run sequential processing on your videos
- **Monitor**: Track job status and view outputs
- **Download**: Get processed videos from Snowflake stages

## Migration from Local Version

If upgrading from the local file-based version, see [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for:
- Backup procedures
- User account migration
- Video file migration
- Verification steps

## Key Modules

### `snowflake_config.py`
Singleton connection manager for Snowflake.

```python
from app.snowflake_config import SnowflakeConnection, init_snowflake_tables

sf = SnowflakeConnection()
sf.execute("SELECT * FROM users")
init_snowflake_tables()  # Creates required tables if missing
```

### `snowflake_storage.py`
Handle file uploads/downloads to/from stages.

```python
from app.snowflake_storage import SnowflakeStageStorage

# Upload
stage_path = SnowflakeStageStorage.upload_file(
    "local_file.mp4",
    SnowflakeStageStorage.UPLOADS_STAGE,
    "remote_name.mp4"
)

# Download
local_path = SnowflakeStageStorage.download_file(stage_path, "local.mp4")

# List
files = SnowflakeStageStorage.list_stage_files()
```

### `snowflake_auth.py`
User authentication backed by Snowflake.

```python
from app.snowflake_auth import register_user, authenticate_user

register_user("username", "password")
is_valid = authenticate_user("username", "password")
```

### `snowflake_state.py`
Persistent queue management in Snowflake.

```python
from app.snowflake_state import SnowflakeQueue

# Create job
job = SnowflakeQueue.create_job(
    username="user1",
    filename="video.mp4",
    file_hash="abc123",
    style="hormozi",
    pos_x=0.5, pos_y=0.9,
    fast=True,
    emphasized_words=["important", "words"],
    auto_emphasis=True,
)

# Get jobs
pending = SnowflakeQueue.get_pending_jobs()
user_jobs = SnowflakeQueue.get_user_queue("user1")

# Update status
SnowflakeQueue.update_job_status(
    job_id="123",
    status="done",
    output_stage_path="@out/file.mp4",
    transcript="...",
    burn_seconds=45.2,
)
```

## Troubleshooting

### Connection Issues
1. Verify environment variables: `python deploy_check.py`
2. Check Snowflake credentials are correct
3. Ensure warehouse is active

### Stages Not Found
```sql
CREATE STAGE @auto_captions_uploads;
CREATE STAGE @auto_captions_outputs;
```

### Audio Processing Slow
- Check FFmpeg installation: `which ffmpeg`
- Ensure video format is supported
- Try smaller resolution input

### Database Errors
1. Verify schema exists: `SHOW SCHEMAS`;
2. Check table created: `SHOW TABLES;`
3. Run initialization: `python deploy_check.py` → Database Initialization

For detailed troubleshooting, see [SNOWFLAKE_SETUP.md#troubleshooting](SNOWFLAKE_SETUP.md#troubleshooting)

## Performance

### Typical Processing Times
- Extract audio: 5-15 seconds
- Transcribe (Whisper): 30-120 seconds (depends on audio length)
- Render captions: 30-300 seconds (depends on video resolution)

**Total**: 1-10 minutes per video

### Scaling
- Single processing worker: Use `SMALL` warehouse
- 2-4 workers: Use `MEDIUM` warehouse
- 5+ workers: Use `LARGE` warehouse

## Cost Optimization

### Warehouse Configuration
```sql
ALTER WAREHOUSE COMPUTE_WH SET AUTO_SUSPEND = 5;  -- Suspend after 5 min idle
ALTER WAREHOUSE COMPUTE_WH SET AUTO_RESUME = TRUE;
```

### Storage Cleanup
```sql
-- Delete old jobs (> 30 days) to free space
DELETE FROM processing_queue 
WHERE updated_at < CURRENT_TIMESTAMP - INTERVAL '30 days'
  AND status = 'done';
```

## Development

### Running Tests
```bash
pytest tests/
```

### Code Style
```bash
black app/
flake8 app/
```

### Local Development
To test locally without Snowflake (using local storage):
```bash
git checkout local-version
pip install -r requirements.txt
streamlit run interfaces/streamlit_app.py
```

## Security

- **Credentials**: Use environment variables, never commit `.env`
- **Encryption**: Enable Snowflake encryption for stages
- **Access Control**: Use roles with minimal permissions
- **Monitoring**: Check Snowflake audit logs
- **Backups**: Snowflake Time Travel retains 90 days by default

For security best practices, see [SNOWFLAKE_SETUP.md#security-best-practices](SNOWFLAKE_SETUP.md#security-best-practices)

## License

[Your License Here]

## Support

For issues:
1. Check troubleshooting sections above
2. Review [SNOWFLAKE_SETUP.md](SNOWFLAKE_SETUP.md)
3. See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for upgrade help
4. Run `python deploy_check.py` for diagnostics

For Snowflake-specific help: https://docs.snowflake.com
