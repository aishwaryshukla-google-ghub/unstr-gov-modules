# Cross-Cloud Lakehouse (CCL) Private Bridge Module

This domain capability module automates establishing the **Layer 4 and Layer 7 private network backbone** over **Partner Cross-Cloud Interconnect (CCI)**. It securely bridges remote AWS S3 PrivateLink Elastic Network Interfaces (ENIs) directly into Google Cloud Service Directory using an internal regional managed TCP proxy load balancing tier.

## Architecture & Primitives Sourcing

This composite module imports atomic building blocks from `tf-goog-modules`:
1. `modules/lb/neg`: Provisions a Zonal Hybrid NEG (`NON_GCP_PRIVATE_IP_PORT`) attaching remote AWS S3 ENI IP addresses without requiring native VM instance IDs.
2. `modules/lb/region_health_check`: Actively monitors TCP port `443` across the Partner Interconnect.
3. `modules/lb/region_backend_service`: Pools the Hybrid NEG targets with connection-based managed load balancing.
4. `modules/lb/tcp_routing`: Creates a regional target TCP proxy (`proxy_header = "NONE"`).
5. `modules/lb/forwarding_rule`: Allocates an internal Virtual IP (VIP) inside your target GCP workload subnetwork.
6. `modules/service_directory`: Automatically registers the Load Balancer VIP into a private Service Directory namespace and service.

## Key Highlights
* **Automatic Network URI Normalization**: Incorporates internal string parsing to ensure that whatever network syntax your Platform team supplies (HTTP Compute URLs or basic global paths), Service Directory always receives its strictly mandated Resource Manager syntax (`projects/<proj>/locations/global/networks/<vpc_name>`).
* **Zero Race Conditions**: HCL attribute chaining across all six sub-modules guarantees sequential creation and teardown without triggering GCP `resourceInUseByAnotherResource` lock errors.

## Usage Example

```hcl
module "ccl_bridge" {
  source             = "../../modules/ccl_private_bridge"
  project_id         = "my-gcp-data-project-01"
  region             = "us-east4" # Co-located with AWS us-east-1 / Databricks
  zone               = "us-east4-a"
  vpc_network        = "projects/my-host-vpc-project/global/networks/crosscloud-vpc"
  subnetwork         = "projects/my-host-vpc-project/regions/us-east4/subnetworks/data-workloads"

  # IP addresses supplied by the AWS Infrastructure Team (S3 PrivateLink ENIs)
  aws_s3_private_endpoints = {
    "s3-eni-subnet-a" = { ip_address = "10.200.10.45", port = 443 }
    "s3-eni-subnet-b" = { ip_address = "10.200.11.88", port = 443 }
  }

  service_directory_config = {
    namespace_id = "ccl-databricks-ns"
    service_id   = "aws-s3-private-service"
    endpoint_id  = "s3-ilb-endpoint"
  }
}

# Chain directly into the federated catalog capability module:
module "ccl_catalog" {
  source                       = "../../modules/ccl_federated_catalog"
  project_id                   = "my-gcp-data-project-01"
  region                       = "us-east4"
  service_directory_service_id = module.ccl_bridge.service_directory_service_id
  # ... catalog configurations ...
}
```
