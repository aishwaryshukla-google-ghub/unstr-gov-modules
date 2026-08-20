variable "project_id" {
  description = "The Google Cloud project ID."
  type        = string
  default     = "databricks-playground-497321"
}

variable "region" {
  description = "The target GCP region."
  type        = string
  default     = "us-central1"
}

variable "deploy_sa_email" {
  description = "Deployment service account email."
  type        = string
  default     = null
}

variable "function_name" {
  description = "The name of the Cloud Run Function."
  type        = string
  default     = "nyl-dataplex-catalog-sync"
}

variable "description" {
  description = "Description for the Cloud Run Function."
  type        = string
  default     = "NYL Dataplex Universal Catalog Metadata Sync Cloud Run Function (2nd Gen)"
}

variable "runtime" {
  description = "The runtime environment for the function."
  type        = string
  default     = "python311"
}

variable "entry_point" {
  description = "The function entrypoint."
  type        = string
  default     = "bq_remote_function_handler"
}

variable "source_bucket_name" {
  description = "Optional custom name for GCS source bucket."
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

variable "available_cpu" {
  description = "CPUs allocated for function container."
  type        = string
  default     = "1"
}

variable "timeout_seconds" {
  description = "Function execution timeout in seconds."
  type        = number
  default     = 120
}

variable "environment_variables" {
  description = "Map of runtime environment variables."
  type        = map(string)
  default     = {}
}

variable "secret_environment_variables" {
  description = "List of secret environment variables to populate from Secret Manager."
  type = list(object({
    key        = string
    project_id = string
    secret     = string
    version    = string
  }))
  default = []
}

variable "ingress_settings" {
  description = "Ingress settings. Allowed: ALLOW_ALL, ALLOW_INTERNAL_ONLY, ALLOW_INTERNAL_AND_GCLOUD."
  type        = string
  default     = "ALLOW_ALL"
}

variable "all_traffic_on_latest_revision" {
  description = "Whether to route 100% traffic to latest revision."
  type        = bool
  default     = true
}

variable "create_service_account" {
  description = "Whether to provision a net-new dedicated execution Service Account."
  type        = bool
  default     = true
}

variable "service_account_id" {
  description = "The short account ID when provisioning a net-new Service Account."
  type        = string
  default     = "nyl-dataplex-sync-sa"
}

variable "service_account_email" {
  description = "Existing Service account email under which function executes."
  type        = string
  default     = null
}

variable "build_service_account" {
  description = "Build service account email used by Cloud Build."
  type        = string
  default     = null
}

variable "invokers" {
  description = "List of IAM principals allowed to invoke the function."
  type        = list(string)
  default     = []
}

variable "invoker_role" {
  description = "IAM role granted for invokers."
  type        = string
  default     = "roles/run.invoker"
}

variable "labels" {
  description = "Governance labels applied to created resources."
  type        = map(string)
  default = {
    application         = "dataplex-catalog-sync"
    environment         = "dev"
    managed_by          = "terraform"
    data_classification = "confidential"
  }
}
