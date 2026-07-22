terraform {
  required_version = ">= 1.3.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 7.39.0, < 8.0.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# -----------------------------------------------------------------------------
# 1. CROSS-CLOUD PRIVATE BRIDGE (Layer 4 & Layer 7 Interconnect Backbone)
# Provisions Net-New Subnets (if needed), Reserved Static IP, Hybrid NEG, TCP Proxy LB, & Service Directory.
# -----------------------------------------------------------------------------
module "private_bridge" {
  source                   = "../../modules/ccl_private_bridge"
  project_id               = var.project_id
  region                   = var.region
  zone                     = var.zone
  vpc_network              = var.vpc_network
  subnetwork               = var.subnetwork
  workload_subnet_cidr     = var.workload_subnet_cidr
  proxy_subnet_cidr        = var.proxy_subnet_cidr
  create_static_ip         = var.create_static_ip
  forwarding_rule_ip       = var.forwarding_rule_ip
  aws_s3_private_endpoints = var.aws_s3_private_endpoints
  service_directory_config = var.service_directory_config
  labels                   = var.labels
}

# -----------------------------------------------------------------------------
# 2. BIGLAKE FEDERATED CATALOG (Databricks Unity Catalog Metadata Bridge)
# Wires the Service Directory private link directly into BigLake for secure S3 scans.
# -----------------------------------------------------------------------------
module "federated_catalog" {
  source                       = "../../modules/ccl_federated_catalog"
  project_id                   = var.project_id
  region                       = var.region
  service_directory_service_id = module.private_bridge.service_directory_service_id
  federated_catalogs           = var.federated_catalogs
}
