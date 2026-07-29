variable "project_id" {
  description = "The Google Cloud project ID."
  type        = string
  default     = "nyl-pr-dbx-data-dev-01"
}

variable "region" {
  description = "The target GCP region."
  type        = string
  default     = "us-east4"
}

variable "deploy_sa_email" {
  description = "The Harness IACM deployment service account email automatically passed by Harness pipeline."
  type        = string
  default     = null
}

variable "function_name" {
  description = "The name of the Cloud Run Function."
  type        = string
  default     = "nyl-gov-cloud-run-func"
}

variable "description" {
  description = "Description for the Cloud Run Function."
  type        = string
  default     = "NYL Unstructured Governance Cloud Run Function (2nd Gen)"
}

variable "runtime" {
  description = "The runtime environment for the function."
  type        = string
  default     = "python311"
}

variable "entry_point" {
  description = "The function entrypoint."
  type        = string
  default     = "hello_world"
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
  default     = "256Mi"
}

variable "available_cpu" {
  description = "CPUs allocated for function container."
  type        = string
  default     = null
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

variable "service_account_email" {
  description = "Service account email under which function executes."
  type        = string
  default     = null
}

variable "build_service_account" {
  description = "Build service account email used by Cloud Build."
  type        = string
  default     = null
}

variable "vpc_connector" {
  description = "Serverless VPC Access connector name/path."
  type        = string
  default     = null
}

variable "vpc_connector_egress_settings" {
  description = "VPC connector egress settings. Allowed: ALL_TRAFFIC, PRIVATE_RANGES_ONLY."
  type        = string
  default     = null
}

variable "event_trigger" {
  description = "Eventarc trigger configuration object."
  type = object({
    trigger_region        = optional(string, null)
    event_type            = string
    pubsub_topic          = optional(string, null)
    service_account_email = optional(string, null)
    retry_policy          = optional(string, "RETRY_POLICY_DO_NOT_RETRY")
    event_filters = optional(list(object({
      attribute = string
      value     = string
      operator  = optional(string, null)
    })), [])
  })
  default = null
}

variable "invokers" {
  description = "List of IAM principals allowed to invoke the function."
  type        = list(string)
  default     = []
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
    application         = "unstructured-governance"
    environment         = "dev"
    managed_by          = "terraform"
    data_classification = "confidential"
  }
}
