variable "project_id" {
  description = "The GCP Project ID where the Cloud Run Function will be deployed."
  type        = string
}

variable "region" {
  description = "The GCP region to deploy the function (e.g. us-east4)."
  type        = string
  default     = "us-east4"
}

variable "function_name" {
  description = "The name of the Cloud Run function."
  type        = string
}

variable "description" {
  description = "A user-defined description of the function."
  type        = string
  default     = "Managed Cloud Run Function (2nd Gen)"
}

variable "runtime" {
  description = "The runtime in which to run the function (e.g., python311, nodejs20, go121)."
  type        = string
  default     = "python311"
}

variable "entry_point" {
  description = "The name of the function (as defined in source code) that will be executed."
  type        = string
  default     = "main"
}

variable "storage_source" {
  description = "GCS Storage source location object containing bucket name, object key, and optional generation."
  type = object({
    bucket     = string
    object     = string
    generation = optional(string, null)
  })
  default = null
}

variable "repo_source" {
  description = "Cloud Source Repository location object."
  type = object({
    project_id   = optional(string, null)
    repo_name    = string
    branch_name  = optional(string, null)
    tag_name     = optional(string, null)
    commit_sha   = optional(string, null)
    dir          = optional(string, null)
    invert_regex = optional(bool, null)
  })
  default = null
}

variable "docker_repository" {
  description = "User managed repository created in Artifact Registry to which the function image should be pushed."
  type        = string
  default     = null
}

variable "build_service_account" {
  description = "Service account to be used for building the container image."
  type        = string
  default     = null
}

variable "build_environment_variables" {
  description = "User-provided build environment variables for the function."
  type        = map(string)
  default     = {}
}

variable "max_instance_count" {
  description = "The limit on the maximum number of function instances that may co-exist at a given time."
  type        = number
  default     = 10
}

variable "min_instance_count" {
  description = "The limit on the minimum number of function instances that may co-exist at a given time."
  type        = number
  default     = 0
}

variable "available_memory" {
  description = "The amount of memory available for a function instance (e.g. 256Mi, 512Mi, 1Gi, 2Gi)."
  type        = string
  default     = "256Mi"
}

variable "available_cpu" {
  description = "The number of CPUs allocated for a function instance (e.g. '1', '0.5', '2')."
  type        = string
  default     = null
}

variable "timeout_seconds" {
  description = "The function execution timeout in seconds. Defaults to 60s."
  type        = number
  default     = 60
}

variable "environment_variables" {
  description = "Environment variables to be passed to the function container."
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
  description = "Ingress settings for the function. Allowed values: ALLOW_ALL, ALLOW_INTERNAL_ONLY, ALLOW_INTERNAL_AND_GCLOUD."
  type        = string
  default     = "ALLOW_ALL"
}

variable "all_traffic_on_latest_revision" {
  description = "Whether 100% of traffic is routed to the latest revision."
  type        = bool
  default     = true
}

variable "service_account_email" {
  description = "The email of the service account under which the function will run."
  type        = string
  default     = null
}

variable "vpc_connector" {
  description = "The Serverless VPC Access connector path or ID."
  type        = string
  default     = null
}

variable "vpc_connector_egress_settings" {
  description = "Egress settings for the VPC connector. Allowed values: ALL_TRAFFIC, PRIVATE_RANGES_ONLY."
  type        = string
  default     = null
}

variable "event_trigger" {
  description = "Eventarc trigger configuration for event-driven functions (e.g., GCS, Pub/Sub)."
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
  description = "List of IAM members to grant invoker role (e.g. ['allUsers'], ['user:foo@example.com'], ['serviceAccount:bar@proj.iam.gserviceaccount.com'])."
  type        = list(string)
  default     = []
}

variable "invoker_role" {
  description = "IAM role for invocation. Defaults to roles/cloudfunctions.invoker."
  type        = string
  default     = "roles/cloudfunctions.invoker"
}

variable "labels" {
  description = "Key-value map of labels to assign to the Cloud Run function."
  type        = map(string)
  default = {
    managed_by = "terraform"
  }
}
