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

import logging

import pandas as pd
import numpy as np
from pathlib import Path
from core.constants import MORTALITY_FILE_COLSPECS, MORTALITY_FILE_COLNAMES

logger = logging.getLogger(__name__)


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
            logger.warning("Mortality file not found: %s", self.mortality_file)

    def load_mortality(self) -> pd.DataFrame:
        """
        Load fixed-width mortality file.

        Returns:
            DataFrame with columns: seqn, deceased (0/1), followup_years
        """
        logger.info("NHANES Mortality Linkage Loader")
        logger.info("Loading mortality data from: %s", self.mortality_file)

        # Read fixed-width format file
        # Column specifications from NCHS documentation
        mort = pd.read_fwf(
            self.mortality_file,
            colspecs=MORTALITY_FILE_COLSPECS,
            names=MORTALITY_FILE_COLNAMES,
            dtype={'SEQN': int}
        )

        logger.info("Loaded %d mortality records", len(mort))

        # Rename to lowercase
        mort = mort.rename(columns={col: col.lower() for col in mort.columns})

        # Convert MORTSTAT and PERMTH_EXM to numeric (handles '.' as NaN)
        mort['mortstat'] = pd.to_numeric(mort['mortstat'], errors='coerce')
        mort['permth_exm'] = pd.to_numeric(mort['permth_exm'], errors='coerce')

        logger.info("Data Summary")

        # Filter to eligible participants only
        mort_eligible = mort[mort['eligstat'] == 1].copy()
        logger.info("Eligible participants: %d", len(mort_eligible))

        # Create binary deceased indicator
        mort_eligible['deceased'] = (mort_eligible['mortstat'] == 1).astype(int)

        # Convert follow-up months to years
        mort_eligible['followup_years'] = mort_eligible['permth_exm'] / 12.0

        # Calculate statistics
        n_deceased = mort_eligible['deceased'].sum()
        n_alive = len(mort_eligible) - n_deceased
        mortality_rate = (n_deceased / len(mort_eligible)) * 100

        logger.info("Deaths during follow-up: %d (%.1f%%)", n_deceased, mortality_rate)
        logger.info("Alive/censored: %d (%.1f%%)", n_alive, 100 - mortality_rate)
        logger.info("Mean follow-up: %.1f years", mort_eligible['followup_years'].mean())
        logger.info("Median follow-up: %.1f years", mort_eligible['followup_years'].median())
        logger.info("Follow-up range: [%.1f, %.1f] years",
                     mort_eligible['followup_years'].min(),
                     mort_eligible['followup_years'].max())

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
        logger.info("Merging PhenoAge with Mortality Data")
        logger.info("PhenoAge cohort: %d participants", len(df_phenoage))
        logger.info("Mortality records: %d participants", len(df_mortality))

        # Merge on SEQN
        merged = df_phenoage.merge(df_mortality, on='seqn', how='inner')

        logger.info("Merged cohort: %d participants", len(merged))

        # Calculate statistics
        n_deceased = merged['deceased'].sum()
        mortality_rate = (n_deceased / len(merged)) * 100

        logger.info("Deaths: %d (%.1f%%)", n_deceased, mortality_rate)
        logger.info("Mean follow-up: %.1f years", merged['followup_years'].mean())

        # Check for reasonable mortality rate (expected: 20-30%)
        if 15 < mortality_rate < 35:
            logger.info("Mortality rate within expected range (20-30%%)")
        else:
            logger.warning("Mortality rate outside expected range (20-30%%)")

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
