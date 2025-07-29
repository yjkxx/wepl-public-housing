#!/usr/bin/env python3
"""
Setup helper script for AI Video Generator
This script helps you create and configure the necessary files.
"""

import os
import json

def create_client_secret_template():
    """Create a template for YouTube API client secret"""
    template = {
        "web": {
            "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
            "project_id": "your-project-id",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": "YOUR_CLIENT_SECRET",
            "redirect_uris": ["http://localhost"]
        }
    }
    
    with open("client_secret_template.json", "w") as f:
        json.dump(template, f, indent=2)
    
    print("✅ Created client_secret_template.json")
    print("   📝 Replace with your actual YouTube API credentials and rename to client_secret.json")

def create_env_file():
    """Create .env file from template if it doesn't exist"""
    if not os.path.exists(".env"):
        if os.path.exists(".env.example"):
            with open(".env.example", "r") as f:
                content = f.read()
            with open(".env", "w") as f:
                f.write(content)
            print("✅ Created .env file from template")
            print("   📝 Please fill in your actual API keys and configuration")
        else:
            print("❌ .env.example not found")
    else:
        print("ℹ️  .env file already exists")

def check_requirements():
    """Check if all required packages are installed"""
    try:
        import boto3
        import google.generativeai as genai
        import mysql.connector
        from googleapiclient.discovery import build
        print("✅ All required packages are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing package: {e}")
        print("   Run: pip install -r requirements.txt")
        return False

def main():
    print("🚀 AI Video Generator Setup Helper")
    print("=" * 40)
    
    # Check if virtual environment is activated
    if hasattr(os.environ, 'VIRTUAL_ENV') or 'venv' in os.environ.get('PATH', ''):
        print("✅ Virtual environment detected")
    else:
        print("⚠️  Virtual environment not detected")
        print("   Consider activating: source venv/bin/activate")
    
    # Check requirements
    check_requirements()
    
    # Create configuration files
    create_env_file()
    create_client_secret_template()
    
    print("\n📋 Next Steps:")
    print("1. Fill in your .env file with actual API keys")
    print("2. Set up YouTube API credentials in client_secret.json")
    print("3. Create your database and table structure")
    print("4. Test the script with: python ai-api.py --workflow")
    
    print("\n🔗 Useful Links:")
    print("- Gemini API: https://ai.google.dev/")
    print("- HeyGen API: https://heygen.com/")
    print("- YouTube Data API: https://console.cloud.google.com/")
    print("- AWS S3: https://aws.amazon.com/s3/")

if __name__ == "__main__":
    main()
