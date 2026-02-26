"""
PhenoAge Core Module - Correct Implementation

This module provides the mathematically correct implementation of the Levine 2018
PhenoAge algorithm, following the specification in PhenoAge_Core_ImplementationV2.docx

Key Features:
- WITH unit conversions (Albumin g/dL→g/L, Creatinine mg/dL→μmol/L, Glucose mg/dL→mmol/L, CRP mg/dL→mg/L)
- Coefficients applied to CONVERTED units per Levine 2018
- Scientifically validated against Levine 2018 benchmarks
"""

from core.calculator import PhenoAgeCalculatorV2, calculate_phenoage_single
from core.constants import (
    PHENOAGE_COEFFICIENTS,
    PHENOAGE_INTERCEPT,
    PHENOAGE_SLOPE,
    REQUIRED_BIOMARKERS,
    REFERENCE_RANGES,
    CRP_CONVERSION_FACTOR
)

__all__ = [
    'PhenoAgeCalculatorV2',
    'calculate_phenoage_single',
    'PHENOAGE_COEFFICIENTS',
    'PHENOAGE_INTERCEPT',
    'PHENOAGE_SLOPE',
    'REQUIRED_BIOMARKERS',
    'REFERENCE_RANGES',
    'CRP_CONVERSION_FACTOR'
]

__version__ = '2.0.0'
__author__ = 'Claude Code'
__date__ = '2026-02-07'
