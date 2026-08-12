variable "project_id" {
  type        = string
  description = "GCP Project ID"
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
  description = "Map of data products to manage"
}
