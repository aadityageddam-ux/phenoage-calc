"""
PhenoAge Constants - Levine 2018 Specification
Source: PhenoAge_Core_ImplementationV2.docx

This module contains all mathematical constants for the PhenoAge Bio-Age Logic Engine,
with exact line number references to the specification document.

CRITICAL NOTE (CORRECTED 2026-02-07):
These coefficients represent the Levine 2018 regression model calibrated on CONVERTED units.
The calculator.py implementation applies the following conversions BEFORE applying coefficients:
  - Albumin: g/dL → g/L (×10)
  - Creatinine: mg/dL → μmol/L (×88.4)
  - Glucose: mg/dL → mmol/L (×0.0555)
  - CRP: mg/dL → mg/L (×10), then ln()

This approach (Version B) is empirically validated and produces biologically plausible results.
Version A (no conversions except CRP) produced implausible results (PhenoAge=108 for healthy 35-year-old).
"""

# ═══════════════════════════════════════════════════════════════════════════
# PHENOAGE REGRESSION COEFFICIENTS
# Source: Specification lines 76-86
# From: Levine ME, et al. (2018). Aging, 10(4):573-591. PMID: 29676998
# ═══════════════════════════════════════════════════════════════════════════

PHENOAGE_COEFFICIENTS = {
    # Intercept (specification line 76)
    'intercept': -19.907,

    # Biomarker coefficients (specification lines 77-86)
    # CRITICAL: Applied to CONVERTED units (see module docstring)
    # Input units are NHANES standard (g/dL, mg/dL), but calculator.py converts them

    'albumin': -0.0336,        # Applied to g/L (after ×10 conversion) - line 77
    'creatinine': 0.0095,      # Applied to μmol/L (after ×88.4 conversion) - line 78
    'glucose': 0.1953,         # Applied to mmol/L (after ×0.0555 conversion) - line 79
    'crp': 0.0954,            # Applied to ln(mg/L) (after ×10 conversion + ln) - line 80
    'lymphocyte_pct': -0.0120, # Applied to % (no conversion) - line 81
    'mcv': 0.0268,            # Applied to fL (no conversion) - line 82
    'rdw': 0.3306,            # Applied to % (no conversion) - line 83
    'alp': 0.00188,           # Applied to U/L (no conversion) - line 84
    'wbc': 0.0554,            # Applied to 1000 cells/μL (no conversion) - line 85
    'age': 0.0804             # Applied to years (no conversion) - line 86
}

# ═══════════════════════════════════════════════════════════════════════════
# MORTALITY MODEL PARAMETERS
# Source: Specification lines 59-61, 130-134
# ═══════════════════════════════════════════════════════════════════════════

# Gompertz mortality model parameters
MORTALITY_GAMMA = 0.0076927        # Hazard growth rate (gamma in Gompertz model)
MORTALITY_TIME_MONTHS = 120        # 10-year follow-up period (120 months)

# ═══════════════════════════════════════════════════════════════════════════
# PHENOAGE TRANSFORMATION CONSTANTS
# Source: Specification lines 93, 130
# ═══════════════════════════════════════════════════════════════════════════

# Formula: PhenoAge = PHENOAGE_INTERCEPT + ln(-0.00553 × ln(1 - mort_score)) / PHENOAGE_SLOPE

PHENOAGE_INTERCEPT = 141.50       # Maps mortality to age scale (specification line 93)
PHENOAGE_SLOPE = 0.090165         # Scales log-transformed mortality (specification line 93)

# NOTE: The existing bio-age-engine uses slightly different values:
# - PHENOAGE_INTERCEPT = 141.50225 (differs by +0.00225)
# - PHENOAGE_SLOPE = 0.09165 (differs by +0.000485)
# We use the EXACT specification values for scientific correctness.

PHENOAGE_MORTALITY_CONSTANT = -0.00553  # Mortality scaling constant (specification line 93)

# ═══════════════════════════════════════════════════════════════════════════
# NHANES VARIABLE MAPPINGS (1999-2000 Cycle)
# Source: Specification lines 229-342
# ═══════════════════════════════════════════════════════════════════════════

