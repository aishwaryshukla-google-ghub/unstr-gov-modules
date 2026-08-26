# =============================================================================
# NYL DATA PLATFORM - COMPLETE WORKING FIX FOR BQ ASSETS
# =============================================================================

# -----------------------------------------------------------------------------
# FIX 1: RESTORE THE ORIGINAL UNDERWRITING SILVER TABLE ID (Line ~431)
# (Setting table_id back to tbl_risk_variance_sftp_v2 stops the destroy attempt)
# -----------------------------------------------------------------------------
# resource "google_bigquery_table" "risk_variance_sftp_table" {
#   project             = "nyl-pr-dbx-data-dev-01"
#   dataset_id          = google_bigquery_dataset.dtst_underwriting_silver.dataset_id
#   table_id            = "tbl_risk_variance_sftp_v2"
#   deletion_protection = false
#   ...
# }

# -----------------------------------------------------------------------------
# FIX 2: REUSE EXISTING CONNECTION FOR ENRICHED SHAREPOINT OBJECT TABLE
# (Reusing module.claims_object_tables eliminates GCP IAM propagation 400 error)
# -----------------------------------------------------------------------------

# 1. Grant the existing Connection SA read access to gcp-native-ws2-unstructured-dev
resource "google_storage_bucket_iam_member" "sharepoint_enriched_reader" {
  bucket = "gcp-native-ws2-unstructured-dev"
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${module.claims_object_tables.connection_service_account}"
}

# 2. Bronze Object Table pointing directly to 177 files in gcp-native-ws2-unstructured-dev
resource "google_bigquery_table" "obj_tbl_sharepoint_nylfinancetechnology" {
  project             = "nyl-pr-dbx-data-dev-01"
  dataset_id          = google_bigquery_dataset.dtst_claims_bronze.dataset_id
  table_id            = "obj_tbl_sharepoint_nylfinancetechnology"
  deletion_protection = false
  max_staleness       = "0-0 0 0:30:0"

  external_data_configuration {
    autodetect          = false
    object_metadata     = "SIMPLE"
    connection_id       = module.claims_object_tables.connection_id
    metadata_cache_mode = "AUTOMATIC"

    source_uris = [
      "gs://gcp-native-ws2-unstructured-dev/enriched/sharepoint/nylfinancetechnology/*"
    ]
  }

  depends_on = [google_storage_bucket_iam_member.sharepoint_enriched_reader]
}

# 3. Automated Cache Refresh Job (Runs under Harness deployment Service Account)
resource "google_bigquery_job" "refresh_sharepoint_metadata_cache" {
  job_id   = "job_refresh_sharepoint_cache_${formatdate("YYYYMMDDhhmmss", timestamp())}"
  project  = "nyl-pr-dbx-data-dev-01"
  location = "us-east4"

  query {
    query          = "CALL BQ.REFRESH_EXTERNAL_METADATA_CACHE('`nyl-pr-dbx-data-dev-01.claims_bronze.obj_tbl_sharepoint_nylfinancetechnology`');"
    use_legacy_sql = false
  }

  depends_on = [google_bigquery_table.obj_tbl_sharepoint_nylfinancetechnology]
}

# 4. Silver Population Job for SharePoint Nylfinancetechnology
resource "google_bigquery_job" "populate_sharepoint_nylfinancetechnology_silver_table" {
  job_id   = "job_populate_sharepoint_nylfinancetechnology_silver_table_${formatdate("YYYYMMDDhhmmss", timestamp())}"
  project  = "nyl-pr-dbx-data-dev-01"
  location = "us-east4"

  query {
    query          = <<-SQL
      select
        t_1.uri as gcs_uri
        , `${module.bigquery_remote_function_gemini.complete_path}`(
          'extract all details as is and ensure the structure is maintained. Please do not add even a single word'
          , t_1.uri
          , 'gemini'
        ) as extracted_content
        , current_timestamp() as process_ts
      from `${google_bigquery_dataset.dtst_claims_bronze.dataset_id}.${google_bigquery_table.obj_tbl_sharepoint_nylfinancetechnology.table_id}` t_1
      ;
    SQL
    use_legacy_sql = false

    destination_table {
      project_id = "nyl-pr-dbx-data-dev-01"
      dataset_id = google_bigquery_dataset.dtst_claims_silver.dataset_id
      table_id   = "tbl_sharepoint_nylfinancetechnology"
    }

    create_disposition = "CREATE_IF_NEEDED"
    write_disposition  = "WRITE_TRUNCATE"
  }

  depends_on = [
    google_bigquery_dataset.dtst_claims_bronze,
    google_bigquery_dataset.dtst_claims_silver,
    google_bigquery_table.obj_tbl_sharepoint_nylfinancetechnology,
    google_bigquery_job.refresh_sharepoint_metadata_cache,
    module.bigquery_remote_function_gemini
  ]
}



