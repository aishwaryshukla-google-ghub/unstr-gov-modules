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

variable "dataplex_location" {
  description = "The Dataplex Data Product location (e.g. 'us', 'us-east4')."
  type        = string
  default     = "us"
}

variable "data_products" {
  type = map(object({
    location     = string
    display_name = optional(string)
    description  = optional(string)
    labels       = optional(map(string))
    owner_emails = optional(list(string))
    access_groups = optional(map(object({
      display_name = optional(string)
      description  = optional(string)
      google_group = optional(string)
    })))
  }))
  default     = {}
  description = "Map of Dataplex Data Products to manage in the environment"
}

variable "data_product_assets" {
  type = map(map(object({
    data_asset_id = optional(string, null)
    resource      = string
    labels        = optional(map(string), null)
    access_group_configs = optional(list(object({
      access_group = string
      iam_roles    = optional(list(string), ["roles/bigquery.dataViewer"])
    })), [])
  })))
  default     = {}
  description = "Map of Data Product IDs to their mapped data assets and access group permissions"
}

variable "customer_id" {
  description = "The Google Cloud Identity / Workspace Directory Customer ID (e.g. C03iuyfcm)."
  type        = string
  default     = "C03iuyfcm"
}

variable "organization_domain" {
  description = "The organization identity domain for Google Groups."
  type        = string
  default     = "aishwaryshukla.altostrat.com"
}

variable "crf_subnetwork" {
  description = "Subnetwork for Cloud Run Function Direct VPC Egress."
  type        = string
  default     = null
}

variable "crf_vpc_network" {
  description = "VPC network for Cloud Run Function Direct VPC Egress."
  type        = string
  default     = null
}

variable "crf_network_tags" {
  description = "Network tags for Cloud Run Function."
  type        = list(string)
  default     = []
}


