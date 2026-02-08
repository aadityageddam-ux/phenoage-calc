"""
Comprehensive tests for SecureStorage module.

Tests encryption, decryption, Excel persistence, data integrity, and error handling.

Test Classes:
- TestEncryptionBasics: Core encryption/decryption functionality
- TestPatientDataStorage: CRUD operations
- TestDataIntegrity: CRITICAL - verify exact data preservation
- TestExcelPersistence: File operations and persistence
- TestErrorHandling: Edge cases and error conditions

Author: Claude Code
Date: 2026-02-07
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime
import json
import pandas as pd
from cryptography.fernet import Fernet

from storage import (
    SecureStorage,
    SecureStorageConfig,
    generate_encryption_key,
    setup_env_file
)


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def temp_storage_dir():
    """Create temporary directory for test storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_env_file(temp_storage_dir):
    """Create temporary .env file with valid encryption key."""
    env_path = temp_storage_dir / ".env"
    key = generate_encryption_key()
    with open(env_path, 'w') as f:
        f.write(f"PHENOAGE_ENCRYPTION_KEY={key}\n")
    yield env_path


@pytest.fixture
def secure_storage(temp_storage_dir, temp_env_file):
    """SecureStorage instance with temporary configuration."""
    config = SecureStorageConfig(
        storage_dir=temp_storage_dir,
        env_file=temp_env_file
    )
    return SecureStorage(config)


@pytest.fixture
def sample_biomarkers():
    """Standard test biomarker data (NHANES units)."""
    return {
        'albumin': 4.5,           # g/dL
        'creatinine': 0.9,        # mg/dL
        'glucose': 95.0,          # mg/dL
        'crp': 0.1,              # mg/dL
        'lymphocyte_pct': 30.0,  # %
        'mcv': 90.0,             # fL
        'rdw': 13.0,             # %
        'alp': 65.0,             # U/L
        'wbc': 6.5,              # 1000 cells/μL
        'age': 50.0              # years
    }


@pytest.fixture
def sample_results():
    """Standard test PhenoAge calculation results."""
    return {
        'phenoage': 47.3,
        'chronological_age': 50.0,
        'delta_age': -2.7,
        'xb': -9.5,
        'mort_score': 0.012,
        'intermediate_values': {
            'albumin_g_L': 45.0,
            'creatinine_umol_L': 79.56,
            'glucose_mmol_L': 5.27,
            'crp_mg_L': 1.0,
            'log_crp': 0.0
        }
    }


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

