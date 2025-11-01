# Terraform Configuration for 2000+ Users
# This configuration is optimized for handling 2000-3000 concurrent users

# Environment
aws_region  = "us-east-1"
environment = "prod"
app_name    = "routine-operations-dashboard"

# Application Tier - Scaled for High Traffic
# Original: 256 CPU, 512 MB memory, 1 task
# Updated: 1024 CPU (1 vCPU), 2048 MB (2 GB), 10 tasks minimum
container_cpu     = 1024
container_memory  = 2048
desired_count     = 10          # Minimum 10 tasks always running
container_port    = 5000
docker_image_tag  = "latest"

# VPC Configuration
vpc_cidr = "10.0.0.0/16"

# Database Tier - Scaled for High Load
# Original: db.t3.micro (1 vCPU, 1 GB RAM)
# Updated: db.r5.xlarge (4 vCPU, 32 GB RAM) with Multi-AZ
rds_instance_class    = "db.r5.xlarge"
rds_allocated_storage = 100                # 20 GB → 100 GB storage
rds_engine_version    = "8.0.35"
# Note: Production RDS will have:
# - Multi-AZ enabled (automatic in code for prod)
# - 30-day backup retention (automatic in code for prod)
# - Storage encryption enabled (automatic in code)
# - 6000 IOPS provisioned (add variable if needed)

# Cache Layer - Scaled for Session & Query Caching
# Original: cache.t3.micro (500 MB)
# Updated: cache.r6g.xlarge (8 GB) with Multi-node support
redis_node_type    = "cache.r6g.xlarge"
redis_engine_version = "7.0"

# Tags for resource organization
tags = {
  Environment = "production"
  Project     = "routine-operations-dashboard"
  ManagedBy   = "terraform"
  ScaledFor   = "2000-plus-users"
}
