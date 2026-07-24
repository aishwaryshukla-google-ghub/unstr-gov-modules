terraform {
  required_version = ">= 1.3.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "7.39.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "7.39.0"
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

# =============================================================================
# 1. BIGQUERY OMNI AWS CONNECTION, DATASET & 7 EXTERNAL TABLES
# Direct hardcoded configuration for BigQuery Omni cross-cloud AWS S3 access.
# =============================================================================
module "bq_omni_connection" {
  source           = "./modules/bigquery/omni/aws"
  project_id       = var.project_id
  omni_location    = "aws-us-east-1"
  connection_id    = "nyl-ws2-bq-omni-conn"
  connection_name  = "NYL BigQuery Omni AWS Connection"
  aws_iam_role_arn = "arn:aws:iam::083822479215:role/BQ_OMNI_READ_WRITE_ROLE"
}

resource "google_bigquery_dataset" "omni_dataset" {
  project       = var.project_id
  dataset_id    = "bq_omni_test_dtst"
  friendly_name = "NYL BigQuery Omni AWS Dataset"
  description   = "BigQuery Omni Dataset located in AWS region aws-us-east-1"
  location      = "aws-us-east-1"
}

# -----------------------------------------------------------------------------
# 7 EXTERNAL TABLES DEFINED OVER AWS S3 DATA
# -----------------------------------------------------------------------------

# Table 1: Structured Parquet Data
resource "google_bigquery_table" "ext_tbl_omni_str_parquet" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.omni_dataset.dataset_id
  table_id   = "ext_tbl_omni_str_parquet"

  external_data_configuration {
    autodetect    = true
    source_format = "PARQUET"
    source_uris   = ["s3://nyl-cross-cloud-data-store-083822479215-us-east-1-an/structured_data/parquet/*.parquet"]
    connection_id = module.bq_omni_connection.connection_name
  }
}

# Table 2: Sales Transactions CSV Data
resource "google_bigquery_table" "ext_tbl_omni_sales_csv" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.omni_dataset.dataset_id
  table_id   = "ext_tbl_omni_sales_csv"

  external_data_configuration {
    autodetect    = true
    source_format = "CSV"
    source_uris   = ["s3://nyl-cross-cloud-data-store-083822479215-us-east-1-an/sales_data/*.csv"]
    connection_id = module.bq_omni_connection.connection_name

    csv_options {
      quote                 = "\""
      allow_quoted_newlines = true
      skip_leading_rows     = 1
      field_delimiter       = ","
    }
  }
}

# Table 3: Customer Profiles JSON Data
resource "google_bigquery_table" "ext_tbl_omni_customer_json" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.omni_dataset.dataset_id
  table_id   = "ext_tbl_omni_customer_json"

  external_data_configuration {
    autodetect    = true
    source_format = "NEWLINE_DELIMITED_JSON"
    source_uris   = ["s3://nyl-cross-cloud-data-store-083822479215-us-east-1-an/customer_data/*.json"]
    connection_id = module.bq_omni_connection.connection_name
  }
}

# Table 4: System Operational Logs AVRO Data
resource "google_bigquery_table" "ext_tbl_omni_logs_avro" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.omni_dataset.dataset_id
  table_id   = "ext_tbl_omni_logs_avro"

  external_data_configuration {
    autodetect    = true
    source_format = "AVRO"
    source_uris   = ["s3://nyl-cross-cloud-data-store-083822479215-us-east-1-an/logs_data/*.avro"]
    connection_id = module.bq_omni_connection.connection_name
  }
}

# Table 5: Performance Metrics ORC Data
resource "google_bigquery_table" "ext_tbl_omni_metrics_orc" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.omni_dataset.dataset_id
  table_id   = "ext_tbl_omni_metrics_orc"

  external_data_configuration {
    autodetect    = true
    source_format = "ORC"
    source_uris   = ["s3://nyl-cross-cloud-data-store-083822479215-us-east-1-an/metrics_data/*.orc"]
    connection_id = module.bq_omni_connection.connection_name
  }
}

# Table 6: Unstructured Document Metadata Parquet
resource "google_bigquery_table" "ext_tbl_omni_unstructured_metadata" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.omni_dataset.dataset_id
  table_id   = "ext_tbl_omni_unstructured_metadata"

  external_data_configuration {
    autodetect    = true
    source_format = "PARQUET"
    source_uris   = ["s3://nyl-cross-cloud-data-store-083822479215-us-east-1-an/unstructured_metadata/*.parquet"]
    connection_id = module.bq_omni_connection.connection_name
  }
}

# Table 7: Security Audit Logs CSV Data
resource "google_bigquery_table" "ext_tbl_omni_audit_csv" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.omni_dataset.dataset_id
  table_id   = "ext_tbl_omni_audit_csv"

  external_data_configuration {
    autodetect    = true
    source_format = "CSV"
    source_uris   = ["s3://nyl-cross-cloud-data-store-083822479215-us-east-1-an/audit_logs/*.csv"]
    connection_id = module.bq_omni_connection.connection_name

    csv_options {
      quote                 = "\""
      allow_quoted_newlines = true
      skip_leading_rows     = 1
      field_delimiter       = ","
    }
  }
}

# =============================================================================
# 2. CROSS-CLOUD PRIVATE BRIDGE (Layer 4 & Layer 7 Interconnect Backbone)
# Provisions Net-New Subnets, Reserved Static IP, Hybrid NEG, TCP Proxy LB, & Service Directory.
# =============================================================================
module "private_bridge" {
  source               = "./modules/ccl_private_bridge"
  project_id           = var.project_id
  region               = var.region
  zone                 = "${var.region}-a"
  vpc_network          = "projects/nyl-transit-vpc-prod/global/networks/nyl-transit-vpc"
  subnetwork           = null
  workload_subnet_cidr = "10.107.16.0/24" # Fwd S1 (Forwarding Rule VIP subnet)
  proxy_subnet_cidr    = "10.107.32.0/23" # Proxy S2 (REGIONAL_MANAGED_PROXY subnet)
  create_static_ip     = true
  forwarding_rule_ip   = null

  aws_s3_private_endpoints = {
    "aws-s3-eni-az1" = {
      ip_address = "10.200.15.42"
      port       = 443
    }
    "aws-s3-eni-az2" = {
      ip_address = "10.200.16.89"
      port       = 443
    }
  }

  service_directory_config = {
    namespace_id = "ccl-federation-ns"
    service_id   = "aws-s3-private-service"
    endpoint_id  = "s3-private-endpoint"
  }

  labels = {
    application_id      = "cross-cloud-lakehouse"
    business_unit       = "data-platform"
    environment         = "prod"
    owner_team          = "analytics-engineering"
    managed_by          = "terraform"
    data_classification = "confidential"
  }
}

# =============================================================================
# 3. BIGLAKE FEDERATED CATALOG (Databricks Unity Catalog Metadata Bridge)
# Wires the Service Directory private link directly into BigLake for secure S3 scans.
# =============================================================================
module "federated_catalog" {
  source                       = "./modules/ccl_federated_catalog"
  project_id                   = var.project_id
  region                       = var.region
  service_directory_service_id = module.private_bridge.service_directory_service_id

  federated_catalogs = {
    "nyl-unity-catalog" = {
      catalog_name                     = "nyl_prod_catalog"
      unity_instance_name              = "nyl-prod.cloud.databricks.com"
      unity_catalog_name               = "nyl_lakehouse"
      refresh_interval                 = "300s"
      service_principal_application_id = "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d"
    }
  }
}
