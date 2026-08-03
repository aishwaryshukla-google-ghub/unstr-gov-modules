# -----------------------------------------------------------------------------
# CLOUD RUN FUNCTION (CLOUD FUNCTIONS GEN 2) MODULE
# Deploys a Cloud Run Function (Cloud Functions 2nd Gen) with configurable
# build settings, runtime configuration, VPC networking, and Eventarc triggers.
# -----------------------------------------------------------------------------

resource "google_cloudfunctions2_function" "function" {
  name        = var.function_name
  location    = var.region
  project     = var.project_id
  description = var.description

  build_config {
    runtime     = var.runtime
    entry_point = var.entry_point

    dynamic "source" {
      for_each = var.storage_source != null ? [var.storage_source] : []
      content {
        storage_source {
          bucket     = source.value.bucket
          object     = source.value.object
          generation = try(source.value.generation, null)
        }
      }
    }

    dynamic "source" {
      for_each = var.repo_source != null ? [var.repo_source] : []
      content {
        repo_source {
          project_id   = try(source.value.project_id, var.project_id)
          repo_name    = source.value.repo_name
          branch_name  = try(source.value.branch_name, null)
          tag_name     = try(source.value.tag_name, null)
          commit_sha   = try(source.value.commit_sha, null)
          dir          = try(source.value.dir, null)
          invert_regex = try(source.value.invert_regex, null)
        }
      }
    }

    docker_repository = var.docker_repository
    service_account = var.build_service_account != null && var.build_service_account != "" ? (
      startswith(var.build_service_account, "projects/") ? var.build_service_account : (
        startswith(var.build_service_account, "serviceAccount:") ?
        "projects/${var.project_id}/serviceAccounts/${replace(var.build_service_account, "serviceAccount:", "")}" :
        "projects/${var.project_id}/serviceAccounts/${var.build_service_account}"
      )
    ) : null
    environment_variables = var.build_environment_variables
  }

  service_config {
    max_instance_count             = var.max_instance_count
    min_instance_count             = var.min_instance_count
    available_memory               = var.available_memory
    available_cpu                  = var.available_cpu
    timeout_seconds                = var.timeout_seconds
    environment_variables          = var.environment_variables
    ingress_settings               = var.ingress_settings
    all_traffic_on_latest_revision = var.all_traffic_on_latest_revision
    service_account_email          = var.service_account_email
    vpc_connector                  = var.vpc_connector
    vpc_connector_egress_settings  = var.vpc_connector_egress_settings

    dynamic "secret_environment_variables" {
      for_each = var.secret_environment_variables
      content {
        key        = secret_environment_variables.value.key
        project_id = secret_environment_variables.value.project_id
        secret     = secret_environment_variables.value.secret
        version    = secret_environment_variables.value.version
      }
    }
  }

  dynamic "event_trigger" {
    for_each = var.event_trigger != null ? [var.event_trigger] : []
    content {
      trigger_region        = try(event_trigger.value.trigger_region, var.region)
      event_type            = event_trigger.value.event_type
      pubsub_topic          = try(event_trigger.value.pubsub_topic, null)
      service_account_email = try(event_trigger.value.service_account_email, var.service_account_email)
      retry_policy          = try(event_trigger.value.retry_policy, "RETRY_POLICY_DO_NOT_RETRY")

      dynamic "event_filters" {
        for_each = try(event_trigger.value.event_filters, [])
        content {
          attribute = event_filters.value.attribute
          value     = event_filters.value.value
          operator  = try(event_filters.value.operator, null)
        }
      }
    }
  }

  labels = var.labels
}

# Grant Invoker permissions to specified IAM members on the underlying Cloud Run service
resource "google_cloud_run_v2_service_iam_member" "invoker" {
  for_each = toset(var.invokers)

  project  = var.project_id
  location = var.region
  name     = google_cloudfunctions2_function.function.service_config[0].service
  role     = var.invoker_role == "roles/cloudfunctions.invoker" ? "roles/run.invoker" : var.invoker_role
  member   = each.value
}
