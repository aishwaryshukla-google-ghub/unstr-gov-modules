# VPC Peering Module

This domain module manages the creation of VPC Network Peering between two Google Cloud VPC networks (either in the same project or across different projects).

## Usage

```hcl
module "vpc_peering" {
  source                 = "./modules/vpc_peering"
  peering_name           = "crf-to-mulesoft-peering"
  local_network          = module.vpc.network_self_link
  peer_network           = "projects/mulesoft-host-proj/global/networks/mulesoft-vpc"
  create_reverse_peering = false # Set true if this Terraform workspace manages both projects
}
```
