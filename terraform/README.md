# AWS Infrastructure Setup with Terraform

This directory contains Terraform configurations for deploying the Routine Operations Dashboard application to AWS.

## Architecture Overview

The infrastructure includes:

- **ECR**: Docker image repository
- **VPC**: Virtual Private Cloud with public and private subnets across 2 availability zones
- **ECS Fargate**: Container orchestration
- **ALB**: Application Load Balancer with HTTPS termination
- **RDS MySQL**: Managed database
- **ElastiCache Redis**: In-memory cache
- **S3**: Static assets and backups
- **Secrets Manager**: Secure credential storage
- **CloudWatch**: Logging and monitoring

## Prerequisites

1. **AWS Account**: With appropriate permissions
2. **Terraform**: >= 1.0 installed
3. **AWS CLI**: Configured with credentials
4. **GitHub Secrets**: Set up for CI/CD

## Setup Instructions

### 1. Create S3 Backend for Terraform State

```bash
# Create S3 bucket for Terraform state (only once)
aws s3api create-bucket \
  --bucket routine-operations-dashboard-tfstate \
  --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket routine-operations-dashboard-tfstate \
  --versioning-configuration Status=Enabled

# Block public access
aws s3api put-public-access-block \
  --bucket routine-operations-dashboard-tfstate \
  --public-access-block-configuration \
  "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

# Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
  --region us-east-1
```

### 2. Initialize Terraform

```bash
cd terraform

# Initialize Terraform
terraform init

# Verify configuration
terraform validate
```

### 3. Plan Deployment

```bash
# Generate plan
terraform plan -out=tfplan

# Review output
```

### 4. Deploy Infrastructure

```bash
# Apply configuration
terraform apply tfplan

# Save outputs
terraform output -json > ../terraform-outputs.json
```

### 5. Configure GitHub Secrets

Set the following secrets in your GitHub repository:

- `AWS_ACCESS_KEY_ID`: AWS IAM user access key
- `AWS_SECRET_ACCESS_KEY`: AWS IAM user secret key

### 6. Update ACM Certificate

After Terraform deployment, validate the SSL certificate in AWS Certificate Manager:

1. Go to AWS Console → Certificate Manager
2. Find the pending certificate for `dashboard.crossidentity.com`
3. Follow DNS validation steps (add CNAME records to your DNS provider)

## Customization

### Environment Variables

Edit `terraform.tfvars` to customize:

- `aws_region`: AWS region (default: us-east-1)
- `environment`: Environment name (dev/prod)
- `container_cpu`: ECS task CPU (256, 512, 1024, etc.)
- `container_memory`: ECS task memory in MB
- `desired_count`: Number of ECS tasks
- `rds_instance_class`: RDS instance type
- `redis_node_type`: ElastiCache node type

### Production Deployment

For production, create a separate tfvars file:

```bash
# terraform/prod.tfvars
aws_region             = "us-east-1"
environment            = "prod"
desired_count          = 2
rds_instance_class     = "db.t3.small"
redis_node_type        = "cache.t3.small"
```

Deploy with:

```bash
terraform apply -var-file="prod.tfvars"
```

## Outputs

After deployment, Terraform outputs key values:

```bash
terraform output -json
```

Key outputs:
- `ecr_repository_url`: ECR repository URL
- `alb_dns_name`: ALB DNS name
- `rds_endpoint`: RDS database endpoint (sensitive)
- `redis_endpoint`: Redis endpoint (sensitive)
- `cloudwatch_log_group`: CloudWatch log group for ECS

## Monitoring

### CloudWatch Logs

View ECS logs:

```bash
aws logs tail /ecs/routine-operations-dashboard-dev --follow
```

### ECS Service Status

Check service health:

```bash
aws ecs describe-services \
  --cluster routine-operations-dashboard-cluster-dev \
  --services routine-operations-dashboard-service
```

## Cleanup

**WARNING**: This will delete all resources!

```bash
terraform destroy
```

Then manually delete:
- S3 bucket (if retention not needed)
- DynamoDB table (if not needed for other projects)

## Security Best Practices

✅ Implemented:
- VPC with private subnets for databases
- Security groups with least-privilege rules
- RDS encryption at rest
- Redis encryption in transit
- S3 bucket encryption
- Secrets Manager for credentials
- IAM roles with minimal permissions
- ALB with HTTPS
- Container image scanning (Trivy)

⚠️ To-Do:
- Enable AWS WAF on ALB
- Set up VPC Flow Logs
- Enable GuardDuty
- Configure CloudTrail logging
- Implement backup and disaster recovery

## Troubleshooting

### Terraform State Locked

If state is locked:

```bash
terraform force-unlock <LOCK_ID>
```

### ECS Service Won't Start

Check logs:

```bash
aws logs tail /ecs/routine-operations-dashboard-dev --follow
```

### Database Connection Issues

Verify security group rules:

```bash
aws ec2 describe-security-groups --group-names routine-operations-dashboard-rds-sg
```

## Support

For issues or questions, refer to:
- [Terraform AWS Provider Docs](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [ECS Best Practices](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/)
- [AWS Security Best Practices](https://aws.amazon.com/architecture/security-identity-compliance/)
