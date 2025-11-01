variable "aws_region" {
  type        = string
  description = "AWS region for resources"
  default     = "us-east-1"
}

variable "environment" {
  type        = string
  description = "Environment name (dev/prod)"
  validation {
    condition     = contains(["dev", "prod"], var.environment)
    error_message = "Environment must be 'dev' or 'prod'."
  }
}

variable "app_name" {
  type        = string
  description = "Application name"
  default     = "routine-operations-dashboard"
}

variable "docker_image_tag" {
  type        = string
  description = "Docker image tag"
  default     = "latest"
}

variable "container_port" {
  type        = number
  description = "Port exposed by the container"
  default     = 5000
}

variable "container_cpu" {
  type        = number
  description = "ECS task CPU units"
  default     = 256
}

variable "container_memory" {
  type        = number
  description = "ECS task memory in MB"
  default     = 512
}

variable "desired_count" {
  type        = number
  description = "Desired number of ECS tasks"
  default     = 1
}

variable "vpc_cidr" {
  type        = string
  description = "CIDR block for VPC"
  default     = "10.0.0.0/16"
}

variable "rds_allocated_storage" {
  type        = number
  description = "RDS allocated storage in GB"
  default     = 20
}

variable "rds_engine_version" {
  type        = string
  description = "MySQL engine version"
  default     = "8.0.35"
}

variable "rds_instance_class" {
  type        = string
  description = "RDS instance class"
  default     = "db.t3.micro"
}

variable "redis_engine_version" {
  type        = string
  description = "Redis engine version"
  default     = "7.0"
}

variable "redis_node_type" {
  type        = string
  description = "ElastiCache node type"
  default     = "cache.t3.micro"
}

variable "tags" {
  type        = map(string)
  description = "Additional tags for resources"
  default     = {}
}
