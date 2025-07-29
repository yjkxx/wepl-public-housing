#!/bin/bash

# AWS Lambda Deployment Script for WEPL Housing Application
# This script packages and deploys your housing detail page generator to AWS Lambda

set -e

echo "🚀 Starting AWS Lambda deployment for WEPL Housing Application..."

# Configuration
FUNCTION_NAME="wepl-housing-generator"
REGION="ap-northeast-2"
PYTHON_VERSION="3.9"
TIMEOUT=900  # 15 minutes
MEMORY_SIZE=1024

# Clean up any previous deployment artifacts
echo "🧹 Cleaning up previous artifacts..."
rm -rf lambda-package wepl-lambda-deployment.zip

# Create deployment package
echo "📦 Creating deployment package..."
mkdir lambda-package

# Copy your Python files
cp apitest03.py lambda-package/
cp lambda_handler.py lambda-package/
cp index.html lambda-package/
cp script.js lambda-package/
cp style.css lambda-package/

# Install dependencies using pip3
echo "📥 Installing dependencies..."
pip3 install -r requirements.txt -t lambda-package/ --no-deps --force-reinstall

# Also install any missing core dependencies
pip3 install typing_extensions==4.12.2 -t lambda-package/ --no-deps --force-reinstall

# Create ZIP file
echo "🗜️ Creating ZIP package..."
cd lambda-package
zip -r ../wepl-lambda-deployment.zip . -x "*.pyc" "__pycache__/*"
cd ..

echo "✅ Package created: wepl-lambda-deployment.zip ($(du -h wepl-lambda-deployment.zip | cut -f1))"

# Check if Lambda function exists
echo "🔍 Checking if Lambda function exists..."
if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION >/dev/null 2>&1; then
    echo "🔄 Updating existing Lambda function..."
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://wepl-lambda-deployment.zip \
        --region $REGION
    
    # Update function configuration
    aws lambda update-function-configuration \
        --function-name $FUNCTION_NAME \
        --timeout $TIMEOUT \
        --memory-size $MEMORY_SIZE \
        --region $REGION
else
    echo "🆕 Creating new Lambda function..."
    
    # IAM role ARN with your actual account ID
    IAM_ROLE="arn:aws:iam::743992917350:role/wepl-lambda-execution-role"
    
    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --runtime python$PYTHON_VERSION \
        --role $IAM_ROLE \
        --handler lambda_handler.lambda_handler \
        --zip-file fileb://wepl-lambda-deployment.zip \
        --timeout $TIMEOUT \
        --memory-size $MEMORY_SIZE \
        --region $REGION \
        --environment Variables='{DB_HOST=wepl-database-mysql.cd4gwa442142.ap-northeast-2.rds.amazonaws.com,DB_PORT=3306,DB_NAME=wepl,DB_USER=admin,DB_PASSWORD=wepl1234,GEMINI_API_KEY=AIzaSyB_H9F0tkZYJS2hC9nuiFdiBI8gMysX57M,KAKAO_API=36403d643d740d02d316dd063c88c341}'
fi

echo "✅ Lambda function deployed successfully!"

# Test the function with a simple sync operation
echo "🧪 Testing Lambda function..."
aws lambda invoke \
    --function-name $FUNCTION_NAME \
    --payload '{"action": "sync_index", "s3_detail_bucket": "wepl-posting-pages", "s3_main_bucket": "wepl-mainpage"}' \
    --region $REGION \
    test-output.json

echo "📋 Test result:"
cat test-output.json

echo ""
echo "🎉 Deployment completed!"
echo ""
echo "📝 Your Lambda function is now ready to:"
echo "  • Generate HTML for all postings: {\"action\": \"generate_all\"}"
echo "  • Generate HTML for specific postings: {\"action\": \"generate_specific\", \"posting_ids\": [1,2,3]}"
echo "  • Sync main index page: {\"action\": \"sync_index\"}"
echo "  • Generate AI summaries: {\"action\": \"generate_summaries\"}"