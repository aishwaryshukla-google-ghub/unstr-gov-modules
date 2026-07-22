locals {
  # Automatically extract network basename to generate flawless Service Directory API Resource Manager syntax:
  # projects/<project_id>/locations/global/networks/<network_name>
  network_name          = basename(var.vpc_network)
  normalized_sd_network = "projects/${var.project_id}/locations/global/networks/${local.network_name}"
}

# -----------------------------------------------------------------------------
# 0. OPTIONAL NET-NEW SUBNETWORKS & STATIC IP RESERVATION
# Supports environments where proxy subnets or workload subnets do not exist yet.
# -----------------------------------------------------------------------------
resource "google_compute_subnetwork" "proxy_subnet" {
  count         = var.proxy_subnet_cidr != null ? 1 : 0
  name          = "${var.bridge_name_prefix}-proxy-subnet"
  project       = var.project_id
  region        = var.region
  network       = var.vpc_network
  ip_cidr_range = var.proxy_subnet_cidr
  purpose       = "REGIONAL_MANAGED_PROXY"
  role          = "ACTIVE"
  description   = "Net-new Proxy-only subnet for regional Envoy load balancers over Partner CCI"
}

resource "google_compute_subnetwork" "workload_subnet" {
  count         = var.workload_subnet_cidr != null ? 1 : 0
  name          = "${var.bridge_name_prefix}-workload-subnet"
  project       = var.project_id
  region        = var.region
  network       = var.vpc_network
  ip_cidr_range = var.workload_subnet_cidr
  purpose       = "PRIVATE"
  description   = "Net-new Workload subnetwork for Cross-Cloud Lakehouse internal forwarding rule VIP"
}

locals {
  target_subnetwork = var.subnetwork != null ? var.subnetwork : (length(google_compute_subnetwork.workload_subnet) > 0 ? google_compute_subnetwork.workload_subnet[0].id : null)
}

resource "google_compute_address" "vip_address" {
  count        = var.create_static_ip ? 1 : 0
  name         = "${var.bridge_name_prefix}-vip-address"
  project      = var.project_id
  region       = var.region
  subnetwork   = local.target_subnetwork
  address_type = "INTERNAL"
  address      = var.forwarding_rule_ip
  description  = "Reserved internal static IP address for Cross-Cloud Lakehouse S3 load balancer VIP"
}

locals {
  effective_vip = var.create_static_ip ? google_compute_address.vip_address[0].address : var.forwarding_rule_ip
}

# -----------------------------------------------------------------------------
# 1. HYBRID NETWORK ENDPOINT GROUP (NON_GCP_PRIVATE_IP_PORT)
# Ingests AWS S3 PrivateLink ENI IP addresses across the Partner Interconnect.
# -----------------------------------------------------------------------------
module "hybrid_neg" {
  source                = "../../../tf-goog-modules/modules/lb/neg"
  name                  = "${var.bridge_name_prefix}-neg"
  network_endpoint_type = "NON_GCP_PRIVATE_IP_PORT"
  network               = var.vpc_network
  zone                  = var.zone
  default_port          = 443

  endpoints = {
    for k, ep in var.aws_s3_private_endpoints : k => {
      ip_address = ep.ip_address
      port       = try(ep.port, 443)
    }
  }
}

# -----------------------------------------------------------------------------
# 2. REGIONAL HEALTH CHECK & BACKEND SERVICE
# Probes TCP port 443 across the Partner CCI and pools the Hybrid NEG targets.
# -----------------------------------------------------------------------------
module "region_health_check" {
  source      = "../../../tf-goog-modules/modules/lb/region_health_check"
  name        = "${var.bridge_name_prefix}-hc"
  region      = var.region
  description = "TCP Health Check for AWS S3 PrivateLink ENIs across Partner CCI"
  
  tcp_health_check = {
    port         = 443
    proxy_header = "NONE"
  }
}

module "region_backend_service" {
  source                = "../../../tf-goog-modules/modules/lb/region_backend_service"
  name                  = "${var.bridge_name_prefix}-backend-srv"
  region                = var.region
  description           = "Regional internal managed TCP backend service pooling AWS S3 ENIs over Partner CCI"
  load_balancing_scheme = "INTERNAL_MANAGED"
  protocol              = "TCP"
  health_checks         = [module.region_health_check.id]

  backends = [
    {
      group           = module.hybrid_neg.id
      balancing_mode  = "CONNECTION"
      max_connections = 1000
      capacity_scaler = 1.0
    }
  ]
}

# -----------------------------------------------------------------------------
# 3. REGIONAL MANAGED TARGET TCP PROXY & FORWARDING RULE (VIP)
# Allocates a reserved static internal Virtual IP inside the VPC subnet to represent remote AWS S3.
# -----------------------------------------------------------------------------
module "tcp_target_proxy" {
  source          = "../../../tf-goog-modules/modules/lb/tcp_routing"
  name            = "${var.bridge_name_prefix}-tcp-proxy"
  region          = var.region
  description     = "Target TCP proxy steering internal traffic to AWS S3 Hybrid NEG backend"
  backend_service = module.region_backend_service.id
  proxy_header    = "NONE"
}

module "forwarding_rule" {
  source                = "../../../tf-goog-modules/modules/lb/forwarding_rule"
  name                  = "${var.bridge_name_prefix}-fr"
  region                = var.region
  description           = "Internal managed forwarding rule VIP for Cross-Cloud Lakehouse S3 bridge"
  load_balancing_scheme = "INTERNAL_MANAGED"
  network               = var.vpc_network
  subnetwork            = local.target_subnetwork
  ip_address            = local.effective_vip
  ip_protocol           = "TCP"
  port_range            = "443"
  target                = module.tcp_target_proxy.id
  labels                = var.labels

  depends_on = [google_compute_subnetwork.proxy_subnet]
}

# -----------------------------------------------------------------------------
# 4. SERVICE DIRECTORY PRIVATE NAMING BRIDGE
# Registers the Load Balancer VIP into Google Cloud Service Directory so BigLake
# queries resolve and stream data privately across the Interconnect wire.
# -----------------------------------------------------------------------------
module "service_directory" {
  source       = "../../../tf-goog-modules/modules/service_directory"
  project_id   = var.project_id
  location     = var.region
  namespace_id = var.service_directory_config.namespace_id
  labels       = var.labels

  services = {
    "${var.service_directory_config.service_id}" = {
      metadata = {
        purpose = "cross-cloud-lakehouse-s3-bridge"
        region  = var.region
      }
    }
  }

  endpoints = {
    "${var.service_directory_config.endpoint_id}" = {
      service_id = var.service_directory_config.service_id
      address    = module.forwarding_rule.ip_address
      port       = 443
      network    = local.normalized_sd_network
    }
  }
}
