# ---------------------------------------------------------------------------
# GCP GCS — Test Bucket
# ---------------------------------------------------------------------------

resource "google_storage_bucket" "test" {
  name          = "${local.bucket_base}-${local.suffix}"
  location      = upper(var.gcp_region)
  project       = var.gcp_project
  force_destroy = var.force_destroy

  # Uniform bucket-level access (no per-object ACLs)
  uniform_bucket_level_access = true

  # Storage class — Standard is fine for short-lived test data
  storage_class = "STANDARD"

  # Auto-delete test objects after N days
  lifecycle_rule {
    condition {
      age = var.object_expiration_days
    }
    action {
      type = "Delete"
    }
  }

  labels = {
    project     = "dataenginex"
    environment = "test"
    managed-by  = "terraform"
  }
}
