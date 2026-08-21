# ==============================================================================
# 1. GCS - CONVERSATION MEMORY STORE & ARTIFACT REPOSITORY
# ==============================================================================
resource "google_storage_bucket" "agent_memory" {
  name                        = "${var.project_id}-agent-memory-${var.region}"
  location                    = var.region
  project                     = var.project_id
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = true
  labels                      = var.labels
}

# ==============================================================================
# 2. CRF - MCP (Cloud Run Function Tool Execution Service)
# ==============================================================================
data "archive_file" "mcp_zip" {
  type        = "zip"
  source_dir  = "${path.module}/mcp_server"
  output_path = "${path.module}/mcp_source.zip"
}

resource "google_storage_bucket_object" "mcp_zip" {
  name   = "mcp-source-${data.archive_file.mcp_zip.output_md5}.zip"
  bucket = google_storage_bucket.function_bucket.name
  source = data.archive_file.mcp_zip.output_path
}

resource "google_cloudfunctions2_function" "nyl_mcp_server" {
  name        = "nyl-mcp-server"
  location    = var.region
  project     = var.project_id
  description = "NYL MCP Server hosting BigQuery RAG tools and GCS export tools"
  labels      = var.labels

  build_config {
    runtime         = "python311"
    entry_point     = "handle_tool_request"
    service_account = "projects/${var.project_id}/serviceAccounts/${var.service_account_email}"

    source {
      storage_source {
        bucket = google_storage_bucket.function_bucket.name
        object = google_storage_bucket_object.mcp_zip.name
      }
    }
  }

  service_config {
    max_instance_count    = 2
    available_memory      = "512M"
    timeout_seconds       = 120
    ingress_settings      = var.ingress_settings
    service_account_email = var.service_account_email
    environment_variables = {
      PROJECT_ID    = var.project_id
      DATASET_ID    = var.dataset_id
      MEMORY_BUCKET = google_storage_bucket.agent_memory.name
    }
  }

  depends_on = [
    google_project_iam_member.storage_viewer,
    google_project_iam_member.log_writer,
    google_project_iam_member.artifact_writer
  ]
}

# Allow Agent Function to call MCP Server
resource "google_cloud_run_service_iam_member" "mcp_invoker" {
  project  = var.project_id
  location = var.region
  service  = google_cloudfunctions2_function.nyl_mcp_server.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${var.service_account_email}"
}

# ==============================================================================
# 3. CRF - AGENT (Cloud Run Function LLM Reasoning & Memory Orchestration)
# ==============================================================================
data "archive_file" "agent_zip" {
  type        = "zip"
  source_dir  = "${path.module}/agent_app"
  output_path = "${path.module}/agent_source.zip"
}

resource "google_storage_bucket_object" "agent_zip" {
  name   = "agent-source-${data.archive_file.agent_zip.output_md5}.zip"
  bucket = google_storage_bucket.function_bucket.name
  source = data.archive_file.agent_zip.output_path
}

resource "google_cloudfunctions2_function" "nyl_agent_function" {
  name        = "nyl-agent-function"
  location    = var.region
  project     = var.project_id
  description = "NYL Gemini Agent Orchestrator with GCS Session Memory and MCP Tools"
  labels      = var.labels

  build_config {
    runtime         = "python311"
    entry_point     = "handle_agent_request"
    service_account = "projects/${var.project_id}/serviceAccounts/${var.service_account_email}"

    source {
      storage_source {
        bucket = google_storage_bucket.function_bucket.name
        object = google_storage_bucket_object.agent_zip.name
      }
    }
  }

  service_config {
    max_instance_count             = 2
    available_memory               = "512M"
    timeout_seconds                = 120
    ingress_settings               = var.ingress_settings
    service_account_email          = var.service_account_email
    vpc_connector                  = var.vpc_connector
    vpc_connector_egress_settings  = var.vpc_connector != null ? var.vpc_connector_egress_settings : null
    environment_variables = {
      PROJECT_ID     = var.project_id
      REGION         = var.region
      DATASET_ID     = var.dataset_id
      MODEL_NAME     = var.model_name
      AI_GATEWAY_URL = var.ai_gateway_url
      MEMORY_BUCKET  = google_storage_bucket.agent_memory.name
      MCP_SERVER_URL = google_cloudfunctions2_function.nyl_mcp_server.service_config[0].uri
    }
  }

  depends_on = [
    google_project_iam_member.storage_viewer,
    google_project_iam_member.log_writer,
    google_project_iam_member.artifact_writer,
    google_project_iam_member.agent_vertex_user,
    google_storage_bucket_iam_member.agent_memory_admin
  ]
}

# Allow BigQuery Connection to invoke CRF - AGENT
resource "google_cloud_run_service_iam_member" "agent_invoker" {
  project  = var.project_id
  location = var.region
  service  = google_cloudfunctions2_function.nyl_agent_function.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_bigquery_connection.remote_connection.cloud_resource[0].service_account_id}"
}

# ==============================================================================
# 4. BIGQUERY REMOTE FUNCTION (ROUTINE) FOR AGENT QUERY
# ==============================================================================
resource "google_bigquery_routine" "agent_query_function" {
  dataset_id   = var.dataset_id
  routine_id   = "agent_query"
  routine_type = "SCALAR_FUNCTION"
  project      = var.project_id

  definition_body = ""

  return_type = "{\"typeKind\" : \"STRING\"}"

  arguments {
    name      = "prompt"
    data_type = "{\"typeKind\" : \"STRING\"}"
  }

  arguments {
    name      = "session_id"
    data_type = "{\"typeKind\" : \"STRING\"}"
  }

  remote_function_options {
    endpoint   = google_cloudfunctions2_function.nyl_agent_function.service_config[0].uri
    connection = google_bigquery_connection.remote_connection.name
  }
}

# ==============================================================================
# 5. IAM ROLES FOR AGENT & MCP RUNTIME SERVICE ACCOUNT
# ==============================================================================
resource "google_project_iam_member" "agent_vertex_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${var.service_account_email}"
}

resource "google_storage_bucket_iam_member" "agent_memory_admin" {
  bucket = google_storage_bucket.agent_memory.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${var.service_account_email}"
}

