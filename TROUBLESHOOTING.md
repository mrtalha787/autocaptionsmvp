# Snowflake Troubleshooting Guide

## Error: "'NoneType' object has no attribute 'find'"

This error indicates that environment variables are not set or connection configuration is incomplete.

### Quick Fix (5 minutes)

1. **Set Environment Variables** 
   ```bash
   # Copy template
   cp .env.example .env
   
   # Edit .env with your Snowflake credentials
   # On Linux/macOS: nano .env
   # On Windows: notepad .env
   ```

2. **Load Environment Variables**
   
   **Linux/macOS:**
   ```bash
   export $(cat .env | xargs)
   ```
   
   **Windows PowerShell:**
   ```powershell
   Get-Content .env | ForEach-Object {
       $name, $value = $_ -split '=', 2
       [Environment]::SetEnvironmentVariable($name, $value)
   }
   ```
   
   **Windows Command Prompt:**
   ```cmd
   for /f "tokens=*" %%a in (.env) do set %%a
   ```

3. **Run Diagnostics**
   ```bash
   python snowflake_diagnose.py
   ```

4. **Verify Setup**
   ```bash
   python deploy_check.py
   ```

---

## Common Error Messages

### "Missing required environment variables"

**Cause**: Environment variables not set

**Solution**:
```bash
# Check which are missing
python snowflake_diagnose.py

# Set them
export SNOWFLAKE_USER=your_username
export SNOWFLAKE_PASSWORD=your_password
export SNOWFLAKE_ACCOUNT=xy12345.us-east-1
export SNOWFLAKE_WAREHOUSE=COMPUTE_WH
export SNOWFLAKE_DATABASE=AUTO_CAPTIONS
export SNOWFLAKE_SCHEMA=PUBLIC
```

### "Failed to connect to Snowflake"

**Causes & Solutions**:

1. **Wrong SNOWFLAKE_ACCOUNT format**
   - ❌ Wrong: `myaccount` or `myaccount.snowflakecomputing.com`
   - ✓ Right: `xy12345.us-east-1`
   - Find yours at: Snowflake Web UI → Account → Account Locator

2. **Invalid credentials**
   - Verify username/password work in Snowflake Web UI
   - Check password doesn't have special characters that need escaping

3. **Warehouse not running**
   - Log into Snowflake Web UI
   - Check that COMPUTE_WH (or your warehouse) is active
   - Resume it if suspended

4. **Network/VPN issues**
   - Check firewall allows outbound to Snowflake
   - If using VPN, try disconnecting/reconnecting

---

## Diagnostic Steps

### Step 1: Verify Environment Variables

```bash
echo $SNOWFLAKE_USER
echo $SNOWFLAKE_ACCOUNT
echo $SNOWFLAKE_WAREHOUSE
```

If nothing prints, variables aren't set. Go back and load .env file.

### Step 2: Test Python Import

```bash
python -c "import snowflake.connector; print('✓ Snowflake package installed')"
```

If this fails, reinstall:
```bash
pip install -r requirements.txt
```

### Step 3: Run Full Diagnostics

```bash
python snowflake_diagnose.py
```

This will test:
- Environment variables
- Package installation
- Snowflake connection
- Table creation
- Stage creation

### Step 4: Verify Snowflake Account

1. Go to Snowflake Web UI
2. Your account name is shown in the browser URL:
   - URL: `https://xy12345.us-east-1.snowflakecomputing.com`
   - Account: `xy12345.us-east-1`

3. Ensure:
   - Database exists: `AUTO_CAPTIONS`
   - Schema exists: `PUBLIC`
   - Warehouse exists: `COMPUTE_WH` (or your warehouse name)
   - Warehouse is running

---

## Snowflake Setup Checklist

- [ ] Account created and login works
- [ ] Database created: `AUTO_CAPTIONS`
- [ ] Schema created: `PUBLIC`
- [ ] Warehouse created: `COMPUTE_WH`
- [ ] Warehouse is active/running
- [ ] User has permissions on database/schema/warehouse

