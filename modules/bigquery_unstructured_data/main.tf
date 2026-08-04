######################################################################
# DISCLAIMER: THIS MODULE IS THOUGHT FOR LOCAL POC TESTING PURPOSES. #
# IT SHOULD NOT BE PORTED AS IS TO NYL REPOSITORY! ###################
######################################################################

# 1. Create the BigQuery Dataset
resource "google_bigquery_dataset" "unstructured_ds" {
  dataset_id  = var.dataset_id
  project     = var.project_id
  location    = var.region
  description = "Dataset for indexing and governing unstructured data"
  delete_contents_on_destroy = true
}

# 2. BigQuery Connection (Required to query external data [DEPENDENT ON BQ OMNI CONNECTION TO S3])
resource "google_bigquery_connection" "gcs_connection" {
  connection_id = "gcs-unstructured-conn"
  project       = var.project_id
  location      = var.region
  description   = "Cloud Resource connection to access GCS metadata"
  cloud_resource {}
}

# 3. Delay to allow GCP IAM to fully register the newly generated SA
resource "time_sleep" "wait_for_sa_propagation" {
  create_duration = "20s"

  depends_on = [
    google_bigquery_connection.gcs_connection
  ]
}

# 4. Grant the BigQuery Connection SA read access to the bucket
resource "google_storage_bucket_iam_member" "connection_gcs_reader" {
  bucket = var.bucket_name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_bigquery_connection.gcs_connection.cloud_resource[0].service_account_id}"

  depends_on = [ 
    time_sleep.wait_for_sa_propagation
  ]
}

# 5. BigQuery Object Table indexing ALL files (PDF, DOCX, XLSX, PPTX) at root or subfolders
resource "google_bigquery_table" "documents_object_table" {
  dataset_id = google_bigquery_dataset.unstructured_ds.dataset_id
  table_id   = var.table_id
  project    = var.project_id

  external_data_configuration {
    autodetect    = false

    # Dynamic ternary logic normalizes root paths ("") vs subfolder paths ("documents/")
    source_uris = [
      var.documents_folder_path == "" || var.documents_folder_path == "/" ? "gs://${var.bucket_name}/*" : "gs://${var.bucket_name}/${trim(var.documents_folder_path, "/")}/*"
    ]

    # Converting to an Object Table
    object_metadata = "SIMPLE"
    connection_id   = google_bigquery_connection.gcs_connection.name
  }

  depends_on = [
    google_bigquery_connection.gcs_connection,
    google_storage_bucket_iam_member.connection_gcs_reader
  ]
  deletion_protection = false
}