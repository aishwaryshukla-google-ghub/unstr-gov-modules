variable "project_id" {
  description = "The Google Cloud project ID."
  type        = string
  default     = "nyl-pr-dbx-data-dev-01"
}

variable "region" {
  description = "The target GCP region (e.g., us-east4 or us-east1)."
  type        = string
  default     = "us-east4"
}

variable "deploy_sa_email" {
  description = "The Harness IACM deployment service account email automatically passed by Harness pipeline."
  type        = string
  default     = null
}

variable "raw_docs_bucket_name" {
    description = "The bucket where raw unstructured data is stored"
    type = string
}

variable "raw_docs_bucket_folder_path" {
    description = "The bucket folder path where raw unstructured data is stored"
    type = string
}

variable "bq_raw_docs_dataset_id" {
    description = "The BigQuery Dataset ID where the documents metadata will be stored"
    type = string
}

variable "bq_raw_docs_table_id" {
    description = "The BigQuery table ID where the documents metadata will be stored"
    type = string
}