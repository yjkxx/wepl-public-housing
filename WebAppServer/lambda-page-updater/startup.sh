#!/bin/bash

# WEPL Lambda Deployment - Complete Setup and Deployment Script
# This script handles the entire process from AWS setup to Lambda deployment

set -e

echo "🚀 WEPL Housing Lambda - Complete Setup & Deployment"
echo "=================================================="

# Check if AWS CLI is configured
if ! aws sts get-caller-identity >/dev/null 2>&1; then
    echo "❌ AWS CLI not configured. Please run 'aws configure' first."
    exit 1
fi

echo "✅ AWS CLI is configured"

# Step 1: Setup AWS resources
echo ""
echo "Step 1: Setting up AWS resources (IAM role, S3 buckets)..."
if [ -f "setup-aws-resources.sh" ]; then
    ./setup-aws-resources.sh
else
    echo "❌ setup-aws-resources.sh not found"
    exit 1
fi

# Step 2: Get the IAM role ARN and update deploy script
echo ""
echo "Step 2: Updating deployment script with IAM role..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ROLE_ARN="arn:aws:iam::$ACCOUNT_ID:role/wepl-lambda-execution-role"

# Update the deploy-lambda.sh script with the correct IAM role
sed -i.bak "s|IAM_ROLE=\"arn:aws:iam::YOUR_ACCOUNT_ID:role/lambda-execution-role\"|IAM_ROLE=\"$ROLE_ARN\"|g" deploy-lambda.sh
echo "✅ Updated deploy-lambda.sh with IAM role: $ROLE_ARN"

# Step 3: Deploy Lambda function
echo ""
echo "Step 3: Deploying Lambda function..."
if [ -f "deploy-lambda.sh" ]; then
    ./deploy-lambda.sh
else
    echo "❌ deploy-lambda.sh not found"
    exit 1
fi

# Step 4: Upload static files to S3 buckets
echo ""
echo "Step 4: Uploading static files to S3 buckets..."

# Upload to main bucket
echo "📤 Uploading static files to wepl-mainpage bucket..."
aws s3 cp script.js s3://wepl-mainpage/ --content-type "text/javascript"
aws s3 cp style.css s3://wepl-mainpage/ --content-type "text/css"
aws s3 cp index.html s3://wepl-mainpage/ --content-type "text/html"

# Upload to detail pages bucket
echo "📤 Uploading static files to wepl-posting-pages bucket..."
aws s3 cp script.js s3://wepl-posting-pages/ --content-type "text/javascript"
aws s3 cp style.css s3://wepl-posting-pages/ --content-type "text/css"

echo "✅ Static files uploaded successfully"

# Step 5: Test Lambda function
echo ""
echo "Step 5: Testing Lambda function..."
echo "🧪 Testing sync_index action..."
aws lambda invoke \
    --function-name wepl-housing-generator \
    --payload '{"action": "sync_index", "s3_detail_bucket": "wepl-posting-pages", "s3_main_bucket": "wepl-mainpage"}' \
    --region ap-northeast-2 \
    test-sync-output.json

echo "📋 Sync test result:"
cat test-sync-output.json

echo ""
echo "🧪 Testing generate_all action..."
aws lambda invoke \
    --function-name wepl-housing-generator \
    --payload '{"action": "generate_all", "s3_detail_bucket": "wepl-posting-pages", "s3_main_bucket": "wepl-mainpage"}' \
    --region ap-northeast-2 \
    test-generate-output.json

echo "📋 Generate test result:"
cat test-generate-output.json

# Display final information
echo ""
echo "🎉 WEPL Lambda deployment completed successfully!"
echo "=============================================="
echo ""
echo "📋 Your Lambda function is ready:"
echo "   🔧 Function name: wepl-housing-generator"
echo "   🌍 Region: ap-northeast-2"
echo "   ⏱️ Timeout: 15 minutes"
echo "   💾 Memory: 1024 MB"
echo ""
echo "🌐 Your websites are available at:"
echo "   📱 Main site: http://wepl-mainpage.s3-website-ap-northeast-2.amazonaws.com"
echo "   📄 Detail pages: http://wepl-posting-pages.s3-website-ap-northeast-2.amazonaws.com"
echo ""
echo "🔧 Available Lambda actions:"
echo "   • generate_all - Generate detail pages for all postings"
echo "   • generate_specific - Generate pages for specific posting IDs"
echo "   • sync_index - Update index.html with latest database data"
echo "   • generate_summaries - Generate AI summaries for postings"
echo ""
echo "📝 Example invocation:"
echo "aws lambda invoke --function-name wepl-housing-generator \\"
echo "  --payload '{\"action\":\"generate_all\"}' \\"
echo "  --region ap-northeast-2 output.json"
echo ""
echo "🕒 To set up automated scheduling:"
echo "1. Go to AWS EventBridge (CloudWatch Events)"
echo "2. Create a rule with cron expression (e.g., daily at 2 AM: 0 2 * * ? *)"
echo "3. Set target to Lambda function: wepl-housing-generator"
echo "4. Configure input with: {\"action\":\"sync_index\"}"

# Cleanup test files
rm -f test-sync-output.json test-generate-output.json

echo "🧹 Cleanup completed"
