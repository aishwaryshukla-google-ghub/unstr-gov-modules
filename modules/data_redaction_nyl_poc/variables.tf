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

variable "ingress_settings" {
  description = "Ingress settings for Cloud Run functions"
  type        = string
  default     = "ALLOW_INTERNAL_AND_GCLB"
}

variable "model_name" {
  description = "Gemini model name"
  type        = string
  default     = "gemini-3.5-flash"
}

variable "ai_gateway_url" {
  description = "NYL Enterprise AI Gateway endpoint for Gemini"
  type        = string
  default     = "https://dev.aigw.newyorklife.com/eis-llm-gemini/gemini-3.5-flash:generateContent"
}

variable "vpc_connector" {
  description = "Optional Serverless VPC Access connector name/path to route traffic through NYL internal corporate network"
  type        = string
  default     = null
}

variable "vpc_connector_egress_settings" {
  description = "VPC connector egress settings. Allowed: ALL_TRAFFIC, PRIVATE_RANGES_ONLY."
  type        = string
  default     = "ALL_TRAFFIC"
}

variable "subnetwork" {
  description = "The subnetwork name or URI for Direct VPC Egress (e.g. projects/nyl-pr-infra-nw-dev-01/regions/us-east4/subnetworks/vpc-g-aid-edm-dev-platform-use4)"
  type        = string
  default     = null
}

variable "vpc_network" {
  description = "Optional VPC network name or URI for Direct VPC Egress (e.g. projects/nyl-pr-infra-nw-dev-01/global/networks/vpc-g-aid-edm-dev)"
  type        = string
  default     = null
}

variable "network_tags" {
  description = "Optional network tags for Direct VPC Egress"
  type        = list(string)
  default     = []
}
