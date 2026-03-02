# DEX Test Storage — Terraform

Provisions ephemeral S3 and GCS buckets for running the storage integration tests (`tests/integration/test_storage_real.py`).

## Prerequisites

| Tool | Purpose |
|------|---------|
| [Terraform](https://developer.hashicorp.com/terraform/install) ≥ 1.5 | Infrastructure provisioning |
| AWS CLI / credentials | `aws configure` or `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` |
| GCP `gcloud` CLI / ADC | `gcloud auth application-default login` or `GOOGLE_APPLICATION_CREDENTIALS` |

## Quick Start

```bash
cd infra/terraform/test-storage

# 1. Configure — set your GCP project (required)
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars: gcp_project = "your-project-id"

# 2. Provision buckets
terraform init
terraform apply

# 3. Export env vars for tests
eval "$(terraform output -raw env_vars)"

# 4. Run integration tests
cd ../../..
uv run pytest tests/integration/test_storage_real.py -v

# 5. Tear down when done
cd infra/terraform/test-storage
terraform destroy
```

## What Gets Created

| Resource | Details |
|----------|---------|
| S3 bucket | `dex-test-storage-<random>` in us-east-1, public access blocked, AES-256 encryption, 1-day lifecycle |
| GCS bucket | `dex-test-storage-<random>` in US-CENTRAL1, uniform access, 1-day lifecycle |

Both buckets have `force_destroy = true` so `terraform destroy` works even with objects inside.

## Cost

Near zero — buckets are empty most of the time and objects auto-expire within 24 hours.

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `aws_region` | `us-east-1` | AWS region |
| `gcp_project` | *(required)* | GCP project ID |
| `gcp_region` | `us-central1` | GCP region |
| `object_expiration_days` | `1` | Auto-delete objects after N days |
| `force_destroy` | `true` | Allow destroy with objects inside |
