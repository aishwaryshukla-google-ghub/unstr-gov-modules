# BigQuery Object Tables Module

This module provisions BigQuery Cloud Resource Connections, assigns GCS IAM read permissions, creates BigQuery datasets, and dynamically registers BigQuery **Object Tables** mapped to GCS folder paths with metadata caching enabled.

## Features

- **Automated IAM Assignment**: Automatically grants `roles/storage.objectViewer` to the Cloud Resource Connection service account on the target GCS bucket.
- **Dynamic Folder Mapping**: Takes a map of table keys to GCS prefixes (`pdf = "pdf/"`, `audio = "audio/"`) and creates corresponding `obj_tbl_<key>` tables.
- **Performance Optimized**: Enables `AUTOMATIC` metadata caching with configurable `max_staleness` to avoid high GCS list API overhead.

## Usage

```hcl
module "bq_object_tables" {
  source          = "../../modules/bq_object_tables"
  project_id      = "my-gcp-project"
  region          = "us-central1"
  dataset_id      = "unstructured_analytics"
  gcs_bucket_name = "my-unstructured-bucket"

  table_mappings = {
    "pdf"   = "pdf/"
    "docx"  = "docx/"
    "audio" = "audio/"
  }

  labels = {
    environment = "dev"
    managed_by  = "terraform"
  }
}
```
