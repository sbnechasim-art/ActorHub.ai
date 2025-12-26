# S3 Module

variable "bucket_prefix" {
  type = string
}

variable "environment" {
  type = string
}

variable "buckets" {
  type = list(object({
    name       = string
    acl        = string
    versioning = bool
    lifecycle_rules = optional(list(object({
      id      = string
      enabled = bool
      transition = optional(object({
        days          = number
        storage_class = string
      }))
      expiration = optional(object({
        days = number
      }))
    })))
  }))
}

variable "tags" {
  type    = map(string)
  default = {}
}

# Create S3 buckets
resource "aws_s3_bucket" "buckets" {
  for_each = { for b in var.buckets : b.name => b }

  bucket = "${var.bucket_prefix}-${each.value.name}-${var.environment}"

  tags = merge(var.tags, {
    Name = "${var.bucket_prefix}-${each.value.name}-${var.environment}"
  })
}

# Bucket versioning
resource "aws_s3_bucket_versioning" "buckets" {
  for_each = { for b in var.buckets : b.name => b if b.versioning }

  bucket = aws_s3_bucket.buckets[each.key].id

  versioning_configuration {
    status = "Enabled"
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "buckets" {
  for_each = { for b in var.buckets : b.name => b }

  bucket = aws_s3_bucket.buckets[each.key].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "buckets" {
  for_each = { for b in var.buckets : b.name => b }

  bucket = aws_s3_bucket.buckets[each.key].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Lifecycle rules
resource "aws_s3_bucket_lifecycle_configuration" "buckets" {
  for_each = { for b in var.buckets : b.name => b if b.lifecycle_rules != null }

  bucket = aws_s3_bucket.buckets[each.key].id

  dynamic "rule" {
    for_each = each.value.lifecycle_rules
    content {
      id     = rule.value.id
      status = rule.value.enabled ? "Enabled" : "Disabled"

      dynamic "transition" {
        for_each = rule.value.transition != null ? [rule.value.transition] : []
        content {
          days          = transition.value.days
          storage_class = transition.value.storage_class
        }
      }

      dynamic "expiration" {
        for_each = rule.value.expiration != null ? [rule.value.expiration] : []
        content {
          days = expiration.value.days
        }
      }
    }
  }
}

# CORS for uploads bucket
resource "aws_s3_bucket_cors_configuration" "uploads" {
  for_each = { for b in var.buckets : b.name => b if b.name == "uploads" }

  bucket = aws_s3_bucket.buckets[each.key].id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST"]
    allowed_origins = ["*"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

# Outputs
output "bucket_names" {
  value = { for k, v in aws_s3_bucket.buckets : k => v.bucket }
}

output "bucket_arns" {
  value = { for k, v in aws_s3_bucket.buckets : k => v.arn }
}
