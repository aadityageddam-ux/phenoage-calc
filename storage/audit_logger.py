"""
HIPAA-compliant audit logger for PhenoAge patient data access.

Implements audit logging with strict PHI protection - logs only non-identifying metadata
for compliance with HIPAA audit requirements (45 CFR § 164.308, § 164.312).

CRITICAL PHI PROTECTION:
- ONLY logs: timestamp, hashed patient ID, chronological age, action type, user ID
- NEVER logs: biomarker values, phenoage results, delta_age, mort_score, or any clinical data

Key Features:
- CSV-based append-only audit log
- SHA-256 hashed patient IDs (consistent with SecureStorage)
- Strict PHI filtering
- Supports 3 action types: phenoage_calculation, data_access, data_deletion

Author: Claude Code
Date: 2026-02-07
Specification: spec_extract.txt lines 860-935
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any, Literal
from pathlib import Path
from datetime import datetime
import csv
import hashlib


# Type alias for action types (enforces valid values)
ActionType = Literal["phenoage_calculation", "data_access", "data_deletion"]


class AuditLoggerConfig:
    """
    Configuration for audit logger.

    Attributes:
        log_dir: Directory for audit log files (default: patient_data/)
        log_filename: Name of audit log CSV file (default: audit_log.csv)
    """

    def __init__(
        self,
        log_dir: Path = Path("patient_data"),
        log_filename: str = "audit_log.csv"
    ):
        self.log_dir = log_dir
        self.log_path = log_dir / log_filename


class AuditLogger:
    """
    HIPAA-compliant audit logger with strict PHI protection.

    Logs patient data access events for HIPAA compliance without storing
    Protected Health Information (PHI) in the audit log.

    PHI Protection Rules:
    - ✓ ALLOWED: timestamp, hashed patient ID, chronological age (demographic), action, user ID
    - ✗ FORBIDDEN: biomarker values, phenoage, delta_age, mort_score, lab results

    Example:
        >>> audit = AuditLogger()
        >>> audit.log_calculation(patient_id=12345, chronological_age=50.0)
        >>> audit.log_data_access(patient_id=12345, age=50.0, user_id="dr_smith")
        >>> entries = audit.get_recent_entries(limit=10)
    """

    # CSV column headers
    _CSV_HEADERS = ['timestamp', 'hashed_patient_id', 'age', 'action', 'user_id']

    def __init__(self, config: Optional[AuditLoggerConfig] = None):
        """
        Initialize audit logger with configuration.

        Args:
            config: Audit logger configuration (uses defaults if None)
        """
        self.config = config if config is not None else AuditLoggerConfig()

        # Ensure log directory exists
        self.config.log_dir.mkdir(parents=True, exist_ok=True)

        # Initialize log file if needed
        self._initialize_log_file()

    def _initialize_log_file(self) -> None:
        """
        Create CSV log file with headers if it doesn't exist.
        """
        if not self.config.log_path.exists():
            with open(self.config.log_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self._CSV_HEADERS)
                writer.writeheader()

    def _hash_patient_id(self, patient_id: int) -> str:
        """
        Generate SHA-256 hash of patient ID (consistent with SecureStorage).

        Args:
            patient_id: Patient identifier

        Returns:
            64-character hexadecimal hash string
        """
        id_bytes = str(patient_id).encode('utf-8')
        hash_obj = hashlib.sha256(id_bytes)
        return hash_obj.hexdigest()

    def _write_entry(
        self,
        timestamp: str,
        hashed_patient_id: str,
        age: float,
        action: ActionType,
        user_id: Optional[str]
    ) -> None:
        """
        Write audit entry to CSV file (internal method).

        Args:
            timestamp: ISO 8601 timestamp
            hashed_patient_id: SHA-256 hash of patient ID
            age: Chronological age (years)
            action: Action type (phenoage_calculation, data_access, data_deletion)
            user_id: Optional user identifier
        """
        with open(self.config.log_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self._CSV_HEADERS)
            writer.writerow({
                'timestamp': timestamp,
                'hashed_patient_id': hashed_patient_id,
                'age': age,
                'action': action,
                'user_id': user_id if user_id else ''
            })

    def log_calculation(
        self,
        patient_id: int,
        chronological_age: float,
        user_id: Optional[str] = None
    ) -> None:
        """
        Log a PhenoAge calculation event.

        Records when PhenoAge is calculated for a patient (action="phenoage_calculation").

        PHI Protection: Only logs chronological age (demographic), NOT phenoage result,
        NOT biomarker values, NOT delta_age, NOT mort_score.

        Args:
            patient_id: Patient identifier
            chronological_age: Patient's chronological age in years (demographic, not PHI)
            user_id: Optional identifier of user who performed calculation

        Example:
            >>> audit.log_calculation(patient_id=12345, chronological_age=50.0)
        """
        timestamp = datetime.now().isoformat()
        hashed_id = self._hash_patient_id(patient_id)

        self._write_entry(
            timestamp=timestamp,
            hashed_patient_id=hashed_id,
            age=chronological_age,
            action="phenoage_calculation",
            user_id=user_id
        )

    def log_data_access(
        self,
        patient_id: int,
        age: float,
        user_id: Optional[str] = None
    ) -> None:
        """
        Log patient data access event.

        Records when patient history is loaded (action="data_access").

        Args:
            patient_id: Patient identifier
            age: Patient's chronological age in years
            user_id: Optional identifier of user who accessed data

        Example:
            >>> audit.log_data_access(patient_id=12345, age=50.0, user_id="dr_smith")
        """
        timestamp = datetime.now().isoformat()
        hashed_id = self._hash_patient_id(patient_id)

        self._write_entry(
            timestamp=timestamp,
            hashed_patient_id=hashed_id,
            age=age,
            action="data_access",
            user_id=user_id
        )

    def log_deletion(
        self,
        patient_id: int,
        age: float,
        user_id: Optional[str] = None
    ) -> None:
        """
        Log patient data deletion event.

        Records when patient data is deleted (action="data_deletion").
        Implements audit trail for patient right to deletion (HIPAA § 164.526).

        Args:
            patient_id: Patient identifier
            age: Patient's chronological age in years
            user_id: Optional identifier of user who deleted data

        Example:
            >>> audit.log_deletion(patient_id=12345, age=50.0, user_id="admin")
        """
        timestamp = datetime.now().isoformat()
        hashed_id = self._hash_patient_id(patient_id)

        self._write_entry(
            timestamp=timestamp,
            hashed_patient_id=hashed_id,
            age=age,
            action="data_deletion",
            user_id=user_id
        )

    def get_recent_entries(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieve recent audit entries.

        Args:
            limit: Maximum number of entries to return (default: 100)

        Returns:
            List of dictionaries with keys: timestamp, hashed_patient_id, age, action, user_id
            Ordered by timestamp (most recent last)

        Example:
            >>> entries = audit.get_recent_entries(limit=10)
            >>> for entry in entries:
            ...     print(f"{entry['timestamp']}: {entry['action']}")
        """
        if not self.config.log_path.exists():
            return []

        entries = []
        with open(self.config.log_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                entries.append(row)

        # Return last N entries
        return entries[-limit:] if len(entries) > limit else entries

    def get_entries_for_patient(self, patient_id: int) -> List[Dict[str, Any]]:
        """
        Get all audit entries for a specific patient.

        Retrieves all logged events for a patient (by hashed ID).

        Args:
            patient_id: Patient identifier

        Returns:
            List of audit entries for this patient, ordered by timestamp

        Example:
            >>> entries = audit.get_entries_for_patient(12345)
            >>> print(f"Patient has {len(entries)} logged events")
        """
        if not self.config.log_path.exists():
            return []

        # Hash patient ID for lookup
        hashed_id = self._hash_patient_id(patient_id)

        # Filter entries
        matching_entries = []
        with open(self.config.log_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['hashed_patient_id'] == hashed_id:
                    matching_entries.append(row)

        return matching_entries

    def verify_no_phi_leakage(self) -> bool:
        """
        Verify audit log contains no Protected Health Information (PHI).

        Checks that audit log only contains allowed fields and no sensitive data.
        This is a safety check for HIPAA compliance.

        Returns:
            True if audit log is clean (no PHI detected)
            False if potential PHI detected

        Checks performed:
        - Column names match expected headers
        - No unexpected columns that might contain PHI
        - File exists and is readable

        Example:
            >>> is_clean = audit.verify_no_phi_leakage()
            >>> assert is_clean, "PHI detected in audit log!"
        """
        if not self.config.log_path.exists():
            return True  # Empty log is clean

        try:
            with open(self.config.log_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                # Check column headers
                if reader.fieldnames is None:
                    return False

                # Verify only expected columns exist
                expected_cols = set(self._CSV_HEADERS)
                actual_cols = set(reader.fieldnames)

                if actual_cols != expected_cols:
                    print(f"Warning: Unexpected columns in audit log: {actual_cols - expected_cols}")
                    return False

            return True

        except Exception as e:
            print(f"Error verifying audit log: {e}")
            return False
