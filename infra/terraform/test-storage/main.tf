# ---------------------------------------------------------------------------
# DEX — Test Storage Infrastructure
#
# Provisions S3 and GCS buckets for integration testing.
# Objects auto-expire after 1 day to keep costs near zero.
#
# Usage:
#   cd infra/terraform/test-storage
#   terraform init
#   terraform apply                          # creates buckets
#   eval $(terraform output -json | jq -r '.env_vars.value')  # export env vars
#   uv run pytest tests/integration/test_storage_real.py -v   # run tests
#   terraform destroy                        # cleanup
# ---------------------------------------------------------------------------

terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "dataenginex"
      Environment = "test"
      ManagedBy   = "terraform"
    }
  }
}

provider "google" {
  project = var.gcp_project
  region  = var.gcp_region
}

# ---------------------------------------------------------------------------
# Random suffix to avoid global name collisions
# ---------------------------------------------------------------------------

resource "random_id" "suffix" {
  byte_length = 4
}

locals {
  suffix      = random_id.suffix.hex
  bucket_base = "dex-test-storage"
}
