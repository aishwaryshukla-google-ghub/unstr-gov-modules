output "function_id" {
  description = "An identifier for the resource with format projects/{{project}}/locations/{{location}}/functions/{{name}}"
  value       = google_cloudfunctions2_function.function.id
}

output "function_name" {
  description = "The name of the Cloud Run Function."
  value       = google_cloudfunctions2_function.function.name
}

output "function_uri" {
  description = "The HTTP URL endpoint trigger for the Cloud Run Function."
  value       = try(google_cloudfunctions2_function.function.service_config[0].uri, null)
}

output "cloud_run_service_name" {
  description = "The name of the underlying Cloud Run service deployed by this function."
  value       = try(google_cloudfunctions2_function.function.service_config[0].service, null)
}

output "service_account_email" {
  description = "The service account email configured for the function runtime."
  value       = try(google_cloudfunctions2_function.function.service_config[0].service_account_email, var.service_account_email)
}

output "state" {
  description = "The current state of the function."
  value       = google_cloudfunctions2_function.function.state
}
