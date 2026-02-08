import os
from pathlib import Path

def verify_system_integrity():
    required_files = [
        "CLAUDE.md",
        "core/calculator.py",
        "storage/secure_storage.py",
        ".env",
        "patient_data/patient_data_encrypted.xlsx"
    ]

    print("--- PHENOAGE SYSTEM INTEGRITY CHECK ---")
    for file in required_files:
        if Path(file).exists():
            print(f"✅ FOUND: {file}")
        else:
            print(f"❌ MISSING: {file} - Action Required!")

    # Check for Encryption Key
    with open(".env", "r") as f:
        content = f.read()
        if "PHENOAGE_ENCRYPTION_KEY" in content:
            print("✅ ENCRYPTION KEY: Configured in .env")
        else:
            print("❌ ENCRYPTION KEY: Missing from .env!")

if __name__ == "__main__":
    verify_system_integrity()
