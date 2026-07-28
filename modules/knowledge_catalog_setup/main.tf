###############
# Enable APIs #
###############
resource "google_project_service" "enabled_apis" {
    for_each = toset(var.gcp_apis)

    project = var.project_id
    service = each.value

    # Prevents disabling the API when removing the resource from Terraform state, 
    # which avoids accidentally breaking dependent downstream services.
    disable_on_destroy = false
}

#########################
# Create Lake and Zones #
#########################
resource "google_dataplex_lake" "primary_lake" {
  name         = var.lake_name
  location     = var.region
  project      = var.project_id
  display_name = "Knowledge Catalog Data Lake"
  description  = "Data Domain for unstructured data"

  depends_on = [ google_project_service.enabled_apis ]
  # Explicit dependency ensures APIs are active before lake creation begins
}

resource "google_dataplex_zone" "medallion_zones" {
  for_each = var.zones

  name     = each.key # bronze, silver, gold
  location = var.region
  project  = var.project_id
  lake     = google_dataplex_lake.primary_lake.name

  display_name = each.value.display_name
  description  = each.value.description
  type         = each.value.type # RAW for Bronze; CURATED for Silver/Gold

  # discovery_spec is a required param
  discovery_spec {
    enabled  = false        # Enable to cron metadata discovery and auto-cataloging
    schedule = "0 * * * *"  # e.g. hourly discovery scan
  }

  resource_spec {
    location_type = "SINGLE_REGION"
  }
}

##############################################
# Create Business Glossary and example Terms #
##############################################
resource "google_dataplex_glossary" "business_glossary" {
  glossary_id  = "enterprise-data-glossary"
  location     = var.region
  project      = var.project_id
  display_name = "Enterprise Data Glossary"
  description  = "Central business glossary defining data classification and domain concepts"

  depends_on = [ google_project_service.enabled_apis ]
}

resource "google_dataplex_glossary_term" "term_internal" {
  term_id      = "internal"
  location     = var.region
  project      = var.project_id
  glossary_id  = google_dataplex_glossary.business_glossary.glossary_id
  parent       = "projects/${google_dataplex_glossary.business_glossary.project}/locations/${google_dataplex_glossary.business_glossary.location}/glossaries/${google_dataplex_glossary.business_glossary.glossary_id}"
  display_name = "Internal"
  description  = "Data accessible to anyone within the company."
}

resource "google_dataplex_glossary_term" "term_sensitive" {
  term_id      = "sensitive"
  location     = var.region
  project      = var.project_id
  glossary_id  = google_dataplex_glossary.business_glossary.glossary_id
  parent       = "projects/${google_dataplex_glossary.business_glossary.project}/locations/${google_dataplex_glossary.business_glossary.location}/glossaries/${google_dataplex_glossary.business_glossary.glossary_id}"
  display_name = "Sensitive"
  description  = "Access to data is restricted to a specific group of authorized people."
}

resource "google_dataplex_aspect_type" "data_access" {
  aspect_type_id  = "data-access-classification"
  location        = var.region
  project         = var.project_id
  display_name    = "Data Access Classification"
  description         = "Specifies whether dataset access is Internal or Sensitive"
  data_classification = "DATA_CLASSIFICATION_UNSPECIFIED"

  # Metadata template defines the schema for this Aspect in JSON schema format
  metadata_template = jsonencode({
    name = "data_access_schema"
    type = "record"
    recordFields = [
      {
        name  = "access_level"
        type  = "enum"
        index = 1
        annotations = {
          displayName = "Access Level"
          description = "The confidentiality/restriction level of this asset"
        }
        constraints = {
          required = true
        }
        enumValues = [
          {
            name  = "INTERNAL"
            index = 1
          },
          {
            name  = "SENSITIVE"
            index = 2
          }
        ]
      }
    ]
  })

  depends_on = [google_project_service.enabled_apis]
}