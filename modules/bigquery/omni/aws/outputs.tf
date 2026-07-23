output "connection_id" {
  description = "The full resource ID of the BigQuery Omni AWS connection."
  value       = google_bigquery_connection.aws_omni.id
}

output "connection_name" {
  description = "The resource name of the BigQuery Omni AWS connection (e.g. projects/p/locations/l/connections/c)."
  value       = google_bigquery_connection.aws_omni.name
}

output "aws_identity_id" {
  description = "The GCP Service Account Identity ID generated for BigQuery Omni. MUST be added to your AWS IAM Role Trust Policy."
  value       = try(google_bigquery_connection.aws_omni.aws[0].access_role[0].identity, null)
}