class TestEncryptionBasics:
    """Test core encryption/decryption functionality."""

    def test_generate_key_format(self):
        """Test key generation produces valid Fernet key."""
        key = generate_encryption_key()

        # Fernet keys are base64-encoded, 44 characters
        assert isinstance(key, str)
        assert len(key) == 44

        # Should be valid for Fernet
        key_bytes = key.encode('utf-8')
        fernet = Fernet(key_bytes)  # Should not raise

    def test_encrypt_decrypt_roundtrip(self, secure_storage, sample_biomarkers):
        """Test data survives encryption/decryption unchanged."""
        # Create test data
        test_data = {
            'patient_id': 12345,
            'biomarkers': sample_biomarkers,
            'timestamp': '2024-01-15T14:32:07'
        }

        # Encrypt
        encrypted = secure_storage._encrypt_data(test_data)
        assert isinstance(encrypted, str)
        assert len(encrypted) > 0

        # Decrypt
        decrypted = secure_storage._decrypt_data(encrypted)

        # Verify exact match
        assert decrypted == test_data
        assert decrypted['patient_id'] == test_data['patient_id']
        assert decrypted['biomarkers'] == test_data['biomarkers']

    def test_different_keys_produce_different_ciphertext(self, temp_storage_dir):
        """Test encryption is key-dependent."""
        # Create two storage instances with different keys
        env1 = temp_storage_dir / ".env1"
        env2 = temp_storage_dir / ".env2"

        key1 = generate_encryption_key()
        key2 = generate_encryption_key()

        with open(env1, 'w') as f:
            f.write(f"PHENOAGE_ENCRYPTION_KEY={key1}\n")
        with open(env2, 'w') as f:
            f.write(f"PHENOAGE_ENCRYPTION_KEY={key2}\n")

        config1 = SecureStorageConfig(storage_dir=temp_storage_dir, env_file=env1)
        config2 = SecureStorageConfig(storage_dir=temp_storage_dir, env_file=env2)

        storage1 = SecureStorage(config1)
        storage2 = SecureStorage(config2)

        # Encrypt same data with both keys
        test_data = {'test': 'value'}
        encrypted1 = storage1._encrypt_data(test_data)
        encrypted2 = storage2._encrypt_data(test_data)

        # Should produce different ciphertext
        assert encrypted1 != encrypted2

    def test_patient_id_hashing_consistency(self, secure_storage):
        """Test same patient_id always produces same hash."""
        patient_id = 12345

        # Hash multiple times
        hash1 = secure_storage._hash_patient_id(patient_id)
        hash2 = secure_storage._hash_patient_id(patient_id)
        hash3 = secure_storage._hash_patient_id(patient_id)

        # Should be identical (deterministic)
        assert hash1 == hash2 == hash3

        # Should be 64 characters (SHA-256 hex digest)
        assert len(hash1) == 64
        assert all(c in '0123456789abcdef' for c in hash1)

    def test_different_patient_ids_produce_different_hashes(self, secure_storage):
        """Test different patient IDs produce different hashes."""
        hash1 = secure_storage._hash_patient_id(12345)
        hash2 = secure_storage._hash_patient_id(12346)
        hash3 = secure_storage._hash_patient_id(54321)

        # All should be different
        assert hash1 != hash2
        assert hash2 != hash3
        assert hash1 != hash3


class TestPatientDataStorage:
    """Test complete storage workflows (CRUD operations)."""

    def test_save_and_load_patient_data(self, secure_storage, sample_biomarkers, sample_results):
        """Test saving and retrieving complete patient record."""
        patient_id = 12345

        # Save data
        hashed_id = secure_storage.save_patient_data(
            patient_id=patient_id,
            biomarkers=sample_biomarkers,
            results=sample_results
        )

        # Verify hash returned
        assert isinstance(hashed_id, str)
        assert len(hashed_id) == 64

        # Load data
        loaded_data = secure_storage.load_patient_data(patient_id)

        # Verify data loaded
        assert loaded_data is not None
        assert loaded_data['patient_id'] == patient_id
        assert loaded_data['input_biomarkers'] == sample_biomarkers
        assert loaded_data['calculation_results'] == sample_results
        assert 'timestamp' in loaded_data

    def test_multiple_patients_storage(self, secure_storage, sample_biomarkers, sample_results):
        """Test storing multiple patients in same Excel file."""
        # Save 3 patients
        patient_ids = [10001, 10002, 10003]

        for patient_id in patient_ids:
            secure_storage.save_patient_data(
                patient_id=patient_id,
                biomarkers=sample_biomarkers,
                results=sample_results
            )

        # Verify all can be loaded
        for patient_id in patient_ids:
            data = secure_storage.load_patient_data(patient_id)
            assert data is not None
            assert data['patient_id'] == patient_id

        # Verify list_all_records shows 3 records
        records = secure_storage.list_all_records()
        assert len(records) == 3

    def test_load_nonexistent_patient(self, secure_storage):
        """Test loading non-existent patient returns None."""
        data = secure_storage.load_patient_data(99999)
        assert data is None

    def test_delete_patient_data(self, secure_storage, sample_biomarkers, sample_results):
        """Test patient deletion removes record."""
        patient_id = 12345

        # Save patient
        secure_storage.save_patient_data(patient_id, sample_biomarkers, sample_results)

        # Verify exists
        assert secure_storage.load_patient_data(patient_id) is not None

        # Delete
        deleted = secure_storage.delete_patient_data(patient_id)
        assert deleted is True

        # Verify no longer exists
        assert secure_storage.load_patient_data(patient_id) is None

    def test_delete_nonexistent_patient(self, secure_storage):
        """Test deleting non-existent patient returns False."""
        deleted = secure_storage.delete_patient_data(99999)
        assert deleted is False


