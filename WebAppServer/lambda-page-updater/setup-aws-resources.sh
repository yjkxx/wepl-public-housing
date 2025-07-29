#!/bin/bash

# Setup script for AWS resources needed for WEPL Lambda deployment
# This script creates the necessary IAM role and S3 buckets

set -e

echo "🔧 Setting up AWS resources for WEPL Lambda deployment..."

# Configuration
ROLE_NAME="wepl-lambda-execution-role"
POLICY_NAME="wepl-lambda-policy"
REGION="ap-northeast-2"
DETAIL_BUCKET="wepl-posting-pages"
MAIN_BUCKET="wepl-mainpage"

# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "📋 AWS Account ID: $ACCOUNT_ID"

# Create IAM role
echo "👤 Creating IAM role..."

# Trust policy for Lambda
cat > trust-policy.json << EOF
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

# Create the role
aws iam create-role \
    --role-name $ROLE_NAME \
    --assume-role-policy-document file://trust-policy.json \
    --description "Execution role for WEPL housing Lambda function"

echo "✅ IAM role created: $ROLE_NAME"

# Create and attach policy
echo "📜 Creating IAM policy..."

cat > lambda-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:*:*:*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:PutObjectAcl",
                "s3:DeleteObject"
            ],
            "Resource": [
                "arn:aws:s3:::$DETAIL_BUCKET/*",
                "arn:aws:s3:::$MAIN_BUCKET/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::$DETAIL_BUCKET",
                "arn:aws:s3:::$MAIN_BUCKET"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "rds:DescribeDBInstances",
                "rds-db:connect"
            ],
            "Resource": "*"
        }
    ]
}
EOF

# Create policy
aws iam create-policy \
    --policy-name $POLICY_NAME \
    --policy-document file://lambda-policy.json \
    --description "Policy for WEPL Lambda function"

# Attach policy to role
aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn "arn:aws:iam::$ACCOUNT_ID:policy/$POLICY_NAME"

echo "✅ IAM policy created and attached"

# Create S3 buckets
echo "🪣 Creating S3 buckets..."

# Create detail pages bucket
aws s3 mb s3://$DETAIL_BUCKET --region $REGION
echo "✅ Created S3 bucket: $DETAIL_BUCKET"

# Create main page bucket
aws s3 mb s3://$MAIN_BUCKET --region $REGION
echo "✅ Created S3 bucket: $MAIN_BUCKET"

# Configure buckets for public website hosting
echo "🌐 Configuring buckets for web hosting..."

# Enable public access for main bucket (for website hosting)
aws s3 website s3://$MAIN_BUCKET --index-document index.html --error-document index.html

# Set bucket policy for public read access on main bucket
cat > main-bucket-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::$MAIN_BUCKET/*"
        }
    ]
}
EOF

aws s3api put-bucket-policy --bucket $MAIN_BUCKET --policy file://main-bucket-policy.json
echo "✅ Main bucket configured for public website hosting"

# Set bucket policy for public read access on detail pages bucket
cat > detail-bucket-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::$DETAIL_BUCKET/*"
        }
    ]
}
EOF

aws s3api put-bucket-policy --bucket $DETAIL_BUCKET --policy file://detail-bucket-policy.json
echo "✅ Detail pages bucket configured for public access"

# Display results
echo ""
echo "🎉 AWS resources setup completed!"
echo ""
echo "📋 Created resources:"
echo "   👤 IAM Role: $ROLE_NAME"
echo "   📜 IAM Policy: $POLICY_NAME"
echo "   🪣 S3 Bucket (detail pages): $DETAIL_BUCKET"
echo "   🪣 S3 Bucket (main page): $MAIN_BUCKET"
echo ""
echo "🔗 Role ARN: arn:aws:iam::$ACCOUNT_ID:role/$ROLE_NAME"
echo "🌐 Main website URL: http://$MAIN_BUCKET.s3-website-$REGION.amazonaws.com"
echo "🌐 Detail pages URL: http://$DETAIL_BUCKET.s3-website-$REGION.amazonaws.com"
echo ""
echo "📝 Next steps:"
echo "1. Update the IAM_ROLE variable in deploy-lambda.sh with:"
echo "   IAM_ROLE=\"arn:aws:iam::$ACCOUNT_ID:role/$ROLE_NAME\""
echo "2. Run ./deploy-lambda.sh to deploy your Lambda function"
echo "3. Upload your static files (script.js, style.css) to both S3 buckets"

# Cleanup temporary files
rm -f trust-policy.json lambda-policy.json main-bucket-policy.json detail-bucket-policy.json

echo "🧹 Cleanup completed"