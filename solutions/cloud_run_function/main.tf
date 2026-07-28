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
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# -----------------------------------------------------------------------------
# 1. GCS BUCKET FOR FUNCTION SOURCE ARCHIVES
# -----------------------------------------------------------------------------
resource "google_storage_bucket" "source_bucket" {
  name                        = var.source_bucket_name != null ? var.source_bucket_name : "${var.project_id}-crf-source-${var.region}"
  project                     = var.project_id
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true
  labels                      = var.labels
}

# -----------------------------------------------------------------------------
# 2. SOURCE ZIP ARCHIVE PACKAGE
# -----------------------------------------------------------------------------
# Packaged function source archive (e.g. function_source.zip)
# Upload to GCS using native filemd5 hash for automatic deployment triggers

# -----------------------------------------------------------------------------
# 3. UPLOAD SOURCE ZIP ARCHIVE TO GCS
# -----------------------------------------------------------------------------
resource "google_storage_bucket_object" "function_source_object" {
  name   = "source-${filemd5("${path.module}/function_source.zip")}.zip"
  bucket = google_storage_bucket.source_bucket.name
  source = "${path.module}/function_source.zip"
}

# -----------------------------------------------------------------------------
# 4. CLOUD RUN FUNCTION MODULE INVOCATION
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
  environment_variables          = var.environment_variables
  secret_environment_variables   = var.secret_environment_variables
  ingress_settings               = var.ingress_settings
  all_traffic_on_latest_revision = var.all_traffic_on_latest_revision
  service_account_email          = var.service_account_email
  vpc_connector                  = var.vpc_connector
  vpc_connector_egress_settings  = var.vpc_connector_egress_settings
  event_trigger                  = var.event_trigger
  invokers                       = var.invokers
  invoker_role                   = var.invoker_role
  labels                         = var.labels
}
