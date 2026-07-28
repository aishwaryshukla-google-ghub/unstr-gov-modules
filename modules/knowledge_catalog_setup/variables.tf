variable "project_id" {
    description = "The GCP Project ID"
    type        = string
}

variable "region" {
    description = "The GCP region for the project resources"
    type        = string
}

variable "gcp_apis" {
    description = "List of GCP APIs to enable"
    type        = list(string)
    default = [
        "dataplex.googleapis.com",
        "datalineage.googleapis.com",
        "datacatalog.googleapis.com"
    ]
}

variable "lake_name" {
    description = "Unique identifier for the KC lake"
    type        = string
    default     = "nyl-unstructured-data-lake"  
}

# Define the 3 Medallion Zones and their Dataplex types
variable "zones" {
  description = "Map of zones (Bronze, Silver, Gold) and their corresponding Dataplex Zone types"
  type = map(object({
    display_name = string
    type         = string # Valid GCP types: RAW, CURATED
    description  = string
  }))
  default = {
    "bronze" = {
      display_name = "Bronze Zone (Raw Data)"
      type         = "RAW"
      description  = "Landing zone for raw documents"
    }
    "silver" = {
      display_name = "Silver Zone (Extracted Data)"
      type         = "CURATED"
      description  = "Zone for processed documents data"
    }
    "gold" = {
      display_name = "Gold Zone (Agent Ready)"
      type         = "CURATED"
      description  = "Zone for chunked, enriched data"
    }
  }
}