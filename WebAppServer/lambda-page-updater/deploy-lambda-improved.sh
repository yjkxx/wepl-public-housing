#!/bin/bash

echo "🚀 WEPL Lambda Deployment Script"
echo "================================="

# Configuration
FUNCTION_NAME="wepl-render-pages"
REGION="ap-northeast-2"
ROLE_NAME="wepl-lambda-execution-role"
ZIP_FILE="lambda-deployment.zip"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    print_error "AWS credentials not configured. Run 'aws configure' first."
    exit 1
fi

print_status "AWS credentials verified"

# Create deployment package
echo ""
echo "📦 Creating deployment package..."

# Clean up old package
rm -f $ZIP_FILE

# Create a temporary directory for the deployment package
TEMP_DIR=$(mktemp -d)
print_status "Created temporary directory: $TEMP_DIR"

# Copy the Lambda function
cp lambda-render-pages.py $TEMP_DIR/

# Install dependencies in the temp directory
echo "Installing Python dependencies..."
if [ -f requirements.txt ]; then
    pip3 install --target $TEMP_DIR -r requirements.txt &> /dev/null
    if [ $? -eq 0 ]; then
        print_status "Dependencies installed from requirements.txt successfully"
    else
        print_warning "Some dependencies may have failed to install from requirements.txt"
    fi
else
    # Fallback to individual packages
    pip3 install --target $TEMP_DIR requests pymysql aiohttp boto3 typing_extensions &> /dev/null
    if [ $? -eq 0 ]; then
        print_status "Dependencies installed successfully"
    else
        print_warning "Some dependencies may have failed to install"
    fi
fi

# Create the zip file
cd $TEMP_DIR
zip -r ../$ZIP_FILE . > /dev/null
cd - > /dev/null
mv $TEMP_DIR/../$ZIP_FILE .

# Clean up temp directory
rm -rf $TEMP_DIR

print_status "Deployment package created: $ZIP_FILE"

# Check if Lambda function exists
echo ""
echo "🔍 Checking if Lambda function exists..."

if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION &> /dev/null; then
    print_status "Function exists, updating code..."
    
    # Update existing function
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://$ZIP_FILE \
        --region $REGION
    
    if [ $? -eq 0 ]; then
        print_status "Lambda function code updated successfully"
    else
        print_error "Failed to update Lambda function code"
        exit 1
    fi
    
    # Update function configuration
    aws lambda update-function-configuration \
        --function-name $FUNCTION_NAME \
        --timeout 300 \
        --memory-size 512 \
        --environment Variables="{\"SECRET_NAME\":\"wepl-lambda-secrets\",\"AWS_REGION\":\"ap-northeast-2\"}" \
        --region $REGION > /dev/null
    
    print_status "Lambda function configuration updated"
    
else
    print_warning "Function does not exist, creating new function..."
    
    # Get account ID for role ARN
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    ROLE_ARN="arn:aws:iam::$ACCOUNT_ID:role/$ROLE_NAME"
    
    # Create the Lambda function
    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --runtime python3.9 \
        --role $ROLE_ARN \
        --handler lambda-render-pages.lambda_handler \
        --zip-file fileb://$ZIP_FILE \
        --timeout 300 \
        --memory-size 512 \
        --region $REGION
    
    if [ $? -eq 0 ]; then
        print_status "Lambda function created successfully"
        
        # Now update environment variables
        print_status "Setting environment variables..."
        aws lambda update-function-configuration \
            --function-name $FUNCTION_NAME \
            --environment Variables="{\"SECRET_NAME\":\"wepl-lambda-secrets\",\"AWS_REGION\":\"ap-northeast-2\"}" \
            --region $REGION > /dev/null
        
        if [ $? -eq 0 ]; then
            print_status "Environment variables set successfully"
        else
            print_warning "Failed to set environment variables, but function was created"
        fi
    else
        print_error "Failed to create Lambda function"
        echo ""
        echo "Make sure the IAM role '$ROLE_NAME' exists with the following policies:"
        echo "1. AWSLambdaBasicExecutionRole"
        echo "2. SecretsManagerReadWrite (or custom policy for wepl-lambda-secrets)"
        echo "3. AmazonS3FullAccess (for S3 operations)"
        echo "4. AmazonRDSDataFullAccess (for database access)"
        exit 1
    fi
fi

# Test the function
echo ""
echo "🧪 Testing Lambda function..."

TEST_RESULT=$(aws lambda invoke \
    --function-name $FUNCTION_NAME \
    --payload '{"action": "check_apis"}' \
    --region $REGION \
    response.json 2>&1)

if [ $? -eq 0 ]; then
    print_status "Lambda function test completed"
    echo "Response saved to response.json"
    
    if [ -f response.json ]; then
        echo "Response content:"
        cat response.json | python3 -m json.tool 2>/dev/null || cat response.json
        echo ""
    fi
else
    print_error "Lambda function test failed: $TEST_RESULT"
fi

# Clean up
rm -f response.json

echo ""
echo "🎉 Deployment completed!"
echo ""
echo "Available Lambda actions:"
echo "• complete_workflow - Run the full LH workflow"
echo "• sync_index - Sync index.html with database"
echo "• check_apis - Check API connectivity"
echo "• update_recent_pages - Update recent detail pages"
echo ""
echo "Example invocation:"
echo "aws lambda invoke --function-name $FUNCTION_NAME --payload '{\"action\": \"complete_workflow\"}' output.json"
echo ""
echo "To view logs:"
echo "aws logs tail /aws/lambda/$FUNCTION_NAME --follow --region $REGION"
