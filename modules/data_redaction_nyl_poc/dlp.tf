resource "google_data_loss_prevention_inspect_template" "nyl_inspect_template" {
  parent       = "projects/${var.project_id}/locations/${var.region}"
  description  = "Inspect template for NYL OOB Redaction"
  display_name = "nyl_inspect_template"

  inspect_config {
    info_types {
      name = "STREET_ADDRESS"
    }
    info_types {
      name = "EMAIL_ADDRESS"
    }
    info_types {
      name = "PHONE_NUMBER"
    }
    info_types {
      name = "PERSON_NAME"
    }
  }
}

resource "google_data_loss_prevention_deidentify_template" "nyl_deidentify_template" {
  parent       = "projects/${var.project_id}/locations/${var.region}"
  description  = "De-identify template for NYL OOB Redaction"
  display_name = "nyl_deidentify_template"

  deidentify_config {
    info_type_transformations {
      transformations {
        info_types {
          name = "STREET_ADDRESS"
        }
        info_types {
          name = "EMAIL_ADDRESS"
        }
        info_types {
          name = "PHONE_NUMBER"
        }
        info_types {
          name = "PERSON_NAME"
        }
        primitive_transformation {
          replace_with_info_type_config = true
        }
      }
    }
  }
}
