"""
NHANES Data Loader - 1999-2000 Cycle
Loads and merges raw NHANES XPT files for PhenoAge calculation

File Requirements:
- DEMO.XPT: Demographics (SEQN, RIDAGEYR, RIAGENDR)
- LAB10.XPT: Biochemistry - Albumin, Glucose
- LAB11.XPT: C-Reactive Protein
- LAB18.XPT: Kidney/Liver - Creatinine, Alkaline Phosphatase
- LAB25.XPT: Complete Blood Count - Lymphocyte%, MCV, RDW, WBC

Author: Claude Code
Date: 2026-02-07
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional
from core.constants import NHANES_VARIABLES, REQUIRED_BIOMARKERS, EXPECTED_COHORT_SIZES


class NHANESLoaderV2:
    """
    Load and merge NHANES 1999-2000 raw data files.

    Implements specification lines 229-342: NHANES Data Pipeline
    """

    def __init__(self, data_dir: str = "../bio-age-engine/data/raw/1999-2000"):
        """
        Initialize loader with path to NHANES raw data directory.

        Args:
            data_dir: Path to directory containing NHANES XPT files
        """
        self.data_dir = Path(data_dir)

        # Define file paths
        # NOTE: In NHANES 1999-2000, albumin (LBXSAL), glucose (LBXSGL),
        # creatinine (LBXSCR), and ALP (LBXSAPSI) are all in LAB18.xpt
        # (Standard Biochemistry Profile). LAB10.xpt is not required.
        self.files = {
            'demographics': self.data_dir / 'DEMO.xpt',
            'biochemistry': self.data_dir / 'LAB18.xpt',     # Albumin, Glucose, Creatinine, ALP
            'crp': self.data_dir / 'LAB11.xpt',              # C-Reactive Protein
            'cbc': self.data_dir / 'LAB25.xpt'               # WBC, Lymph%, MCV, RDW
        }

        # Verify files exist
        missing_files = [name for name, path in self.files.items() if not path.exists()]
        if missing_files:
            print(f"WARNING: Warning: Missing files: {missing_files}")
            print(f"   Looking in: {self.data_dir}")

    def load_and_merge(self) -> pd.DataFrame:
        """
        Load all NHANES files and merge by SEQN.

        Returns:
            DataFrame with standardized column names (seqn, age, albumin, etc.)
        """
        print("\n" + "="*70)
        print("NHANES 1999-2000 Data Loader")
        print("="*70)

        # Load each file
        print("\n[1/4] Loading demographics (DEMO.xpt)...")
        demo = pd.read_sas(self.files['demographics'], format='xport')
        print(f"      Loaded {len(demo)} participants")

        print("\n[2/4] Loading biochemistry (LAB18.xpt) - Albumin, Glucose, Creatinine, ALP...")
        lab18 = pd.read_sas(self.files['biochemistry'], format='xport')
        print(f"      Loaded {len(lab18)} records")

        print("\n[3/4] Loading C-Reactive Protein (LAB11.xpt)...")
        lab11 = pd.read_sas(self.files['crp'], format='xport')
        print(f"      Loaded {len(lab11)} records")

        print("\n[4/4] Loading complete blood count (LAB25.xpt) - WBC, Lymph%, MCV, RDW...")
        lab25 = pd.read_sas(self.files['cbc'], format='xport')
        print(f"      Loaded {len(lab25)} records")

        # Select only needed columns from each file
        print("\n" + "-"*70)
        print("Selecting required biomarker columns...")
        print("-"*70)

        demo_subset = demo[['SEQN', 'RIDAGEYR', 'RIAGENDR']].copy()

        # LAB18: Albumin, Glucose, Creatinine, ALP (all standard biochemistry)
        lab18_cols = ['SEQN', 'LBXSAL', 'LBXSGL', 'LBXSCR', 'LBXSAPSI']
        lab18_subset = lab18[lab18_cols].copy()

        # LAB11: CRP
        lab11_subset = lab11[['SEQN', 'LBXCRP']].copy()

        # LAB25: CBC components
        lab25_cols = ['SEQN', 'LBXLYPCT', 'LBXMCVSI', 'LBXRDW', 'LBXWBCSI']
        lab25_subset = lab25[lab25_cols].copy()

        # Merge sequentially (inner join to keep only complete records)
        print("\nMerging files by SEQN (participant ID)...")
        merged = demo_subset

        print(f"  Starting with DEMO: {len(merged)} participants")

        merged = merged.merge(lab18_subset, on='SEQN', how='inner')
        print(f"  After LAB18 merge:  {len(merged)} participants")

        merged = merged.merge(lab11_subset, on='SEQN', how='inner')
        print(f"  After LAB11 merge:  {len(merged)} participants")

        merged = merged.merge(lab25_subset, on='SEQN', how='inner')
        print(f"  After LAB25 merge:  {len(merged)} participants")

        # Rename columns to standardized names
        print("\nRenaming columns to standardized names...")
        merged = merged.rename(columns={
            'SEQN': 'seqn',
            'RIDAGEYR': 'age',
            'RIAGENDR': 'gender',
            'LBXSAL': 'albumin',        # g/dL
            'LBXSCR': 'creatinine',     # mg/dL
            'LBXSGL': 'glucose',        # mg/dL
            'LBXCRP': 'crp',            # mg/dL
            'LBXSAPSI': 'alp',          # U/L
            'LBXLYPCT': 'lymphocyte_pct',  # %
            'LBXMCVSI': 'mcv',          # fL
            'LBXRDW': 'rdw',            # %
            'LBXWBCSI': 'wbc'           # 1000 cells/μL
        })

        print("="*70)
        print(f"OK: Successfully merged {len(merged)} participants with all biomarkers")
        print("="*70 + "\n")

        return merged

    def clean_data(self, df: pd.DataFrame, age_min: int = 20, age_max: int = 90) -> pd.DataFrame:
        """
        Apply data cleaning rules from specification.

        Cleaning steps:
        1. Age filter: 20-90 years (Levine validation range)
        2. Remove participants with missing biomarkers
        3. Remove participants with CRP <= 0 (invalid for log transformation)

        Args:
            df: DataFrame from load_and_merge()
            age_min: Minimum age (default: 20)
            age_max: Maximum age (default: 90)

        Returns:
            Cleaned DataFrame ready for PhenoAge calculation
        """
        print("\n" + "="*70)
        print("Data Cleaning Pipeline")
        print("="*70)

        print(f"\nInitial cohort: {len(df)} participants")

        # Step 1: Age filter
        print(f"\n[1/3] Applying age filter ({age_min}-{age_max} years)...")
        df_filtered = df[(df['age'] >= age_min) & (df['age'] <= age_max)].copy()
        removed_age = len(df) - len(df_filtered)
        print(f"      Removed {removed_age} participants outside age range")
        print(f"      Remaining: {len(df_filtered)} participants")

        # Step 2: Remove missing biomarkers
        print(f"\n[2/3] Removing participants with missing biomarkers...")
        required_cols = ['albumin', 'creatinine', 'glucose', 'crp',
                        'lymphocyte_pct', 'mcv', 'rdw', 'alp', 'wbc', 'age']

        df_complete = df_filtered.dropna(subset=required_cols).copy()
        removed_missing = len(df_filtered) - len(df_complete)
        print(f"      Removed {removed_missing} participants with missing data")
        print(f"      Remaining: {len(df_complete)} participants")

        # Step 3: Remove CRP <= 0 (cannot take log)
        print(f"\n[3/3] Removing participants with CRP <= 0...")
        df_valid = df_complete[df_complete['crp'] > 0].copy()
        removed_crp = len(df_complete) - len(df_valid)
        print(f"      Removed {removed_crp} participants with CRP <= 0")
        print(f"      Remaining: {len(df_valid)} participants")

        # Summary
        print("\n" + "-"*70)
        print("Data Quality Summary")
        print("-"*70)
        print(f"Initial participants:     {len(df)}")
        print(f"After age filter:         {len(df_filtered)} (-{removed_age})")
        print(f"After removing missing:   {len(df_complete)} (-{removed_missing})")
        print(f"After CRP filter:         {len(df_valid)} (-{removed_crp})")
        print(f"Final cohort:             {len(df_valid)} participants")

        # Check against expected
        expected = EXPECTED_COHORT_SIZES['complete_biomarkers']
        diff = len(df_valid) - expected
        if abs(diff) < 200:
            print(f"\nOK: Cohort size matches expected (~{expected} ± 200)")
        else:
            print(f"\nWARNING: Cohort size differs from expected {expected} by {diff}")

        print("="*70 + "\n")

        return df_valid

    def get_biomarker_statistics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate descriptive statistics for all biomarkers.

        Args:
            df: DataFrame with biomarkers

        Returns:
            DataFrame with mean, std, min, max for each biomarker
        """
        biomarker_cols = ['albumin', 'creatinine', 'glucose', 'crp',
                         'lymphocyte_pct', 'mcv', 'rdw', 'alp', 'wbc', 'age']

        stats = df[biomarker_cols].describe().T
        stats['median'] = df[biomarker_cols].median()

        return stats[['mean', 'std', 'median', 'min', 'max']]


def load_nhanes_1999_2000(data_dir: Optional[str] = None) -> pd.DataFrame:
    """
    Convenience function to load and clean NHANES 1999-2000 data.

    Args:
        data_dir: Path to NHANES raw data directory (optional)

    Returns:
        Cleaned DataFrame ready for PhenoAge calculation
    """
    if data_dir is None:
        data_dir = "../bio-age-engine/data/raw/1999-2000"

    loader = NHANESLoaderV2(data_dir)
    df = loader.load_and_merge()
    df_clean = loader.clean_data(df)

    return df_clean
