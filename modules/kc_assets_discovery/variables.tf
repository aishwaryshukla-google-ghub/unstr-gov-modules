variable "project_id" {
  description = "The GCP Project ID where resources live"
  type        = string
}

variable "region" {
  description = "GCP Region for Dataplex resources"
  type        = string
}

variable "lake_name" {
  description = "The Dataplex Lake name/ID where the asset belongs"
  type        = string
}

variable "zone_name" {
  description = "The Dataplex Zone name/ID (e.g., bronze, silver, gold)"
  type        = string
}

variable "asset_id" {
  description = "Unique ID for the Dataplex Asset"
  type        = string
}

variable "bucket_name" {
  description = "The name of the GCS bucket storing the unstructured data files"
  type        = string
}

variable "bucket_folder_prefix" {
  description = "Optional subfolder/prefix path inside the bucket (leave empty for whole bucket)"
  type        = string
}