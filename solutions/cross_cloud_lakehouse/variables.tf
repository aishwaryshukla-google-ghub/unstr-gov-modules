variable "project_id" {
  description = "The Google Cloud project ID where the Cross-Cloud Lakehouse solution is deployed."
  type        = string
}

variable "region" {
  description = "The target GCP region co-located closest to your AWS Databricks workspace (e.g., us-east4 for AWS us-east-1)."
  type        = string
  default     = "us-east4"
}

variable "zone" {
  description = "The target GCP zone for the zonal Hybrid NEG (e.g., us-east4-a)."
  type        = string
  default     = "us-east4-a"
}

# -----------------------------------------------------------------------------
# 1. PLATFORM TEAM PARAMETERS (Network & Interconnect Termination)
# -----------------------------------------------------------------------------
variable "vpc_network" {
  description = "The fully qualified network URI or path (projects/<p>/global/networks/<n>) where Partner CCI is bound."
  type        = string
}

variable "subnetwork" {
  description = "Optional fully qualified subnetwork path in the target region where the internal Load Balancer VIP is allocated. If null, workload_subnet_cidr must be supplied."
  type        = string
  default     = null
}

variable "workload_subnet_cidr" {
  description = "Optional CIDR range (e.g., 10.10.16.0/20) to provision a net-new PRIVATE subnetwork for the forwarding rule VIP if one does not exist."
  type        = string
  default     = null
}

variable "proxy_subnet_cidr" {
  description = "Optional CIDR range (e.g., 10.10.32.0/23) to provision a net-new REGIONAL_MANAGED_PROXY subnetwork for Envoy proxies if one does not exist."
  type        = string
  default     = null
}

variable "create_static_ip" {
  description = "Whether to provision an internal static IP address resource for the Load Balancer VIP instead of an ephemeral assignment."
  type        = bool
  default     = true
}

variable "forwarding_rule_ip" {
  description = "Optional static internal VIP address to assign to the reserved static address / S3 bridge Load Balancer. Defaults to automatic subnet allocation."
  type        = string
  default     = null
}

# -----------------------------------------------------------------------------
# 2. AWS INFRASTRUCTURE TEAM PARAMETERS (Remote PrivateLink Target ENIs)
# -----------------------------------------------------------------------------
variable "aws_s3_private_endpoints" {
  description = "Map of private IP addresses for AWS S3 Interface VPC Endpoint (com.amazonaws.<region>.s3) across Partner CCI."
  type = map(object({
    ip_address = string
    port       = optional(number, 443)
  }))
  default = {}
}

# -----------------------------------------------------------------------------
# 3. DATA & CATALOG FEDERATION PARAMETERS (Databricks Unity Catalog)
# -----------------------------------------------------------------------------
variable "federated_catalogs" {
  description = "Map of BigLake federated catalogs to establish against remote Databricks Unity Catalog instances."
  type = map(object({
    catalog_name                           = string
    unity_instance_name                    = string
    unity_catalog_name                     = string
    refresh_interval                       = optional(string, "300s")
    namespace_filters                      = optional(list(string), [])
    secret_name                            = optional(string, null)
    unity_service_principal_application_id = optional(string, null)
    service_principal_application_id       = optional(string, null)
  }))
  default = {}
}

variable "service_directory_config" {
  description = "Configuration naming for the Service Directory namespace, service, and endpoint private bridge."
  type = object({
    namespace_id = optional(string, "ccl-federation-ns")
    service_id   = optional(string, "aws-s3-private-service")
    endpoint_id  = optional(string, "s3-private-endpoint")
  })
  default = {}
}

variable "labels" {
  description = "Enterprise governance labels applied across all natively managed cloud resources."
  type        = map(string)
  default = {
    application         = "cross-cloud-lakehouse"
    environment         = "prod"
    managed_by          = "terraform"
    data_classification = "confidential"
  }
}
