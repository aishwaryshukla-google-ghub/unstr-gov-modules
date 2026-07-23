variable "project_id" {
  description = "The GCP project ID where the BigQuery Omni AWS connection will be created."
  type        = string
}

variable "omni_location" {
  description = "The BigQuery Omni multi-cloud location corresponding to your AWS region (e.g. aws-us-east-1, aws-us-west-2)."
  type        = string
  default     = "aws-us-east-1"
}

variable "connection_id" {
  description = "The unique ID of the BigQuery Omni AWS connection resource."
  type        = string
  default     = "nyl_bq_omni_aws_conn"
}

variable "connection_name" {
  description = "Optional friendly display name for the BigQuery Omni AWS connection."
  type        = string
  default     = null
}

variable "aws_iam_role_arn" {
  description = "The AWS IAM Role ARN (arn:aws:iam::<aws_account>:role/<role_name>) configured to grant BigQuery access to AWS S3 buckets."
  type        = string
}