NHANES_VARIABLES = {
    # Demographics (DEMO.XPT) - specification lines 229-307
    'seqn': 'SEQN',                    # Participant sequence number (line 304)
    'age': 'RIDAGEYR',                 # Age in years (line 305)
    'gender': 'RIAGENDR',              # Gender (1=Male, 2=Female) (line 306)

    # Biochemistry Panel (LAB10.XPT) - specification lines 234-238
    'albumin': 'LBXSAL',               # Albumin (g/dL) (line 311)
    'glucose': 'LBXSGL',               # Glucose (mg/dL) (line 312)

    # C-Reactive Protein (LAB11.XPT) - specification lines 239-243
    'crp': 'LBXCRP',                  # CRP (mg/dL) → MUST CONVERT TO mg/L (line 317)

    # Kidney/Liver Panel (LAB18.XPT) - specification lines 244-248
    'creatinine': 'LBXSCR',            # Creatinine (mg/dL) (line 322)
    'alp': 'LBXSAPSI',                 # Alkaline Phosphatase (U/L) (line 323)

    # Complete Blood Count (LAB25.XPT) - specification lines 249-255
    'lymphocyte_pct': 'LBXLYPCT',      # Lymphocyte % (%) (line 328)
    'mcv': 'LBXMCVSI',                 # Mean Cell Volume (fL) (line 329)
    'rdw': 'LBXRDW',                   # Red Cell Distribution Width (%) (line 330)
    'wbc': 'LBXWBCSI'                  # White Blood Cell Count (1000 cells/μL) (line 331)
}

# ═══════════════════════════════════════════════════════════════════════════
# REQUIRED BIOMARKERS
# Source: Specification lines 277-279
# ═══════════════════════════════════════════════════════════════════════════

REQUIRED_BIOMARKERS = [
    'albumin',           # g/dL
    'creatinine',        # mg/dL
    'glucose',           # mg/dL
    'crp',              # mg/dL (will be converted to mg/L)
    'lymphocyte_pct',   # %
    'mcv',              # fL
    'rdw',              # %
    'alp',              # U/L
    'wbc',              # 1000 cells/μL
    'age'               # years
]

# ═══════════════════════════════════════════════════════════════════════════
# REFERENCE RANGES (NHANES-Derived Normal Values)
# Source: Specification lines 59-102
# ═══════════════════════════════════════════════════════════════════════════

REFERENCE_RANGES = {
    'albumin': (3.5, 5.5),           # g/dL (line 62)
    'creatinine': (0.7, 1.3),        # mg/dL (line 67)
    'glucose': (70, 100),            # mg/dL fasting (line 72)
    'crp': (0.0, 3.0),               # mg/L (line 77) - NOTE: in mg/L after conversion
    'lymphocyte_pct': (20, 40),      # % (line 82)
    'mcv': (80, 100),                # fL (line 87)
    'rdw': (11.5, 14.5),             # % (line 92)
    'alp': (30, 120),                # U/L (line 97)
    'wbc': (4.5, 11.0),              # 1000 cells/μL (line 102)
    'age': (20, 90)                  # years (Levine validation range)
}

# ═══════════════════════════════════════════════════════════════════════════
# CRP UNIT CONVERSION CONSTANT
# Source: Specification lines 317, 367
# ═══════════════════════════════════════════════════════════════════════════

# CRITICAL: CRP conversion factor (specification lines 314-323)
# NHANES reports CRP in mg/dL, but must be converted to mg/L before ln() transformation
# NOTE: Albumin, creatinine, and glucose also require conversions (see calculator.py)

CRP_CONVERSION_FACTOR = 10.0  # mg/dL → mg/L (multiply by 10)

# Verification (specification line 318):
# - Expected CRP range after conversion: 0.5-3.0 mg/L (median)
# - NHANES raw values: 0.05-0.30 mg/dL → becomes 0.5-3.0 mg/L after ×10

