output "email" {
  description = "The email address of the created Service Account."
  value       = google_service_account.this.email
}

output "id" {
  description = "The fully qualified resource ID of the created Service Account."
  value       = google_service_account.this.id
}

output "name" {
  description = "The fully qualified name of the created Service Account."
  value       = google_service_account.this.name
}

output "unique_id" {
  description = "The unique numeric ID of the created Service Account."
  value       = google_service_account.this.unique_id
}
