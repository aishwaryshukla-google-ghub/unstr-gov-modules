variable "project_id" {
  description = "The GCP project ID where the cross-cloud load balancing bridge and Service Directory namespace will be created."
  type        = string
}

variable "region" {
  description = "The primary Google Cloud region for the internal managed load balancer and Service Directory (e.g., us-east4)."
  type        = string
}

variable "zone" {
  description = "The Google Cloud zone for the zonal Hybrid NEG (e.g., us-east4-a)."
  type        = string
}

variable "vpc_network" {
  description = "The fully qualified network path (projects/<proj>/global/networks/<vpc_name>) or resource URI where Partner CCI terminates."
  type        = string
}

variable "subnetwork" {
  description = "Optional fully qualified existing subnetwork path in the target region. If null, workload_subnet_cidr must be supplied to provision a new subnetwork."
  type        = string
  default     = null
}

variable "workload_subnet_cidr" {
  description = "Optional CIDR range (e.g., 10.10.16.0/20) to provision a net-new PRIVATE subnetwork for the forwarding rule VIP."
  type        = string
  default     = null
}

variable "proxy_subnet_cidr" {
  description = "Optional CIDR range (e.g., 10.10.32.0/23) to provision a net-new REGIONAL_MANAGED_PROXY subnet for Envoy proxy load balancers."
  type        = string
  default     = null
}

variable "create_static_ip" {
  description = "Whether to provision an internal static IP address resource for the Load Balancer VIP instead of an ephemeral assignment."
  type        = bool
  default     = true
}

variable "aws_s3_private_endpoints" {
  description = "Map of AWS S3 PrivateLink ENI IP addresses (com.amazonaws.<region>.s3) across the Partner Interconnect to attach to the Hybrid NEG."
  type = map(object({
    ip_address = string
    port       = optional(number, 443)
  }))
  default = {}
}

variable "bridge_name_prefix" {
  description = "Naming prefix applied to the created Hybrid NEG, health check, backend service, TCP proxy, and forwarding rule."
  type        = string
  default     = "ccl-s3-bridge"
}

variable "forwarding_rule_ip" {
  description = "Optional static internal IP address to assign to the reserved static address / Load Balancer VIP. If null, GCP allocates one from the subnetwork."
  type        = string
  default     = null
}

variable "service_directory_config" {
  description = "Configuration for the Service Directory namespace, service, and endpoint binding."
  type = object({
    namespace_id = optional(string, "ccl-federation-ns")
    service_id   = optional(string, "aws-s3-private-service")
    endpoint_id  = optional(string, "s3-private-endpoint")
  })
  default = {}
}

variable "labels" {
  description = "An optional map of enterprise labels to assign to all resources under label governance."
  type        = map(string)
  default     = {}
}
