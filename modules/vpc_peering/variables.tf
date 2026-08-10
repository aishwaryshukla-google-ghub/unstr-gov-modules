variable "peering_name" {
  description = "Name of the peering connection."
  type        = string
}

variable "local_network" {
  description = "The primary (local) network self_link or URI."
  type        = string
}

variable "peer_network" {
  description = "The peer (remote) network self_link or URI."
  type        = string
}

variable "export_custom_routes" {
  description = "Whether to export custom routes to peer network."
  type        = bool
  default     = false
}

variable "import_custom_routes" {
  description = "Whether to import custom routes from peer network."
  type        = bool
  default     = false
}

variable "export_subnet_routes_with_public_ip" {
  description = "Whether subnet routes with public IP range are exported."
  type        = bool
  default     = true
}

variable "import_subnet_routes_with_public_ip" {
  description = "Whether subnet routes with public IP range are imported."
  type        = bool
  default     = false
}

variable "stack_type" {
  description = "Which IP version(s) of traffic and routes are allowed over this peering. Allowed: IPV4_ONLY, IPV4_IPV6."
  type        = string
  default     = "IPV4_ONLY"
}

variable "create_reverse_peering" {
  description = "Whether to create the reverse peering from peer_network to local_network (requires permissions on both projects)."
  type        = bool
  default     = false
}

variable "reverse_peering_name" {
  description = "Optional custom name for the reverse peering connection."
  type        = string
  default     = null
}

variable "peer_export_custom_routes" {
  description = "Optional override for peer network exporting custom routes. Defaults to import_custom_routes."
  type        = bool
  default     = null
}

variable "peer_import_custom_routes" {
  description = "Optional override for peer network importing custom routes. Defaults to export_custom_routes."
  type        = bool
  default     = null
}

variable "peer_export_subnet_routes_with_public_ip" {
  description = "Optional override for peer network exporting public IP subnet routes."
  type        = bool
  default     = null
}

variable "peer_import_subnet_routes_with_public_ip" {
  description = "Optional override for peer network importing public IP subnet routes."
  type        = bool
  default     = null
}
