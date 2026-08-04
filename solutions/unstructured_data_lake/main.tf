terraform {
  required_version = ">= 1.3.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# -----------------------------------------------------------------------------
# UNSTRUCTURED DATA LAKE OBJECT TABLES SOLUTION
# Instantiates the bq_object_tables module to map GCS folders to BigQuery
# -----------------------------------------------------------------------------
module "object_tables" {
  source          = "../../modules/bq_object_tables"
  project_id      = var.project_id
  region          = var.region
  dataset_id      = var.dataset_id
  dataset_name    = var.dataset_name
  create_dataset  = var.create_dataset
  gcs_bucket_name = var.gcs_bucket_name
  connection_id   = var.connection_id
  table_mappings  = var.table_mappings
  max_staleness   = var.max_staleness
  labels          = var.labels
}
