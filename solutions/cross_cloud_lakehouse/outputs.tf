output "load_balancer_vip" {
  description = "The internal Virtual IP (VIP) allocated to the Forwarding Rule representing remote AWS S3 endpoints across Partner CCI."
  value       = module.private_bridge.load_balancer_vip
}

output "service_directory_service_id" {
  description = "The fully qualified Resource Manager path of the created Service Directory service bridge."
  value       = module.private_bridge.service_directory_service_id
}

output "hybrid_neg_id" {
  description = "The resource ID of the Zonal Hybrid NEG binding AWS S3 PrivateLink ENI IP addresses."
  value       = module.private_bridge.hybrid_neg_id
}

output "catalog_names" {
  description = "Map of active BigLake federated catalog identifiers ready for BigQuery analytics."
  value       = module.federated_catalog.catalog_names
}
