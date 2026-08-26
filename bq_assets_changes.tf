# =============================================================================
# NYL DATA PLATFORM - BQ ASSETS CHANGES FOR SHAREPOINT NYLFINANCETECHNOLOGY
# =============================================================================
# Direct Pointing Approach: Points BigQuery Object Table directly to
# 'gs://gcp-native-ws2-unstructured-dev/enriched/sharepoint/nylfinancetechnology/*'
# with ZERO file migration required.
# =============================================================================

# -----------------------------------------------------------------------------
# STEP 1: ADD OBJECT TABLE MODULE FOR ENRICHED SHAREPOINT DATA
# Paste this block into bq_assets.tf in the Object Tables section:
# -----------------------------------------------------------------------------
module "claims_sharepoint_enriched_object_tables" {
  source          = "./modules/bigquery/tables/object"
  project_id      = "nyl-pr-dbx-data-dev-01"
  region          = "us-east4"
  dataset_id      = "claims_bronze"
  create_dataset  = false
  gcs_bucket_name = "gcp-native-ws2-unstructured-dev"

  table_mappings = {
    "sharepoint_nylfinancetechnology" = "enriched/sharepoint/nylfinancetechnology/*"
  }

  metadata_cache_mode = "AUTOMATIC"
  max_staleness       = "0-0 0 0:30:0"

  labels = {
    domain = "claims"
    env    = "env"
  }
}

# -----------------------------------------------------------------------------
# STEP 2: SILVER TABLE POPULATION BIGQUERY JOB
# Paste this block into bq_assets.tf in the BigQuery Jobs section:
# -----------------------------------------------------------------------------
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
      from `${google_bigquery_dataset.dtst_claims_bronze.dataset_id}.${module.claims_sharepoint_enriched_object_tables.object_table_ids["sharepoint_nylfinancetechnology"]}` t_1
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
    module.claims_sharepoint_enriched_object_tables,
    module.bigquery_remote_function_gemini
  ]
}

