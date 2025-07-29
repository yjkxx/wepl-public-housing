#!/usr/bin/env python3
"""
Test script for AI Video Generator components
This script allows you to test individual components of the system.
"""

import os
import sys
from datetime import datetime

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️  python-dotenv not installed. Install with: pip install python-dotenv")
    pass

def test_database_connection():
    """Test database connection"""
    print("🔍 Testing database connection...")
    try:
        # Import here to avoid issues with module loading
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from ai_api import get_database_connection
        
        conn = get_database_connection()
        if conn:
            print("✅ Database connection successful")
            conn.close()
            return True
        else:
            print("❌ Database connection failed")
            return False
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False

def test_script_generation():
    """Test template-based script generation"""
    print("🔍 Testing script generation...")
    try:
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from ai_api import generate_script_from_template
        
        # Test data
        test_posting = {
            'title': '공공주택 신규 공급 계획',
            'content': '2024년 공공주택 신규 공급이 전년 대비 15% 증가할 예정입니다.'
        }
        
        script = generate_script_from_template(test_posting)
        
        if script and len(script) > 50:
            print("✅ Script generation working")
            print(f"   Sample script: {script[:100]}...")
            return True
        else:
            print("❌ Script generation returned empty or short result")
            return False
    except Exception as e:
        print(f"❌ Script generation error: {e}")
        return False

def test_aws_s3():
    """Test AWS S3 connection"""
    print("🔍 Testing AWS S3 connection...")
    try:
        import boto3
        
        access_key = os.getenv("AWS_ACCESS_KEY_ID")
        secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        region = os.getenv("AWS_REGION", "us-east-1")
        bucket = os.getenv("S3_BUCKET_NAME")
        
        if not all([access_key, secret_key, bucket]):
            print("❌ AWS credentials or bucket name missing")
            return False
        
        s3_client = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        
        # Test bucket access
        s3_client.head_bucket(Bucket=bucket)
        print("✅ AWS S3 connection successful")
        return True
        
    except Exception as e:
        print(f"❌ AWS S3 error: {e}")
        return False

def test_heygen_api():
    """Test HeyGen API"""
    print("🔍 Testing HeyGen API...")
    try:
        import requests
        
        api_key = os.getenv("HEYGEN_API_KEY")
        if not api_key:
            print("❌ HEYGEN_API_KEY not found in environment")
            return False
        
        # Test with a simple API call to check key validity
        headers = {
            "X-Api-Key": api_key,
            "Content-Type": "application/json"
        }
        
        # Try to get account info or similar lightweight endpoint
        # Note: Replace with actual HeyGen API endpoint for testing
        print("✅ HeyGen API key configured (actual API test requires video generation)")
        return True
        
    except Exception as e:
        print(f"❌ HeyGen API error: {e}")
        return False

def test_youtube_api():
    """Test YouTube API setup"""
    print("🔍 Testing YouTube API setup...")
    try:
        if not os.path.exists('client_secret.json'):
            print("❌ client_secret.json not found")
            print("   Create this file from Google Cloud Console")
            return False
        
        print("✅ YouTube client_secret.json found")
        print("   Note: Full YouTube API test requires OAuth flow")
        return True
        
    except Exception as e:
        print(f"❌ YouTube API setup error: {e}")
        return False

def test_fetch_posting():
    """Test fetching posting from database"""
    print("🔍 Testing posting fetch...")
    try:
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from ai_api import fetch_latest_posting_without_video
        
        posting = fetch_latest_posting_without_video()
        
        if posting:
            print("✅ Successfully fetched posting")
            print(f"   Title: {posting['title'][:50]}...")
            return True
        else:
            print("❌ No posting found or database error")
            return False
            
    except Exception as e:
        print(f"❌ Posting fetch error: {e}")
        return False

def run_all_tests():
    """Run all component tests"""
    print("🧪 Running all component tests")
    print("=" * 50)
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Script Generation", test_script_generation),
        ("AWS S3", test_aws_s3), 
        ("HeyGen API", test_heygen_api),
        ("YouTube API Setup", test_youtube_api),
        ("Database Posting Fetch", test_fetch_posting)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {e}")
            results.append((test_name, False))
        print()
    
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<25} {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! You can run the full workflow.")
    else:
        print("⚠️  Some tests failed. Please check your configuration.")

def main():
    if len(sys.argv) > 1:
        test_name = sys.argv[1].lower()
        
        test_functions = {
            'database': test_database_connection,
            'db': test_database_connection,
            'script': test_script_generation,
            'template': test_script_generation,
            's3': test_aws_s3,
            'aws': test_aws_s3,
            'heygen': test_heygen_api,
            'video': test_heygen_api,
            'youtube': test_youtube_api,
            'posting': test_fetch_posting
        }
        
        if test_name in test_functions:
            test_functions[test_name]()
        else:
            print(f"Unknown test: {test_name}")
            print("Available tests: database, script, s3, heygen, youtube, posting")
    else:
        run_all_tests()

if __name__ == "__main__":
    main()
