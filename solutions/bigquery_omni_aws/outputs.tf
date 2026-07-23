output "bigquery_omni_connection_id" {
  description = "Full resource identifier of the created BigQuery Omni AWS Connection."
  value       = module.bq_omni_connection.connection_id
}

output "bigquery_omni_connection_name" {
  description = "Name of the BigQuery Omni AWS Connection."
  value       = module.bq_omni_connection.connection_name
}

output "aws_identity_id" {
  description = "CRITICAL: The GCP BigQuery Omni Identity ID. Update your AWS IAM Role Trust Policy with this Identity ID!"
  value       = module.bq_omni_connection.aws_identity_id
}

output "dataset_id" {
  description = "The BigQuery Omni Dataset ID created."
  value       = google_bigquery_dataset.omni_dataset.dataset_id
}

output "table_ids" {
  description = "Map of created BigQuery Omni external tables."
  value       = { for k, v in google_bigquery_table.omni_external_table : k => v.table_id }
}
