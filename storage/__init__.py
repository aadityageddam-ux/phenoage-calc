"""
Secure storage module for PhenoAge patient data.

Provides HIPAA-compliant encrypted storage and audit logging for clinical patient data.

Key Components:
- SecureStorage: AES-256 encrypted patient data storage with Excel backend
- AuditLogger: PHI-protected audit logging for HIPAA compliance
- Utility functions: Encryption key generation and environment setup

Usage:
    >>> from storage import SecureStorage, AuditLogger
    >>> storage = SecureStorage()
    >>> audit = AuditLogger()
    >>>
    >>> # Save patient data
    >>> hashed_id = storage.save_patient_data(12345, biomarkers, results)
    >>> audit.log_calculation(12345, chronological_age=50.0)
    >>>
    >>> # Load patient data
    >>> data = storage.load_patient_data(12345)
    >>> audit.log_data_access(12345, age=50.0)

Author: Claude Code
Date: 2026-02-07
"""

from storage.secure_storage import (
    SecureStorage,
    SecureStorageConfig,
    generate_encryption_key,
    setup_env_file
)

from storage.audit_logger import (
    AuditLogger,
    AuditLoggerConfig,
    ActionType
)

__all__ = [
    # Core classes
    "SecureStorage",
    "SecureStorageConfig",
    "AuditLogger",
    "AuditLoggerConfig",
    # Types
    "ActionType",
    # Utility functions
    "generate_encryption_key",
    "setup_env_file"
]

__version__ = "2.0.0"
__author__ = "Claude Code"
