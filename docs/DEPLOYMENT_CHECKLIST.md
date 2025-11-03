# AWS Deployment Checklist

Complete this checklist before deploying to production.

## Pre-Deployment (One-Time)

### AWS Account Setup
- [ ] AWS Account created
- [ ] IAM user created with programmatic access
- [ ] Access Key ID and Secret Access Key saved securely
- [ ] AWS CLI installed and configured locally
- [ ] Terraform 1.5+ installed
- [ ] Docker installed locally

### Backend Infrastructure
- [ ] S3 bucket created for Terraform state (`routine-operations-dashboard-tfstate`)
- [ ] S3 bucket versioning enabled
- [ ] S3 bucket public access blocked
- [ ] DynamoDB table created for state locking (`terraform-locks`)
- [ ] AWS credentials configured in GitHub Secrets

### GitHub Repository Setup
- [ ] GitHub repository forked
- [ ] Branch `arvi/aws-setup` created
- [ ] GitHub Secrets added:
  - [ ] `AWS_ACCESS_KEY_ID`
  - [ ] `AWS_SECRET_ACCESS_KEY`
- [ ] Workflow permissions configured

## Development Deployment

### Infrastructure Setup
- [ ] Terraform initialized: `terraform init`
- [ ] Terraform validated: `terraform validate`
- [ ] Terraform plan reviewed: `terraform plan -out=tfplan`
- [ ] Infrastructure applied: `terraform apply tfplan`
- [ ] Outputs saved: `terraform output -json > ../terraform-outputs.json`

### Service Verification
- [ ] ECR repository created and accessible
- [ ] ECS cluster created and active
- [ ] ECS service running 1 task
- [ ] RDS MySQL instance created and accessible
- [ ] ElastiCache Redis cluster created
- [ ] S3 bucket created for assets
- [ ] Secrets Manager secret created with database credentials
- [ ] CloudWatch log group created
- [ ] ALB created and health checks passing

### Application Configuration
- [ ] app.py reads DATABASE_URL from environment
- [ ] app.py reads REDIS_HOST from environment
- [ ] Database migrations run: `mysql ... < migrations/001_create_indexes.sql`
- [ ] Redis connection tested
- [ ] Application starts without errors

### CI/CD Setup
- [ ] GitHub Actions workflow enabled
- [ ] Workflow tested by pushing to `arvi/aws-setup` branch
- [ ] Docker image built successfully
- [ ] Image pushed to ECR
- [ ] ECS service updated with new image
- [ ] Application accessible via ALB DNS name

## Security Verification

### Network Security
- [ ] VPC created with public/private subnets
- [ ] Security groups configured with least-privilege rules
- [ ] RDS not publicly accessible
- [ ] Redis not publicly accessible
- [ ] ALB allows HTTP (redirects to HTTPS) and HTTPS only

### Data Security
- [ ] RDS encryption enabled
- [ ] Redis encryption in transit enabled
- [ ] S3 bucket encryption enabled
- [ ] Secrets Manager storing database credentials
- [ ] IAM roles with minimal permissions

### Monitoring & Logging
- [ ] CloudWatch logs receiving ECS task logs
- [ ] CloudWatch alarms configured (optional)
- [ ] Application errors logged and visible
- [ ] ECS service auto-scaling configured

## Pre-Production Handoff

### Documentation
- [ ] `docs/DEPLOYMENT.md` reviewed and up-to-date
- [ ] `docs/ENVIRONMENTS.md` reviewed with prod config
- [ ] `docs/AWS_QUICKSTART.md` tested and working
- [ ] Terraform outputs documented
- [ ] Database credentials stored securely

### Testing
- [ ] Application accessible via ALB DNS
- [ ] HTTP endpoints respond correctly
- [ ] Database queries working
- [ ] Redis caching working
- [ ] Static assets served from S3 (if configured)
- [ ] Load test completed (100+ concurrent users)

### Operational Readiness
- [ ] Runbook created for common tasks
- [ ] Troubleshooting guide prepared
- [ ] Cost monitoring dashboard set up
- [ ] Backup strategy documented
- [ ] Disaster recovery plan documented

## Production Deployment

### Pre-Deployment Review
- [ ] Prod tfvars prepared: `prod.tfvars`
- [ ] Infrastructure plan reviewed: `terraform plan -var-file=prod.tfvars`
- [ ] Multi-AZ RDS enabled in prod config
- [ ] 2+ ECS tasks configured for HA
- [ ] Larger instance sizes reviewed for cost

### Domain & SSL Configuration
- [ ] Domain DNS records updated (if using Route 53)
- [ ] ACM certificate validation pending (check AWS Console)
- [ ] DNS validation CNAME records added to DNS provider
- [ ] Certificate validation complete
- [ ] HTTPS accessible at domain (e.g., dashboard.crossidentity.com)

### Production Deployment
- [ ] Terraform init with prod config
- [ ] Terraform plan reviewed by 2 people
- [ ] Terraform apply executed
- [ ] All services verified running
- [ ] Monitoring dashboards active

### Post-Deployment Validation
- [ ] Application accessible via production domain
- [ ] All endpoints working correctly
- [ ] Database backups configured
- [ ] Auto-scaling tested under load
- [ ] Logging and monitoring verified
- [ ] Team trained on operational procedures

### Go-Live Readiness
- [ ] Traffic slowly increased to production
- [ ] Monitoring alerts active
- [ ] On-call rotation established
- [ ] Incident response plan ready
- [ ] Rollback plan documented and tested

## Ongoing Maintenance

### Weekly
- [ ] Check CloudWatch logs for errors
- [ ] Monitor CPU and memory utilization
- [ ] Verify backup jobs completed
- [ ] Check for security updates

### Monthly
- [ ] Review AWS costs
- [ ] Analyze performance metrics
- [ ] Update dependencies
- [ ] Test disaster recovery procedures
- [ ] Review and optimize database queries

### Quarterly
- [ ] Security audit
- [ ] Capacity planning review
- [ ] Cost optimization review
- [ ] Architecture review
- [ ] Update runbooks and documentation

## Rollback Procedure

If production deployment has critical issues:

```bash
cd terraform

# Option 1: Revert infrastructure
terraform plan -destroy -var-file=prod.tfvars
# Review carefully, then:
terraform destroy -var-file=prod.tfvars

# Option 2: Revert ECS service to previous image
aws ecs update-service \
  --cluster routine-operations-dashboard-cluster-prod \
  --service routine-operations-dashboard-service \
  --force-new-deployment

# Option 3: Restore database from backup
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier routine-operations-dashboard-mysql-prod-restore \
  --db-snapshot-identifier [snapshot-id]
```

## Sign-Off

- [ ] Development deployment approved by: _________________ Date: _______
- [ ] Security review completed by: _________________ Date: _______
- [ ] Production deployment approved by: _________________ Date: _______
- [ ] Business stakeholder sign-off: _________________ Date: _______

---

**Deployment Date**: _______________
**Deployed By**: _______________
**Reviewed By**: _______________

**Notes**:
```
[Add any deployment notes or issues here]
```
