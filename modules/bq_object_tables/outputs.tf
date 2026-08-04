output "connection_id" {
  description = "The fully qualified resource connection ID for Vertex AI / BigQuery ML."
  value       = google_bigquery_connection.this.name
}

output "connection_service_account" {
  description = "The service account email attached to the Cloud Resource Connection."
  value       = google_bigquery_connection.this.cloud_resource[0].service_account_id
}

output "dataset_id" {
  description = "The target dataset ID."
  value       = local.target_dataset_id
}

output "object_table_ids" {
  description = "Map of created object table IDs."
  value       = { for k, v in google_bigquery_table.object_tables : k => v.table_id }
}
