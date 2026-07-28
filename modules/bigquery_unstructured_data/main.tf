######################################################################
# DISCLAIMER: THIS MODULE IS THOUGHT FOR LOCAL POC TESTING PURPOSES. #
# IT SHOULD NOT BE PORTED AS IS TO NYL REPOSITORY! ###################
######################################################################

# 1. Create the BigQuery Dataset
resource "google_bigquery_dataset" "unstructured_ds" {
  dataset_id  = var.dataset_id
  project     = var.project_id
  location    = var.region
  description = "Dataset for indexing and governing unstructured PDF data"
}

# 2. BigQuery Connection (Required to query external data [DEPENDENT ON BQ OMNI CONNECTION TO S3])
resource "google_bigquery_connection" "gcs_connection" {
  connection_id = "gcs-unstructured-conn"
  project       = var.project_id
  location      = var.region
  description   = "Cloud Resource connection to access GCS PDF metadata"
  cloud_resource {}
}

# 3. Delay to allow GCP IAM to fully register the newly generated SA
resource "time_sleep" "wait_for_sa_propagation" {
  create_duration = "15s"

  depends_on = [
    google_bigquery_connection.gcs_connection
  ]
}

# 4. Grant the BigQuery Connection SA read access scoped strictly to the PDF folder prefix
resource "google_storage_bucket_iam_member" "connection_gcs_reader" {
  bucket = var.bucket_name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_bigquery_connection.gcs_connection.cloud_resource[0].service_account_id}"

  # IAM Condition restricting read access solely to objects under the /pdfs/ folder path
  #condition {
  #  title       = "ScopedToUnstructuredDataFolder"
  #  description = "Grant read access only to objects starting with ${var.documents_folder_path}/"
  #  expression  = "resource.name.startsWith('projects/_/buckets/${var.bucket_name}/objects/${var.documents_folder_path}/')"
  #}
  depends_on = [ 
    time_sleep.wait_for_sa_propagation
  ]
}

# 5. BigQuery Object Table over the PDF folder wildcard path
resource "google_bigquery_table" "pdf_object_table" {
  dataset_id = google_bigquery_dataset.unstructured_ds.dataset_id
  table_id   = var.table_id
  project    = var.project_id

  external_data_configuration {
    autodetect    = false

    # Wildcard dynamically captures all current and future PDFs under this path
    source_uris = [
      "gs://${var.bucket_name}/${var.documents_folder_path}/*.pdf"
    ]

    # Converting to an Object Table
    object_metadata = "SIMPLE"
    connection_id   = google_bigquery_connection.gcs_connection.name
  }

  depends_on = [
    google_bigquery_connection.gcs_connection
  ]
}