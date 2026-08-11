
data "archive_file" "function_zip" {
  type        = "zip"
  source_dir  = "${path.module}/app"
  output_path = "${path.module}/function_source.zip"
}

resource "google_storage_bucket" "function_bucket" {
  name                        = "${var.project_id}-fn-source"
  location                    = var.region
  project                     = var.project_id
  uniform_bucket_level_access = true
  labels                      = var.labels
}

resource "google_storage_bucket_object" "function_zip" {
  name   = "source-${data.archive_file.function_zip.output_md5}.zip"
  bucket = google_storage_bucket.function_bucket.name
  source = data.archive_file.function_zip.output_path
}

resource "google_cloudfunctions2_function" "nyl_flask_app_cloud_function" {
  name        = "nyl-sample-flask-app"
  location    = var.region
  project     = var.project_id
  description = "NYL Flask App via Cloud Functions 2nd Gen"
  labels      = var.labels

  build_config {
    runtime         = "python311"
    entry_point     = "handle_request"
    service_account = "projects/${var.project_id}/serviceAccounts/${var.service_account_email}"
    environment_variables = {
      GOOGLE_FUNCTION_SOURCE = "app.py"
      PROJECT_ID             = var.project_id
    }
    source {
      storage_source {
        bucket = google_storage_bucket.function_bucket.name
        object = google_storage_bucket_object.function_zip.name
      }
    }
  }

  service_config {
    max_instance_count    = 1
    available_memory      = "256M"
    timeout_seconds       = 60
    ingress_settings      = "ALLOW_INTERNAL_AND_GCLB"
    service_account_email = var.service_account_email
    environment_variables = {
      INSPECT_TEMPLATE_NAME    = google_data_loss_prevention_inspect_template.nyl_inspect_template.id
      DEIDENTIFY_TEMPLATE_NAME = google_data_loss_prevention_deidentify_template.nyl_deidentify_template.id
      DLP_LOCATION             = var.region
      PROJECT_ID               = var.project_id
    }
  }
}

resource "google_cloud_run_service_iam_member" "invoker" {
  project  = var.project_id
  location = var.region
  service  = google_cloudfunctions2_function.nyl_flask_app_cloud_function.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_bigquery_connection.remote_connection.cloud_resource[0].service_account_id}"
}

# 3. BigQuery Remote Connection
resource "google_bigquery_connection" "remote_connection" {
  connection_id = "nyl_remote_connection"
  location      = var.region
  project       = var.project_id

  cloud_resource {}
}

# 4. BigQuery Remote Function (Routine)
resource "google_bigquery_routine" "remote_function" {
  dataset_id   = var.dataset_id
  routine_id   = "dlp_redact_text"
  routine_type = "SCALAR_FUNCTION"
  project      = var.project_id

  definition_body = ""

  return_type = "{\"typeKind\" : \"STRING\"}"

  arguments {
    name      = "input_text"
    data_type = "{\"typeKind\" : \"STRING\"}"
  }

  remote_function_options {
    endpoint   = google_cloudfunctions2_function.nyl_flask_app_cloud_function.service_config[0].uri
    connection = google_bigquery_connection.remote_connection.name
  }
}

resource "google_project_iam_member" "dlp_user" {
  project = var.project_id
  role    = "roles/dlp.user"
  member  = "serviceAccount:${var.service_account_email}"
}

resource "google_project_iam_member" "dlp_template_reader" {
  project = var.project_id
  role    = "roles/dlp.reader"
  member  = "serviceAccount:${var.service_account_email}"
}

resource "google_project_iam_member" "service_usage" {
  project = var.project_id
  role    = "roles/serviceusage.serviceUsageConsumer"
  member  = "serviceAccount:${var.service_account_email}"
}

# Clean up stuck state entry without calling provider
removed {
  from = null_resource.build_and_push_image

  lifecycle {
    destroy = false
  }
}

