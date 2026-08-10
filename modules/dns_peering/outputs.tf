output "zone_id" {
  description = "The ID of the DNS peering managed zone."
  value       = google_dns_managed_zone.peering_zone.id
}

output "zone_name" {
  description = "The name of the DNS managed zone."
  value       = google_dns_managed_zone.peering_zone.name
}

output "dns_name" {
  description = "The DNS domain name serviced by this zone."
  value       = google_dns_managed_zone.peering_zone.dns_name
}

output "name_servers" {
  description = "The name servers allocated for the managed zone."
  value       = google_dns_managed_zone.peering_zone.name_servers
}
