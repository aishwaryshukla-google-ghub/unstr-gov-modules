# =============================================================================
# NYL DATA PLATFORM - BQ ASSETS CHANGES FOR SHAREPOINT NYLFINANCETECHNOLOGY
# =============================================================================
# This file contains the exact Terraform blocks to merge into the client's
# 'bq_assets.tf' file in the 'nyl-ws2-gcp-data-platform' repository.
# =============================================================================

# -----------------------------------------------------------------------------
# STEP 1: AUTOMATED GCS FILE MIGRATION (177 Markdown Files)
# Runs during 'terraform apply' under Harness / Service Account permissions.
# -----------------------------------------------------------------------------
resource "terraform_data" "migrate_sharepoint_markdown_files" {
  triggers_replace = [
    "gs://gcp-native-ws2-unstructured-dev/enriched/sharepoint/nylfinancetechnology/",
    "gs://gcp-native-ws2-unstructured-dev-claims/builder/bronze/sharepoint/nylfinancetechnology/"
  ]

  provisioner "local-exec" {
    command = <<-EOT
      echo "[GCS_MIGRATION] Copying 177 markdown files from enriched to claims bronze..."
      gcloud storage cp -r \
        "gs://gcp-native-ws2-unstructured-dev/enriched/sharepoint/nylfinancetechnology/*" \
        "gs://gcp-native-ws2-unstructured-dev-claims/builder/bronze/sharepoint/nylfinancetechnology/"
    EOT
  }
}

# -----------------------------------------------------------------------------
# STEP 2: UPDATE CLAIMS OBJECT TABLES MODULE IN bq_assets.tf
# Add the 'sharepoint_nylfinancetechnology' mapping to module "claims_object_tables"
# -----------------------------------------------------------------------------
# In bq_assets.tf (approx Line 35):
#
# module "claims_object_tables" {
#   source          = "./modules/bigquery/tables/object"
#   project_id      = "nyl-pr-dbx-data-dev-01"
#   region          = "us-east4"
#   dataset_id      = "claims_bronze"
#   create_dataset  = false
#   gcs_bucket_name = "gcp-native-ws2-unstructured-dev-claims"
#
#   table_mappings = {
#     "payor_checks_sftp"               = "builder/bronze/sftp/iq-compensation/3rd Party Payor Checks.pdf"
#     "pay_to_date_sftp"                = "builder/bronze/sftp/iq-compensation/4AE4 and Risk Paid to Date Handling.docx"
#     "refund_sharepoint"               = "builder/bronze/sftp/iq-compensation/1x EFT Payment - eRefunds (Electronic Refunds) Examples."
#     "variance_sharepoint"             = "builder/bronze/sftp/iq-compensation/5EC6 Variance.pdf"
#     # NEW MAPPING:
#     "sharepoint_nylfinancetechnology" = "builder/bronze/sharepoint/nylfinancetechnology/*"
#   }
#
#   metadata_cache_mode = "AUTOMATIC"
#   max_staleness       = "0-0 0 0:30:0"
#
#   labels = {
#     domain = "claims"
#     env    = "env"
#   }
#
#   depends_on = [
#     terraform_data.migrate_sharepoint_markdown_files
#   ]
# }

# -----------------------------------------------------------------------------
# STEP 3: SILVER TABLE POPULATION BIGQUERY JOB
# Appended to the BigQuery Jobs section in bq_assets.tf
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
      from `${google_bigquery_dataset.dtst_claims_bronze.dataset_id}.${module.claims_object_tables.object_table_ids["sharepoint_nylfinancetechnology"]}` t_1
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
    module.claims_object_tables,
    module.bigquery_remote_function_gemini
  ]
}
