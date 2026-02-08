"""
Population Validation - Cox Regression & Hazard Ratio Analysis
Validates PhenoAge implementation against Levine 2018 benchmark (HR ~= 1.08)

This module performs survival analysis to confirm that the PhenoAge calculator
produces the correct relationship with mortality, as reported in the original
Levine 2018 paper.

Expected Results:
- Hazard Ratio: 1.06-1.10 per 1-year increase in PhenoAge
- C-statistic: 0.73-0.82
- P-value: < 0.001

Author: Claude Code
Date: 2026-02-07
Reference: Levine ME, et al. (2018). Aging, 10(4):573-591. PMID: 29676998
"""

import pandas as pd
import numpy as np
from typing import Dict
from lifelines import CoxPHFitter
from lifelines.utils import concordance_index
from core.constants import (
    LEVINE_2018_HR,
    LEVINE_2018_HR_CI_LOWER,
    LEVINE_2018_HR_CI_UPPER,
    VALIDATION_HR_MIN,
    VALIDATION_HR_MAX,
    VALIDATION_P_VALUE_MAX,
    VALIDATION_C_STATISTIC_MIN,
    EXPECTED_C_STATISTIC_MIN,
    EXPECTED_C_STATISTIC_MAX
)


class PopulationValidator:
    """
    Validate PhenoAge implementation using Cox proportional hazards regression.

    The validation confirms that:
    1. Each 1-year increase in PhenoAge -> ~8% higher mortality risk (HR ~= 1.08)
    2. Model discrimination is good (C-statistic > 0.70)
    3. Relationship is statistically significant (p < 0.001)
    """

    def __init__(self):
        """Initialize validator with Levine 2018 benchmarks."""
        self.benchmark_hr = LEVINE_2018_HR
        self.benchmark_ci = (LEVINE_2018_HR_CI_LOWER, LEVINE_2018_HR_CI_UPPER)

    def calculate_hazard_ratio(self, df: pd.DataFrame) -> Dict:
        """
        Calculate Hazard Ratio for PhenoAge using Cox regression.

        Args:
            df: DataFrame with columns:
                - phenoage: Biological age in years
                - age: Chronological age in years
                - deceased: Binary indicator (0=alive, 1=deceased)
                - followup_years: Follow-up time in years

        Returns:
            {
                'phenoage_hr': float,
                'phenoage_ci': (lower, upper),
                'phenoage_p': float,
                'phenoage_c_statistic': float,
                'age_hr': float,
                'age_ci': (lower, upper),
                'age_p': float,
                'validation_status': str ('PASS' or 'FAIL'),
                'n_participants': int,
                'n_deaths': int,
                'mean_followup': float
            }
        """
        print("\n" + "="*70)
        print("COX PROPORTIONAL HAZARDS REGRESSION")
        print("Validating Against Levine 2018 Benchmark (HR ~= 1.08)")
        print("="*70)

        # Prepare survival data
        survival_cols = ['phenoage', 'age', 'deceased', 'followup_years']
        survival_df = df[survival_cols].dropna()

        n_participants = len(survival_df)
        n_deaths = survival_df['deceased'].sum()
        mean_followup = survival_df['followup_years'].mean()

        print(f"\nCohort Statistics:")
        print(f"  Total participants:  {n_participants}")
        print(f"  Deaths:              {n_deaths} ({n_deaths/n_participants*100:.1f}%)")
        print(f"  Mean follow-up:      {mean_followup:.1f} years")

        # =====================================================================
        # Model 1: PhenoAge (primary validation)
        # =====================================================================
        print(f"\n" + "-"*70)
        print("Model 1: PhenoAge as Predictor")
        print("-"*70)

        cph_pheno = CoxPHFitter()
        cph_pheno.fit(
            survival_df[['phenoage', 'deceased', 'followup_years']],
            duration_col='followup_years',
            event_col='deceased'
        )

        # Extract PhenoAge hazard ratio
        phenoage_coef = cph_pheno.summary.loc['phenoage', 'coef']
        phenoage_hr = np.exp(phenoage_coef)
        phenoage_ci_lower = np.exp(cph_pheno.summary.loc['phenoage', 'coef lower 95%'])
        phenoage_ci_upper = np.exp(cph_pheno.summary.loc['phenoage', 'coef upper 95%'])
        phenoage_p = cph_pheno.summary.loc['phenoage', 'p']

        print(f"\nPhenoAge Results:")
        print(f"  Hazard Ratio:     {phenoage_hr:.4f}")
        print(f"  95% CI:           ({phenoage_ci_lower:.4f}, {phenoage_ci_upper:.4f})")
        print(f"  P-value:          {phenoage_p:.2e}")
        print(f"\n  Interpretation: Each 1-year increase in PhenoAge ->")
        print(f"                  {(phenoage_hr - 1) * 100:.1f}% higher mortality risk")

        # Calculate C-statistic for PhenoAge
        phenoage_c_stat = concordance_index(
            survival_df['followup_years'],
            -survival_df['phenoage'],  # Negative because higher PhenoAge = higher risk
            survival_df['deceased']
        )
        print(f"  C-statistic:      {phenoage_c_stat:.4f}")

        # =====================================================================
        # Model 2: Chronological Age (comparison baseline)
        # =====================================================================
        print(f"\n" + "-"*70)
        print("Model 2: Chronological Age (Baseline Comparison)")
        print("-"*70)

        cph_age = CoxPHFitter()
        cph_age.fit(
            survival_df[['age', 'deceased', 'followup_years']],
            duration_col='followup_years',
            event_col='deceased'
        )

        age_coef = cph_age.summary.loc['age', 'coef']
        age_hr = np.exp(age_coef)
        age_ci_lower = np.exp(cph_age.summary.loc['age', 'coef lower 95%'])
        age_ci_upper = np.exp(cph_age.summary.loc['age', 'coef upper 95%'])
        age_p = cph_age.summary.loc['age', 'p']

        print(f"\nChronological Age Results:")
        print(f"  Hazard Ratio:     {age_hr:.4f}")
        print(f"  95% CI:           ({age_ci_lower:.4f}, {age_ci_upper:.4f})")
        print(f"  P-value:          {age_p:.2e}")

        # =====================================================================
        # Validation Against Levine 2018 Benchmark
        # =====================================================================
        print(f"\n" + "="*70)
        print("VALIDATION AGAINST LEVINE 2018 BENCHMARK")
        print("="*70)

        print(f"\nExpected (Levine 2018):")
        print(f"  Hazard Ratio:     {self.benchmark_hr:.2f}")
        print(f"  95% CI:           ({self.benchmark_ci[0]:.2f}, {self.benchmark_ci[1]:.2f})")

        print(f"\nObserved (This Implementation):")
        print(f"  Hazard Ratio:     {phenoage_hr:.4f}")
        print(f"  Difference:       {phenoage_hr - self.benchmark_hr:+.4f}")

        # Validation criteria
        hr_in_range = VALIDATION_HR_MIN <= phenoage_hr <= VALIDATION_HR_MAX
        p_significant = phenoage_p < VALIDATION_P_VALUE_MAX
        c_stat_good = phenoage_c_stat > VALIDATION_C_STATISTIC_MIN

        validation_status = 'PASS' if (hr_in_range and p_significant and c_stat_good) else 'FAIL'

        print(f"\n" + "-"*70)
        print("Validation Criteria:")
        print("-"*70)
        print(f"  HR in range [{VALIDATION_HR_MIN}, {VALIDATION_HR_MAX}]:  "
              f"{'OK: PASS' if hr_in_range else 'FAIL: FAIL'} (HR = {phenoage_hr:.4f})")
        print(f"  P-value < {VALIDATION_P_VALUE_MAX}:                      "
              f"{'OK: PASS' if p_significant else 'FAIL: FAIL'} (p = {phenoage_p:.2e})")
        print(f"  C-statistic > {VALIDATION_C_STATISTIC_MIN}:                     "
              f"{'OK: PASS' if c_stat_good else 'FAIL: FAIL'} (C = {phenoage_c_stat:.4f})")

        print(f"\n" + "="*70)
        print(f"OVERALL VALIDATION STATUS: {validation_status}")
        print("="*70)

        if validation_status == 'PASS':
            print(f"\nOK: SUCCESS: Implementation matches Levine 2018 benchmark!")
            print(f"  The PhenoAge calculator produces the correct relationship")
            print(f"  with mortality, confirming mathematical correctness.")
        else:
            print(f"\nFAIL: FAILURE: Implementation deviates from Levine 2018 benchmark")
            print(f"  Review formula, coefficients, and unit conversions.")

        print("\n")

        return {
            'phenoage_hr': phenoage_hr,
            'phenoage_ci': (phenoage_ci_lower, phenoage_ci_upper),
            'phenoage_p': phenoage_p,
            'phenoage_c_statistic': phenoage_c_stat,
            'age_hr': age_hr,
            'age_ci': (age_ci_lower, age_ci_upper),
            'age_p': age_p,
            'validation_status': validation_status,
            'n_participants': n_participants,
            'n_deaths': n_deaths,
            'mean_followup': mean_followup,
            'benchmark_hr': self.benchmark_hr,
            'benchmark_ci': self.benchmark_ci
        }

    def generate_validation_report(self, results: Dict) -> str:
        """
        Generate human-readable validation report.

        Args:
            results: Dictionary from calculate_hazard_ratio()

        Returns:
            Formatted report string
        """
        status_symbol = "OK:" if results['validation_status'] == 'PASS' else "FAIL:"

        report = f"""
+======================================================================+
|  PhenoAge Population Validation Report                               |
|  Benchmark: Levine 2018 (Aging, PMID: 29676998)                     |
+======================================================================+

COHORT SUMMARY
──────────────────────────────────────────────────────────────────────

Total Participants:        {results['n_participants']}
Deaths During Follow-up:   {results['n_deaths']} ({results['n_deaths']/results['n_participants']*100:.1f}%)
Mean Follow-up Time:       {results['mean_followup']:.1f} years


COX PROPORTIONAL HAZARDS ANALYSIS
──────────────────────────────────────────────────────────────────────

PhenoAge (Per 1-Year Increase):
  Hazard Ratio:     {results['phenoage_hr']:.4f}
  95% CI:           ({results['phenoage_ci'][0]:.4f}, {results['phenoage_ci'][1]:.4f})
  P-value:          {results['phenoage_p']:.2e}
  C-statistic:      {results['phenoage_c_statistic']:.4f}

Interpretation: Each 1-year increase in PhenoAge is associated with a
                {(results['phenoage_hr'] - 1) * 100:.1f}% higher risk of mortality.

Chronological Age (Baseline Comparison):
  Hazard Ratio:     {results['age_hr']:.4f}
  95% CI:           ({results['age_ci'][0]:.4f}, {results['age_ci'][1]:.4f})
  P-value:          {results['age_p']:.2e}


VALIDATION AGAINST LEVINE 2018 BENCHMARK
──────────────────────────────────────────────────────────────────────

Expected HR (Levine 2018):  {results['benchmark_hr']:.2f}
Expected 95% CI:            ({results['benchmark_ci'][0]:.2f}, {results['benchmark_ci'][1]:.2f})

Observed HR (This Study):   {results['phenoage_hr']:.4f}
Difference:                 {results['phenoage_hr'] - results['benchmark_hr']:+.4f}

Validation Criteria:
  HR in range [1.04-1.12]:  {'OK: PASS' if VALIDATION_HR_MIN <= results['phenoage_hr'] <= VALIDATION_HR_MAX else 'FAIL: FAIL'}
  P-value < 0.001:          {'OK: PASS' if results['phenoage_p'] < VALIDATION_P_VALUE_MAX else 'FAIL: FAIL'}
  C-statistic > 0.70:       {'OK: PASS' if results['phenoage_c_statistic'] > VALIDATION_C_STATISTIC_MIN else 'FAIL: FAIL'}


======================================================================

VALIDATION STATUS: {status_symbol} {results['validation_status']}

{('OK: SUCCESS: This implementation matches the Levine 2018 benchmark!\\n'
  '  The PhenoAge calculator produces the correct relationship with mortality,\\n'
  '  confirming that the mathematical formula and unit conversions are accurate.')
  if results['validation_status'] == 'PASS' else
  ('FAIL: FAILURE: This implementation deviates from the Levine 2018 benchmark.\\n'
   '  Review formula, coefficients, and unit conversions for errors.')}

======================================================================
"""

        return report


def validate_phenoage_implementation(df: pd.DataFrame) -> Dict:
    """
    Convenience function to validate PhenoAge implementation.

    Args:
        df: DataFrame with phenoage, age, deceased, followup_years

    Returns:
        Validation results dictionary
    """
    validator = PopulationValidator()
    return validator.calculate_hazard_ratio(df)
