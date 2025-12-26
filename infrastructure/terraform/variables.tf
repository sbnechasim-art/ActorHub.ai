# Project Variables

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "actorhub"
}

variable "environment" {
  description = "Environment (staging, production)"
  type        = string
  default     = "staging"

  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "Environment must be staging or production."
  }
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

# VPC Variables
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "private_subnets" {
  description = "Private subnet CIDR blocks"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "public_subnets" {
  description = "Public subnet CIDR blocks"
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
}

# EKS Variables
variable "eks_cluster_version" {
  description = "Kubernetes version for EKS"
  type        = string
  default     = "1.28"
}

variable "eks_node_groups" {
  description = "EKS Node Group configuration"
  type = map(object({
    instance_types = list(string)
    capacity_type  = string
    min_size       = number
    max_size       = number
    desired_size   = number
    labels         = map(string)
  }))
  default = {
    general = {
      instance_types = ["t3.medium"]
      capacity_type  = "ON_DEMAND"
      min_size       = 2
      max_size       = 10
      desired_size   = 2
      labels = {
        workload = "general"
      }
    }
    ml = {
      instance_types = ["c5.xlarge"]
      capacity_type  = "ON_DEMAND"
      min_size       = 0
      max_size       = 5
      desired_size   = 1
      labels = {
        workload = "ml"
      }
    }
  }
}

# RDS Variables
variable "rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.medium"
}

variable "rds_allocated_storage" {
  description = "Initial storage in GB"
  type        = number
  default     = 20
}

variable "rds_max_allocated_storage" {
  description = "Maximum storage in GB (for autoscaling)"
  type        = number
  default     = 100
}

# Redis Variables
variable "redis_node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.t3.micro"
}

# Common Tags
variable "common_tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Project   = "ActorHub"
    ManagedBy = "Terraform"
  }
}
