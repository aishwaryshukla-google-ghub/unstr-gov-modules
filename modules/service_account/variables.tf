variable "project_id" {
  description = "The Google Cloud project ID."
  type        = string
}

variable "account_id" {
  description = "The Service Account ID (short name, 6-30 chars, e.g., 'nyl-gov-crf-sa')."
  type        = string
}

variable "display_name" {
  description = "Display name for the Service Account."
  type        = string
  default     = null
}

variable "description" {
  description = "Description for the Service Account."
  type        = string
  default     = "Managed by Terraform"
}

variable "project_roles" {
  description = "List of project IAM roles to grant to the Service Account."
  type        = list(string)
  default     = []
}
