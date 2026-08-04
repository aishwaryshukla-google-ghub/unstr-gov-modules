# Unstructured Data Lake Object Tables Solution

This solution deploys a complete BigQuery Object Table data lake environment for unstructured files stored in Cloud Storage.

## Overview

The solution provisions:
1. **BigQuery Dataset**: Scoped dataset for unstructured data analytics.
2. **Cloud Resource Connection**: Dedicated connection for BQML Remote Models & Object Table queries.
3. **IAM Permissions**: Automatically grants `roles/storage.objectViewer` to the connection service account on the target GCS bucket.
4. **BigQuery Object Tables**: Mapped dynamically per folder (`pdf/`, `docx/`, `audio/`) with automatic metadata caching (`max_staleness = INTERVAL 1 HOUR`).

## Quickstart

1. Copy `terraform.tfvars.sample` to `terraform.tfvars`:
   ```bash
   cp terraform.tfvars.sample terraform.tfvars
   ```
2. Update `project_id`, `gcs_bucket_name`, and `table_mappings` in `terraform.tfvars`.
3. Initialize and deploy:
   ```bash
   terraform init
   terraform apply
   ```
