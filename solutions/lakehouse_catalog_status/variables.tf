variable "project_id" {
  description = "The Google Cloud project ID."
  type        = string
}

variable "region" {
  description = "The target GCP region."
  type        = string
  default     = "us-east4"
}

variable "function_name" {
  description = "The name of the Lakehouse catalog status Cloud Run Function."
  type        = string
  default     = "nyl-lakehouse-catalog-status"
}

variable "description" {
  description = "Description for the Cloud Run Function."
  type        = string
  default     = "NYL Lakehouse Federated Catalog Status & Diagnostic Service (2nd Gen)"
}

variable "runtime" {
  description = "The runtime environment for the function."
  type        = string
  default     = "python311"
}

variable "entry_point" {
  description = "The function entrypoint."
  type        = string
  default     = "get_lakehouse_catalog_status"
}

variable "source_bucket_name" {
  description = "Optional custom name for the GCS bucket storing function source code. If null, auto-generated."
  type        = string
  default     = null
}

variable "max_instance_count" {
  description = "Maximum number of instances."
  type        = number
  default     = 10
}

variable "min_instance_count" {
  description = "Minimum number of instances."
  type        = number
  default     = 0
}

variable "available_memory" {
  description = "Available memory allocated for function container."
  type        = string
  default     = "512Mi"
}

variable "timeout_seconds" {
  description = "Function execution timeout in seconds."
  type        = number
  default     = 60
}

variable "environment_variables" {
  description = "Map of runtime environment variables."
  type        = map(string)
  default     = {}
}

variable "service_account_email" {
  description = "Runtime execution Service Account email under which function executes."
  type        = string
  default     = null
}

variable "invokers" {
  description = "List of IAM principals allowed to invoke the function."
  type        = list(string)
  default     = ["allUsers"]
}

variable "invoker_role" {
  description = "IAM role granted for invokers."
  type        = string
  default     = "roles/cloudfunctions.invoker"
}

variable "labels" {
  description = "Governance labels applied to created resources."
  type        = map(string)
  default = {
    application         = "lakehouse-catalog-status"
    environment         = "dev"
    managed_by          = "terraform"
    data_classification = "confidential"
  }
}
