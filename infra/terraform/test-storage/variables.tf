# ---------------------------------------------------------------------------
# Variables
# ---------------------------------------------------------------------------

variable "aws_region" {
  description = "AWS region for the S3 test bucket."
  type        = string
  default     = "us-east-1"
}

variable "gcp_project" {
  description = "GCP project ID for the GCS test bucket."
  type        = string
}

variable "gcp_region" {
  description = "GCP region for the GCS test bucket."
  type        = string
  default     = "us-central1"
}

variable "object_expiration_days" {
  description = "Days after which test objects are auto-deleted."
  type        = number
  default     = 1
}

variable "force_destroy" {
  description = "Allow terraform destroy to delete non-empty buckets."
  type        = bool
  default     = true
}
