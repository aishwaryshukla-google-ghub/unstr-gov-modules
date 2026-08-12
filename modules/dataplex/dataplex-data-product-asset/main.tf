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

locals {
  flat_assets = merge([
    for prod_id, assets_map in var.data_product_assets : {
      for asset_key, asset_val in assets_map :
      "${prod_id}.${asset_key}" => {
        data_product_id      = prod_id
        data_asset_id        = coalesce(try(asset_val.data_asset_id, null), asset_key)
        resource             = asset_val.resource
        labels               = try(asset_val.labels, null)
        access_group_configs = try(asset_val.access_group_configs, [])
      }
    }
  ]...)
}

resource "google_dataplex_data_product_data_asset" "assets" {
  for_each        = local.flat_assets
  project         = var.project_id
  location        = var.location
  data_product_id = each.value.data_product_id
  data_asset_id   = each.value.data_asset_id
  resource        = each.value.resource
  labels          = each.value.labels

  dynamic "access_group_configs" {
    for_each = each.value.access_group_configs
    content {
      access_group = access_group_configs.value.access_group
      iam_roles    = access_group_configs.value.iam_roles
    }
  }
}
