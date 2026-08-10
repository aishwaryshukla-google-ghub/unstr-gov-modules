# -----------------------------------------------------------------------------
# VPC NETWORK MODULE
# Provisions a Google Cloud VPC Network with custom subnetworks,
# secondary IP ranges, Private Google Access, and Proxy-Only subnets.
# -----------------------------------------------------------------------------

resource "google_compute_network" "vpc" {
  name                            = var.network_name
  project                         = var.project_id
  auto_create_subnetworks         = var.auto_create_subnetworks
  routing_mode                    = var.routing_mode
  description                     = var.description
  delete_default_routes_on_create = var.delete_default_routes_on_create
  mtu                             = var.mtu
}

resource "google_compute_subnetwork" "subnets" {
  for_each = { for s in var.subnets : s.subnet_name => s }

  name                     = each.value.subnet_name
  project                  = var.project_id
  region                   = each.value.subnet_region
  ip_cidr_range            = each.value.subnet_ip
  network                  = google_compute_network.vpc.id
  private_ip_google_access = lookup(each.value, "subnet_private_access", true)
  purpose                  = lookup(each.value, "purpose", null)
  role                     = lookup(each.value, "role", null)
  description              = lookup(each.value, "description", null)

  dynamic "secondary_ip_range" {
    for_each = lookup(each.value, "secondary_ip_ranges", [])
    content {
      range_name    = secondary_ip_range.value.range_name
      ip_cidr_range = secondary_ip_range.value.ip_cidr_range
    }
  }

  dynamic "log_config" {
    for_each = lookup(each.value, "subnet_flow_logs", false) ? [1] : []
    content {
      aggregation_interval = lookup(each.value, "subnet_flow_logs_interval", "INTERVAL_5_SEC")
      flow_sampling        = lookup(each.value, "subnet_flow_logs_sampling", "0.5")
      metadata             = lookup(each.value, "subnet_flow_logs_metadata", "INCLUDE_ALL_METADATA")
    }
  }
}
