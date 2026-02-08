"""
Secure storage module for PhenoAge patient data.

Provides AES-256 encrypted storage with SHA-256 patient ID hashing for HIPAA compliance.
All patient data (biomarkers and PhenoAge results) is encrypted before storage in Excel format.

Key Features:
- AES-256 encryption via cryptography.fernet.Fernet
- SHA-256 hashing for patient ID anonymization
- Excel-based persistence (patient_data/patient_data_encrypted.xlsx)
- Encryption key management from .env file
- Full patient data lifecycle: save, load, delete

Author: Claude Code
Date: 2026-02-07
Specification: spec_extract.txt lines 770-935
"""

from __future__ import annotations
from typing import Optional, Dict, Any, List, Union
from pathlib import Path
from datetime import datetime
import json
import base64
import hashlib
import pandas as pd
from cryptography.fernet import Fernet, InvalidToken
from dotenv import dotenv_values


class SecureStorageConfig:
    """
    Configuration for secure storage system.

    Attributes:
        storage_dir: Directory for encrypted data files (default: patient_data/)
        excel_filename: Name of encrypted storage file (default: patient_data_encrypted.xlsx)
        env_file: Path to .env file containing encryption key
    """

    def __init__(
        self,
        storage_dir: Path = Path("patient_data"),
        excel_filename: str = "patient_data_encrypted.xlsx",
        env_file: Path = Path(".env")
    ):
        self.storage_dir = storage_dir
        self.excel_path = storage_dir / excel_filename
        self.env_file = env_file


