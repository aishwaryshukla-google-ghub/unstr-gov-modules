output "service_directory_service_id" {
  description = "The fully qualified Resource Manager path of the Service Directory service. Feed this directly into module 'ccl_federated_catalog'."
  value       = module.service_directory.service_ids[var.service_directory_config.service_id]
}

output "load_balancer_vip" {
  description = "The internal Virtual IP (VIP) allocated to the Forwarding Rule representing remote AWS S3 endpoints."
  value       = module.forwarding_rule.ip_address
}

output "hybrid_neg_id" {
  description = "The ID of the Zonal Hybrid Network Endpoint Group holding AWS S3 PrivateLink ENI IP addresses."
  value       = module.hybrid_neg.id
}

output "service_directory_namespace_id" {
  description = "The ID of the created Service Directory namespace."
  value       = module.service_directory.namespace_id
}