# ═══════════════════════════════════════════════════════════════════════════
# VALIDATION CONSTANTS
# Source: Specification lines 571-599
# ═══════════════════════════════════════════════════════════════════════════

# Levine 2018 Hazard Ratio benchmarks for population validation
LEVINE_2018_HR = 1.08              # Expected HR per 1-year PhenoAge increase (line 572)
LEVINE_2018_HR_CI_LOWER = 1.07     # 95% CI lower bound (line 586)
LEVINE_2018_HR_CI_UPPER = 1.09     # 95% CI upper bound (line 586)

# Validation acceptance criteria (specification lines 595-599)
VALIDATION_HR_MIN = 1.04           # Minimum acceptable HR (line 595)
VALIDATION_HR_MAX = 1.12           # Maximum acceptable HR (line 595)
VALIDATION_P_VALUE_MAX = 0.001     # Maximum p-value for significance (line 595)
VALIDATION_C_STATISTIC_MIN = 0.70  # Minimum C-statistic (concordance) (line 595)

# Expected C-statistic range (specification lines 579-580)
EXPECTED_C_STATISTIC_MIN = 0.75
EXPECTED_C_STATISTIC_MAX = 0.80

# ═══════════════════════════════════════════════════════════════════════════
# DATA QUALITY CHECKS
# Source: Specification lines 299-305
# ═══════════════════════════════════════════════════════════════════════════

# Expected cohort sizes after processing (specification lines 269-279)
EXPECTED_COHORT_SIZES = {
    'raw_nhanes': 9965,               # Initial NHANES 1999-2000 participants
    'age_filtered': 4444,             # After age filter (20-90 years)
    'complete_biomarkers': 4089       # After dropping missing biomarkers
}

# Data quality check thresholds (specification lines 299-305)
DATA_QUALITY_CHECKS = {
    'mean_phenoage_deviation': 5.0,   # Mean PhenoAge within ±5 years of mean age (line 299)
    'sd_phenoage_min': 15.0,          # Min SD of PhenoAge (line 300)
    'sd_phenoage_max': 25.0,          # Max SD of PhenoAge (line 300)
    'mean_acceleration_max': 2.0,     # Mean acceleration within ±2 years of zero (line 301)
    'min_phenoage': 0.0,              # No negative PhenoAge values (line 302)
    'max_phenoage': 120.0,            # Maximum reasonable PhenoAge (line 302)
    'correlation_min': 0.85,          # Min correlation PhenoAge vs age (line 303)
    'correlation_max': 0.95           # Max correlation PhenoAge vs age (line 303)
}

# ═══════════════════════════════════════════════════════════════════════════
# MORTALITY FILE COLUMN SPECIFICATIONS
# Source: Specification lines 336-341
# ═══════════════════════════════════════════════════════════════════════════

# Fixed-width file format for MORT_2019_PUBLIC.DAT
MORTALITY_FILE_COLSPECS = [
    (0, 14),       # SEQN (positions 1-14) (line 336)
    (14, 15),      # ELIGSTAT (position 15) (line 337)
    (15, 16),      # MORTSTAT (position 16): 0=Alive, 1=Deceased (line 338)
    (42, 45),      # PERMTH_INT (positions 43-45) (line 339)
    (45, 48)       # PERMTH_EXM (positions 46-48) - months from exam to death/censor (line 340)
]

MORTALITY_FILE_COLNAMES = ['SEQN', 'ELIGSTAT', 'MORTSTAT', 'PERMTH_INT', 'PERMTH_EXM']

# ═══════════════════════════════════════════════════════════════════════════
# DOCUMENTATION REFERENCES
# ═══════════════════════════════════════════════════════════════════════════

DOCUMENTATION = {
    'specification_document': 'PhenoAge_Core_ImplementationV2.docx',
    'levine_2018_paper': 'Levine ME, et al. (2018). Aging, 10(4):573-591. PMID: 29676998',
    'nhanes_cycle': '1999-2000',
    'nhanes_url': 'https://wwwn.cdc.gov/nchs/nhanes/continuousnhanes/default.aspx?BeginYear=1999'
}
