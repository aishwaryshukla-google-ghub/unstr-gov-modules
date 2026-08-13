variable "project_id" {
  description = "The GCP project ID where BigQuery dataset, connection, and object tables will be created."
  type        = string
}

variable "region" {
  description = "The GCP region for the dataset, Cloud Resource Connection, and Object Tables (e.g., us-central1)."
  type        = string
}

variable "dataset_id" {
  description = "Target BigQuery dataset ID for the object tables."
  type        = string
}

variable "dataset_name" {
  description = "Friendly display name for the BigQuery dataset."
  type        = string
  default     = null
}

variable "create_dataset" {
  description = "Whether to create a new BigQuery dataset or use an existing dataset."
  type        = bool
  default     = true
}

variable "gcs_bucket_name" {
  description = "The GCS bucket name containing the unstructured files."
  type        = string
}

variable "connection_id" {
  description = "Cloud Resource Connection ID. If null, defaults to '<dataset_id>-vertex-conn'."
  type        = string
  default     = null
}

variable "table_mappings" {
  description = "Map of table suffix to GCS folder prefix (e.g. pdf = 'pdf/'). Object tables are named 'obj_tbl_<key>'."
  type        = map(string)
  default     = {}
}

variable "max_staleness" {
  description = "Staleness interval for BigQuery Object Table metadata cache (format: '0-0 0 1:0:0' for 1 hour, '0-0 0 4:0:0' for 4 hours)."
  type        = string
  default     = "0-0 0 1:0:0"
}

variable "metadata_cache_mode" {
  description = "Metadata caching mode for Object Tables ('AUTOMATIC' or 'MANUAL')."
  type        = string
  default     = "AUTOMATIC"
}

variable "labels" {
  description = "An optional map of enterprise labels to assign to all resources."
  type        = map(string)
  default     = {}
}
