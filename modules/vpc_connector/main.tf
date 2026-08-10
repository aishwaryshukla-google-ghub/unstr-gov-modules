# -----------------------------------------------------------------------------
# SERVERLESS VPC ACCESS CONNECTOR MODULE
# Provisions a Google Cloud Serverless VPC Access connector to route outbound
# traffic from Cloud Run / Cloud Functions into a VPC network.
# -----------------------------------------------------------------------------

resource "google_vpc_access_connector" "connector" {
  name          = var.connector_name
  project       = var.project_id
  region        = var.region
  ip_cidr_range = var.subnet_name == null ? var.ip_cidr_range : null
  network       = var.subnet_name == null ? var.network : null

  dynamic "subnet" {
    for_each = var.subnet_name != null ? [1] : []
    content {
      name       = var.subnet_name
      project_id = var.subnet_project_id != null ? var.subnet_project_id : var.project_id
    }
  }

  min_instances  = var.min_instances
  max_instances  = var.max_instances
  machine_type   = var.machine_type
  min_throughput = var.min_throughput
  max_throughput = var.max_throughput
}