class TestDataIntegrity:
    """CRITICAL: Test data accuracy and exact preservation."""

    def test_decrypted_data_exactly_matches_input(self, secure_storage, sample_biomarkers, sample_results):
        """CRITICAL: Verify decryption produces exact original dictionary."""
        patient_id = 12345

        # Save data
        secure_storage.save_patient_data(patient_id, sample_biomarkers, sample_results)

        # Load data
        loaded = secure_storage.load_patient_data(patient_id)

        # Verify exact match
        assert loaded is not None
        assert loaded['patient_id'] == patient_id
        assert loaded['input_biomarkers'] == sample_biomarkers
        assert loaded['calculation_results'] == sample_results

        # Verify individual fields
        assert loaded['input_biomarkers']['albumin'] == 4.5
        assert loaded['calculation_results']['phenoage'] == 47.3
        assert loaded['calculation_results']['delta_age'] == -2.7

    def test_float_precision_preservation(self, secure_storage):
        """Test floating-point biomarker values preserved accurately."""
        patient_id = 12345

        # High-precision test data
        biomarkers = {
            'albumin': 4.123456789,
            'creatinine': 0.987654321,
            'glucose': 95.11111111,
            'crp': 0.12345678,
            'lymphocyte_pct': 30.55555555,
            'mcv': 90.99999999,
            'rdw': 13.12121212,
            'alp': 65.77777777,
            'wbc': 6.54321,
            'age': 50.5
        }

        results = {'phenoage': 47.123456789, 'chronological_age': 50.5,
                   'delta_age': -3.373456789, 'xb': -9.5, 'mort_score': 0.012,
                   'intermediate_values': {}}

        # Save and load
        secure_storage.save_patient_data(patient_id, biomarkers, results)
        loaded = secure_storage.load_patient_data(patient_id)

        # Verify precision preserved (should match exactly via JSON)
        assert loaded['input_biomarkers'] == biomarkers
        assert loaded['calculation_results'] == results

    def test_timestamp_format(self, secure_storage, sample_biomarkers, sample_results):
        """Test timestamp is ISO 8601 format."""
        patient_id = 12345

        secure_storage.save_patient_data(patient_id, sample_biomarkers, sample_results)
        loaded = secure_storage.load_patient_data(patient_id)

        # Verify timestamp exists and is parseable
        assert 'timestamp' in loaded
        timestamp = loaded['timestamp']

        # Should be valid ISO 8601 format
        parsed = datetime.fromisoformat(timestamp)
        assert isinstance(parsed, datetime)

    def test_verify_data_integrity_method(self, secure_storage, sample_biomarkers, sample_results):
        """Test integrity verification detects valid data."""
        patient_id = 12345

        # Before saving - should return False
        assert secure_storage.verify_data_integrity(patient_id) is False

        # After saving - should return True
        secure_storage.save_patient_data(patient_id, sample_biomarkers, sample_results)
        assert secure_storage.verify_data_integrity(patient_id) is True


