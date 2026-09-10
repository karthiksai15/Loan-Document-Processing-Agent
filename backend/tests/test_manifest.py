import os
import pandas as pd
from app.core.config import settings

def test_document_manifest_integrity():
    manifest_path = os.path.join(settings.DATA_DIR, "processed", "document_manifest.csv")
    assert os.path.exists(manifest_path), f"Manifest file missing at {manifest_path}"
    
    df = pd.read_csv(manifest_path)
    assert len(df) == 38, f"Expected 38 documents, found {len(df)}"
    
    required_cols = {"document_id", "applicant_id", "document_type", "filename", "file_path", "scenario"}
    assert required_cols.issubset(set(df.columns)), f"Missing required columns in manifest: {df.columns}"
    
    # Verify file paths exist
    project_root = os.path.dirname(settings.DATA_DIR)
    for idx, row in df.iterrows():
        abs_path = os.path.join(project_root, row["file_path"])
        assert os.path.exists(abs_path), f"Document file missing: {abs_path}"
