/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

resource "google_dataplex_data_product" "data_products" {
  for_each        = var.data_products
  project         = var.project_id
  location        = each.value.location
  data_product_id = each.key
  display_name    = coalesce(each.value.display_name, each.key)
  description     = each.value.description
  labels          = try(each.value.labels, {})
  owner_emails    = try(each.value.owner_emails, [])

  dynamic "access_groups" {
    for_each = each.value.access_groups != null ? each.value.access_groups : {}
    content {
      id           = access_groups.key
      group_id     = access_groups.key
      display_name = coalesce(access_groups.value.display_name, access_groups.key)
      description  = access_groups.value.description
      dynamic "principal" {
        for_each = access_groups.value.google_group != null && access_groups.value.google_group != "" ? [access_groups.value.google_group] : []
        content {
          google_group = principal.value
        }
      }
    }
  }
}