class TestExcelPersistence:
    """Test Excel file operations and persistence."""

    def test_excel_file_created(self, secure_storage, sample_biomarkers, sample_results):
        """Test Excel file created on first save."""
        excel_path = secure_storage.config.excel_path
        assert not excel_path.exists()

        # Save data
        secure_storage.save_patient_data(12345, sample_biomarkers, sample_results)

        # Verify file created
        assert excel_path.exists()
        assert excel_path.suffix == '.xlsx'

    def test_excel_has_correct_columns(self, secure_storage, sample_biomarkers, sample_results):
        """Test Excel file has required columns."""
        # Save data
        secure_storage.save_patient_data(12345, sample_biomarkers, sample_results)

        # Read Excel directly
        df = pd.read_excel(secure_storage.config.excel_path, engine='openpyxl')

        # Verify columns
        assert 'hashed_patient_id' in df.columns
        assert 'encrypted_data' in df.columns
        assert 'timestamp' in df.columns
        assert len(df.columns) == 3

    def test_excel_survives_reload(self, temp_storage_dir, temp_env_file,
                                   sample_biomarkers, sample_results):
        """Test data persists after reloading storage instance."""
        config = SecureStorageConfig(storage_dir=temp_storage_dir, env_file=temp_env_file)

        # First instance - save data
        storage1 = SecureStorage(config)
        storage1.save_patient_data(12345, sample_biomarkers, sample_results)

        # Second instance - load data
        storage2 = SecureStorage(config)
        loaded = storage2.load_patient_data(12345)

        # Verify data persisted
        assert loaded is not None
        assert loaded['patient_id'] == 12345


class TestErrorHandling:
    """Test edge cases and error conditions."""

    def test_missing_encryption_key_raises_error(self, temp_storage_dir):
        """Test missing .env key raises ValueError."""
        # Create empty .env
        env_path = temp_storage_dir / ".env"
        with open(env_path, 'w') as f:
            f.write("# Empty file\n")

        config = SecureStorageConfig(storage_dir=temp_storage_dir, env_file=env_path)

        with pytest.raises(ValueError, match="Encryption key not found"):
            SecureStorage(config)

    def test_invalid_patient_id_type(self, secure_storage, sample_biomarkers, sample_results):
        """Test non-integer patient_id raises TypeError."""
        with pytest.raises(TypeError):
            secure_storage.save_patient_data("12345", sample_biomarkers, sample_results)

        with pytest.raises(TypeError):
            secure_storage.save_patient_data(12345.5, sample_biomarkers, sample_results)

    def test_missing_storage_directory_created(self, temp_storage_dir, temp_env_file):
        """Test non-existent storage directory is created automatically."""
        nonexistent_dir = temp_storage_dir / "nonexistent"
        assert not nonexistent_dir.exists()

        config = SecureStorageConfig(storage_dir=nonexistent_dir, env_file=temp_env_file)
        storage = SecureStorage(config)

        # Directory should be created
        assert nonexistent_dir.exists()


class TestUtilityFunctions:
    """Test helper functions."""

    def test_setup_env_file_creates_file(self, temp_storage_dir):
        """Test setup_env_file creates .env with key."""
        env_path = temp_storage_dir / ".env"
        assert not env_path.exists()

        # Run setup
        setup_env_file(env_path)

        # Verify created
        assert env_path.exists()

        # Verify contains key
        content = env_path.read_text()
        assert "PHENOAGE_ENCRYPTION_KEY=" in content
        assert len(content) > 50

    def test_setup_env_file_skips_if_exists(self, temp_storage_dir):
        """Test setup_env_file doesn't overwrite existing file."""
        env_path = temp_storage_dir / ".env"

        # Create existing file
        existing_content = "EXISTING_KEY=test123\n"
        with open(env_path, 'w') as f:
            f.write(existing_content)

        # Run setup
        setup_env_file(env_path)

        # Verify not overwritten
        content = env_path.read_text()
        assert content == existing_content

    def test_list_all_records(self, secure_storage, sample_biomarkers, sample_results):
        """Test listing records returns metadata without decryption."""
        # Save 2 patients
        secure_storage.save_patient_data(10001, sample_biomarkers, sample_results)
        secure_storage.save_patient_data(10002, sample_biomarkers, sample_results)

        # List records
        records = secure_storage.list_all_records()

        # Verify count
        assert len(records) == 2

        # Verify structure (metadata only, no decryption)
        for record in records:
            assert 'hashed_patient_id' in record
            assert 'timestamp' in record
            assert len(record) == 2  # Only metadata
