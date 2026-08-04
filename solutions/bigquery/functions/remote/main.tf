# -----------------------------------------------------------------------------
# 1. BIGQUERY CLOUD RESOURCE CONNECTION (if not using an existing connection)
# -----------------------------------------------------------------------------
resource "google_bigquery_connection" "connection" {
  count         = var.existing_connection_id == null ? 1 : 0
  connection_id = var.connection_id
  project       = var.project_id
  location      = var.region
  friendly_name = "BigQuery Remote Function Connection (${var.routine_id})"
  description   = "Cloud Resource Connection for BigQuery Remote Function ${var.routine_id} to invoke Cloud Run"

  cloud_resource {}
}

locals {
  effective_connection_id = var.existing_connection_id != null ? var.existing_connection_id : google_bigquery_connection.connection[0].name
  connection_sa_email     = var.existing_connection_id != null ? null : try(google_bigquery_connection.connection[0].cloud_resource[0].service_account_id, null)
}

# -----------------------------------------------------------------------------
# 2. IAM BINDING: GRANT CLOUD RUN INVOKER TO CONNECTION SERVICE ACCOUNT
# -----------------------------------------------------------------------------
resource "google_cloud_run_service_iam_member" "bq_invoker" {
  count    = (var.cloud_run_service_name != null && var.existing_connection_id == null) ? 1 : 0
  project  = var.project_id
  location = var.region
  service  = var.cloud_run_service_name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_bigquery_connection.connection[0].cloud_resource[0].service_account_id}"
}


# -----------------------------------------------------------------------------
# 3. BIGQUERY ROUTINE (SCALAR REMOTE FUNCTION)
# -----------------------------------------------------------------------------
resource "google_bigquery_routine" "remote_function" {
  project         = var.project_id
  dataset_id      = var.dataset_id
  routine_id      = var.routine_id
  routine_type    = "SCALAR_FUNCTION"
  language        = "SQL"
  description     = var.description
  definition_body = ""

  dynamic "arguments" {
    for_each = var.arguments
    content {
      name      = arguments.value.name
      data_type = arguments.value.data_type
    }
  }

  return_type = var.return_type

  remote_function_options {
    endpoint          = var.endpoint
    connection        = local.effective_connection_id
    max_batching_rows = tostring(var.max_batching_rows)
  }

  depends_on = [
    google_cloud_run_service_iam_member.bq_invoker
  ]
}