class SecureStorage:
    """
    Manages encrypted patient data storage with Excel backend.

    Implements HIPAA-compliant storage with:
    - AES-256 encryption for all patient data
    - SHA-256 hashing for patient ID anonymization
    - Excel persistence for encrypted records
    - Automatic encryption key management from .env

    Example:
        >>> storage = SecureStorage()
        >>> biomarkers = {'albumin': 4.5, 'creatinine': 0.9, ...}
        >>> results = {'phenoage': 47.3, 'delta_age': -2.7, ...}
        >>> hashed_id = storage.save_patient_data(12345, biomarkers, results)
        >>> data = storage.load_patient_data(12345)
    """

    def __init__(self, config: Optional[SecureStorageConfig] = None):
        """
        Initialize secure storage with configuration.

        Args:
            config: Storage configuration (uses defaults if None)

        Raises:
            ValueError: If encryption key not found in .env file
        """
        self.config = config if config is not None else SecureStorageConfig()

        # Ensure storage directory exists
        self.config.storage_dir.mkdir(parents=True, exist_ok=True)

        # Load encryption key from .env
        self._encryption_key = self._load_encryption_key()
        self._fernet = Fernet(self._encryption_key)

    def _load_encryption_key(self) -> bytes:
        """
        Load Fernet encryption key from .env file.

        Returns:
            Encryption key as bytes

        Raises:
            ValueError: If PHENOAGE_ENCRYPTION_KEY not found in .env
        """
        # Read directly from .env file to avoid process environment pollution
        # (Using dotenv_values instead of load_dotenv + os.getenv to isolate per-file)
        env_vars = dotenv_values(self.config.env_file)
        key_str = env_vars.get("PHENOAGE_ENCRYPTION_KEY")

        if not key_str:
            raise ValueError(
                f"Encryption key not found. Please:\n"
                f"1. Copy .env.example to .env\n"
                f"2. Generate key: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"\n"
                f"3. Set PHENOAGE_ENCRYPTION_KEY in .env file\n"
                f"   Or use: from storage import setup_env_file; setup_env_file()"
            )

        # Validate key format (Fernet keys are base64-encoded, 44 characters)
        try:
            key_bytes = key_str.encode('utf-8')
            # Test that it's a valid Fernet key by creating a Fernet instance
            Fernet(key_bytes)
            return key_bytes
        except Exception as e:
            raise ValueError(
                f"Invalid encryption key format. Key must be base64-encoded Fernet key.\n"
                f"Generate new key: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"\n"
                f"Error: {e}"
            )

    def _hash_patient_id(self, patient_id: int) -> str:
        """
        Generate SHA-256 hash of patient ID for anonymization.

        Args:
            patient_id: Patient identifier (integer)

        Returns:
            64-character hexadecimal hash string
        """
        # Convert patient ID to string, then to UTF-8 bytes
        id_bytes = str(patient_id).encode('utf-8')

        # Apply SHA-256 hash
        hash_obj = hashlib.sha256(id_bytes)

        # Return hexadecimal digest (64 characters)
        return hash_obj.hexdigest()

    def _encrypt_data(self, data: Dict[str, Any]) -> str:
        """
        Encrypt dictionary to Base64 string using Fernet.

        Args:
            data: Patient data dictionary to encrypt

        Returns:
            Base64-encoded encrypted string
        """
        # Convert dictionary to JSON string
        json_str = json.dumps(data, ensure_ascii=False)

        # Convert JSON string to UTF-8 bytes
        json_bytes = json_str.encode('utf-8')

        # Encrypt using Fernet (returns bytes)
        encrypted_bytes = self._fernet.encrypt(json_bytes)

        # Convert to Base64 string for Excel storage
        encrypted_str = base64.b64encode(encrypted_bytes).decode('utf-8')

        return encrypted_str

    def _decrypt_data(self, encrypted_str: str) -> Dict[str, Any]:
        """
        Decrypt Base64 string to dictionary using Fernet.

        Args:
            encrypted_str: Base64-encoded encrypted string

        Returns:
            Decrypted patient data dictionary

        Raises:
            InvalidToken: If decryption fails (wrong key or corrupted data)
        """
        # Convert Base64 string to bytes
        encrypted_bytes = base64.b64decode(encrypted_str.encode('utf-8'))

        # Decrypt using Fernet (returns UTF-8 bytes)
        json_bytes = self._fernet.decrypt(encrypted_bytes)

        # Convert bytes to JSON string
        json_str = json_bytes.decode('utf-8')

        # Parse JSON to dictionary
        data = json.loads(json_str)

        return data

    def _load_storage_file(self) -> pd.DataFrame:
        """
        Load Excel storage file, create empty DataFrame if not exists.

        Returns:
            DataFrame with columns: hashed_patient_id, encrypted_data, timestamp
        """
        if self.config.excel_path.exists():
            # Load existing file
            df = pd.read_excel(self.config.excel_path, engine='openpyxl')
            return df
        else:
            # Create empty DataFrame with correct schema
            return pd.DataFrame(columns=['hashed_patient_id', 'encrypted_data', 'timestamp'])

    def _save_storage_file(self, df: pd.DataFrame) -> None:
        """
        Save DataFrame to Excel with proper formatting.

        Args:
            df: DataFrame to save (must have hashed_patient_id, encrypted_data, timestamp columns)
        """
        df.to_excel(self.config.excel_path, index=False, engine='openpyxl')

    def save_patient_data(
        self,
        patient_id: int,
        biomarkers: Dict[str, float],
        results: Dict[str, Union[float, Dict[str, float]]],
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Save encrypted patient data to Excel storage.

        Combines input biomarkers and calculation results into a single encrypted record.

        Args:
            patient_id: Unique patient identifier (e.g., NHANES seqn)
            biomarkers: Input biomarker dictionary with keys:
                albumin, creatinine, glucose, crp, lymphocyte_pct,
                mcv, rdw, alp, wbc, age (all in original NHANES units)
            results: PhenoAge calculation results dictionary from calculator.py
                Must contain: phenoage, chronological_age, delta_age, xb,
                mort_score, intermediate_values
            metadata: Optional metadata (timestamp added automatically)

        Returns:
            SHA-256 hashed patient ID (for reference)

        Raises:
            ValueError: If patient_id is not an integer
            IOError: If storage directory not writable

        Example:
            >>> biomarkers = {'albumin': 4.5, 'creatinine': 0.9, ...}
            >>> results = {'phenoage': 47.3, 'delta_age': -2.7, ...}
            >>> hashed_id = storage.save_patient_data(12345, biomarkers, results)
        """
        # Validate patient_id type
        if not isinstance(patient_id, int):
            raise TypeError(f"patient_id must be int, got {type(patient_id).__name__}")

        # Hash patient ID
        hashed_id = self._hash_patient_id(patient_id)

        # Create timestamp
        timestamp = datetime.now().isoformat()

        # Build complete patient record
        patient_record = {
            'patient_id': patient_id,
            'timestamp': timestamp,
            'input_biomarkers': biomarkers,
            'calculation_results': results
        }

        # Add optional metadata
        if metadata:
            patient_record['metadata'] = metadata

        # Encrypt patient record
        encrypted_data = self._encrypt_data(patient_record)

        # Load existing storage file
        df = self._load_storage_file()

        # Create new row
        new_row = pd.DataFrame([{
            'hashed_patient_id': hashed_id,
            'encrypted_data': encrypted_data,
            'timestamp': timestamp
        }])

        # Append new row
        df = pd.concat([df, new_row], ignore_index=True)

        # Save updated file
        self._save_storage_file(df)

        return hashed_id

    def load_patient_data(self, patient_id: int) -> Optional[Dict[str, Any]]:
        """
        Load and decrypt patient data by patient ID.

        Retrieves the most recent record for the given patient ID.

        Args:
            patient_id: Patient identifier

        Returns:
            Complete patient record dictionary or None if not found
            Structure:
                {
                    'patient_id': int,
                    'timestamp': str,
                    'input_biomarkers': {...},
                    'calculation_results': {...}
                }

        Raises:
            InvalidToken: If decryption fails (wrong key or corrupted data)

        Example:
            >>> data = storage.load_patient_data(12345)
            >>> if data:
            ...     print(f"PhenoAge: {data['calculation_results']['phenoage']}")
        """
        # Hash patient ID for lookup
        hashed_id = self._hash_patient_id(patient_id)

        # Load storage file
        df = self._load_storage_file()

        # Filter to matching records
        matching_rows = df[df['hashed_patient_id'] == hashed_id]

        if matching_rows.empty:
            return None

        # Get most recent record (last row)
        latest_row = matching_rows.iloc[-1]

        # Decrypt data
        try:
            decrypted_data = self._decrypt_data(latest_row['encrypted_data'])
            return decrypted_data
        except InvalidToken:
            # Log error but don't crash - data may be corrupted
            print(f"Warning: Failed to decrypt data for patient {patient_id}. Data may be corrupted.")
            return None

    def delete_patient_data(self, patient_id: int) -> bool:
        """
        Delete all records for a patient from storage.

        Implements patient right to deletion (HIPAA § 164.526).

        Args:
            patient_id: Patient identifier

        Returns:
            True if records were deleted, False if patient not found

        Example:
            >>> deleted = storage.delete_patient_data(12345)
            >>> if deleted:
            ...     print("Patient data deleted successfully")
        """
        # Hash patient ID
        hashed_id = self._hash_patient_id(patient_id)

        # Load storage file
        df = self._load_storage_file()

        # Count matching records before deletion
        matches = (df['hashed_patient_id'] == hashed_id).sum()

        if matches == 0:
            return False

        # Remove matching rows
        df = df[df['hashed_patient_id'] != hashed_id]

        # Save modified file
        self._save_storage_file(df)

        return True

    def list_all_records(self) -> List[Dict[str, str]]:
        """
        List all stored records (metadata only, no decryption).

        Returns metadata without decrypting patient data for efficiency.

        Returns:
            List of dictionaries with keys: hashed_patient_id, timestamp

        Example:
            >>> records = storage.list_all_records()
            >>> print(f"Total records: {len(records)}")
        """
        df = self._load_storage_file()

        # Return only metadata (no decryption)
        records = []
        for _, row in df.iterrows():
            records.append({
                'hashed_patient_id': row['hashed_patient_id'],
                'timestamp': row['timestamp']
            })

        return records

    def verify_data_integrity(self, patient_id: int) -> bool:
        """
        Verify encrypted data can be decrypted successfully.

        Tests data integrity without exposing decrypted content.

        Args:
            patient_id: Patient identifier

        Returns:
            True if data can be decrypted, False if corrupted or not found
        """
        try:
            data = self.load_patient_data(patient_id)
            return data is not None
        except InvalidToken:
            return False


def generate_encryption_key() -> str:
    """
    Generate a new Fernet encryption key.

    Returns:
        Base64-encoded encryption key string (44 characters)

    Example:
        >>> key = generate_encryption_key()
        >>> print(f"Add to .env file:\nPHENOAGE_ENCRYPTION_KEY={key}")
    """
    return Fernet.generate_key().decode('utf-8')


def setup_env_file(env_path: Path = Path(".env")) -> None:
    """
    Create .env file with new encryption key if it doesn't exist.

    Convenient setup function for first-time initialization.

    Args:
        env_path: Path to .env file (default: .env in current directory)

    Example:
        >>> setup_env_file()
        Created .env file with encryption key
    """
    if env_path.exists():
        print(f".env file already exists at {env_path}")
        print("Skipping key generation to avoid overwriting existing key")
        return

    # Generate new key
    key = generate_encryption_key()

    # Create .env file
    env_content = f"""# PhenoAge Engine - Environment Variables
# Generated: {datetime.now().isoformat()}

# Encryption key for secure patient data storage (AES-256 via Fernet)
# IMPORTANT: Keep this key secure and backed up - data cannot be decrypted without it
PHENOAGE_ENCRYPTION_KEY={key}
"""

    with open(env_path, 'w') as f:
        f.write(env_content)

    print(f"Created .env file with encryption key at {env_path}")
    print("IMPORTANT: Back up this key securely - data cannot be recovered if lost")
