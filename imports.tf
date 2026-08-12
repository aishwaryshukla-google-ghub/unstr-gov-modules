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
