variable "project_id" {
  description = "The GCP project ID where the DNS Peering zone is created (the requesting project, e.g. Cloud Run project)."
  type        = string
}

variable "zone_name" {
  description = "The unique resource name for the Cloud DNS managed zone."
  type        = string
}

variable "dns_name" {
  description = "The fully qualified DNS name of the zone to forward/peer (e.g. 'mulesoft.internal.' or 'api.internal')."
  type        = string
}

variable "description" {
  description = "Description of the DNS peering zone."
  type        = string
  default     = "Managed Cloud DNS Peering Zone"
}

variable "local_network_urls" {
  description = "List of local VPC network URLs authorized to query this DNS peering zone."
  type        = list(string)
}

variable "target_network_url" {
  description = "The target VPC network URL where the authoritative DNS zone / records reside (e.g., MuleSoft VPC)."
  type        = string
}

variable "labels" {
  description = "Optional map of enterprise labels to apply."
  type        = map(string)
  default     = {}
}
