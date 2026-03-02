# ---------------------------------------------------------------------------
# AWS S3 — Test Bucket
# ---------------------------------------------------------------------------

resource "aws_s3_bucket" "test" {
  bucket        = "${local.bucket_base}-${local.suffix}"
  force_destroy = var.force_destroy

  tags = {
    Name = "${local.bucket_base}-${local.suffix}"
  }
}

# Block all public access
resource "aws_s3_bucket_public_access_block" "test" {
  bucket = aws_s3_bucket.test.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# KMS key for S3 bucket encryption
resource "aws_kms_key" "s3_test" {
  description             = "CMK for DEX test S3 bucket"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = {
    Name = "dex-test-s3-key"
  }
}

resource "aws_kms_alias" "s3_test" {
  name          = "alias/dex-test-s3"
  target_key_id = aws_kms_key.s3_test.key_id
}

# Server-side encryption (SSE-KMS with customer managed key)
resource "aws_s3_bucket_server_side_encryption_configuration" "test" {
  bucket = aws_s3_bucket.test.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.s3_test.arn
    }
    bucket_key_enabled = true
  }
}

# Auto-expire objects after N days
resource "aws_s3_bucket_lifecycle_configuration" "test" {
  bucket = aws_s3_bucket.test.id

  rule {
    id     = "expire-test-objects"
    status = "Enabled"

    filter {
      prefix = "dex-test/"
    }

    expiration {
      days = var.object_expiration_days
    }
  }
}

# Versioning disabled — test bucket, no need to keep history
resource "aws_s3_bucket_versioning" "test" {
  bucket = aws_s3_bucket.test.id

  versioning_configuration {
    status = "Suspended"
  }
}
