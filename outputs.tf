output "bq_omni_connection_id" {
  description = "The full resource ID of the BigQuery Omni AWS Connection."
  value       = module.bq_omni_connection.connection_id
}

output "bq_omni_aws_identity_id" {
  description = "The GCP Service Account Identity ID generated for BigQuery Omni."
  value       = module.bq_omni_connection.aws_identity_id
}

output "omni_dataset_id" {
  description = "The BigQuery Omni Dataset ID created."
  value       = google_bigquery_dataset.omni_dataset.dataset_id
}

output "load_balancer_vip" {
  description = "The reserved internal static IP address for the S3 Interconnect Load Balancer VIP."
  value       = module.private_bridge.load_balancer_vip
}

output "service_directory_service_id" {
  description = "The Service Directory Service resource ID."
  value       = module.private_bridge.service_directory_service_id
}
