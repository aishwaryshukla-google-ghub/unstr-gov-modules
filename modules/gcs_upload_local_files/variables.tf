variable "gcs_bucket_to_upload" {
    description = "The GCS bucket to upload files to"
    type        = string
}

variable "files_folder" {
    description = "The local folder where files are located"
    type        = string  
}

variable "environment" {
    description = "The deploy environment (builder, integration, execution)"
    type        = string
}

variable "files_source" {
    description = "The files origin system (e.g. sharepoint, sftp)"
    type        = string
}

variable "files_owner_team" {
    description = "The team that owns the files (e.g. field-experience)"
    type        = string  
}