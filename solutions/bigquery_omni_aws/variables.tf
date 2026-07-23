variable "project_id" {
  description = "The Google Cloud project ID where BigQuery Omni resources are deployed."
  type        = string
}

variable "region" {
  description = "The GCP provider default region (e.g. us-east4)."
  type        = string
  default     = "us-east4"
}

variable "omni_location" {
  description = "The BigQuery Omni location corresponding to your AWS S3 bucket region (e.g. aws-us-east-1, aws-us-west-2)."
  type        = string
  default     = "aws-us-east-1"
}

variable "connection_id" {
  description = "The unique ID for the BigQuery Omni AWS connection."
  type        = string
  default     = "nyl-bq-omni-aws-s3-conn"
}

variable "connection_name" {
  description = "Optional friendly display name for the BigQuery Omni AWS connection."
  type        = string
  default     = "NYL BigQuery Omni AWS S3 Connection"
}

variable "aws_iam_role_arn" {
  description = "The AWS IAM Role ARN (arn:aws:iam::<aws_account_id>:role/<role_name>) that BigQuery Omni will assume to access S3."
  type        = string
}

variable "dataset_id" {
  description = "The dataset ID for the BigQuery Omni dataset."
  type        = string
  default     = "nyl_bq_omni_s3_dataset"
}

variable "dataset_name" {
  description = "Optional friendly display name for the BigQuery Omni dataset."
  type        = string
  default     = "NYL BigQuery Omni AWS S3 Dataset"
}

variable "external_tables" {
  description = "Map of external tables to create over AWS S3 objects."
  type = map(object({
    source_uris   = list(string)
    source_format = optional(string, "PARQUET")
    autodetect    = optional(bool, true)
    csv_options = optional(object({
      quote                 = optional(string, "\"")
      allow_quoted_newlines = optional(bool, false)
      skip_leading_rows     = optional(number, 1)
      field_delimiter       = optional(string, ",")
    }), null)
  }))
  default = {}
}

variable "labels" {
  description = "Enterprise governance labels applied to all created resources."
  type        = map(string)
  default = {
    application         = "bigquery-omni-aws"
    environment         = "prod"
    managed_by          = "terraform"
    data_classification = "confidential"
  }
}
