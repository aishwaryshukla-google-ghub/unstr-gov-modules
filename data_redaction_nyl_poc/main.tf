
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
    runtime     = "python39"
    entry_point = "handle_request"
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
    service_account_email = var.service_account_email
    environment_variables = {
      INSPECT_TEMPLATE_NAME    = google_data_loss_prevention_inspect_template.nyl_inspect_template.id
      DEIDENTIFY_TEMPLATE_NAME = google_data_loss_prevention_deidentify_template.nyl_deidentify_template.id
      DLP_LOCATION             = var.region
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
  routine_id   = "sample_remote_function"
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
