variable "project_id" {
  description = "Target GCP Project ID."
  type        = string
}

variable "region" {
  description = "Primary GCP Region."
  type        = string
  default     = "us-central1"
}

variable "dataset_id" {
  description = "Target BigQuery Dataset ID."
  type        = string
  default     = "bq_unstructured_analytics"
}

variable "dataset_name" {
  description = "Friendly display name for Dataset."
  type        = string
  default     = "Unstructured Data Analytics Lake"
}

variable "create_dataset" {
  description = "Whether to create dataset or use existing."
  type        = bool
  default     = true
}

variable "gcs_bucket_name" {
  description = "Name of GCS Bucket containing unstructured files."
  type        = string
}

variable "connection_id" {
  description = "Optional custom connection ID."
  type        = string
  default     = null
}

variable "table_mappings" {
  description = "Map of table suffix key to folder prefix in GCS."
  type        = map(string)
  default = {
    "pdf"   = "pdf/"
    "docx"  = "docx/"
    "audio" = "audio/"
  }
}

variable "max_staleness" {
  description = "Metadata cache max staleness."
  type        = string
  default     = "INTERVAL 1 HOUR"
}

variable "labels" {
  description = "Enterprise governance labels."
  type        = map(string)
  default     = {}
}
