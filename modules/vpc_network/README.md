# VPC Network Module

This domain module manages the creation of a Google Cloud VPC Network and its associated subnetworks, secondary IP ranges, Private Google Access, and Proxy-Only subnets.

## Usage

```hcl
module "vpc" {
  source       = "./modules/vpc_network"
  project_id   = "my-project-id"
  network_name = "nyl-gov-vpc"
  routing_mode = "GLOBAL"

  subnets = [
    {
      subnet_name           = "subnet-workload-useast4"
      subnet_ip             = "10.10.0.0/24"
      subnet_region         = "us-east4"
      subnet_private_access = true
    },
    {
      subnet_name           = "subnet-proxy-useast4"
      subnet_ip             = "10.10.1.0/24"
      subnet_region         = "us-east4"
      purpose               = "REGIONAL_MANAGED_PROXY"
      role                  = "ACTIVE"
    }
  ]
}
```
