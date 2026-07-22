output "catalog_names" {
  description = "Map of created BigLake federated catalog identifiers."
  value = {
    for k, v in var.federated_catalogs : k => v.catalog_name
  }
}
