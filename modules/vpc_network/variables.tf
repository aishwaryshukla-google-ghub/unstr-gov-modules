variable "project_id" {
  description = "The GCP project ID where the VPC network will be created."
  type        = string
}

variable "network_name" {
  description = "The name of the VPC network."
  type        = string
}

variable "auto_create_subnetworks" {
  description = "When set to true, the network is created in auto subnet mode and it will create a subnet for each region automatically."
  type        = bool
  default     = false
}

variable "routing_mode" {
  description = "The network routing mode (GLOBAL or REGIONAL)."
  type        = string
  default     = "GLOBAL"
}

variable "description" {
  description = "An optional description of this VPC network."
  type        = string
  default     = "Managed by Terraform"
}

variable "delete_default_routes_on_create" {
  description = "If set to true, default routes (0.0.0.0/0) will be deleted immediately after network creation."
  type        = bool
  default     = false
}

variable "mtu" {
  description = "Maximum Transmission Unit in bytes. Default is 1460."
  type        = number
  default     = 1460
}

variable "subnets" {
  description = "List of subnets to create within the VPC network."
  type = list(object({
    subnet_name               = string
    subnet_ip                 = string
    subnet_region             = string
    subnet_private_access     = optional(bool, true)
    purpose                   = optional(string, null)
    role                      = optional(string, null)
    description               = optional(string, null)
    subnet_flow_logs          = optional(bool, false)
    subnet_flow_logs_interval = optional(string, "INTERVAL_5_SEC")
    subnet_flow_logs_sampling = optional(string, "0.5")
    subnet_flow_logs_metadata = optional(string, "INCLUDE_ALL_METADATA")
    secondary_ip_ranges = optional(list(object({
      range_name    = string
      ip_cidr_range = string
    })), [])
  }))
  default = []
}
