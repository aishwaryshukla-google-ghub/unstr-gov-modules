# Unstructured Governance Terraform Modules (`unstr-gov-modules`)

Enterprise Terraform modules and turnkey solutions for Google Cloud Platform data platform, serverless workloads, cross-cloud lakehouse federation, and secure hybrid networking.

---

## Networking & Interconnect Modules

| Module | Location | Purpose |
| :--- | :--- | :--- |
| **VPC Network** | [modules/vpc_network](file:///Users/aishwaryshukla/Desktop/projects/google_cloud/80_percent/NYL/experiments/unstr-gov-modules/modules/vpc_network) | Provisions custom VPC Networks, subnetworks, secondary IP ranges, and proxy subnets. |
| **VPC Access Connector** | [modules/vpc_connector](file:///Users/aishwaryshukla/Desktop/projects/google_cloud/80_percent/NYL/experiments/unstr-gov-modules/modules/vpc_connector) | Provisions Serverless VPC Access connectors to route Cloud Run egress into private VPCs. |
| **VPC Network Peering** | [modules/vpc_peering](file:///Users/aishwaryshukla/Desktop/projects/google_cloud/80_percent/NYL/experiments/unstr-gov-modules/modules/vpc_peering) | Manages Layer 3 VPC Peering between local and remote VPCs. |
| **Cloud DNS Peering** | [modules/dns_peering](file:///Users/aishwaryshukla/Desktop/projects/google_cloud/80_percent/NYL/experiments/unstr-gov-modules/modules/dns_peering) | Resolves cross-VPC private domains (fixes `NameResolutionError`) via Cloud DNS peering. |
| **CCL Private Bridge** | [modules/ccl_private_bridge](file:///Users/aishwaryshukla/Desktop/projects/google_cloud/80_percent/NYL/experiments/unstr-gov-modules/modules/ccl_private_bridge) | L4/L7 hybrid NEG, TCP Proxy LB, and Service Directory for Partner CCI. |

---

## Solution Recipe: Cloud Run to Remote MuleSoft Flex Gateway

To enable a Cloud Run function in Project A to privately communicate with a MuleSoft Flex Gateway residing in Project B:

```hcl
# 1. Local VPC Network & Subnet
module "vpc_network" {
  source       = "./modules/vpc_network"
  project_id   = var.project_id
  network_name = "nyl-crf-vpc"

  subnets = [
    {
      subnet_name   = "crf-workload-subnet"
      subnet_ip     = "10.10.0.0/24"
      subnet_region = var.region
    }
  ]
}

# 2. Serverless VPC Access Connector for Cloud Run
module "vpc_connector" {
  source         = "./modules/vpc_connector"
  project_id     = var.project_id
  region         = var.region
  connector_name = "crf-vpc-conn"
  network        = module.vpc_network.network_name
  ip_cidr_range  = "10.10.1.0/28"
}

# 3. VPC Peering (Project A <-> Project B MuleSoft VPC)
module "vpc_peering" {
  source        = "./modules/vpc_peering"
  peering_name  = "crf-to-mulesoft-peering"
  local_network = module.vpc_network.network_self_link
  peer_network  = "projects/mulesoft-project-id/global/networks/mulesoft-vpc"
}

# 4. Cloud DNS Peering Zone (Resolves NameResolutionError for MuleSoft domain)
module "dns_peering" {
  source             = "./modules/dns_peering"
  project_id         = var.project_id
  zone_name          = "mulesoft-dns-peering"
  dns_name           = "mulesoft.internal."
  local_network_urls = [module.vpc_network.network_self_link]
  target_network_url = "projects/mulesoft-project-id/global/networks/mulesoft-vpc"
}

# 5. Cloud Run Function configured with VPC Connector
module "cloud_run_function" {
  source                        = "./solutions/cloud_run_function"
  project_id                    = var.project_id
  region                        = var.region
  function_name                 = "nyl-gov-cloud-run-func"
  vpc_connector                 = module.vpc_connector.connector_id
  vpc_connector_egress_settings = "ALL_TRAFFIC" # or "PRIVATE_RANGES_ONLY"
}
```