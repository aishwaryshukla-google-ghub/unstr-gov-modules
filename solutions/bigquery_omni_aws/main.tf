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
# 1. BIGQUERY OMNI AWS CONNECTION MODULE
# Manages the GCP-to-AWS cross-cloud identity connection.
# -----------------------------------------------------------------------------
module "bq_omni_connection" {
  source           = "../../modules/bigquery/omni/aws"
  project_id       = var.project_id
  omni_location    = var.omni_location
  connection_id    = var.connection_id
  connection_name  = var.connection_name
  aws_iam_role_arn = var.aws_iam_role_arn
}

# -----------------------------------------------------------------------------
# 2. BIGQUERY OMNI DATASET
# Dataset created in the Omni multi-cloud location (e.g., aws-us-east-1).
# -----------------------------------------------------------------------------
resource "google_bigquery_dataset" "omni_dataset" {
  project       = var.project_id
  dataset_id    = var.dataset_id
  friendly_name = var.dataset_name != null ? var.dataset_name : var.dataset_id
  description   = "BigQuery Omni Dataset located in AWS region ${var.omni_location}"
  location      = var.omni_location
  labels        = var.labels
}

# -----------------------------------------------------------------------------
# 3. BIGQUERY OMNI EXTERNAL TABLES OVER AWS S3
# Creates external tables pointing to S3 bucket paths using the connection.
# -----------------------------------------------------------------------------
resource "google_bigquery_table" "omni_external_table" {
  for_each = var.external_tables

  project    = var.project_id
  dataset_id = google_bigquery_dataset.omni_dataset.dataset_id
  table_id   = each.key

  external_data_configuration {
    autodetect    = try(each.value.autodetect, true)
    source_format = try(each.value.source_format, "PARQUET")
    source_uris   = each.value.source_uris
    connection_id = module.bq_omni_connection.connection_name

    dynamic "csv_options" {
      for_each = try(each.value.source_format, "PARQUET") == "CSV" ? [1] : []
      content {
        quote                 = try(each.value.csv_options.quote, "\"")
        allow_quoted_newlines = try(each.value.csv_options.allow_quoted_newlines, false)
        skip_leading_rows     = try(each.value.skip_leading_rows, 1)
        field_delimiter       = try(each.value.csv_options.field_delimiter, ",")
      }
    }
  }

  labels = var.labels
}
