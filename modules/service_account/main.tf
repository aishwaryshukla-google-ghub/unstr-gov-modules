# -----------------------------------------------------------------------------
# SERVICE ACCOUNT MODULE
# Provisions a GCP Service Account with configurable IAM role bindings.
# -----------------------------------------------------------------------------

resource "google_service_account" "this" {
  account_id   = var.account_id
  display_name = var.display_name != null ? var.display_name : var.account_id
  description  = var.description
  project      = var.project_id
}

resource "google_project_iam_member" "roles" {
  for_each = setunion(var.project_roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.this.email}"
}
