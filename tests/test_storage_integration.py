"""
Integration tests for secure storage + audit logger combined workflows.

Tests the complete patient data lifecycle and verifies that storage operations
correctly coordinate with audit logging.

Test Classes:
- TestPatientLifecycle: Full save → load → delete workflows
- TestStorageAuditCoordination: Verify audit log matches storage operations
- TestCalculatorIntegration: Integration with PhenoAge calculator

Author: Claude Code
Date: 2026-02-07
"""

import pytest
import tempfile
from pathlib import Path

from storage import (
    SecureStorage,
    SecureStorageConfig,
    AuditLogger,
    AuditLoggerConfig,
    generate_encryption_key
)


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def temp_dir():
    """Create temporary directory for all storage files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_env_file(temp_dir):
    """Create temporary .env file with valid encryption key."""
    env_path = temp_dir / ".env"
    key = generate_encryption_key()
    with open(env_path, 'w') as f:
        f.write(f"PHENOAGE_ENCRYPTION_KEY={key}\n")
    return env_path


@pytest.fixture
def storage(temp_dir, temp_env_file):
    """SecureStorage instance."""
    config = SecureStorageConfig(storage_dir=temp_dir, env_file=temp_env_file)
    return SecureStorage(config)


@pytest.fixture
def audit(temp_dir):
    """AuditLogger instance in same directory."""
    config = AuditLoggerConfig(log_dir=temp_dir)
    return AuditLogger(config)


@pytest.fixture
def sample_biomarkers():
    """Standard test biomarkers."""
    return {
        'albumin': 4.5,
        'creatinine': 0.9,
        'glucose': 95.0,
        'crp': 0.1,
        'lymphocyte_pct': 30.0,
        'mcv': 90.0,
        'rdw': 13.0,
        'alp': 65.0,
        'wbc': 6.5,
        'age': 50.0
    }


@pytest.fixture
def sample_results():
    """Standard test results."""
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

class TestPatientLifecycle:
    """Full patient data lifecycle tests."""

    def test_complete_save_load_cycle(self, storage, audit, sample_biomarkers, sample_results):
        """Test complete save → log → load → log cycle."""
        patient_id = 12345
        age = sample_biomarkers['age']

        # STEP 1: Calculate and save
        hashed_id = storage.save_patient_data(patient_id, sample_biomarkers, sample_results)
        audit.log_calculation(patient_id, age)

        # STEP 2: Load and access
        loaded = storage.load_patient_data(patient_id)
        audit.log_data_access(patient_id, age)

        # STEP 3: Verify data integrity
        assert loaded is not None
        assert loaded['patient_id'] == patient_id
        assert loaded['input_biomarkers'] == sample_biomarkers
        assert loaded['calculation_results'] == sample_results

        # STEP 4: Verify audit has 2 entries
        entries = audit.get_entries_for_patient(patient_id)
        assert len(entries) == 2
        assert entries[0]['action'] == 'phenoage_calculation'
        assert entries[1]['action'] == 'data_access'

    def test_complete_delete_cycle(self, storage, audit, sample_biomarkers, sample_results):
        """Test save → delete lifecycle with audit trail."""
        patient_id = 12345
        age = sample_biomarkers['age']

        # Save
        storage.save_patient_data(patient_id, sample_biomarkers, sample_results)
        audit.log_calculation(patient_id, age)

        # Delete
        deleted = storage.delete_patient_data(patient_id)
        audit.log_deletion(patient_id, age)

        # Verify deleted
        assert deleted is True
        assert storage.load_patient_data(patient_id) is None

        # Verify audit has deletion entry
        entries = audit.get_entries_for_patient(patient_id)
        assert len(entries) == 2
        assert entries[-1]['action'] == 'data_deletion'

    def test_full_lifecycle(self, storage, audit, sample_biomarkers, sample_results):
        """Test full lifecycle: save → load → delete → verify."""
        patient_id = 12345
        age = sample_biomarkers['age']

        # Save patient
        hashed_id = storage.save_patient_data(patient_id, sample_biomarkers, sample_results)
        audit.log_calculation(patient_id, age)

        # Load patient
        data = storage.load_patient_data(patient_id)
        audit.log_data_access(patient_id, age)

        # Verify loaded
        assert data is not None
        assert data['calculation_results']['phenoage'] == 47.3

        # Delete patient
        storage.delete_patient_data(patient_id)
        audit.log_deletion(patient_id, age)

        # Verify deleted
        assert storage.load_patient_data(patient_id) is None

        # Verify audit trail has 3 entries
        entries = audit.get_entries_for_patient(patient_id)
        assert len(entries) == 3
        actions = [e['action'] for e in entries]
        assert actions == ['phenoage_calculation', 'data_access', 'data_deletion']

    def test_multiple_patients_lifecycle(self, storage, audit, sample_biomarkers, sample_results):
        """Test lifecycle with multiple patients."""
        patients = [10001, 10002, 10003]

        # Save all patients
        for patient_id in patients:
            storage.save_patient_data(patient_id, sample_biomarkers, sample_results)
            audit.log_calculation(patient_id, sample_biomarkers['age'])

        # Verify all stored
        records = storage.list_all_records()
        assert len(records) == 3

        # Load and verify each patient
        for patient_id in patients:
            data = storage.load_patient_data(patient_id)
            audit.log_data_access(patient_id, sample_biomarkers['age'])
            assert data is not None
            assert data['patient_id'] == patient_id

        # Delete one patient
        storage.delete_patient_data(10002)
        audit.log_deletion(10002, sample_biomarkers['age'])

        # Verify only 2 remain
        records = storage.list_all_records()
        assert len(records) == 2

        # Verify deleted patient gone, others still present
        assert storage.load_patient_data(10001) is not None
        assert storage.load_patient_data(10002) is None
        assert storage.load_patient_data(10003) is not None


class TestStorageAuditCoordination:
    """Verify audit log accurately reflects storage operations."""

    def test_audit_hashes_match_storage_hashes(self, storage, audit, sample_biomarkers, sample_results):
        """Verify SHA-256 hashes are consistent between storage and audit."""
        patient_id = 12345
        age = 50.0

        # Storage operation
        hashed_from_storage = storage.save_patient_data(patient_id, sample_biomarkers, sample_results)

        # Audit operation
        audit.log_calculation(patient_id, age)

        # Get hashed ID from audit
        entries = audit.get_entries_for_patient(patient_id)
        hashed_from_audit = entries[0]['hashed_patient_id']

        # Both should produce the same SHA-256 hash
        assert hashed_from_storage == hashed_from_audit

    def test_audit_records_correct_age(self, storage, audit, sample_biomarkers, sample_results):
        """Verify audit correctly records chronological age (not phenoage)."""
        patient_id = 12345
        chronological_age = 50.0
        phenoage = 47.3  # Should NOT be logged

        storage.save_patient_data(patient_id, sample_biomarkers, sample_results)
        audit.log_calculation(patient_id, chronological_age)

        entries = audit.get_entries_for_patient(patient_id)
        logged_age = float(entries[0]['age'])

        assert logged_age == chronological_age
        assert logged_age != phenoage

    def test_storage_operations_have_audit_trail(self, storage, audit,
                                                  sample_biomarkers, sample_results):
        """Test that all storage operations have corresponding audit entries."""
        patient_id = 12345
        age = 50.0

        # SAVE - should have calculation log
        storage.save_patient_data(patient_id, sample_biomarkers, sample_results)
        audit.log_calculation(patient_id, age)

        # LOAD - should have access log
        storage.load_patient_data(patient_id)
        audit.log_data_access(patient_id, age)

        # DELETE - should have deletion log
        storage.delete_patient_data(patient_id)
        audit.log_deletion(patient_id, age)

        # Verify audit trail is complete
        all_entries = audit.get_entries_for_patient(patient_id)
        assert len(all_entries) == 3

        # Verify no PHI in audit
        assert audit.verify_no_phi_leakage() is True


class TestCalculatorIntegration:
    """Test integration with PhenoAge calculator."""

    def test_calculator_output_storable(self, storage, audit, sample_biomarkers):
        """Test that calculator output can be directly stored."""
        # Import and use the actual calculator
        from core.calculator import calculate_phenoage_single

        patient_id = 99001

        # Calculate PhenoAge
        results = calculate_phenoage_single(
            albumin=sample_biomarkers['albumin'],
            creatinine=sample_biomarkers['creatinine'],
            glucose=sample_biomarkers['glucose'],
            crp=sample_biomarkers['crp'],
            lymphocyte_pct=sample_biomarkers['lymphocyte_pct'],
            mcv=sample_biomarkers['mcv'],
            rdw=sample_biomarkers['rdw'],
            alp=sample_biomarkers['alp'],
            wbc=sample_biomarkers['wbc'],
            age=sample_biomarkers['age']
        )

        # Save to storage
        hashed_id = storage.save_patient_data(patient_id, sample_biomarkers, results)
        audit.log_calculation(patient_id, sample_biomarkers['age'])

        # Load back
        loaded = storage.load_patient_data(patient_id)
        audit.log_data_access(patient_id, sample_biomarkers['age'])

        # Verify results match
        assert loaded is not None
        assert loaded['calculation_results']['phenoage'] == results['phenoage']
        assert loaded['calculation_results']['delta_age'] == results['delta_age']
        assert loaded['calculation_results']['mort_score'] == results['mort_score']

        # Verify biomarkers preserved
        assert loaded['input_biomarkers'] == sample_biomarkers

        # Verify audit trail
        assert audit.verify_no_phi_leakage() is True
        entries = audit.get_entries_for_patient(patient_id)
        assert len(entries) == 2

    def test_calculated_phenoage_is_biologically_plausible(self, storage, sample_biomarkers):
        """Test that stored PhenoAge values are biologically plausible."""
        from core.calculator import calculate_phenoage_single

        patient_id = 99002

        results = calculate_phenoage_single(
            albumin=sample_biomarkers['albumin'],
            creatinine=sample_biomarkers['creatinine'],
            glucose=sample_biomarkers['glucose'],
            crp=sample_biomarkers['crp'],
            lymphocyte_pct=sample_biomarkers['lymphocyte_pct'],
            mcv=sample_biomarkers['mcv'],
            rdw=sample_biomarkers['rdw'],
            alp=sample_biomarkers['alp'],
            wbc=sample_biomarkers['wbc'],
            age=sample_biomarkers['age']
        )

        # Store and retrieve
        storage.save_patient_data(patient_id, sample_biomarkers, results)
        loaded = storage.load_patient_data(patient_id)

        phenoage = loaded['calculation_results']['phenoage']

        # Biologically plausible range: 0-120 years
        assert 0 < phenoage < 120

        # Should be reasonably close to chronological age
        chron_age = loaded['input_biomarkers']['age']
        assert abs(phenoage - chron_age) < 30  # Within 30 years
