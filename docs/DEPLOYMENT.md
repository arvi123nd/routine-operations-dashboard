# AWS Deployment Guide

Complete step-by-step guide for deploying the Routine Operations Dashboard to AWS.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [AWS Account Setup](#aws-account-setup)
3. [Terraform Deployment](#terraform-deployment)
4. [GitHub Actions Setup](#github-actions-setup)
5. [Application Configuration](#application-configuration)
6. [Verification & Testing](#verification--testing)
7. [Monitoring & Maintenance](#monitoring--maintenance)

## Prerequisites

Ensure you have:

- AWS Account with appropriate permissions
- AWS CLI configured locally
- Terraform 1.5+ installed
- Docker installed (for local testing)
- Git and GitHub account
- Domain (e.g., dashboard.crossidentity.com)

### Install Required Tools

```bash
# macOS (using Homebrew)
brew install terraform awscli docker

# Verify installations
terraform --version
aws --version
docker --version
```

## AWS Account Setup

### 1. Create IAM User for Terraform/CI-CD

```bash
# Create IAM user
aws iam create-user --user-name terraform-user

# Create access key
aws iam create-access-key --user-name terraform-user

# Attach policies (repeat for each policy)
aws iam attach-user-policy \
  --user-name terraform-user \
  --policy-arn arn:aws:iam::aws:policy/AdministratorAccess

# Save credentials securely
```

### 2. Configure AWS CLI Locally

```bash
aws configure

# Enter:
# AWS Access Key ID: [from step 1]
# AWS Secret Access Key: [from step 1]
# Default region: us-east-1
# Default output format: json
```

### 3. Create S3 Backend Infrastructure

```bash
# Navigate to terraform directory
cd terraform

# Create S3 bucket
aws s3api create-bucket \
  --bucket routine-operations-dashboard-tfstate-$(date +%s) \
  --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket routine-operations-dashboard-tfstate-$(date +%s) \
  --versioning-configuration Status=Enabled

# Block public access
aws s3api put-public-access-block \
  --bucket routine-operations-dashboard-tfstate-$(date +%s) \
  --public-access-block-configuration \
  "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

# Create DynamoDB table for locking
aws dynamodb create-table \
  --table-name terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

## Terraform Deployment

### Step 1: Initialize Terraform

```bash
cd terraform

# Initialize
terraform init \
  -backend-config="bucket=routine-operations-dashboard-tfstate-XXXXXXXXXX" \
  -backend-config="key=terraform.tfstate" \
  -backend-config="region=us-east-1" \
  -backend-config="encrypt=true"

# Validate configuration
terraform validate

# Check formatting
terraform fmt -recursive
```

### Step 2: Plan Infrastructure

```bash
# Generate plan (review before applying)
terraform plan -out=tfplan -var-file=terraform.tfvars

# Save plan for reference
terraform show tfplan > tfplan.txt
```

### Step 3: Apply Configuration

```bash
# Apply infrastructure
terraform apply tfplan

# Confirm changes
# Review and type 'yes'

# Save outputs
terraform output -json > ../terraform-outputs.json
```

### Step 4: Verify Deployment

```bash
# Check ECR repository created
aws ecr describe-repositories --repository-names routine-operations-dashboard-dev

# Check ECS cluster
aws ecs describe-clusters --clusters routine-operations-dashboard-cluster-dev

# Check RDS instance
aws rds describe-db-instances --db-instance-identifier routine-operations-dashboard-mysql-dev

# Check ALB
aws elbv2 describe-load-balancers --names routine-operations-dashboard-alb-dev
```

## GitHub Actions Setup

### Step 1: Add GitHub Secrets

Navigate to: **Settings → Secrets and variables → Actions**

Add the following secrets:

| Secret Name | Value |
|------------|-------|
| `AWS_ACCESS_KEY_ID` | From IAM user |
| `AWS_SECRET_ACCESS_KEY` | From IAM user |

### Step 2: Update Workflow Variables

Edit `.github/workflows/deploy.yml`:

```yaml
env:
  AWS_REGION: us-east-1
  ECR_REPOSITORY: routine-operations-dashboard-dev
  ECS_CLUSTER: routine-operations-dashboard-cluster-dev
  ECS_SERVICE: routine-operations-dashboard-service
```

### Step 3: Trigger First Deployment

```bash
# Push to main or arvi/aws-setup branch
git add .
git commit -m "Setup AWS infrastructure"
git push origin arvi/aws-setup
```

Monitor workflow in: **Actions → Deploy to AWS**

## Application Configuration

### Step 1: Update Application for AWS

Ensure `app.py` reads from environment:

```python
import os
from flask import Flask

app = Flask(__name__)

# Database configuration
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASS = os.getenv('DB_PASSWORD', '')
DB_NAME = os.getenv('DB_NAME', 'appdb')

# Redis configuration
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
```

### Step 2: Update Docker Environment

The ECS task passes environment variables via:

1. **Secrets Manager** (for sensitive data):
   - Database credentials
   - API keys
   - Tokens

2. **Environment Variables** (in task definition):
   - App version
   - Environment name
   - Configuration flags

### Step 3: Initialize Database

After deployment, connect and run migrations:

```bash
# Get RDS endpoint from Terraform output
RDS_ENDPOINT=$(aws rds describe-db-instances \
  --db-instance-identifier routine-operations-dashboard-mysql-dev \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text)

# Connect to database
mysql -h $RDS_ENDPOINT -u admin -p appdb

# Run SQL migrations from migrations/ directory
mysql -h $RDS_ENDPOINT -u admin -p appdb < migrations/001_create_indexes.sql
```

## Verification & Testing

### Test 1: Verify ALB Health

```bash
# Get ALB DNS name
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --names routine-operations-dashboard-alb-dev \
  --query 'LoadBalancers[0].DNSName' \
  --output text)

# Test HTTP (should redirect to HTTPS)
curl -I http://$ALB_DNS

# Test HTTPS (requires valid certificate)
curl -I https://dashboard.crossidentity.com
```

### Test 2: Check ECS Service Status

```bash
# Get service details
aws ecs describe-services \
  --cluster routine-operations-dashboard-cluster-dev \
  --services routine-operations-dashboard-service \
  --query 'services[0].[runningCount,desiredCount,status]'

# Expected output: [1, 1, ACTIVE]
```

### Test 3: View Application Logs

```bash
# Stream logs from CloudWatch
aws logs tail /ecs/routine-operations-dashboard-dev --follow

# View recent logs
aws logs get-log-events \
  --log-group-name /ecs/routine-operations-dashboard-dev \
  --log-stream-name ecs/routine-operations-dashboard/$(aws ecs describe-services \
    --cluster routine-operations-dashboard-cluster-dev \
    --services routine-operations-dashboard-service \
    --query 'services[0].taskDefinition' \
    --output text | cut -d'/' -f3)
```

### Test 4: Database Connectivity

```bash
# Get RDS endpoint and credentials from Secrets Manager
SECRET=$(aws secretsmanager get-secret-value \
  --secret-id routine-operations-dashboard/dev/secrets \
  --query SecretString \
  --output text)

# Extract values
DB_HOST=$(echo $SECRET | jq -r '.db_host')
DB_USER=$(echo $SECRET | jq -r '.db_user')
DB_PASS=$(echo $SECRET | jq -r '.db_password')

# Test connection
mysql -h $DB_HOST -u $DB_USER -p"$DB_PASS" -e "SELECT 1"
```

### Test 5: Load Testing

```bash
# Install Apache Bench (if not installed)
brew install httpd

# Run load test
ab -n 100 -c 10 https://dashboard.crossidentity.com/

# Monitor ECS auto-scaling
aws ecs describe-services \
  --cluster routine-operations-dashboard-cluster-dev \
  --services routine-operations-dashboard-service
```

## Monitoring & Maintenance

### CloudWatch Dashboard

Create a custom dashboard:

```bash
aws cloudwatch put-dashboard \
  --dashboard-name routine-operations-dashboard \
  --dashboard-body file://dashboard-config.json
```

### Auto-Scaling Policies

Current policies:

- **CPU**: Scale up if average CPU > 70%
- **Memory**: Scale up if average memory > 80%
- **Min Tasks**: 1 (dev) / 2 (prod)
- **Max Tasks**: 3

Adjust in `terraform.tfvars`:

```hcl
desired_count = 2
```

### Scheduled Backups

RDS is configured with:

- **Backup Retention**: 7 days (dev) / 30 days (prod)
- **Multi-AZ**: No (dev) / Yes (prod)
- **Backup Window**: 03:00-04:00 UTC

### Security Patching

- ECS tasks are updated automatically with latest images
- RDS receives automated minor patches
- Keep Terraform and dependencies updated

### Cost Optimization

Monitor costs:

```bash
aws ce get-cost-and-usage \
  --time-period Start=2025-11-01,End=2025-11-30 \
  --granularity DAILY \
  --metrics "BlendedCost" \
  --group-by Type=DIMENSION,Key=SERVICE
```

### Troubleshooting Common Issues

**Issue**: ECS tasks not starting
```bash
aws logs tail /ecs/routine-operations-dashboard-dev --follow --since 1m
```

**Issue**: Database connection fails
```bash
aws ec2 describe-security-groups --group-names routine-operations-dashboard-rds-sg
# Verify inbound rule allows port 3306 from ECS security group
```

**Issue**: ALB shows unhealthy targets
```bash
aws elbv2 describe-target-health \
  --target-group-arn arn:aws:elasticloadbalancing:us-east-1:ACCOUNT:targetgroup/...
```

## Next Steps

1. ✅ Set up AWS infrastructure with Terraform
2. ✅ Configure GitHub Actions for CI/CD
3. ✅ Deploy application to ECS
4. ⏳ Set up custom domain DNS records (Route 53)
5. ⏳ Configure SSL certificate validation (ACM)
6. ⏳ Set up monitoring alerts (CloudWatch)
7. ⏳ Implement automated backups
8. ⏳ Plan disaster recovery

## Support & Documentation

- [AWS ECS Best Practices](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [AWS Security Best Practices](https://aws.amazon.com/architecture/security-identity-compliance/)
