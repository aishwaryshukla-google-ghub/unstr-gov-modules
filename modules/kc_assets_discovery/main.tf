# Register the GCS Bucket/Folder as a Data Asset inside a Lake & Zone
resource "google_dataplex_asset" "gcs_unstructured_data_asset" {
  name     = var.asset_id
  location = var.region
  project  = var.project_id
  lake     = var.lake_name
  dataplex_zone = var.zone_name

  display_name = "Unstructured Documents Storage"
  description  = "GCS bucket storage asset configured for automated Data cataloging and discovery"

  # Resource specification pointing to the GCS bucket or folder path
  resource_spec {
    name = "projects/${var.project_id}/buckets/${var.bucket_name}"
    type = "STORAGE_BUCKET"
  }

  # Discovery specification for automatic schema & metadata cataloging
  discovery_spec {
    enabled = true

    # File format options for unstructured data discovery
    # csv_options {
    #  header_rows = 1
    #}

    # Hourly execution schedule for auto-cataloging new files
    schedule = "0 * * * *"
  }
}