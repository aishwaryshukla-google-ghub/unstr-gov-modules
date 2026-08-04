# -----------------------------------------------------------------------------
# 1. OPTIONAL BIGQUERY DATASET CREATION
# -----------------------------------------------------------------------------
resource "google_bigquery_dataset" "this" {
  count         = var.create_dataset ? 1 : 0
  project       = var.project_id
  dataset_id    = var.dataset_id
  friendly_name = var.dataset_name != null ? var.dataset_name : var.dataset_id
  location      = var.region
  labels        = var.labels
}

locals {
  target_dataset_id = var.create_dataset ? google_bigquery_dataset.this[0].dataset_id : var.dataset_id
  effective_conn_id = var.connection_id != null ? var.connection_id : "${var.dataset_id}-vertex-conn"
}

# -----------------------------------------------------------------------------
# 2. CLOUD RESOURCE CONNECTION
# Connection used by BigQuery ML / Remote Models and Object Tables
# -----------------------------------------------------------------------------
resource "google_bigquery_connection" "this" {
  project       = var.project_id
  connection_id = local.effective_conn_id
  location      = var.region
  cloud_resource {}
}

# -----------------------------------------------------------------------------
# 3. IAM PERMISSIONS
# Grant BigQuery Connection Service Account Storage Object Viewer on the target GCS bucket
# -----------------------------------------------------------------------------
resource "google_storage_bucket_iam_member" "gcs_reader" {
  bucket = var.gcs_bucket_name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_bigquery_connection.this.cloud_resource[0].service_account_id}"
}

# -----------------------------------------------------------------------------
# 4. BIGQUERY EXTERNAL OBJECT TABLES
# Provisions object tables per folder mapping with metadata caching enabled
# -----------------------------------------------------------------------------
resource "google_bigquery_table" "object_tables" {
  for_each            = var.table_mappings
  project             = var.project_id
  dataset_id          = local.target_dataset_id
  table_id            = "obj_tbl_${each.key}"
  deletion_protection = false

  external_data_configuration {
    autodetect          = false
    source_format       = "GOOGLE_CLOUD_STORAGE"
    object_metadata     = "SIMPLE"
    connection_id       = google_bigquery_connection.this.name
    metadata_cache_mode = var.metadata_cache_mode
    max_staleness       = var.max_staleness

    source_uris = [
      "gs://${var.gcs_bucket_name}/${each.value}*"
    ]
  }

  depends_on = [google_storage_bucket_iam_member.gcs_reader]
}
