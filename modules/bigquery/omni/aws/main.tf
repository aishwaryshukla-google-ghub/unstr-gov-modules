# -----------------------------------------------------------------------------
# BIGQUERY OMNI AWS CONNECTION MODULE
# Manages the GCP-to-AWS cross-cloud identity connection.
# -----------------------------------------------------------------------------

resource "google_bigquery_connection" "aws_omni" {
  project       = var.project_id
  location      = var.omni_location
  connection_id = var.connection_id
  friendly_name = var.connection_name != null ? var.connection_name : var.connection_id
  description   = "BigQuery Omni connection to access data in S3 on AWS."

  aws {
    access_role {
      iam_role_id = var.aws_iam_role_arn
    }
  }
}
