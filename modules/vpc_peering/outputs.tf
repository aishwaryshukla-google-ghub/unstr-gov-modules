output "peering_id" {
  description = "The ID of the primary peering connection."
  value       = google_compute_network_peering.local_to_peer.id
}

output "peering_name" {
  description = "The name of the primary peering connection."
  value       = google_compute_network_peering.local_to_peer.name
}

output "peering_state" {
  description = "The state of the primary peering connection."
  value       = google_compute_network_peering.local_to_peer.state
}

output "reverse_peering_id" {
  description = "The ID of the reverse peering connection if created."
  value       = try(google_compute_network_peering.peer_to_local[0].id, null)
}

output "reverse_peering_state" {
  description = "The state of the reverse peering connection if created."
  value       = try(google_compute_network_peering.peer_to_local[0].state, null)
}
