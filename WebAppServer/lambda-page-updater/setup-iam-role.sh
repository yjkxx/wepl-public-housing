#!/bin/bash

echo "🔧 Creating IAM Role for WEPL Lambda Function"
echo "============================================="

# Configuration
ROLE_NAME="wepl-lambda-execution-role"
POLICY_NAME="wepl-lambda-policy"
REGION="ap-northeast-2"

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

# Create trust policy document
cat > trust-policy-lambda.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF

print_status "Trust policy document created"

# Check if role exists
if aws iam get-role --role-name $ROLE_NAME &> /dev/null; then
    print_warning "IAM role '$ROLE_NAME' already exists"
else
    # Create the IAM role
    echo "Creating IAM role '$ROLE_NAME'..."
    aws iam create-role \
        --role-name $ROLE_NAME \
        --assume-role-policy-document file://trust-policy-lambda.json \
        --description "Execution role for WEPL Lambda function"
    
    if [ $? -eq 0 ]; then
        print_status "IAM role created successfully"
    else
        print_error "Failed to create IAM role"
        exit 1
    fi
fi

# Attach AWS managed policy for basic Lambda execution
echo "Attaching AWSLambdaBasicExecutionRole policy..."
aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

print_status "Basic execution policy attached"

# Create and attach custom policy for WEPL-specific permissions
echo "Creating custom policy for WEPL Lambda function..."
aws iam put-role-policy \
    --role-name $ROLE_NAME \
    --policy-name $POLICY_NAME \
    --policy-document file://lambda-iam-policy.json

if [ $? -eq 0 ]; then
    print_status "Custom policy attached successfully"
else
    print_error "Failed to attach custom policy"
    exit 1
fi

# Wait for role to be ready
echo "Waiting for IAM role to be ready..."
sleep 10

# Verify role exists and has correct policies
echo ""
echo "🔍 Verifying IAM role setup..."

# Check role exists
if aws iam get-role --role-name $ROLE_NAME &> /dev/null; then
    print_status "Role exists and is accessible"
    
    # List attached policies
    echo "Attached managed policies:"
    aws iam list-attached-role-policies --role-name $ROLE_NAME --query 'AttachedPolicies[].PolicyName' --output table
    
    echo "Inline policies:"
    aws iam list-role-policies --role-name $ROLE_NAME --query 'PolicyNames' --output table
    
else
    print_error "Role verification failed"
    exit 1
fi

# Clean up temporary files
rm -f trust-policy-lambda.json

echo ""
print_status "IAM role setup completed successfully!"
echo ""
echo "Role ARN: $(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text)"
echo ""
echo "You can now run: ./deploy-lambda-improved.sh"
