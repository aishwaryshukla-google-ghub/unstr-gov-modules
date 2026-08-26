# =============================================================================
# NYL DATA PLATFORM - BQ ASSETS CHANGES FOR SHAREPOINT NYLFINANCETECHNOLOGY
# =============================================================================
# These are the ONLY changes needed in the client's repository ('nyl-ws2-gcp-data-platform')
# =============================================================================

# -----------------------------------------------------------------------------
# STEP 1: AUTOMATED STORAGE TRANSFER SERVICE (STS) (Bucket-to-Bucket File Copy)
# Paste this in 'bq_assets.tf' (or 'main.tf'):
# -----------------------------------------------------------------------------
data "google_storage_transfer_project_service_account" "default" {
  project = "nyl-pr-dbx-data-dev-01"
}

resource "google_storage_bucket_iam_member" "sts_source_reader" {
  bucket = "gcp-native-ws2-unstructured-dev"
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${data.google_storage_transfer_project_service_account.default.email}"
}

resource "google_storage_bucket_iam_member" "sts_sink_writer" {
  bucket = "gcp-native-ws2-unstructured-dev-claims"
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${data.google_storage_transfer_project_service_account.default.email}"
}

resource "google_storage_transfer_job" "copy_sharepoint_files_to_claims" {
  description = "Automated copy of 177 SharePoint markdown files to claims bronze bucket"
  project     = "nyl-pr-dbx-data-dev-01"

  transfer_spec {
    gcs_data_source {
      bucket_name = "gcp-native-ws2-unstructured-dev"
      path        = "enriched/sharepoint/nylfinancetechnology/"
    }

    gcs_data_sink {
      bucket_name = "gcp-native-ws2-unstructured-dev-claims"
      path        = "builder/bronze/sharepoint/nylfinancetechnology/"
    }

    transfer_options {
      overwrite_objects_already_existing_in_sink = true
    }
  }

  schedule {
    schedule_start_date {
      year  = 2026
      month = 8
      day   = 26
    }
  }

  depends_on = [
    google_storage_bucket_iam_member.sts_source_reader,
    google_storage_bucket_iam_member.sts_sink_writer
  ]
}

# -----------------------------------------------------------------------------
# STEP 2: UPDATE 'module "claims_object_tables"' IN 'bq_assets.tf'
# Add the new mapping line and depends_on:
# -----------------------------------------------------------------------------
# In bq_assets.tf (Line ~35):
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
#     # NEW MAPPING (177 Files in claims bucket):
#     "sharepoint_nylfinancetechnology" = "builder/bronze/sharepoint/nylfinancetechnology/*"
#   }
#
#   metadata_cache_mode = "AUTOMATIC"
#   max_staleness       = "0-0 0 0:30:0"
#   labels = {
#     domain = "claims"
#     env    = "env"
#   }
#
#   depends_on = [
#     google_storage_transfer_job.copy_sharepoint_files_to_claims
#   ]
# }

# -----------------------------------------------------------------------------
# STEP 3: SILVER POPULATION JOB IN 'bq_assets.tf'
# Paste this in the BigQuery Jobs section of 'bq_assets.tf':
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




