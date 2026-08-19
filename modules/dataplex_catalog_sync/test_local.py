import json
import os
import unittest

from dataplex_catalog_manager import (
    parse_metadata_json,
    get_governance_compliance_template,
    get_business_taxonomy_template,
    get_source_provenance_template,
)


class TestDataplexCatalogParser(unittest.TestCase):
    def setUp(self):
        sample_path = os.path.join(os.path.dirname(__file__), "sample_metadata.json")
        with open(sample_path, "r", encoding="utf-8") as f:
            self.sample_json = json.load(f)
        self.gcs_uri = "gs://my-nyl-documents-bucket/policies/NYL_Compliance_Underwriting_Policy_2026.docx.json"

    def test_parse_metadata(self):
        entry_core, aspects = parse_metadata_json(self.sample_json, self.gcs_uri)

        # 1. Verify Entry Core
        self.assertEqual(entry_core["entry_id"], "sp-doc-7372")
        self.assertEqual(entry_core["display_name"], "NYL_Compliance_Underwriting_Policy_2026.docx")
        self.assertEqual(entry_core["fully_qualified_name"], "gcs:my-nyl-documents-bucket:policies/NYL_Compliance_Underwriting_Policy_2026.docx.json")

        # 2. Verify Governance & Compliance Aspect
        gov = aspects["governance-compliance"]
        self.assertTrue(gov["governance_approved"])
        self.assertEqual(gov["governance_approval_timestamp"], "2026-08-10T23:03:23.386874Z")
        self.assertEqual(gov["data_classification"], "Confidential")
        self.assertFalse(gov["sec_rule_38a_1"])
        self.assertEqual(gov["certified_business_approved"], "APPROVED")
        self.assertEqual(gov["compliance_tags"]["tag_name"], "NYL_FINANCIAL_RETENTION_7YR")

        # 3. Verify Business Taxonomy Aspect
        tax = aspects["business-taxonomy"]
        self.assertEqual(tax["kmh_short_codes"], ["MMM", "LIS"])
        self.assertEqual(tax["document_type_lookup_id"], "7")
        self.assertEqual(tax["document_sub_type_lookup_id"], "48")
        self.assertEqual(len(tax["lob_lookups"]), 2)
        self.assertEqual(tax["lob_lookups"][0]["lookup_id"], 17)
        self.assertEqual(tax["lob_lookups"][0]["lookup_value"], "Retail Life & Annuities")
        self.assertEqual(tax["function_term"]["label"], "Actuarial Governance")
        self.assertEqual(tax["function_term"]["wss_id"], 8)

        # 4. Verify Source Provenance Aspect
        prov = aspects["source-provenance"]
        self.assertEqual(prov["source_system"], "SharePoint")
        self.assertEqual(prov["item_id"], "7372")
        self.assertEqual(prov["ui_version"], "7.0")
        self.assertEqual(prov["file_size_bytes"], 39023)
        self.assertEqual(prov["created_by"]["email"], "jane.doe@nyl.com")
        self.assertEqual(prov["last_modified_by"]["email"], "john.smith@nyl.com")

        print("\n[SUCCESS] Local test passed! Parsed Entry and Aspects structure:")
        print(json.dumps({"entry": entry_core, "aspects": aspects}, indent=2))


if __name__ == "__main__":
    unittest.main()
