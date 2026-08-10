output "network_id" {
  description = "The ID of the VPC network."
  value       = google_compute_network.vpc.id
}

output "network_name" {
  description = "The name of the VPC network."
  value       = google_compute_network.vpc.name
}

output "network_self_link" {
  description = "The URI of the VPC network."
  value       = google_compute_network.vpc.self_link
}

output "subnets" {
  description = "Map of created subnets."
  value       = google_compute_subnetwork.subnets
}

output "subnets_ids" {
  description = "Map of subnet names to their IDs."
  value       = { for k, v in google_compute_subnetwork.subnets : k => v.id }
}

output "subnets_self_links" {
  description = "Map of subnet names to their self_links."
  value       = { for k, v in google_compute_subnetwork.subnets : k => v.self_link }
}
