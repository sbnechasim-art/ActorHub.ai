# ActorHub.ai Infrastructure
# AWS-based production infrastructure

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.11"
    }
  }

  backend "s3" {
    bucket         = "actorhub-terraform-state"
    key            = "infrastructure/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "actorhub-terraform-locks"
  }
}

# Configure providers
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "ActorHub"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

provider "kubernetes" {
  host                   = module.eks.cluster_endpoint
  cluster_ca_certificate = base64decode(module.eks.cluster_ca_certificate)

  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args        = ["eks", "get-token", "--cluster-name", module.eks.cluster_name]
  }
}

provider "helm" {
  kubernetes {
    host                   = module.eks.cluster_endpoint
    cluster_ca_certificate = base64decode(module.eks.cluster_ca_certificate)

    exec {
      api_version = "client.authentication.k8s.io/v1beta1"
      command     = "aws"
      args        = ["eks", "get-token", "--cluster-name", module.eks.cluster_name]
    }
  }
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

# VPC Module
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${var.project_name}-vpc"
  cidr = var.vpc_cidr

  azs             = slice(data.aws_availability_zones.available.names, 0, 3)
  private_subnets = var.private_subnets
  public_subnets  = var.public_subnets

  enable_nat_gateway   = true
  single_nat_gateway   = var.environment != "production"
  enable_dns_hostnames = true
  enable_dns_support   = true

  # Tags for EKS
  public_subnet_tags = {
    "kubernetes.io/role/elb" = 1
  }
  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = 1
  }

  tags = var.common_tags
}

# EKS Module
module "eks" {
  source = "./modules/eks"

  cluster_name    = "${var.project_name}-${var.environment}"
  cluster_version = var.eks_cluster_version
  vpc_id          = module.vpc.vpc_id
  subnet_ids      = module.vpc.private_subnets

  node_groups = var.eks_node_groups

  tags = var.common_tags
}

# RDS Module
module "rds" {
  source = "./modules/rds"

  identifier     = "${var.project_name}-${var.environment}"
  engine         = "postgres"
  engine_version = "16.1"
  instance_class = var.rds_instance_class

  allocated_storage     = var.rds_allocated_storage
  max_allocated_storage = var.rds_max_allocated_storage

  db_name  = "actorhub"
  username = "actorhub"

  vpc_id          = module.vpc.vpc_id
  subnet_ids      = module.vpc.private_subnets
  security_groups = [module.eks.cluster_security_group_id]

  multi_az               = var.environment == "production"
  backup_retention_period = var.environment == "production" ? 7 : 1

  tags = var.common_tags
}

# Redis Module
module "redis" {
  source = "./modules/redis"

  cluster_id         = "${var.project_name}-${var.environment}"
  node_type          = var.redis_node_type
  num_cache_nodes    = var.environment == "production" ? 2 : 1
  parameter_group_family = "redis7"

  vpc_id          = module.vpc.vpc_id
  subnet_ids      = module.vpc.private_subnets
  security_groups = [module.eks.cluster_security_group_id]

  tags = var.common_tags
}

# S3 Module
module "s3" {
  source = "./modules/s3"

  bucket_prefix = var.project_name
  environment   = var.environment

  buckets = [
    {
      name    = "actor-packs"
      acl     = "private"
      versioning = true
    },
    {
      name    = "uploads"
      acl     = "private"
      versioning = false
    },
    {
      name    = "backups"
      acl     = "private"
      versioning = true
      lifecycle_rules = [
        {
          id      = "archive"
          enabled = true
          transition = {
            days          = 30
            storage_class = "GLACIER"
          }
          expiration = {
            days = 365
          }
        }
      ]
    }
  ]

  tags = var.common_tags
}

# Qdrant (using Helm)
resource "helm_release" "qdrant" {
  name       = "qdrant"
  namespace  = "actorhub"
  repository = "https://qdrant.github.io/qdrant-helm"
  chart      = "qdrant"
  version    = "0.7.6"

  create_namespace = true

  set {
    name  = "resources.requests.memory"
    value = "1Gi"
  }
  set {
    name  = "resources.requests.cpu"
    value = "500m"
  }
  set {
    name  = "resources.limits.memory"
    value = "4Gi"
  }
  set {
    name  = "resources.limits.cpu"
    value = "2000m"
  }
  set {
    name  = "persistence.size"
    value = "50Gi"
  }

  depends_on = [module.eks]
}

# NGINX Ingress Controller
resource "helm_release" "nginx_ingress" {
  name       = "nginx-ingress"
  namespace  = "ingress-nginx"
  repository = "https://kubernetes.github.io/ingress-nginx"
  chart      = "ingress-nginx"
  version    = "4.8.3"

  create_namespace = true

  set {
    name  = "controller.service.type"
    value = "LoadBalancer"
  }
  set {
    name  = "controller.service.annotations.service\\.beta\\.kubernetes\\.io/aws-load-balancer-type"
    value = "nlb"
  }

  depends_on = [module.eks]
}

# Cert-Manager for TLS
resource "helm_release" "cert_manager" {
  name       = "cert-manager"
  namespace  = "cert-manager"
  repository = "https://charts.jetstack.io"
  chart      = "cert-manager"
  version    = "1.13.2"

  create_namespace = true

  set {
    name  = "installCRDs"
    value = "true"
  }

  depends_on = [module.eks]
}

# Outputs
output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "eks_cluster_name" {
  description = "EKS Cluster Name"
  value       = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  description = "EKS Cluster Endpoint"
  value       = module.eks.cluster_endpoint
}

output "rds_endpoint" {
  description = "RDS Endpoint"
  value       = module.rds.endpoint
  sensitive   = true
}

output "redis_endpoint" {
  description = "Redis Endpoint"
  value       = module.redis.endpoint
  sensitive   = true
}

output "s3_buckets" {
  description = "S3 Bucket Names"
  value       = module.s3.bucket_names
}
