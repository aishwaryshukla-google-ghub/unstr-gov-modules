variable "project_id" {
  type        = string
  description = "GCP Project ID where Dataplex data products are created"
  default     = "nyl-pr-dbx-data-dev-01"
}

variable "region" {
  type        = string
  description = "Primary GCP Region"
  default     = "us-east4"
}

variable "location" {
  type        = string
  description = "Dataplex Data Product location (e.g. 'us', 'us-east4')"
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
  description = "Map of Dataplex Data Products to manage"
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
