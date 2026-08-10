locals {
  mime_types = {
    "pdf"  = "application/pdf"
    "docx" = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    "xlsx" = "application/vnd.openxmlformats-officedocument.spreadsheetml.document"
    "mp3"  = "audio/mpeg"
    "wav"  = "audio/wav"
    "png"  = "image/png"
    "jpg"  = "image/jpeg"
    "txt"  = "text/plain"
  }

  # Step 1: Get the list of all files from the directory safely
  all_files = fileset("${path.root}/${var.files_folder}", "**/*")
  # bronze is fixed since this intends to upload only raw files
  bucket_folder_path = "${var.environment}/bronze/${var.files_source}/${var.files_owner_team}"

  # Step 2: Build the nested combination safely using explicit list comprehensions
  file_uploads = flatten([
    for file in local.all_files : [ {
        key       = "${local.bucket_folder_path}/${basename(file)}"
        file      = file
      }
    ]
  ])
}

resource "google_storage_bucket_object" "upload_all_data_folders" {
  for_each = { for item in local.file_uploads : item.key => item }

  name         = each.value.key
  bucket       = "${var.gcs_bucket_to_upload}"
  source       = "${path.root}/${var.files_folder}/${each.value.file}"
  detect_md5hash = filemd5("${path.root}/${var.files_folder}/${each.value.file}")
  
  content_type = lookup(
    local.mime_types,
    element(split(".", each.value.file), length(split(".", each.value.file)) - 1),
    "application/octet-stream"
  )
}