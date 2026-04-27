# Snowflake Environment Configuration Guide

## Required Environment Variables

To run this application on Snowflake, set the following environment variables:

```bash
# Snowflake Connection
export SNOWFLAKE_USER=your_username
export SNOWFLAKE_PASSWORD=your_password
export SNOWFLAKE_ACCOUNT=xy12345.region  # e.g., ab12345.us-east-1
export SNOWFLAKE_WAREHOUSE=COMPUTE_WH    # Your warehouse name
export SNOWFLAKE_DATABASE=AUTO_CAPTIONS  # Database to use
export SNOWFLAKE_SCHEMA=PUBLIC           # Schema to use
export SNOWFLAKE_ROLE=SYSADMIN           # Role with appropriate permissions (optional, defaults to SYSADMIN)
```

## Setup Instructions

### 1. Create Snowflake Database and Schema

```sql
-- In Snowflake SQL Editor
CREATE DATABASE AUTO_CAPTIONS;
CREATE SCHEMA AUTO_CAPTIONS.PUBLIC;
```

### 2. Create Required Internal Stages

The application will automatically create these stages on first run:

```sql
-- These are created automatically by the app, but you can create them manually if needed:
CREATE STAGE @auto_captions_uploads;
CREATE STAGE @auto_captions_outputs;
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Test Snowflake Connection

```bash
python -c "from app.snowflake_config import SnowflakeConnection; sc = SnowflakeConnection(); print('Connected!' if sc.connect() else 'Failed')"
```

### 5. Initialize Database Tables

The app automatically initializes tables on startup. If you need to do it manually:

```bash
python -c "from app.snowflake_config import init_snowflake_tables; init_snowflake_tables(); print('Tables initialized')"
```

## Running the Application

### Streamlit App
```bash
streamlit run interfaces/streamlit_app.py
```

### FastAPI Server
```bash
uvicorn interfaces.fastapi_app:app --reload
```

## Key Changes from Original

### File Storage
- **Before**: Videos stored in local `storage/uploads/` and `storage/outputs/`
- **After**: Videos stored in Snowflake internal stages

### User Authentication
- **Before**: JSON file at `storage/users.json`
- **After**: Snowflake SQL table `users`

### Queue/Session State
- **Before**: In-memory `st.session_state` (lost after session)
- **After**: Persistent Snowflake table `processing_queue`

## New Modules

### `app/snowflake_config.py`
- `SnowflakeConnection`: Singleton for managing DB connections
- `init_snowflake_tables()`: Creates required tables

### `app/snowflake_storage.py`
- `SnowflakeStageStorage`: Handles file uploads/downloads to stages
- Stage operations (PUT, GET, LIST, REMOVE)

### `app/snowflake_auth.py`
- `register_user()`: Create new user account
- `authenticate_user()`: Verify credentials
- `load_user()`: Fetch user info

### `app/snowflake_state.py`
- `QueueJob`: Represents a processing job
- `SnowflakeQueue`: Persistent job queue management

## Architecture Changes

### Data Flow
1. User uploads video → Saved to Snowflake stage
2. Job created in `processing_queue` table
3. Processing reads from stage, processes locally
4. Output uploaded back to stage
5. Job status updated in table

### Session Persistence
- Queue survives across browser sessions
- Multiple users can have concurrent queues
- Job history persists indefinitely

### Scalability
- Can run multiple processing workers reading from same queue
- Snowflake handles concurrent access
- No local storage bottlenecks

## Snowflake Role and Permissions

Ensure your Snowflake user has:
- `CREATE DATABASE` or use existing database
- `CREATE SCHEMA`
- `CREATE STAGE`
- `CREATE TABLE`
- Read/Write on created stages

Minimal role setup:
```sql
-- Create a role for the app
CREATE ROLE AUTO_CAPTIONS_APP;

-- Grant permissions
GRANT CREATE STAGE ON SCHEMA AUTO_CAPTIONS.PUBLIC TO ROLE AUTO_CAPTIONS_APP;
GRANT CREATE TABLE ON SCHEMA AUTO_CAPTIONS.PUBLIC TO ROLE AUTO_CAPTIONS_APP;
GRANT USAGE ON WAREHOUSE COMPUTE_WH TO ROLE AUTO_CAPTIONS_APP;

-- Assign to user
GRANT ROLE AUTO_CAPTIONS_APP TO USER <your_username>;
```

## Troubleshooting

### Connection Failed
- Verify `SNOWFLAKE_ACCOUNT` format (e.g., `xy12345.us-east-1`)
- Check credentials are correct
- Ensure user can login to Snowflake Web UI

### Stages Not Created
- Check warehouse is active
- Verify schema exists
- Run: `SELECT * FROM INFORMATION_SCHEMA.STAGES;`

### Permission Denied
- Check role has required permissions
- Verify warehouse is assigned to role
- Check schema permissions

### Files Not Uploading
- Verify stage path format: `@stage_name/path/file.ext`
- Check FFmpeg is installed (`which ffmpeg`)
- Test manual PUT: `PUT file:///tmp/test.txt @auto_captions_uploads`

## Performance Tuning

### Warehouse Sizing
- Start with `X-SMALL` (1 credit/hour)
- Scale up to `SMALL`, `MEDIUM`, etc. if processing is slow
- Consider auto-suspend: 5-10 minutes

### Network Bandwidth
- Processing happens locally, only video transfer is network-bound
- Large videos may take time to upload/download
- Consider pre-compression before upload

## Security Best Practices

1. **Never commit credentials**: Use environment variables
2. **Use encrypted connection**: Snowflake uses TLS by default
3. **Rotate passwords regularly**
4. **Use role-based access**: Create limited role per application
5. **Monitor stage activity**: `SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.STAGE_FILE_LIST_HISTORY`

## Migration from Local Storage

If migrating from the original local version:

1. Export users from `storage/users.json`
2. Import into Snowflake `users` table
3. Migrate videos from `storage/uploads/` to stages
4. Update job queue in `processing_queue` table

Contact Snowflake support if you need help with large file migrations.
