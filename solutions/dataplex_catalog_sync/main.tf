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
# 1. GCS BUCKET FOR FUNCTION SOURCE ARCHIVES (OPTIONAL CREATION)
# -----------------------------------------------------------------------------
resource "google_storage_bucket" "source_bucket" {
  count                       = var.create_source_bucket ? 1 : 0
  name                        = var.source_bucket_name != null ? var.source_bucket_name : "${var.project_id}-dataplex-sync-src-${var.region}"
  project                     = var.project_id
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = true
  labels                      = var.labels
}

locals {
  effective_source_bucket = var.create_source_bucket ? google_storage_bucket.source_bucket[0].name : var.source_bucket_name
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
  bucket = local.effective_source_bucket
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

  resolved_subnetwork = var.subnetwork != null ? var.subnetwork : var.vpc_subnetwork
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
    bucket = local.effective_source_bucket
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
  build_service_account          = var.build_service_account != null ? var.build_service_account : var.deploy_sa_email
  vpc_connector                  = var.vpc_connector
  vpc_connector_egress_settings  = var.vpc_connector_egress_settings
  event_trigger                  = var.event_trigger
  invokers                       = local.resolved_invokers
  invoker_role                   = var.invoker_role
  labels                         = var.labels
  vpc_network                    = var.vpc_network
  subnetwork                     = local.resolved_subnetwork
  network_tags                   = var.network_tags
}


