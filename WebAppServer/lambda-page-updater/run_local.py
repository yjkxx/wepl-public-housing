#!/usr/bin/env python3
"""
Local development helper script for WEPL Lambda function.
This script loads environment variables from .env file and runs the main function.
"""
import os
import sys
from pathlib import Path

def load_env_file(env_file='.env'):
    """Load environment variables from .env file"""
    env_path = Path(env_file)
    if not env_path.exists():
        print(f"⚠️  Environment file {env_file} not found!")
        print("Please copy .env.example to .env and fill in your values.")
        return False
    
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()
    
    return True

def verify_environment():
    """Verify that required environment variables are set"""
    required_vars = [
        'HUG_API_URL', 'LH_API_URL', 'DB_HOST', 'DB_NAME', 
        'DB_USER', 'DB_PASSWORD', 'GEMINI_API_KEY', 'KAKAO_API_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease check your .env file.")
        return False
    
    print("✅ All required environment variables are set")
    return True

def main():
    """Main function for local development"""
    print("🏠 WEPL Lambda Function - Local Development")
    print("=" * 50)
    
    # Load environment variables
    if not load_env_file():
        sys.exit(1)
    
    # Verify environment
    if not verify_environment():
        sys.exit(1)
    
    # Import and run the lambda function
    try:
        print("\n📥 Loading lambda function...")
        import importlib.util
        spec = importlib.util.spec_from_file_location('lambda_render_pages', 'lambda-render-pages.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        print("✅ Lambda function loaded successfully")
        print(f"Environment: {'Lambda' if module.is_lambda_environment() else 'Local'}")
        
        # Show available functions
        print("\n🔧 Available functions:")
        print("1. complete_lh_workflow() - Full LH data processing")
        print("2. sync_all_postings_to_html() - Sync index.html with database")
        print("3. check_pub_api() - Check API connectivity")
        print("4. main() - Run the main function")
        
        # Run main function
        print("\n🚀 Running main function...")
        module.main()
        
    except Exception as e:
        print(f"❌ Error running lambda function: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
