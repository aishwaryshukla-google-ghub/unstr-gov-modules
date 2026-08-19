output "function_id" {
  description = "The ID of the Cloud Run Function."
  value       = module.cloud_run_function.function_id
}

output "function_name" {
  description = "The name of the Cloud Run Function."
  value       = module.cloud_run_function.function_name
}

output "function_uri" {
  description = "The HTTPS URI of the Cloud Run Function."
  value       = module.cloud_run_function.function_uri
}

output "service_account_email" {
  description = "The execution Service Account email."
  value       = local.resolved_sa_email
}

output "bigquery_remote_function_id" {
  description = "The fully qualified ID of the BigQuery Remote Function."
  value       = var.enable_bigquery_remote_function ? module.bigquery_remote_function[0].routine_id : null
}
