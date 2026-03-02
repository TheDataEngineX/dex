# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------

output "s3_bucket_name" {
  description = "Name of the S3 test bucket."
  value       = aws_s3_bucket.test.id
}

output "s3_bucket_arn" {
  description = "ARN of the S3 test bucket."
  value       = aws_s3_bucket.test.arn
}

output "gcs_bucket_name" {
  description = "Name of the GCS test bucket."
  value       = google_storage_bucket.test.name
}

output "gcs_bucket_url" {
  description = "GCS bucket URL."
  value       = google_storage_bucket.test.url
}

# One-liner to export env vars for integration tests
output "env_vars" {
  description = "Shell export commands for integration test environment variables."
  value       = <<-EOT
    export DEX_TEST_S3_BUCKET="${aws_s3_bucket.test.id}"
    export DEX_TEST_S3_REGION="${var.aws_region}"
    export DEX_TEST_GCS_BUCKET="${google_storage_bucket.test.name}"
    export DEX_TEST_GCS_PROJECT="${var.gcp_project}"
  EOT
}
