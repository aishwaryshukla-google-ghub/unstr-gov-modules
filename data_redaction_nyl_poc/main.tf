
# 1. Artifact Registry to store the image
resource "google_artifact_registry_repository" "repo" {
  project       = var.project_id
  location      = var.region
  repository_id = "nyl-cloudrun-repo"
  description   = "Docker repository for NYL sample app"
  format        = "DOCKER"
  labels        = var.labels
}

# 2. Deploy Cloud Run Service via NYL approved module
module "nyl_flask_app_cloud_run" {
  source     = "app.harness.io/fA6kGr7FTEG47VMeTwdA4Q/nyl-gcp-cloud-run/nyl"
  version    = "1.0.3"
  project_id = var.project_id
  name       = "nyl-sample-flask-app"
  region     = var.region

  service_account_config = {
    create = false
    email  = var.service_account_email
  }

  containers = {
    nyl-flask-app = {
      image = "us-docker.pkg.dev/cloudrun/container/hello"
      env = {
        INSPECT_TEMPLATE_NAME    = google_data_loss_prevention_inspect_template.nyl_inspect_template.id
        DEIDENTIFY_TEMPLATE_NAME = google_data_loss_prevention_deidentify_template.nyl_deidentify_template.id
        DLP_LOCATION             = var.region
      }
    }
  }

  iam = {
    "roles/run.invoker" = [
      "serviceAccount:${google_bigquery_connection.remote_connection.cloud_resource[0].service_account_id}"
    ]
  }

  service_config = {
    ingress = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"
    scaling = {
      min_instance_count = 1
    }
  }

  deletion_protection = false
  labels              = var.labels
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
    endpoint   = module.nyl_flask_app_cloud_run.service_uri
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
