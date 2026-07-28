output "enabled_apis_ids" {
    description = "IDs of the enabled project services"
    value       = [for api in google_project_service.enabled_apis : api.id]
}

output "lake_id" {
  description = "The ID of the KC Lake"
  value       = google_dataplex_lake.primary_lake.id
}

output "zone_ids" {
  description = "Map of created Zone IDs"
  value       = { for k, v in google_dataplex_zone.medallion_zones : k => v.id }
}

output "glossary_id" {
  description = "The ID of the created KC Glossary"
  value       = google_dataplex_glossary.business_glossary.id
}

output "data_access_aspect_type_id" {
  description = "The ID of the Data Access Aspect Type"
  value       = google_dataplex_aspect_type.data_access.id
}