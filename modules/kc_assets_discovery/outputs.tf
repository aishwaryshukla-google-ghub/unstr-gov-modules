output "asset_id" {
  description = "The ID of the registered Data Asset"
  value       = google_dataplex_asset.gcs_unstructured_data_asset.id
}

output "asset_state" {
  description = "The state of the Data Asset"
  value       = google_dataplex_asset.gcs_unstructured_data_asset.state
}