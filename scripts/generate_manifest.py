import os
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILES_PATH = os.path.join(PROJECT_ROOT, "data", "processed", "applicant_profiles.csv")
APPLICANTS_DIR = os.path.join(PROJECT_ROOT, "data", "applicants")
MANIFEST_PATH = os.path.join(PROJECT_ROOT, "data", "processed", "document_manifest.csv")

DOC_TYPE_MAP = {
    "01_payslip": "payslip",
    "02_bank_statement": "bank_statement",
    "03_tax_return": "tax_return",
    "04_kyc": "kyc"
}

def generate_manifest():
    if not os.path.exists(PROFILES_PATH):
        raise FileNotFoundError(f"Applicant profiles not found at {PROFILES_PATH}")
    
    profiles_df = pd.read_csv(PROFILES_PATH)
    scenarios = dict(zip(profiles_df['applicant_id'], profiles_df['scenario']))
    
    manifest_rows = []
    
    for app_id in sorted(os.listdir(APPLICANTS_DIR)):
        app_dir = os.path.join(APPLICANTS_DIR, app_id)
        if not os.path.isdir(app_dir) or not app_id.startswith("A"):
            continue
        
        scenario = scenarios.get(app_id, "unknown")
        
        for fname in sorted(os.listdir(app_dir)):
            if fname.startswith("."):
                continue
            
            stem, ext = os.path.splitext(fname)
            doc_type = DOC_TYPE_MAP.get(stem, stem)
            doc_id = f"DOC_{app_id}_{doc_type.upper()}"
            rel_path = os.path.relpath(os.path.join(app_dir, fname), PROJECT_ROOT)
            
            manifest_rows.append({
                "document_id": doc_id,
                "applicant_id": app_id,
                "document_type": doc_type,
                "filename": fname,
                "file_path": rel_path,
                "file_format": ext.lstrip("."),
                "scenario": scenario
            })
            
    manifest_df = pd.DataFrame(manifest_rows)
    manifest_df.to_csv(MANIFEST_PATH, index=False)
    print(f"Manifest generated successfully at {MANIFEST_PATH} with {len(manifest_df)} documents.")
    return manifest_df

if __name__ == "__main__":
    generate_manifest()
