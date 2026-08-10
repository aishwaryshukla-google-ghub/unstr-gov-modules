# Cloud DNS Peering Module

This domain module configures a **Cloud DNS Peering Zone** in Google Cloud. It enables private DNS resolution across projects/VPCs by forwarding queries for a specific domain name (such as internal MuleSoft Flex Gateway domains) from the local VPC to a target VPC hosting the authoritative DNS records.

## Usage

```hcl
module "dns_peering" {
  source             = "./modules/dns_peering"
  project_id         = "my-crf-project-id"
  zone_name          = "mulesoft-dns-peering"
  dns_name           = "mulesoft.internal."
  local_network_urls = [module.vpc.network_self_link]
  target_network_url = "projects/mulesoft-host-proj/global/networks/mulesoft-vpc"
}
```
