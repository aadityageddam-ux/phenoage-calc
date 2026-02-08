"""
NHANES Mortality Linkage Loader
Loads NHANES 1999-2000 mortality follow-up data through 2019

File: NHANES_1999_2000_MORT_2019_PUBLIC.dat
Format: Fixed-width text file (NOT XPT format)

Columns (specification lines 336-341):
- SEQN (positions 1-14): Participant ID
- ELIGSTAT (position 15): Eligibility status (1=eligible)
- MORTSTAT (position 16): Mortality status (0=alive, 1=deceased)
- PERMTH_EXM (positions 46-48): Follow-up months from exam to death/censoring

Author: Claude Code
Date: 2026-02-07
"""

import pandas as pd
import numpy as np
from pathlib import Path
from core.constants import MORTALITY_FILE_COLSPECS, MORTALITY_FILE_COLNAMES


class MortalityLoaderV2:
    """
    Load NHANES mortality linkage file (fixed-width format).

    Specification lines 336-342: Mortality File Format
    """

    def __init__(self, mortality_file: str = "../bio-age-engine/data/raw/1999-2000/NHANES_1999_2000_MORT_2019_PUBLIC.dat"):
        """
        Initialize loader with path to mortality file.

        Args:
            mortality_file: Path to fixed-width mortality data file
        """
        self.mortality_file = Path(mortality_file)

        if not self.mortality_file.exists():
            print(f"WARNING: Warning: Mortality file not found: {self.mortality_file}")

    def load_mortality(self) -> pd.DataFrame:
        """
        Load fixed-width mortality file.

        Returns:
            DataFrame with columns: seqn, deceased (0/1), followup_years
        """
        print("\n" + "="*70)
        print("NHANES Mortality Linkage Loader")
        print("="*70)

        print(f"\nLoading mortality data from:")
        print(f"  {self.mortality_file}")

        # Read fixed-width format file
        # Column specifications from NCHS documentation
        mort = pd.read_fwf(
            self.mortality_file,
            colspecs=MORTALITY_FILE_COLSPECS,
            names=MORTALITY_FILE_COLNAMES,
            dtype={'SEQN': int}
        )

        print(f"\nOK: Loaded {len(mort)} mortality records")

        # Rename to lowercase
        mort = mort.rename(columns={col: col.lower() for col in mort.columns})

        # Convert MORTSTAT and PERMTH_EXM to numeric (handles '.' as NaN)
        mort['mortstat'] = pd.to_numeric(mort['mortstat'], errors='coerce')
        mort['permth_exm'] = pd.to_numeric(mort['permth_exm'], errors='coerce')

        print(f"\n" + "-"*70)
        print("Data Summary")
        print("-"*70)

        # Filter to eligible participants only
        mort_eligible = mort[mort['eligstat'] == 1].copy()
        print(f"Eligible participants:    {len(mort_eligible)}")

        # Create binary deceased indicator
        mort_eligible['deceased'] = (mort_eligible['mortstat'] == 1).astype(int)

        # Convert follow-up months to years
        mort_eligible['followup_years'] = mort_eligible['permth_exm'] / 12.0

        # Calculate statistics
        n_deceased = mort_eligible['deceased'].sum()
        n_alive = len(mort_eligible) - n_deceased
        mortality_rate = (n_deceased / len(mort_eligible)) * 100

        print(f"Deaths during follow-up:  {n_deceased} ({mortality_rate:.1f}%)")
        print(f"Alive/censored:           {n_alive} ({100-mortality_rate:.1f}%)")
        print(f"Mean follow-up time:      {mort_eligible['followup_years'].mean():.1f} years")
        print(f"Median follow-up time:    {mort_eligible['followup_years'].median():.1f} years")
        print(f"Follow-up range:          [{mort_eligible['followup_years'].min():.1f}, {mort_eligible['followup_years'].max():.1f}] years")

        print("="*70 + "\n")

        return mort_eligible[['seqn', 'deceased', 'followup_years']]

    def merge_with_phenoage(self, df_phenoage: pd.DataFrame,
                           df_mortality: pd.DataFrame) -> pd.DataFrame:
        """
        Merge PhenoAge calculations with mortality outcomes.

        Args:
            df_phenoage: DataFrame with PhenoAge calculations (must have 'seqn' column)
            df_mortality: DataFrame from load_mortality()

        Returns:
            Merged DataFrame with PhenoAge + mortality outcomes
        """
        print("\n" + "="*70)
        print("Merging PhenoAge with Mortality Data")
        print("="*70)

        print(f"\nPhenoAge cohort:    {len(df_phenoage)} participants")
        print(f"Mortality records:  {len(df_mortality)} participants")

        # Merge on SEQN
        merged = df_phenoage.merge(df_mortality, on='seqn', how='inner')

        print(f"Merged cohort:      {len(merged)} participants")

        # Calculate statistics
        n_deceased = merged['deceased'].sum()
        mortality_rate = (n_deceased / len(merged)) * 100

        print(f"\nMortality statistics:")
        print(f"  Deaths:           {n_deceased} ({mortality_rate:.1f}%)")
        print(f"  Mean follow-up:   {merged['followup_years'].mean():.1f} years")

        # Check for reasonable mortality rate (expected: 20-30%)
        if 15 < mortality_rate < 35:
            print(f"\nOK: Mortality rate within expected range (20-30%)")
        else:
            print(f"\nWARNING: Warning: Mortality rate outside expected range (20-30%)")

        print("="*70 + "\n")

        return merged


def load_mortality_1999_2000(mortality_file: str = None) -> pd.DataFrame:
    """
    Convenience function to load NHANES 1999-2000 mortality data.

    Args:
        mortality_file: Path to mortality file (optional)

    Returns:
        DataFrame with seqn, deceased, followup_years
    """
    if mortality_file is None:
        mortality_file = "../bio-age-engine/data/raw/1999-2000/NHANES_1999_2000_MORT_2019_PUBLIC.dat"

    loader = MortalityLoaderV2(mortality_file)
    return loader.load_mortality()
