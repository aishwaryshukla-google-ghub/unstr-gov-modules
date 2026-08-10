variable "project_id" {
  description = "The GCP project ID hosting the BigQuery dataset and connection."
  type        = string
}

variable "region" {
  description = "The GCP region for the BigQuery connection and dataset (e.g. us-east4)."
  type        = string
  default     = "us-east4"
}

variable "dataset_id" {
  description = "The target BigQuery dataset ID where the routine is registered."
  type        = string
}

variable "routine_id" {
  description = "The ID / function name of the BigQuery SQL routine to create."
  type        = string
  default     = "retrieve_llm_result"
}

variable "description" {
  description = "Description for the BigQuery Remote Function."
  type        = string
  default     = "BigQuery Remote Function invoking Cloud Run for LLM processing"
}

variable "endpoint" {
  description = "The HTTPS trigger URI of the target Cloud Run Function or Service."
  type        = string
}

variable "cloud_run_service_name" {
  description = "The target Cloud Run Service/Function name to automatically grant roles/run.invoker to the connection SA."
  type        = string
  default     = null
}

variable "connection_id" {
  description = "The ID of the BigQuery Cloud Resource Connection to create if not referencing an existing one."
  type        = string
  default     = "nyl-crf-connection"
}

variable "existing_connection_id" {
  description = "Optional existing BigQuery Cloud Resource Connection ID (e.g. projects/.../locations/.../connections/...). If provided, skips creating a new connection."
  type        = string
  default     = null
}

variable "arguments" {
  description = "List of arguments for the routine."
  type = list(object({
    name      = string
    data_type = string
  }))
  default = [
    {
      name      = "prompt"
      data_type = "{\"typeKind\" : \"STRING\"}"
    },
    {
      name      = "gcs_uri"
      data_type = "{\"typeKind\" : \"STRING\"}"
    }
  ]
}

variable "return_type" {
  description = "Return data type of the routine as JSON schema string."
  type        = string
  default     = "{\"typeKind\" : \"JSON\"}"
}

variable "max_batching_rows" {
  description = "The maximum number of rows BigQuery sends per batch to the Cloud Run endpoint."
  type        = number
  default     = 10
}
