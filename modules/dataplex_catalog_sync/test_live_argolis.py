#!/usr/bin/env python3
import sys
import os
import json
import logging

# Add current dir to path
sys.path.insert(0, os.path.dirname(__file__))

from main import sync_metadata_to_dataplex

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def main():
    project_id = "databricks-playground-497321"
    location = "us-central1"
    sample_file = os.path.join(os.path.dirname(__file__), "sample_metadata.json")

    print("=" * 80)
    print("🚀 LIVE ARGOLIS TEST: DATAPLEX UNIVERSAL CATALOG METADATA SYNC")
    print(f"   Project : {project_id}")
    print(f"   Location: {location}")
    print(f"   File    : {sample_file}")
    print("=" * 80)

    try:
        # Test auto-derivation of Entry Group (e.g. from parentReference.name: 'Shared Documents' -> 'shared-documents')
        res = sync_metadata_to_dataplex(
            gcs_uri=sample_file,
            project_id=project_id,
            location=location,
        )
        print("\n✅ Sync Result:")
        print(json.dumps(res, indent=2))
        print("\n🎉 Live Argolis Dataplex Catalog Sync Test Succeeded!")
    except Exception as e:
        logger.exception("Live test encountered an error:")
        sys.exit(1)

if __name__ == "__main__":
    main()
