# -----------------------------------------------------------------------------
# CLOUD DNS PEERING MODULE
# Provisions a Cloud DNS Peering Zone to resolve private domain names across
# VPC networks or projects (resolves NameResolutionError).
# -----------------------------------------------------------------------------

locals {
  formatted_dns_name = endswith(var.dns_name, ".") ? var.dns_name : "${var.dns_name}."
}

resource "google_dns_managed_zone" "peering_zone" {
  name        = var.zone_name
  dns_name    = local.formatted_dns_name
  description = var.description
  project     = var.project_id
  visibility  = "private"

  private_visibility_config {
    dynamic "networks" {
      for_each = var.local_network_urls
      content {
        network_url = networks.value
      }
    }
  }

  peering_config {
    target_network {
      network_url = var.target_network_url
    }
  }

  labels = var.labels
}
