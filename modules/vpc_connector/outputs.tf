output "connector_id" {
  description = "The ID of the VPC Access connector."
  value       = google_vpc_access_connector.connector.id
}

output "connector_name" {
  description = "The name of the VPC Access connector."
  value       = google_vpc_access_connector.connector.name
}

output "connector_self_link" {
  description = "The self_link of the VPC Access connector."
  value       = google_vpc_access_connector.connector.self_link
}

output "state" {
  description = "State of the VPC Access connector."
  value       = google_vpc_access_connector.connector.state
}
