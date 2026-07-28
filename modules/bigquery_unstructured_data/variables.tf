variable "project_id" {
    description = "The GCP Project ID"
    type        = string
}

variable "region" {
    description = "The GCP region for the project resources"
    type        = string
}

variable "dataset_id" {
  description = "The BigQuery dataset ID for unstructured data metadata"
  type        = string
}

variable "table_id" {
  description = "The BigQuery Object Table ID"
  type        = string
}

variable "bucket_name" {
  description = "The name of the existing GCS bucket where raw documents are stored"
  type        = string
}

variable "documents_folder_path" {
  description = "The folder path/prefix inside the bucket where documents are stored"
  type        = string
}