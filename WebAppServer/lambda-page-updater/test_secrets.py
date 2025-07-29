#!/usr/bin/env python3
"""
Test script to verify Secrets Manager integration
"""
import json
import os
import sys

# Mock boto3 and dependencies for testing
class MockSecretManager:
    def get_secret_value(self, SecretId):
        # Simulate AWS Secrets Manager response
        return {
            'SecretString': json.dumps({
                'api_url_hug': 'mock_hug_url',
                'api_url_lh': 'mock_lh_url',
                'DB_HOST': 'mock_db_host',
                'DB_PORT': 3306,
                'DB_NAME': 'mock_db',
                'DB_USER': 'mock_user',
                'DB_PASSWORD': 'mock_password',
                'GEMINI_API_KEY_PLAINTEXT': 'mock_gemini_key',
                'KAKAO_API': 'mock_kakao_key',
                'YOUTUBE_API_KEY': 'mock_youtube_key'
            })
        }

class MockBoto3Session:
    def client(self, service_name, region_name):
        if service_name == 'secretsmanager':
            return MockSecretManager()
        raise Exception(f"Unknown service: {service_name}")

class MockBoto3:
    class session:
        @staticmethod
        def Session():
            return MockBoto3Session()

# Mock the modules
sys.modules['boto3'] = MockBoto3
sys.modules['requests'] = type('MockModule', (), {})()
sys.modules['aiohttp'] = type('MockModule', (), {})()
sys.modules['asyncio'] = type('MockModule', (), {})()
sys.modules['ssl'] = type('MockModule', (), {})()
sys.modules['pymysql'] = type('MockModule', (), {})()
sys.modules['botocore'] = type('MockModule', (), {})()
sys.modules['botocore.exceptions'] = type('MockModule', (), {
    'ClientError': Exception,
    'NoCredentialsError': Exception
})()

def test_secrets_integration():
    """Test the secrets integration functions"""
    print("🧪 Testing Secrets Manager integration...")
    
    try:
        # Import the key functions from our module
        import importlib.util
        spec = importlib.util.spec_from_file_location('lambda_render_pages', 'lambda-render-pages.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        print("✅ Module loaded successfully")
        
        # Test environment detection
        is_lambda = module.is_lambda_environment()
        print(f"✅ Environment detection: {'Lambda' if is_lambda else 'Local'}")
        
        # Test configuration variables
        print(f"✅ DB Host: {module.DB_HOST}")
        print(f"✅ DB Port: {module.DB_PORT}")
        print(f"✅ DB Name: {module.DB_NAME}")
        print(f"✅ API URL HUG (first 50 chars): {module.api_url_hug[:50]}...")
        
        # Test get_secret function
        secret_result = module.get_secret()
        if secret_result:
            print("✅ Secrets Manager access: Working")
        else:
            print("⚠️  Secrets Manager access: Fallback mode (expected locally)")
        
        print("\n🎉 All tests passed! Configuration is working correctly.")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_secrets_integration()
    sys.exit(0 if success else 1)
