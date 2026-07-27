variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "region" {
  description = "The GCP region"
  type        = string
  default     = "us-east1"
}

variable "app_source_dir" {
  description = "Path to the application source code directory"
  type        = string
  default     = "./app"
}

variable "service_account_email" {
  description = "Service Account email to run Cloud Run"
  type        = string
}

variable "dataset_id" {
  description = "The BigQuery dataset ID to deploy the remote function into"
  type        = string
  default     = "test_dtst"
}

variable "labels" {
  description = "Labels to apply to resources"
  type        = map(string)
  default = {
    application_id      = "app-14378"
    environment         = "dev"
    business_unit       = "edm"
    data_classification = "internal"
    owner_team          = "edm"
    managed_by          = "harness-iacm"
  }
}