### Create Missing Items

```sql
-- In Snowflake SQL Editor

-- Create database (if missing)
CREATE DATABASE IF NOT EXISTS AUTO_CAPTIONS;

-- Create schema (if missing)
CREATE SCHEMA IF NOT EXISTS AUTO_CAPTIONS.PUBLIC;

-- Create warehouse (if missing)
CREATE WAREHOUSE IF NOT EXISTS COMPUTE_WH 
  WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 5
  AUTO_RESUME = TRUE;

-- Grant permissions
GRANT USAGE ON DATABASE AUTO_CAPTIONS TO ROLE SYSADMIN;
GRANT USAGE ON SCHEMA AUTO_CAPTIONS.PUBLIC TO ROLE SYSADMIN;
GRANT USAGE ON WAREHOUSE COMPUTE_WH TO ROLE SYSADMIN;
```

---

## Still Getting Errors?

### Option 1: Detailed Error Investigation

```bash
# Run with Python verbose output
python -c "
import os
from app.snowflake_config import SnowflakeConnection

try:
    sf = SnowflakeConnection()
    conn = sf.connect()
    print('✓ Connected!')
except Exception as e:
    print(f'✗ Error: {type(e).__name__}')
    print(f'  Message: {str(e)}')
    import traceback
    traceback.print_exc()
"
```

### Option 2: Check Snowflake Logs

In Snowflake Web UI:
1. Go to Account → Activity → Query History
2. Look for recent failed queries
3. Error messages there can help diagnose issues

### Option 3: Restart Everything Fresh

```bash
# 1. Close all Python processes
# 2. Load env vars fresh
export $(cat .env | xargs)

# 3. Run diagnostics
python snowflake_diagnose.py

# 4. If still failing, restart your bash/terminal
```

## Getting Help

When asking for help, provide output from:

```bash
python snowflake_diagnose.py 2>&1 | tee diagnostic_output.txt
```

Share the contents of `diagnostic_output.txt` (without sensitive data like passwords).

---

## Key Environment Variables Explained

| Variable | Example | Purpose |
|----------|---------|---------|
| `SNOWFLAKE_USER` | `your_email@company.com` | Snowflake login username |
| `SNOWFLAKE_PASSWORD` | `MyP@ssw0rd` | Snowflake login password |
| `SNOWFLAKE_ACCOUNT` | `xy12345.us-east-1` | Account identifier (from Web UI URL) |
| `SNOWFLAKE_WAREHOUSE` | `COMPUTE_WH` | Virtual warehouse for queries |
| `SNOWFLAKE_DATABASE` | `AUTO_CAPTIONS` | Database name |
| `SNOWFLAKE_SCHEMA` | `PUBLIC` | Schema within database |
| `SNOWFLAKE_ROLE` | `SYSADMIN` | User role (optional, defaults to SYSADMIN) |

---

## FAQ

**Q: Where do I find my SNOWFLAKE_ACCOUNT?**
A: In Snowflake Web UI, look at the URL in your browser. It's in the format `https://ACCOUNT.snowflakecomputing.com`. Use just the account part with region, e.g., `xy12345.us-east-1`.

**Q: Can I use different credentials per app?**
A: Yes, create a separate user/role in Snowflake with limited permissions for each app.

**Q: What if I don't have a Snowflake account?**
A: Sign up for free at https://signup.snowflake.com (includes $400 free credits)

**Q: Do I need to manually create tables?**
A: No, the app creates them automatically on first run.

**Q: How do I test the connection without running the app?**
A: Run `python snowflake_diagnose.py`

---

## Next Steps After Fixing

Once all diagnostics pass:

```bash
# Run the Streamlit app
streamlit run interfaces/streamlit_app.py

# Or the FastAPI server
uvicorn interfaces.fastapi_app:app --reload
```
