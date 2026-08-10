# Serverless VPC Access Connector Module

This domain module manages the creation of a Serverless VPC Access connector on Google Cloud, allowing serverless workloads such as Cloud Run and Cloud Functions to route outbound requests into private VPC networks.

## Usage

```hcl
module "vpc_connector" {
  source         = "./modules/vpc_connector"
  project_id     = "my-project-id"
  region         = "us-east4"
  connector_name = "crf-vpc-conn"
  network        = module.vpc.network_name
  ip_cidr_range  = "10.8.0.0/28"
}
```
