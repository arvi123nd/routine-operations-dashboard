# Environment Configurations

This directory contains environment-specific Terraform variable files for different deployment stages.

## Development Environment

**File**: `terraform/terraform.tfvars`

```hcl
aws_region             = "us-east-1"
environment            = "dev"
app_name               = "routine-operations-dashboard"
docker_image_tag       = "latest"
container_port         = 5000
container_cpu          = 256
container_memory       = 512
desired_count          = 1
vpc_cidr               = "10.0.0.0/16"
rds_allocated_storage  = 20
rds_engine_version     = "8.0.35"
rds_instance_class     = "db.t3.micro"
redis_engine_version   = "7.0"
redis_node_type        = "cache.t3.micro"
```

**Characteristics**:
- Single ECS task instance
- Minimal RDS (t3.micro)
- Minimal ElastiCache (t3.micro)
- 7-day backup retention
- No multi-AZ for RDS
- Skip final snapshot

**Deploy**:
```bash
cd terraform
terraform apply -var-file=terraform.tfvars
```

## Production Environment

**File**: `terraform/prod.tfvars`

```hcl
aws_region             = "us-east-1"
environment            = "prod"
app_name               = "routine-operations-dashboard"
docker_image_tag       = "v1.0.0"  # Use specific version tags
container_port         = 5000
container_cpu          = 512       # Increased for better performance
container_memory       = 1024      # Increased for better performance
desired_count          = 2         # HA setup
vpc_cidr               = "10.1.0.0/16"  # Different CIDR for isolation
rds_allocated_storage  = 100       # Larger storage
rds_engine_version     = "8.0.35"
rds_instance_class     = "db.t3.small"   # Larger instance
redis_engine_version   = "7.0"
redis_node_type        = "cache.t3.small"  # Larger cache
```

**Characteristics**:
- High Availability (2+ ECS tasks)
- Larger RDS instance (t3.small)
- Larger ElastiCache (t3.small)
- 30-day backup retention
- Multi-AZ enabled for RDS
- Keep final snapshot
- ALB deletion protection enabled
- Auto-scaling 1-3 tasks

**Deploy**:
```bash
cd terraform
terraform apply -var-file=prod.tfvars
```

## Staging Environment (Optional)

**File**: `terraform/staging.tfvars`

```hcl
aws_region             = "us-east-1"
environment            = "staging"
app_name               = "routine-operations-dashboard"
docker_image_tag       = "release-candidate"
container_port         = 5000
container_cpu          = 256
container_memory       = 512
desired_count          = 1
vpc_cidr               = "10.0.0.0/16"
rds_allocated_storage  = 50
rds_engine_version     = "8.0.35"
rds_instance_class     = "db.t3.small"   # Mid-tier for testing
redis_engine_version   = "7.0"
redis_node_type        = "cache.t3.micro"
```

**Deploy**:
```bash
cd terraform
terraform apply -var-file=staging.tfvars
```

## Switching Between Environments

### View Current Environment

```bash
cd terraform
terraform show | grep environment
```

### Switch to Different Environment

```bash
cd terraform

# Backup current state
cp terraform.tfstate terraform.tfstate.backup

# Switch variable file
cp terraform.tfvars terraform.tfvars.dev.backup
cp prod.tfvars terraform.tfvars

# Plan changes
terraform plan

# Apply changes
terraform apply
```

### Manage Multiple Workspaces

Alternatively, use Terraform workspaces:

```bash
cd terraform

# Create workspaces
terraform workspace new dev
terraform workspace new prod

# Select workspace
terraform workspace select dev

# Apply to current workspace
terraform apply -var-file=dev.tfvars
```

## Environment Variables for GitHub Actions

### Development

Create `.github/workflows/deploy-dev.yml`:

```yaml
name: Deploy to Dev

on:
  push:
    branches:
      - arvi/aws-setup

env:
  AWS_REGION: us-east-1
  ENVIRONMENT: dev
  ECR_REPOSITORY: routine-operations-dashboard-dev
  TERRAFORM_VARS: -var-file=terraform.tfvars
```

### Production

Create `.github/workflows/deploy-prod.yml`:

```yaml
name: Deploy to Prod

on:
  push:
    branches:
      - main
    tags:
      - 'v*.*.*'

env:
  AWS_REGION: us-east-1
  ENVIRONMENT: prod
  ECR_REPOSITORY: routine-operations-dashboard-prod
  TERRAFORM_VARS: -var-file=prod.tfvars
```

## Cost Estimation

### Development

- ECS Fargate: ~$5-10/month
- RDS t3.micro: ~$10-15/month
- ElastiCache t3.micro: ~$5-8/month
- NAT Gateway: ~$32/month
- ALB: ~$16/month
- Data Transfer: ~$2-5/month
- **Total**: ~$70-76/month

### Production

- ECS Fargate (2 tasks): ~$15-25/month
- RDS t3.small: ~$20-30/month
- ElastiCache t3.small: ~$15-20/month
- NAT Gateways (2): ~$64/month
- ALB: ~$16/month
- Data Transfer: ~$5-15/month
- **Total**: ~$135-170/month

## Switching Production to Production Configuration

⚠️ **Production deployments require approval**

```bash
# 1. Create PR with prod.tfvars changes
git checkout -b switch-to-prod-config
cp prod.tfvars terraform/terraform.tfvars
git add terraform/terraform.tfvars
git commit -m "Switch infrastructure to production configuration"
git push origin switch-to-prod-config

# 2. Create PR for review
# → Requires 2 approvals before merge

# 3. After merge to main
# → GitHub Actions automatically deploys to production

# 4. Verify deployment
terraform output -json | jq '.alb_dns_name'
```

## Rollback Procedure

If issues occur in production:

```bash
cd terraform

# View previous state
terraform state list

# Plan rollback to previous version
terraform plan -var-file=prod.tfvars -refresh=true

# If needed, revert to backup
cp terraform.tfstate.backup terraform.tfstate
terraform refresh
```

## Migration Between Environments

To promote from Dev → Staging → Production:

```bash
# 1. Export Dev configuration
cd terraform
terraform output -json > dev-output.json

# 2. Create staging resources
cp terraform.tfstate terraform.tfstate.dev.backup
terraform apply -var-file=staging.tfvars

# 3. Run integration tests
./tests/integration-tests.sh

# 4. If successful, promote to production
terraform apply -var-file=prod.tfvars
```

## Best Practices

1. **Always use variable files**: Never apply without explicit tfvars
2. **Review plans**: Run `terraform plan` before `apply`
3. **Backup state**: Keep terraform.tfstate backed up
4. **Tag production releases**: Use semantic versioning (v1.0.0, v1.0.1)
5. **Test in dev first**: Always test changes in development
6. **Monitor costs**: Check AWS Cost Explorer regularly
7. **Document changes**: Update this file for new configurations
