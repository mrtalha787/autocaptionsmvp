#!/usr/bin/env python3
"""
Deployment helper for Snowflake environment.
Run this on startup to verify configuration and initialize tables.
"""

import sys
from pathlib import Path

# Add app to path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

def check_environment():
    """Verify all required environment variables are set."""
    required_vars = [
        "SNOWFLAKE_USER",
        "SNOWFLAKE_PASSWORD",
        "SNOWFLAKE_ACCOUNT",
        "SNOWFLAKE_WAREHOUSE",
        "SNOWFLAKE_DATABASE",
        "SNOWFLAKE_SCHEMA",
    ]
    
    import os
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        print("❌ Missing environment variables:")
        for var in missing:
            print(f"   - {var}")
        print("\nSet these variables before running the application.")
        print("\nExample (Linux/macOS):")
        print("  export SNOWFLAKE_USER=your_username")
        print("  export SNOWFLAKE_PASSWORD=your_password")
        print("  export SNOWFLAKE_ACCOUNT=xy12345.us-east-1")
        print("  export SNOWFLAKE_WAREHOUSE=COMPUTE_WH")
        print("  export SNOWFLAKE_DATABASE=AUTO_CAPTIONS")
        print("  export SNOWFLAKE_SCHEMA=PUBLIC")
        print("\nOr on Windows:")
        print("  set SNOWFLAKE_USER=your_username")
        print("  set SNOWFLAKE_PASSWORD=your_password")
        print("  ...")
        return False
    
    print("✓ All environment variables set")
    
    # Show which values are configured
    for var in required_vars:
        value = os.getenv(var)
        if var == "SNOWFLAKE_PASSWORD":
            print(f"  {var}: {'*' * len(value)}")
        else:
            print(f"  {var}: {value}")
    
    return True


def check_connection():
    """Test Snowflake connection."""
    try:
        from app.snowflake_config import SnowflakeConnection
        sf = SnowflakeConnection()
        conn = sf.connect()
        print("✓ Snowflake connection successful")
        return True
    except Exception as e:
        print(f"❌ Snowflake connection failed: {e}")
        return False


def initialize_database():
    """Create required tables and stages."""
    try:
        from app.snowflake_config import init_snowflake_tables
        from app.snowflake_storage import SnowflakeStageStorage
        
        print("Creating tables...")
        init_snowflake_tables()
        print("✓ Tables initialized")
        
        print("Creating stages...")
        SnowflakeStageStorage.ensure_stages_exist()
        print("✓ Stages created")
        
        return True
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False


def check_dependencies():
    """Verify required packages are installed."""
    required_packages = [
        "fastapi",
        "uvicorn",
        "streamlit",
        "snowflake",
        "faster_whisper",
    ]
    
    import importlib
    missing = []
    
    for package in required_packages:
        try:
            importlib.import_module(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print("❌ Missing Python packages:")
        for pkg in missing:
            print(f"   - {pkg}")
        print("\nInstall with: pip install -r requirements.txt")
        return False
    
    print("✓ All dependencies installed")
    return True


def check_ffmpeg():
    """Verify FFmpeg is available."""
    import shutil
    if shutil.which("ffmpeg"):
        print("✓ FFmpeg installed")
        return True
    else:
        print("⚠ FFmpeg not found in PATH")
        print("  Install with: apt-get install ffmpeg (Linux) or brew install ffmpeg (macOS)")
        return False


def main():
    """Run all checks."""
    print("=" * 60)
    print("Auto Captions - Snowflake Deployment Check")
    print("=" * 60)
    print()
    
    checks = [
        ("Environment Variables", check_environment),
        ("Dependencies", check_dependencies),
        ("FFmpeg Availability", check_ffmpeg),
        ("Snowflake Connection", check_connection),
        ("Database Initialization", initialize_database),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n{name}:")
        print("-" * 60)
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            results.append((name, False))
    
    print()
    print("=" * 60)
    print("Summary:")
    print("=" * 60)
    
    all_passed = True
    for name, result in results:
        status = "✓ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
        if not result:
            all_passed = False
    
    print()
    if all_passed:
        print("🎉 All checks passed! Ready to deploy.")
        return 0
    else:
        print("❌ Some checks failed. Please fix issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
