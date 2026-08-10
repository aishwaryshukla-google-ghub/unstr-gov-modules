# -----------------------------------------------------------------------------
# VPC NETWORK PEERING MODULE
# Provisions VPC Network Peering between two Google Cloud VPC networks
# (either intra-project or cross-project).
# -----------------------------------------------------------------------------

resource "google_compute_network_peering" "local_to_peer" {
  name                                = var.peering_name
  network                             = var.local_network
  peer_network                        = var.peer_network
  export_custom_routes                = var.export_custom_routes
  import_custom_routes                = var.import_custom_routes
  export_subnet_routes_with_public_ip = var.export_subnet_routes_with_public_ip
  import_subnet_routes_with_public_ip = var.import_subnet_routes_with_public_ip
  stack_type                          = var.stack_type
}

resource "google_compute_network_peering" "peer_to_local" {
  count = var.create_reverse_peering ? 1 : 0

  name                                = var.reverse_peering_name != null ? var.reverse_peering_name : "${var.peering_name}-reverse"
  network                             = var.peer_network
  peer_network                        = var.local_network
  export_custom_routes                = var.peer_export_custom_routes != null ? var.peer_export_custom_routes : var.import_custom_routes
  import_custom_routes                = var.peer_import_custom_routes != null ? var.peer_import_custom_routes : var.export_custom_routes
  export_subnet_routes_with_public_ip = var.peer_export_subnet_routes_with_public_ip != null ? var.peer_export_subnet_routes_with_public_ip : var.import_subnet_routes_with_public_ip
  import_subnet_routes_with_public_ip = var.peer_import_subnet_routes_with_public_ip != null ? var.peer_import_subnet_routes_with_public_ip : var.export_subnet_routes_with_public_ip
  stack_type                          = var.stack_type
}
