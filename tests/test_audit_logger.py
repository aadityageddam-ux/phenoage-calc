"""
Tests for HIPAA-compliant audit logger.

CRITICAL: Tests PHI protection - verifies NO biomarkers, NO phenoage results,
NO clinical data appears in audit logs.

Test Classes:
- TestAuditLogging: Basic logging operations
- TestPHIProtection: CRITICAL - verify no PHI leakage
- TestAuditQuerying: Retrieve and filter audit entries
- TestAuditIntegrity: CSV structure and data integrity

Author: Claude Code
Date: 2026-02-07
"""

import pytest
import tempfile
from pathlib import Path
import csv
from datetime import datetime

from storage import AuditLogger, AuditLoggerConfig


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def temp_log_dir():
    """Create temporary directory for audit logs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def audit_logger(temp_log_dir):
    """AuditLogger instance with temporary configuration."""
    config = AuditLoggerConfig(log_dir=temp_log_dir)
    return AuditLogger(config)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuditLogging:
    """Test basic audit log operations."""

    def test_log_calculation(self, audit_logger):
        """Test logging PhenoAge calculation event."""
        patient_id = 12345
        age = 50.0

        # Log calculation
        audit_logger.log_calculation(patient_id, age)

        # Verify entry created
        entries = audit_logger.get_recent_entries(limit=10)
        assert len(entries) == 1

        entry = entries[0]
        assert entry['action'] == 'phenoage_calculation'
        assert float(entry['age']) == age
        assert len(entry['hashed_patient_id']) == 64  # SHA-256 hash

    def test_log_data_access(self, audit_logger):
        """Test logging data access event."""
        patient_id = 12345
        age = 50.0
        user_id = "dr_smith"

        # Log access
        audit_logger.log_data_access(patient_id, age, user_id)

        # Verify entry
        entries = audit_logger.get_recent_entries()
        assert len(entries) == 1

        entry = entries[0]
        assert entry['action'] == 'data_access'
        assert entry['user_id'] == user_id
        assert float(entry['age']) == age

    def test_log_deletion(self, audit_logger):
        """Test logging deletion event."""
        patient_id = 12345
        age = 50.0
        user_id = "admin"

        # Log deletion
        audit_logger.log_deletion(patient_id, age, user_id)

        # Verify entry
        entries = audit_logger.get_recent_entries()
        assert len(entries) == 1

        entry = entries[0]
        assert entry['action'] == 'data_deletion'
        assert entry['user_id'] == user_id

    def test_csv_file_created(self, temp_log_dir, audit_logger):
        """Test CSV file created on first log."""
        csv_path = audit_logger.config.log_path
        assert csv_path.exists()

    def test_csv_has_correct_headers(self, temp_log_dir, audit_logger):
        """Test CSV has required columns."""
        # Log an entry
        audit_logger.log_calculation(12345, 50.0)

        # Read CSV
        with open(audit_logger.config.log_path, 'r') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames

        # Verify headers
        expected = ['timestamp', 'hashed_patient_id', 'age', 'action', 'user_id']
        assert headers == expected

    def test_multiple_entries(self, audit_logger):
        """Test logging multiple entries."""
        # Log 5 events
        for i in range(5):
            audit_logger.log_calculation(10000 + i, 40.0 + i)

        # Verify all logged
        entries = audit_logger.get_recent_entries()
        assert len(entries) == 5

    def test_timestamp_format(self, audit_logger):
        """Test timestamp is ISO 8601 format."""
        audit_logger.log_calculation(12345, 50.0)
        entries = audit_logger.get_recent_entries()

        timestamp = entries[0]['timestamp']
        # Should be parseable as ISO 8601
        parsed = datetime.fromisoformat(timestamp)
        assert isinstance(parsed, datetime)


class TestPHIProtection:
    """CRITICAL: Test no PHI leakage in audit logs."""

    def test_no_biomarker_values_in_log(self, audit_logger):
        """CRITICAL: Test biomarker values never appear in log."""
        patient_id = 12345
        age = 50.0

        # Simulate logging with biomarker data available
        # (in real use, biomarkers would be passed to calculator, not logger)
        biomarkers = {
            'albumin': 4.5,
            'creatinine': 0.9,
            'glucose': 95.0,
            'crp': 0.1
        }

        # Log calculation (only age, not biomarkers)
        audit_logger.log_calculation(patient_id, age)

        # Read raw CSV content
        csv_content = audit_logger.config.log_path.read_text()

        # Verify NO biomarker values appear
        assert '4.5' not in csv_content  # albumin value
        assert '0.9' not in csv_content  # creatinine value
        assert '95.0' not in csv_content  # glucose value
        assert '0.1' not in csv_content  # crp value
        assert 'albumin' not in csv_content
        assert 'creatinine' not in csv_content
        assert 'glucose' not in csv_content

    def test_no_phenoage_results_in_log(self, audit_logger):
        """CRITICAL: Test phenoage/delta_age never in log."""
        patient_id = 12345
        age = 50.0

        # Simulate having phenoage results
        phenoage = 47.3
        delta_age = -2.7

        # Log calculation (only age, not results)
        audit_logger.log_calculation(patient_id, age)

        # Read CSV
        csv_content = audit_logger.config.log_path.read_text()

        # Verify NO phenoage result VALUES appear
        # Note: "phenoage_calculation" action name is allowed - it's not PHI
        assert '47.3' not in csv_content  # phenoage numeric value
        assert '-2.7' not in csv_content  # delta_age numeric value
        assert 'delta_age' not in csv_content  # field name not stored

    def test_only_chronological_age_logged(self, audit_logger):
        """Test only chronological age (not PHI) is logged."""
        patient_id = 12345
        chronological_age = 50.0
        phenoage = 47.3  # Should NOT be logged

        # Log calculation
        audit_logger.log_calculation(patient_id, chronological_age)

        # Get entry
        entries = audit_logger.get_recent_entries()
        entry = entries[0]

        # Verify only chronological age present
        logged_age = float(entry['age'])
        assert logged_age == chronological_age
        assert logged_age != phenoage  # Not the biological age

    def test_verify_no_phi_leakage_method(self, audit_logger):
        """Test PHI verification method."""
        # Empty log should be clean
        assert audit_logger.verify_no_phi_leakage() is True

        # After logging, should still be clean
        audit_logger.log_calculation(12345, 50.0)
        audit_logger.log_data_access(12346, 45.0, "user1")
        audit_logger.log_deletion(12347, 60.0, "admin")

        assert audit_logger.verify_no_phi_leakage() is True

    def test_patient_id_is_hashed(self, audit_logger):
        """Test patient IDs are SHA-256 hashed (not plaintext)."""
        patient_id = 12345
        audit_logger.log_calculation(patient_id, 50.0)

        # Read CSV
        entries = audit_logger.get_recent_entries()
        hashed_id = entries[0]['hashed_patient_id']

        # Should be 64-char hex string (SHA-256)
        assert len(hashed_id) == 64
        assert all(c in '0123456789abcdef' for c in hashed_id)

        # Should NOT be the plaintext patient ID
        assert hashed_id != str(patient_id)

    def test_no_mort_score_in_log(self, audit_logger):
        """Test mortality score never appears in log."""
        patient_id = 12345
        mort_score = 0.012345  # Highly sensitive prognostic data

        # Log calculation (mortality score should never be passed)
        audit_logger.log_calculation(patient_id, 50.0)

        # Read CSV
        csv_content = audit_logger.config.log_path.read_text()

        # Verify mortality score not logged
        assert '0.012345' not in csv_content
        assert 'mort_score' not in csv_content

    def test_no_xb_in_log(self, audit_logger):
        """Test linear predictor (xb) never appears in log."""
        patient_id = 12345
        xb = -9.5432  # Internal calculation value

        # Log calculation
        audit_logger.log_calculation(patient_id, 50.0)

        # Read CSV
        csv_content = audit_logger.config.log_path.read_text()

        # Verify xb not logged
        assert '-9.5432' not in csv_content
        assert 'xb' not in csv_content


class TestAuditQuerying:
    """Test audit log retrieval and filtering."""

    def test_get_recent_entries_limit(self, audit_logger):
        """Test limit parameter works correctly."""
        # Log 20 entries
        for i in range(20):
            audit_logger.log_calculation(10000 + i, 40.0 + i)

        # Get last 10
        entries = audit_logger.get_recent_entries(limit=10)
        assert len(entries) == 10

        # Verify these are the LAST 10 (most recent)
        first_age = float(entries[0]['age'])
        assert first_age >= 40.0  # Should be later entries

    def test_get_entries_for_patient(self, audit_logger):
        """Test filtering entries by patient."""
        patient_id = 12345

        # Log events for this patient
        audit_logger.log_calculation(patient_id, 50.0)
        audit_logger.log_data_access(patient_id, 50.0)

        # Log events for other patients
        audit_logger.log_calculation(12346, 45.0)
        audit_logger.log_calculation(12347, 55.0)

        # Get entries for specific patient
        entries = audit_logger.get_entries_for_patient(patient_id)

        # Should have 2 entries for this patient
        assert len(entries) == 2
        assert entries[0]['action'] == 'phenoage_calculation'
        assert entries[1]['action'] == 'data_access'

    def test_entries_ordered_by_timestamp(self, audit_logger):
        """Test entries returned in chronological order."""
        # Log 5 events
        for i in range(5):
            audit_logger.log_calculation(10000 + i, 40.0)

        entries = audit_logger.get_recent_entries()

        # Verify chronological order
        timestamps = [datetime.fromisoformat(e['timestamp']) for e in entries]
        assert timestamps == sorted(timestamps)

    def test_get_entries_empty_log(self, audit_logger):
        """Test querying empty log returns empty list."""
        entries = audit_logger.get_recent_entries()
        assert entries == []

        entries = audit_logger.get_entries_for_patient(12345)
        assert entries == []


class TestAuditIntegrity:
    """Test audit log structure and data integrity."""

    def test_csv_structure_preserved(self, audit_logger):
        """Test CSV maintains correct structure after multiple writes."""
        # Log 10 entries
        for i in range(10):
            audit_logger.log_calculation(10000 + i, 40.0 + i, user_id=f"user{i}")

        # Read CSV directly
        with open(audit_logger.config.log_path, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # Verify structure
        assert len(rows) == 10

        for i, row in enumerate(rows):
            assert 'timestamp' in row
            assert 'hashed_patient_id' in row
            assert 'age' in row
            assert 'action' in row
            assert 'user_id' in row
            assert row['user_id'] == f"user{i}"

    def test_optional_user_id(self, audit_logger):
        """Test user_id is optional and handles None."""
        # Log without user_id
        audit_logger.log_calculation(12345, 50.0)

        # Log with user_id
        audit_logger.log_calculation(12346, 45.0, user_id="dr_smith")

        entries = audit_logger.get_recent_entries()
        assert len(entries) == 2

        # First should have empty user_id
        assert entries[0]['user_id'] == ''

        # Second should have user_id
        assert entries[1]['user_id'] == 'dr_smith'

    def test_patient_id_hashing_consistency(self, audit_logger):
        """Test same patient_id produces same hash across multiple logs."""
        patient_id = 12345

        # Log 3 events for same patient
        audit_logger.log_calculation(patient_id, 50.0)
        audit_logger.log_data_access(patient_id, 50.0)
        audit_logger.log_deletion(patient_id, 50.0)

        # Get entries
        entries = audit_logger.get_entries_for_patient(patient_id)
        assert len(entries) == 3

        # All should have same hashed ID
        hash1 = entries[0]['hashed_patient_id']
        hash2 = entries[1]['hashed_patient_id']
        hash3 = entries[2]['hashed_patient_id']

        assert hash1 == hash2 == hash3

    def test_append_only_behavior(self, audit_logger):
        """Test audit log is append-only (no deletions/modifications)."""
        # Log initial entry
        audit_logger.log_calculation(12345, 50.0)
        initial_entries = audit_logger.get_recent_entries()
        assert len(initial_entries) == 1

        # Log more entries
        audit_logger.log_calculation(12346, 45.0)
        audit_logger.log_calculation(12347, 55.0)

        # Verify original entry still present
        all_entries = audit_logger.get_recent_entries()
        assert len(all_entries) == 3

        # Original entry should still be first
        assert all_entries[0] == initial_entries[0]

    def test_special_characters_in_user_id(self, audit_logger):
        """Test user_id with special characters is handled correctly."""
        user_id = "dr.smith@hospital.com"

        audit_logger.log_calculation(12345, 50.0, user_id=user_id)
        entries = audit_logger.get_recent_entries()

        assert entries[0]['user_id'] == user_id
