variable "project_id" {
  description = "The GCP project ID where the VPC Access connector will be created."
  type        = string
}

variable "region" {
  description = "The GCP region for the VPC Access connector (must match Cloud Run region)."
  type        = string
}

variable "connector_name" {
  description = "The name of the VPC Access connector (max 21 chars, lowercase alphanumeric and hyphens)."
  type        = string
}

variable "network" {
  description = "Name or self_link of the VPC network. Required when ip_cidr_range is used."
  type        = string
  default     = null
}

variable "ip_cidr_range" {
  description = "An unallocated /28 CIDR block (e.g., 10.8.0.0/28) to reserve for this connector. Required if subnet_name is not provided."
  type        = string
  default     = null
}

variable "subnet_name" {
  description = "Name of an existing /28 subnetwork to attach to the connector. If specified, network and ip_cidr_range should not be used."
  type        = string
  default     = null
}

variable "subnet_project_id" {
  description = "Project ID of the subnetwork if using Shared VPC."
  type        = string
  default     = null
}

variable "min_instances" {
  description = "Minimum number of connector instances (default 2)."
  type        = number
  default     = 2
}

variable "max_instances" {
  description = "Maximum number of connector instances (default 10)."
  type        = number
  default     = 10
}

variable "machine_type" {
  description = "Machine type of VPC Access connector instances (e.g. e2-micro, e2-standard-4, f1-micro)."
  type        = string
  default     = "e2-micro"
}

variable "min_throughput" {
  description = "Minimum throughput of the connector in Mbps (default 200)."
  type        = number
  default     = 200
}

variable "max_throughput" {
  description = "Maximum throughput of the connector in Mbps (default 1000)."
  type        = number
  default     = 1000
}
