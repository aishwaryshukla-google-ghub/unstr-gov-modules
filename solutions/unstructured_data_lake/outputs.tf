output "connection_id" {
  description = "The BigQuery Cloud Resource Connection ID."
  value       = module.object_tables.connection_id
}

output "connection_service_account" {
  description = "The Service Account allocated to the Cloud Resource Connection."
  value       = module.object_tables.connection_service_account
}

output "dataset_id" {
  description = "The BigQuery Dataset ID."
  value       = module.object_tables.dataset_id
}

output "object_table_ids" {
  description = "Created BigQuery Object Tables."
  value       = module.object_tables.object_table_ids
}
