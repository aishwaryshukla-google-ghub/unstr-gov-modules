variable "project_id" {
  description = "The Google Cloud project ID."
  type        = string
  default     = "nyl-pr-dbx-data-dev-01"
}

variable "region" {
  description = "The target GCP region (e.g., us-east4 or us-east1)."
  type        = string
  default     = "us-east4"
}

variable "deploy_sa_email" {
  description = "The Harness IACM deployment service account email automatically passed by Harness pipeline."
  type        = string
  default     = null
}

# -----------------------------------------------------------------------------
# CLOUD RUN FUNCTION VPC & NETWORKING CONFIGURATION
# -----------------------------------------------------------------------------
variable "crf_vpc_network" {
  description = "The VPC network name or self_link to attach the Cloud Run VPC connector to."
  type        = string
  default     = "projects/nyl-transit-vpc-prod/global/networks/nyl-transit-vpc"
}

variable "create_crf_vpc_connector" {
  description = "Whether to provision a dedicated Serverless VPC Access connector for this Cloud Run Function."
  type        = bool
  default     = true
}

variable "crf_vpc_connector_name" {
  description = "The name of the Serverless VPC Access connector for Cloud Run (max 21 chars)."
  type        = string
  default     = "crf-vpc-conn"
}

variable "crf_vpc_connector_cidr" {
  description = "An unallocated /28 CIDR block reserved for the Cloud Run Serverless VPC Access connector."
  type        = string
  default     = "10.107.48.0/28"
}

variable "crf_vpc_connector_egress_settings" {
  description = "Cloud Run VPC egress settings. Allowed: ALL_TRAFFIC, PRIVATE_RANGES_ONLY."
  type        = string
  default     = "ALL_TRAFFIC"
}

variable "enable_crf_dns_peering" {
  description = "Whether to create a Cloud DNS Peering zone to resolve remote MuleSoft Flex Gateway domain."
  type        = bool
  default     = false
}

variable "mulesoft_vpc_network" {
  description = "The target VPC network URI where MuleSoft Flex Gateway and its private DNS zone reside."
  type        = string
  default     = null
}

variable "mulesoft_dns_domain" {
  description = "The DNS domain name of the MuleSoft Flex Gateway to forward (e.g. 'mulesoft.internal.')."
  type        = string
  default     = "mulesoft.internal."
}
