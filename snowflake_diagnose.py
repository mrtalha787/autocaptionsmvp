#!/usr/bin/env python3
"""
Quick Snowflake connection diagnostic tool.
Run this first if you're getting connection errors.
"""

import os
import sys
from pathlib import Path

# Add app to path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))


def check_env_vars():
    """Check if environment variables are set."""
    print("=" * 60)
    print("1. Checking Environment Variables...")
    print("=" * 60)
    
    required_vars = [
        "SNOWFLAKE_USER",
        "SNOWFLAKE_PASSWORD",
        "SNOWFLAKE_ACCOUNT",
        "SNOWFLAKE_WAREHOUSE",
        "SNOWFLAKE_DATABASE",
        "SNOWFLAKE_SCHEMA",
    ]
    
    all_set = True
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            print(f"  ❌ {var}: NOT SET")
            all_set = False
        else:
            if var == "SNOWFLAKE_PASSWORD":
                display = "*" * len(value)
            else:
                display = value
            print(f"  ✓ {var}: {display}")
    
    print()
    return all_set


def check_snowflake_package():
    """Check if snowflake package is installed."""
    print("=" * 60)
    print("2. Checking Snowflake Package...")
    print("=" * 60)
    
    try:
        import snowflake.connector
        print(f"  ✓ snowflake-connector-python installed")
        return True
    except ImportError:
        print(f"  ❌ snowflake-connector-python NOT installed")
        print(f"  Install with: pip install -r requirements.txt")
        return False


def test_connection():
    """Try to connect to Snowflake."""
    print("=" * 60)
    print("3. Testing Snowflake Connection...")
    print("=" * 60)
    
    try:
        from app.snowflake_config import SnowflakeConnection
        
        print("  Attempting to connect...")
        sf = SnowflakeConnection()
        conn = sf.connect()
        print("  ✓ Connection successful!")
        
        # Test a simple query
        cursor = conn.cursor()
        cursor.execute("SELECT 1 as test")
        result = cursor.fetchone()
        cursor.close()
        print("  ✓ Query execution successful!")
        
        return True
    except ValueError as e:
        print(f"  ❌ Configuration error: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Connection failed: {type(e).__name__}")
        print(f"     Error: {str(e)}")
        
        # Help with common errors
        if "find" in str(e).lower():
            print("\n  💡 This error often means:")
            print("     - SNOWFLAKE_ACCOUNT format is wrong (should be xy12345.region)")
            print("     - Try: xy12345.us-east-1 (include region)")
        elif "authentication" in str(e).lower() or "403" in str(e):
            print("\n  💡 This error often means:")
            print("     - Username or password is incorrect")
            print("     - Check if user exists in Snowflake")
        elif "warehouse" in str(e).lower():
            print("\n  💡 This error often means:")
            print("     - Warehouse doesn't exist or is not accessible")
            print("     - Check SNOWFLAKE_WAREHOUSE value")
        
        return False


def test_table_creation():
    """Test if we can create tables."""
    print("=" * 60)
    print("4. Testing Table Creation...")
    print("=" * 60)
    
    try:
        from app.snowflake_config import init_snowflake_tables
        
        print("  Initializing tables...")
        init_snowflake_tables()
        print("  ✓ Tables created successfully!")
        return True
    except Exception as e:
        print(f"  ❌ Table creation failed: {type(e).__name__}")
        print(f"     Error: {str(e)}")
        
        if "syntax" in str(e).lower():
            print("\n  💡 SQL syntax error - Snowflake version mismatch?")
        elif "permission" in str(e).lower():
            print("\n  💡 Permission denied - check role permissions")
        
        return False


def test_stage_creation():
    """Test if we can create stages."""
    print("=" * 60)
    print("5. Testing Stage Creation...")
    print("=" * 60)
    
    try:
        from app.snowflake_storage import SnowflakeStageStorage
        
        print("  Creating stages...")
        SnowflakeStageStorage.ensure_stages_exist()
        print("  ✓ Stages created successfully!")
        return True
    except Exception as e:
        print(f"  ❌ Stage creation failed: {type(e).__name__}")
        print(f"     Error: {str(e)}")
        
        if "permission" in str(e).lower():
            print("\n  💡 Permission denied - may need role adjustment")
        
        return False


def main():
    """Run all diagnostics."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " Snowflake Connection Diagnostics ".center(58) + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    results = []
    
    # Run checks
    results.append(("Environment Variables", check_env_vars()))
    results.append(("Snowflake Package", check_snowflake_package()))
    results.append(("Snowflake Connection", test_connection()))
    results.append(("Table Creation", test_table_creation()))
    results.append(("Stage Creation", test_stage_creation()))
    
    # Summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(result[1] for result in results)
    
    print()
    if all_passed:
        print("🎉 All checks passed! You're ready to run the app.")
        print("\nNext steps:")
        print("  streamlit run interfaces/streamlit_app.py")
        print("  OR")
        print("  uvicorn interfaces.fastapi_app:app --reload")
        return 0
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        print("\nTroubleshooting:")
        print("  1. Check you have the right .env file set up")
        print("  2. Verify credentials work in Snowflake Web UI")
        print("  3. Make sure warehouse is active")
        print("  4. Check role has required permissions")
        return 1


if __name__ == "__main__":
    sys.exit(main())
