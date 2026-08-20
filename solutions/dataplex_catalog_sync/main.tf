terraform {
  required_version = ">= 1.3.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 7.39.0, < 8.0.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = ">= 7.39.0, < 8.0.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = ">= 2.4.0"
    }
  }
}

# -----------------------------------------------------------------------------
# 1. GCS BUCKET FOR FUNCTION SOURCE ARCHIVES
# -----------------------------------------------------------------------------
resource "google_storage_bucket" "source_bucket" {
  name                        = var.source_bucket_name != null ? var.source_bucket_name : "${var.project_id}-dataplex-sync-src-${var.region}"
  project                     = var.project_id
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true
  labels                      = var.labels
}

# -----------------------------------------------------------------------------
# 2. LOCAL SOURCE ZIP ARCHIVE PACKAGING
# -----------------------------------------------------------------------------
data "archive_file" "function_zip" {
  type        = "zip"
  source_dir  = "${path.module}/src"
  output_path = "${path.module}/dataplex_sync_source.zip"
}

# -----------------------------------------------------------------------------
# 3. UPLOAD SOURCE ZIP ARCHIVE TO GCS
# -----------------------------------------------------------------------------
resource "google_storage_bucket_object" "function_source_object" {
  name   = "source-${data.archive_file.function_zip.output_md5}.zip"
  bucket = google_storage_bucket.source_bucket.name
  source = data.archive_file.function_zip.output_path
}

# -----------------------------------------------------------------------------
# 3.1 DEDICATED EXECUTION SERVICE ACCOUNT (WITH DATAPLEX ROLES)
# -----------------------------------------------------------------------------
module "dedicated_service_account" {
  count        = var.create_service_account ? 1 : 0
  source       = "../../modules/service_account"
  project_id   = var.project_id
  account_id   = var.service_account_id
  display_name = "NYL Dataplex Catalog Sync SA (${var.function_name})"
  description  = "Execution Service Account for Dataplex Catalog Sync Cloud Run Function ${var.function_name}"
  project_roles = [
    "roles/logging.logWriter",
    "roles/dataplex.admin",
    "roles/dataplex.catalogEditor",
    "roles/storage.objectViewer",
    "roles/bigquery.jobUser",
    "roles/bigquery.dataViewer",
  ]
}

locals {
  resolved_sa_email = var.create_service_account ? module.dedicated_service_account[0].email : (
    var.service_account_email != null ? var.service_account_email : var.deploy_sa_email
  )

  resolved_invokers = length(var.invokers) > 0 ? var.invokers : (
    local.resolved_sa_email != null ? ["serviceAccount:${local.resolved_sa_email}"] : []
  )
}

# -----------------------------------------------------------------------------
# 4. CLOUD RUN FUNCTION MODULE INVOCATION (2ND GEN)
# -----------------------------------------------------------------------------
module "cloud_run_function" {
  source        = "../../modules/cloud_run_function"
  project_id    = var.project_id
  region        = var.region
  function_name = var.function_name
  description   = var.description
  runtime       = var.runtime
  entry_point   = var.entry_point

  storage_source = {
    bucket = google_storage_bucket.source_bucket.name
    object = google_storage_bucket_object.function_source_object.name
  }

  max_instance_count             = var.max_instance_count
  min_instance_count             = var.min_instance_count
  available_memory               = var.available_memory
  available_cpu                  = var.available_cpu
  timeout_seconds                = var.timeout_seconds
  environment_variables          = merge({
    GCP_PROJECT = var.project_id
    LOCATION    = var.region
  }, var.environment_variables)

  secret_environment_variables   = var.secret_environment_variables
  ingress_settings               = var.ingress_settings
  all_traffic_on_latest_revision = var.all_traffic_on_latest_revision
  service_account_email          = local.resolved_sa_email
  build_service_account          = var.build_service_account != null ? var.build_service_account : local.resolved_sa_email
  invokers                       = local.resolved_invokers
  invoker_role                   = var.invoker_role
  labels                         = var.labels
}

# -----------------------------------------------------------------------------
# 5. BIGQUERY REMOTE FUNCTION (SCALAR UDF WITH CLOUD RESOURCE CONNECTION)
# -----------------------------------------------------------------------------
module "bigquery_remote_function" {
  count                  = var.enable_bigquery_remote_function ? 1 : 0
  source                 = "../bigquery/functions/remote"
  project_id             = var.project_id
  region                 = var.region
  dataset_id             = var.bq_dataset_id
  routine_id             = var.bq_routine_id
  connection_id          = var.bq_connection_id
  existing_connection_id = var.existing_bq_connection_id
  endpoint               = module.cloud_run_function.function_uri
  cloud_run_service_name = module.cloud_run_function.function_name
  max_batching_rows      = var.bq_max_batching_rows

  arguments = [
    { name = "gcs_metadata_uri", data_type = jsonencode({ typeKind = "STRING" }) },
    { name = "gcs_document_uri", data_type = jsonencode({ typeKind = "STRING" }) },
    { name = "project_id", data_type = jsonencode({ typeKind = "STRING" }) },
    { name = "location", data_type = jsonencode({ typeKind = "STRING" }) },
    { name = "entry_group_id", data_type = jsonencode({ typeKind = "STRING" }) }
  ]

  return_type = jsonencode({ typeKind = "JSON" })

  depends_on = [
    module.cloud_run_function
  ]
}
