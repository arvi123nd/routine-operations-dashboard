# Quick Start: AWS Infrastructure

Quick reference for deploying and managing AWS infrastructure.

## One-Time Setup (First Time Only)

```bash
# 1. Create S3 backend
aws s3api create-bucket \
  --bucket routine-operations-dashboard-tfstate \
  --region us-east-1

# 2. Create DynamoDB lock table
aws dynamodb create-table \
  --table-name terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1

# 3. Store GitHub secrets:
# Settings → Secrets → Add:
#   AWS_ACCESS_KEY_ID
#   AWS_SECRET_ACCESS_KEY
```

## Deploy Infrastructure (Development)

```bash
cd terraform

# Initialize
terraform init

# Plan
terraform plan -out=tfplan

# Apply
terraform apply tfplan

# View outputs
terraform output -json
```

## Deploy Infrastructure (Production)

```bash
cd terraform

# Use production config
terraform plan -var-file=prod.tfvars -out=tfplan

# Review changes (should show 2x ECS tasks, Multi-AZ RDS, etc.)
terraform show tfplan

# Apply
terraform apply tfplan
```

## View Infrastructure Status

```bash
# ECS service status
aws ecs describe-services \
  --cluster routine-operations-dashboard-cluster-dev \
  --services routine-operations-dashboard-service

# View recent logs
aws logs tail /ecs/routine-operations-dashboard-dev --follow

# ALB health
aws elbv2 describe-target-health \
  --target-group-arn $(aws elbv2 describe-target-groups \
    --names routine-operations-dashboard-tg-dev \
    --query 'TargetGroups[0].TargetGroupArn' --output text)

# RDS status
aws rds describe-db-instances \
  --db-instance-identifier routine-operations-dashboard-mysql-dev
```

## Common Tasks

### Restart ECS Service

```bash
aws ecs update-service \
  --cluster routine-operations-dashboard-cluster-dev \
  --service routine-operations-dashboard-service \
  --force-new-deployment
```

### Scale ECS Tasks

```bash
# Scale to 2 tasks
aws ecs update-service \
  --cluster routine-operations-dashboard-cluster-dev \
  --service routine-operations-dashboard-service \
  --desired-count 2
```

### View Secrets

```bash
aws secretsmanager get-secret-value \
  --secret-id routine-operations-dashboard/dev/secrets \
  --query SecretString | jq
```

### Update Application

Push to `main` or `arvi/aws-setup` → GitHub Actions automatically:
1. Builds Docker image
2. Pushes to ECR
3. Updates ECS service

### Connect to Database

```bash
# Get endpoint
RDS_ENDPOINT=$(aws rds describe-db-instances \
  --db-instance-identifier routine-operations-dashboard-mysql-dev \
  --query 'DBInstances[0].Endpoint.Address' --output text)

# Get password from Secrets Manager
DB_PASS=$(aws secretsmanager get-secret-value \
  --secret-id routine-operations-dashboard/dev/secrets \
  --query 'SecretString' | jq -r '.db_password')

# Connect
mysql -h $RDS_ENDPOINT -u admin -p"$DB_PASS" appdb
```

### View Logs

```bash
# Stream live logs
aws logs tail /ecs/routine-operations-dashboard-dev --follow

# Last 100 lines
aws logs tail /ecs/routine-operations-dashboard-dev --max-items 100

# Last 5 minutes
aws logs tail /ecs/routine-operations-dashboard-dev --since 5m
```

## Destroy Infrastructure (Clean Up)

```bash
cd terraform

# Plan destruction
terraform plan -destroy -out=tfplan

# Confirm
terraform destroy

# Note: S3 bucket and DynamoDB table persist (to protect state)
```

## Useful CLI Aliases

Add to `~/.zshrc`:

```bash
alias tf='terraform'
alias tfinit='terraform init'
alias tfplan='terraform plan -out=tfplan'
alias tfapply='terraform apply tfplan'
alias tfoutput='terraform output -json | jq'
alias logs='aws logs tail /ecs/routine-operations-dashboard-dev --follow'
alias service-status='aws ecs describe-services --cluster routine-operations-dashboard-cluster-dev --services routine-operations-dashboard-service'
alias scale-tasks='aws ecs update-service --cluster routine-operations-dashboard-cluster-dev --services routine-operations-dashboard-service --desired-count'
```

## Monitoring URLs

- **ALB DNS**: From `terraform output alb_dns_name`
- **Application**: `https://dashboard.crossidentity.com`
- **AWS Console**: https://console.aws.amazon.com/
- **CloudWatch Logs**: https://console.aws.amazon.com/logs
- **ECS Console**: https://console.aws.amazon.com/ecs

## Key Files

| File | Purpose |
|------|---------|
| `terraform/main.tf` | Infrastructure definitions |
| `terraform/variables.tf` | Variable definitions |
| `terraform/outputs.tf` | Output values |
| `terraform/terraform.tfvars` | Dev environment values |
| `terraform/prod.tfvars` | Prod environment values |
| `.github/workflows/deploy.yml` | CI/CD pipeline |
| `docs/DEPLOYMENT.md` | Full deployment guide |
| `docs/ENVIRONMENTS.md` | Environment configurations |

## Troubleshooting

**Tasks not starting?**
```bash
aws logs tail /ecs/routine-operations-dashboard-dev --follow
```

**Database connection fails?**
```bash
# Check security group
aws ec2 describe-security-groups --group-names routine-operations-dashboard-ecs-sg
# Should allow port 3306 from RDS security group
```

**ALB unhealthy?**
```bash
aws elbv2 describe-target-health \
  --target-group-arn [target-group-arn]
```

**Can't apply Terraform?**
```bash
# Refresh state
terraform refresh

# Or unlock if stuck
terraform force-unlock [LOCK_ID]
```

## Cost Estimate

| Component | Dev | Prod |
|-----------|-----|------|
| ECS Fargate | $5-10 | $15-25 |
| RDS MySQL | $10-15 | $20-30 |
| ElastiCache | $5-8 | $15-20 |
| NAT Gateway | $32 | $64 |
| ALB | $16 | $16 |
| **Total/Month** | **$70-76** | **$135-170** |

## Support

- Terraform docs: https://www.terraform.io/docs
- AWS docs: https://docs.aws.amazon.com/
- ECS docs: https://docs.aws.amazon.com/AmazonECS
- This repo: [GitHub Issues]
