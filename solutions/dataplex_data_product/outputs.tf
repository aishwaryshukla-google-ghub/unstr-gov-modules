output "data_products" {
  description = "Map of created Dataplex data product IDs"
  value       = module.dataplex_data_products.data_products
}

output "data_product_assets" {
  description = "Map of created Dataplex data product asset IDs"
  value       = module.dataplex_data_product_assets.data_product_assets
}