# 5. BigQuery Object Table for Unstructured Documents
resource "google_bigquery_table" "unstructured_docs" {
  dataset_id = var.dataset_id
  table_id   = "unstructured_docs"
  project    = var.project_id

  external_data_configuration {
    connection_id   = google_bigquery_connection.remote_connection.name
    autodetect      = false
    object_metadata = "SIMPLE"
    source_uris     = ["gs://gcp-native-ws2-unstructured-dev/*"]
  }
}

# Grant BigQuery Connection SA read access to the bucket
resource "google_storage_bucket_iam_member" "connection_bucket_reader" {
  bucket = "gcp-native-ws2-unstructured-dev"
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_bigquery_connection.remote_connection.cloud_resource[0].service_account_id}"
}

# Grant Cloud Function SA read access to the bucket
resource "google_storage_bucket_iam_member" "function_bucket_reader" {
  bucket = "gcp-native-ws2-unstructured-dev"
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${var.service_account_email}"
}


# 6. BigQuery View (For Real-Time Demo)
resource "google_bigquery_table" "redacted_documents_view" {
  dataset_id = var.dataset_id
  table_id   = "redacted_documents_view"
  project    = var.project_id

  view {
    query          = <<EOF
SELECT 
  uri,
  content_type,
  `${var.project_id}.${var.dataset_id}.dlp_redact_text`(uri) AS redacted_text
FROM `${var.project_id}.${var.dataset_id}.unstructured_docs`
WHERE uri LIKE "%.docx" OR uri LIKE "%.pdf"
EOF
    use_legacy_sql = false
  }

  depends_on = [
    google_bigquery_table.unstructured_docs,
    google_bigquery_routine.remote_function
  ]
}

# 7. Scheduled Query (To physically store data nightly)
resource "google_bigquery_data_transfer_config" "scheduled_redaction" {
  display_name           = "NYL Nightly Unstructured Redaction"
  location               = var.region
  data_source_id         = "scheduled_query"
  schedule               = "every 24 hours"
  destination_dataset_id = var.dataset_id
  project                = var.project_id
  service_account_name   = var.service_account_email

  params = {
    query = <<EOF
CREATE OR REPLACE TABLE `${var.project_id}.${var.dataset_id}.redacted_documents` AS
SELECT 
  uri,
  content_type,
  `${var.project_id}.${var.dataset_id}.dlp_redact_text`(uri) AS redacted_text
FROM `${var.project_id}.${var.dataset_id}.unstructured_docs`
WHERE uri LIKE "%.docx" OR uri LIKE "%.pdf"
EOF
  }

  depends_on = [
    google_bigquery_table.unstructured_docs,
    google_bigquery_routine.remote_function
  ]
}

# ==============================================================================
# MCP Server (Deployed via Cloud Functions Gen 2 to bypass local Docker)
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
  description = "NYL MCP Server hosting BigQuery RAG tools"
  labels      = var.labels

  build_config {
    runtime = "python311"
    # Entry point is ignored because we supply a Procfile, which tells Cloud Buildpacks to run uvicorn natively.
    entry_point     = "dummy"
    service_account = "projects/${var.project_id}/serviceAccounts/${var.service_account_email}"

    source {
      storage_source {
        bucket = google_storage_bucket.function_bucket.name
        object = google_storage_bucket_object.mcp_zip.name
      }
    }
  }

  service_config {
    max_instance_count    = 1
    available_memory      = "512M"
    timeout_seconds       = 60
    ingress_settings      = "ALLOW_ALL"
    service_account_email = var.service_account_email
    environment_variables = {
      PROJECT_ID = var.project_id
      DATASET_ID = var.dataset_id
    }
  }
}

# Allow unauthenticated access for testing. In production, this should be restricted.
resource "google_cloud_run_service_iam_member" "mcp_invoker" {
  project  = var.project_id
  location = var.region
  service  = google_cloudfunctions2_function.nyl_mcp_server.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

output "mcp_server_url" {
  description = "The URL of the deployed MCP Server to register in Agent Platform."
  value       = google_cloudfunctions2_function.nyl_mcp_server.service_config[0].uri
}
