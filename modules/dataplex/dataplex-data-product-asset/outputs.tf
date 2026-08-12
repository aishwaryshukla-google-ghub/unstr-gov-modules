output "data_product_assets" {
  value       = { for k, v in google_dataplex_data_product_data_asset.assets : k => v.id }
  description = "Map of created Dataplex Data Product Asset IDs"
}
