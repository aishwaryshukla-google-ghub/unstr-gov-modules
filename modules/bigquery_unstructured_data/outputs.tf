output "dataset_id" {
  description = "The ID of the created BigQuery dataset"
  value       = google_bigquery_dataset.unstructured_ds.dataset_id
}

output "object_table_id" {
  description = "The ID of the BigQuery Object Table"
  value       = google_bigquery_table.documents_object_table.id
}

output "bigquery_connection_service_account" {
  description = "Service account created by the BigQuery Connection. Give this account Storage Object Viewer on the source bucket."
  value       = google_bigquery_connection.gcs_connection.cloud_resource[0].service_account_id
}