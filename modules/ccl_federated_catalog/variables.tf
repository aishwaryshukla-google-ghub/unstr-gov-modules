variable "project_id" {
  description = "The Google Cloud project ID where the BigLake federated catalog will be deployed."
  type        = string
}

variable "region" {
  description = "The Google Cloud region for the BigLake catalog (must correspond closely to AWS DBX region, e.g., us-east4)."
  type        = string
}

variable "service_directory_service_id" {
  description = "Optional Service Directory service resource name (projects/<p>/locations/<l>/namespaces/<n>/services/<s>) pointing to the Internal Load Balancer VIP for private CCI routing."
  type        = string
  default     = null
}

variable "federated_catalogs" {
  description = "Map of BigLake federated catalogs to create, connecting GCP to remote Databricks Unity Catalog instances."
  type = map(object({
    catalog_name                           = string
    unity_instance_name                    = string
    unity_catalog_name                     = string
    refresh_interval                       = optional(string, "300s")
    namespace_filters                      = optional(list(string), [])
    
    # Optional authentication references (existing secret ID or OIDC application ID)
    secret_name                            = optional(string, null)
    unity_service_principal_application_id = optional(string, null)
    service_principal_application_id       = optional(string, null)
  }))
  default = {}
}
