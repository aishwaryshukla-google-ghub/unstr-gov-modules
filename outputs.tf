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

output "crf_vpc_connector_id" {
  description = "The Resource Manager ID of the Serverless VPC Access connector for Cloud Run."
  value       = try(module.crf_vpc_connector[0].connector_id, null)
}

output "crf_vpc_connector_name" {
  description = "The name of the Serverless VPC Access connector for Cloud Run."
  value       = try(module.crf_vpc_connector[0].connector_name, null)
}

output "crf_vpc_connector_state" {
  description = "The state of the Serverless VPC Access connector for Cloud Run."
  value       = try(module.crf_vpc_connector[0].state, null)
}

output "crf_dns_peering_zone_id" {
  description = "The ID of the Cloud DNS Peering Zone for MuleSoft if enabled."
  value       = try(module.crf_dns_peering[0].zone_id, null)
}

output "cloud_run_function_uri" {
  description = "The HTTP trigger URL endpoint for the Cloud Run Function."
  value       = module.cloud_run_function.function_uri
}

output "cloud_run_function_id" {
  description = "The Resource Manager ID of the Cloud Run Function."
  value       = module.cloud_run_function.function_id
}

output "bigquery_remote_function_routine_id" {
  description = "The routine ID of the BigQuery Remote Function."
  value       = module.bigquery_remote_function.routine_id
}

output "bigquery_remote_function_connection_id" {
  description = "The BigQuery Cloud Resource Connection ID used by the Remote Function."
  value       = module.bigquery_remote_function.connection_id
}

output "lakehouse_status_function_uri" {
  description = "The HTTP trigger URL endpoint for the Lakehouse Federated Catalog Status Function."
  value       = module.lakehouse_catalog_status.function_uri
}

output "lakehouse_status_function_id" {
  description = "The Resource Manager ID of the Lakehouse Federated Catalog Status Function."
  value       = module.lakehouse_catalog_status.function_id
}

output "lakehouse_status_service_sa" {
  description = "The dedicated runtime execution Service Account email for the Lakehouse Status Function."
  value       = module.lakehouse_status_sa.email
}
