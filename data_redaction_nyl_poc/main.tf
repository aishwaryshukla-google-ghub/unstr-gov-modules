
# 1. Artifact Registry to store the image
resource "google_artifact_registry_repository" "repo" {
  location      = var.region
  repository_id = "nyl-cloudrun-repo"
  description   = "Docker repository for NYL sample app"
  format        = "DOCKER"
  labels        = var.labels
}

# 2. Deploy Cloud Run Service
resource "google_cloud_run_v2_service" "app_service" {
  name     = "nyl-sample-flask-app"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY"
  deletion_protection = false
  labels   = var.labels

  template {
    service_account = var.service_account_email
    labels          = var.labels

    scaling {
      min_instance_count = 1
    }

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.repo.repository_id}/nyl-flask-app:latest"
      
      ports {
        container_port = 8080
      }
      
      env {
        name  = "INSPECT_TEMPLATE_NAME"
        value = google_data_loss_prevention_inspect_template.nyl_inspect_template.id
      }
      
      env {
        name  = "DEIDENTIFY_TEMPLATE_NAME"
        value = google_data_loss_prevention_deidentify_template.nyl_deidentify_template.id
      }
    }
  }
}

# 3. BigQuery Remote Connection
resource "google_bigquery_connection" "remote_connection" {
  connection_id = "nyl_remote_connection"
  location      = var.region
  project       = var.project_id
  
  cloud_resource {}
}

# Grant BigQuery Connection access to invoke Cloud Run
resource "google_cloud_run_v2_service_iam_member" "invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.app_service.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_bigquery_connection.remote_connection.cloud_resource[0].service_account_id}"
}

# 4. BigQuery Dataset
resource "google_bigquery_dataset" "dataset" {
  dataset_id = "nyl_sandbox_dataset"
  location   = var.region
  project    = var.project_id
  labels     = var.labels
}

# 5. BigQuery Remote Function (Routine)
resource "google_bigquery_routine" "remote_function" {
  dataset_id      = google_bigquery_dataset.dataset.dataset_id
  routine_id      = "sample_remote_function"
  routine_type    = "SCALAR_FUNCTION"
  project         = var.project_id
  
  definition_body = ""
  
  return_type = "{\"typeKind\" : \"STRING\"}"
  
  arguments {
    name      = "input_text"
    data_type = "{\"typeKind\" : \"STRING\"}"
  }
  
  remote_function_options {
    endpoint   = google_cloud_run_v2_service.app_service.uri
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
