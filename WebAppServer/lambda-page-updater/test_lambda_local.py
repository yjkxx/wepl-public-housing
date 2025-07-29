#!/usr/bin/env python3
"""
Local testing script for WEPL Lambda function
Tests the core functionality without requiring all dependencies
"""
import os
import sys
import json

def test_local_configuration():
    """Test that the configuration works locally"""
    print("🏠 Testing Local Configuration")
    print("=" * 40)
    
    # Set environment to simulate different modes
    
    # Test 1: Local environment (no Lambda env var)
    if 'AWS_LAMBDA_FUNCTION_NAME' in os.environ:
        del os.environ['AWS_LAMBDA_FUNCTION_NAME']
    
    print("\n📋 Test 1: Local Environment Detection")
    try:
        # Mock modules to avoid import errors
        import types
        
        # Create mock modules
        mock_modules = {
            'requests': types.ModuleType('requests'),
            'aiohttp': types.ModuleType('aiohttp'),
            'asyncio': types.ModuleType('asyncio'),
            'ssl': types.ModuleType('ssl'),
            'pymysql': types.ModuleType('pymysql'),
            'boto3': types.ModuleType('boto3'),
            'botocore': types.ModuleType('botocore'),
            'botocore.exceptions': types.ModuleType('botocore.exceptions')
        }
        
        # Add mock exceptions
        mock_modules['botocore.exceptions'].ClientError = Exception
        mock_modules['botocore.exceptions'].NoCredentialsError = Exception
        
        # Mock AWS Secrets Manager failure for local testing
        class MockSecretManagerFail:
            def get_secret_value(self, SecretId):
                raise Exception("No credentials configured")
        
        class MockSessionFail:
            def client(self, service_name, region_name):
                return MockSecretManagerFail()
        
        mock_modules['boto3'].session = types.ModuleType('session')
        mock_modules['boto3'].session.Session = lambda: MockSessionFail()
        
        # Install mocks
        for name, module in mock_modules.items():
            sys.modules[name] = module
        
        # Now import our module
        import importlib.util
        spec = importlib.util.spec_from_file_location('lambda_render_pages', 'lambda-render-pages.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Test environment detection
        is_lambda = module.is_lambda_environment()
        print(f"   Environment detected as: {'Lambda' if is_lambda else 'Local'}")
        assert not is_lambda, "Should detect local environment"
        print("   ✅ Local environment detection: PASS")
        
        # Test configuration fallback
        print(f"   DB Host: {module.DB_HOST}")
        print(f"   DB User: {module.DB_USER}")
        # Check that empty values are handled gracefully
        assert module.DB_HOST == "", "Should use empty fallback values when no env vars set"
        print("   ✅ Configuration fallback: PASS")
        
    except Exception as e:
        print(f"   ❌ Local environment test failed: {e}")
        return False
    
    # Test 2: Lambda environment simulation
    print("\n📋 Test 2: Lambda Environment Simulation")
    try:
        # Set Lambda environment variable
        os.environ['AWS_LAMBDA_FUNCTION_NAME'] = 'test-function'
        
        # Reload the module to pick up the environment change
        spec = importlib.util.spec_from_file_location('lambda_render_pages', 'lambda-render-pages.py')
        module = importlib.util.module_from_spec(spec)
        
        # Mock successful secrets manager for Lambda test
        class MockSecretManagerSuccess:
            def get_secret_value(self, SecretId):
                return {
                    'SecretString': json.dumps({
                        'api_url_hug': 'lambda_hug_url',
                        'api_url_lh': 'lambda_lh_url',
                        'DB_HOST': 'lambda_db_host',
                        'DB_PORT': 3306,
                        'DB_NAME': 'lambda_db',
                        'DB_USER': 'lambda_user',
                        'DB_PASSWORD': 'lambda_password',
                        'GEMINI_API_KEY_PLAINTEXT': 'lambda_gemini_key',
                        'KAKAO_API': 'lambda_kakao_key',
                        'YOUTUBE_API_KEY': 'lambda_youtube_key'
                    })
                }
        
        class MockSessionSuccess:
            def client(self, service_name, region_name):
                return MockSecretManagerSuccess()
        
        mock_modules['boto3'].session.Session = lambda: MockSessionSuccess()
        
        # Reload with successful secrets
        spec.loader.exec_module(module)
        
        # Test environment detection
        is_lambda = module.is_lambda_environment()
        print(f"   Environment detected as: {'Lambda' if is_lambda else 'Local'}")
        assert is_lambda, "Should detect Lambda environment"
        print("   ✅ Lambda environment detection: PASS")
        
        # Test secrets loading
        print(f"   DB Host: {module.DB_HOST}")
        assert module.DB_HOST == 'lambda_db_host', "Should use secrets DB host"
        print("   ✅ Secrets Manager integration: PASS")
        
    except Exception as e:
        print(f"   ❌ Lambda environment test failed: {e}")
        return False
    finally:
        # Clean up environment
        if 'AWS_LAMBDA_FUNCTION_NAME' in os.environ:
            del os.environ['AWS_LAMBDA_FUNCTION_NAME']
    
    print("\n🎉 All configuration tests passed!")
    return True

def test_core_functions():
    """Test core functions without external dependencies"""
    print("\n🔧 Testing Core Functions")
    print("=" * 40)
    
    try:
        # Test data conversion functions
        print("\n📋 Testing utility functions...")
        
        # Mock a posting object
        test_posting = {
            'posting_id': '12345',
            'prefecture': '서울특별시',
            'city': '강남구',
            'detailed_address': '테스트 주소',
            'application_start_date': '2025-01-01',
            'application_end_date': '2025-01-31',
            'building_type': '아파트',
            'deposit': 50000000,
            'rent': 500000
        }
        
        # Import our module again for function testing
        import importlib.util
        spec = importlib.util.spec_from_file_location('lambda_render_pages', 'lambda-render-pages.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Test convert_to_posting_object function
        converted = module.convert_to_posting_object(test_posting)
        assert converted['posting_id'] == '12345'
        assert converted['area_province'] == '서울특별시'
        print("   ✅ convert_to_posting_object: PASS")
        
        # Test make_json_serializable function
        from decimal import Decimal
        import datetime
        
        test_data = {
            'decimal_value': Decimal('123.45'),
            'date_value': datetime.date.today(),
            'normal_value': 'test'
        }
        
        serialized = module.make_json_serializable(test_data)
        assert isinstance(serialized['decimal_value'], float)
        assert isinstance(serialized['date_value'], str)
        print("   ✅ make_json_serializable: PASS")
        
        print("\n🎉 All core function tests passed!")
        return True
        
    except Exception as e:
        print(f"   ❌ Core function test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_deployment_info():
    """Show deployment information"""
    print("\n🚀 Deployment Information")
    print("=" * 40)
    
    print("""
📦 To deploy to AWS Lambda:
   1. Run: ./deploy-lambda-improved.sh
   
🔑 Required AWS Resources:
   1. IAM Role: wepl-lambda-execution-role
      - AWSLambdaBasicExecutionRole
      - Custom policy for Secrets Manager access
      - S3 access for file uploads
      - VPC access for RDS (if in VPC)
   
   2. Secrets Manager: wepl-lambda-secrets
      - Already created and configured ✅
   
   3. Lambda Function: wepl-render-pages
      - Runtime: Python 3.9
      - Timeout: 300 seconds
      - Memory: 512 MB

🧪 Test Lambda Function:
   aws lambda invoke \\
     --function-name wepl-render-pages \\
     --payload '{"action": "complete_workflow"}' \\
     output.json

📊 Available Actions:
   • complete_workflow - Full LH data processing
   • sync_index - Update index.html with DB data
   • check_apis - Test API connectivity
   • update_recent_pages - Update recent detail pages

🏠 Local Usage:
   python3 lambda-render-pages.py
   """)

def main():
    """Main test function"""
    print("🧪 WEPL Lambda Function - Local Testing")
    print("=" * 50)
    
    # Test configuration
    config_success = test_local_configuration()
    
    if not config_success:
        print("\n❌ Configuration tests failed!")
        return False
    
    # Test core functions
    functions_success = test_core_functions()
    
    if not functions_success:
        print("\n❌ Function tests failed!")
        return False
    
    # Show deployment info
    show_deployment_info()
    
    print("\n✅ All tests completed successfully!")
    print("Your Lambda function is ready for deployment! 🎉")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
