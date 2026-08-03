output "function_id" {
  description = "The ID of the deployed Cloud Run Function."
  value       = module.cloud_run_function.function_id
}

output "function_name" {
  description = "The name of the deployed Cloud Run Function."
  value       = module.cloud_run_function.function_name
}

output "function_uri" {
  description = "The HTTP trigger URI of the Cloud Run Function."
  value       = module.cloud_run_function.function_uri
}

output "cloud_run_service_name" {
  description = "The underlying Cloud Run Service name."
  value       = module.cloud_run_function.cloud_run_service_name
}

output "source_bucket_name" {
  description = "The GCS bucket holding the function source ZIP package."
  value       = google_storage_bucket.source_bucket.name
}

output "source_object_name" {
  description = "The GCS object key for the deployed function source ZIP."
  value       = google_storage_bucket_object.function_source_object.name
}

output "service_account_email" {
  description = "The runtime execution service account for the Cloud Run Function."
  value       = module.cloud_run_function.service_account_email
}
