# Enable Dialogflow API required by Chat Engine
resource "google_project_service" "dialogflow" {
  project            = var.project_id
  service            = "dialogflow.googleapis.com"
  disable_on_destroy = false
}

resource "random_id" "vertex_suffix" {
  byte_length = 3
}

# 1. The Data Store that will hold the redacted documents
resource "google_discovery_engine_data_store" "redacted_data_store" {
  location                    = "us"
  data_store_id               = "redacted-docs-store-${random_id.vertex_suffix.hex}"
  display_name                = "Redacted Unstructured Documents"
  industry_vertical           = "GENERIC"
  content_config              = "CONTENT_REQUIRED"
  solution_types              = ["SOLUTION_TYPE_CHAT"]
  project                     = var.project_id
  create_advanced_site_search = false

  depends_on = [google_project_service.dialogflow]
}

# 2. The Chat Agent built on top of the Data Store
resource "google_discovery_engine_chat_engine" "redacted_agent" {
  location          = "us"
  engine_id         = "redacted-docs-agent-${random_id.vertex_suffix.hex}"
  collection_id     = "default_collection"
  display_name      = "Redacted Docs Agent"
  industry_vertical = "GENERIC"
  project           = var.project_id

  data_store_ids = [google_discovery_engine_data_store.redacted_data_store.data_store_id]

  depends_on = [google_project_service.dialogflow]
  
  chat_engine_config {
    agent_creation_config {
      business              = "New York Life"
      default_language_code = "en"
      time_zone             = "America/New_York"
    }
  }
}
