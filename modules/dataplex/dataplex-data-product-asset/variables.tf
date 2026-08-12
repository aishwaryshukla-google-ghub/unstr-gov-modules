variable "project_id" {
  type        = string
  description = "GCP Project ID"
}

variable "location" {
  type        = string
  description = "Location of the Data Product assets"
  default     = "us"
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
  description = "Map of Data Product ID to map of asset definitions"
}
