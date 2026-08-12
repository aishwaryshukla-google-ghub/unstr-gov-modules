import {
  id = "nyl-pr-dbx-data-dev-01/nyl-pr-dbx-data-dev-01-fn-source"
  to = module.data_redaction_nyl_poc.google_storage_bucket.function_bucket
}

import {
  id = "projects/nyl-pr-dbx-data-dev-01/locations/us-east1/connections/nyl_remote_connection"
  to = module.data_redaction_nyl_poc.google_bigquery_connection.remote_connection
}

import {
  id = "projects/nyl-pr-dbx-data-dev-01/locations/us-east1/inspectTemplates/nyl_inspect_template"
  to = module.data_redaction_nyl_poc.google_data_loss_prevention_inspect_template.nyl_inspect_template
}

import {
  id = "projects/nyl-pr-dbx-data-dev-01/locations/us-east1/deidentifyTemplates/nyl_deidentify_template"
  to = module.data_redaction_nyl_poc.google_data_loss_prevention_deidentify_template.nyl_deidentify_template
}

import {
  id = "projects/nyl-pr-dbx-data-dev-01/locations/us-east1/functions/nyl-sample-flask-app"
  to = module.data_redaction_nyl_poc.google_cloudfunctions2_function.nyl_flask_app_cloud_function
}

import {
  id = "projects/nyl-pr-dbx-data-dev-01/datasets/test_dtst/routines/dlp_redact_text"
  to = module.data_redaction_nyl_poc.google_bigquery_routine.remote_function
}

import {
  id = "projects/nyl-pr-dbx-data-dev-01/datasets/test_dtst/tables/unstructured_docs"
  to = module.data_redaction_nyl_poc.google_bigquery_table.unstructured_docs
}

import {
  id = "projects/nyl-pr-dbx-data-dev-01/datasets/test_dtst/tables/redacted_documents_view"
  to = module.data_redaction_nyl_poc.google_bigquery_table.redacted_documents_view
}
import {
  id = "projects/nyl-pr-dbx-data-dev-01/locations/us-east1/functions/nyl-mcp-server"
  to = module.data_redaction_nyl_poc.google_cloudfunctions2_function.nyl_mcp_server
}
