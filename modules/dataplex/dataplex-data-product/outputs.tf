output "data_products" {
  value       = { for k, v in google_dataplex_data_product.data_products : k => v.id }
  description = "Map of created Dataplex data product IDs"
}
