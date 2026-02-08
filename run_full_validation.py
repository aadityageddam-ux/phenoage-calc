"""
PhenoAge Full Validation Pipeline

This script runs the complete validation workflow:
1. Load NHANES 1999-2000 raw data
2. Calculate PhenoAge using Version B (WITH unit conversions)
3. Load mortality linkage data
4. Run Cox regression to calculate Hazard Ratio
5. Validate against Levine 2018 benchmark (HR ≈ 1.08)
6. Generate validation reports

Usage:
    python run_full_validation.py

Outputs:
    - phenoage_calculations.csv (full dataset with PhenoAge)
    - population_validation_report.txt (Hazard Ratio validation)
    - validation_summary.txt (quick reference)

Author: Claude Code
Date: 2026-02-07
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from core import PhenoAgeCalculatorV2
from data.nhanes_loader import NHANESLoaderV2
from data.mortality_loader import MortalityLoaderV2
from analysis.population_validation import PopulationValidator


def main():
    """Run complete validation pipeline."""

    print("\n" + "="*70)
    print("PHENOAGE BIO-AGE LOGIC ENGINE - FULL VALIDATION")
    print("Testing Version B (WITH unit conversions)")
    print("="*70)
    print(f"\nObjective: Confirm that PhenoAge Hazard Ratio ~1.08")
    print(f"           (Levine 2018 benchmark)")
    print("="*70 + "\n")

    # =========================================================================
    # STEP 1: Load NHANES 1999-2000 Data
    # =========================================================================
    print("\n" + "#"*70)
    print("# STEP 1/5: Loading NHANES 1999-2000 Data")
    print("#"*70)

    loader = NHANESLoaderV2(data_dir="../bio-age-engine/data/raw/1999-2000")
    df = loader.load_and_merge()
    df_clean = loader.clean_data(df)

    print(f"\n✓ NHANES data loaded: {len(df_clean)} participants")

    # Display biomarker statistics
    print("\nBiomarker Summary Statistics:")
    stats = loader.get_biomarker_statistics(df_clean)
    print(stats.round(2))

    # =========================================================================
    # STEP 2: Calculate PhenoAge (Version B - WITH Unit Conversions)
    # =========================================================================
    print("\n" + "#"*70)
    print("# STEP 2/5: Calculating PhenoAge (Version B)")
    print("#"*70)

    calc = PhenoAgeCalculatorV2()
    df_phenoage = calc.calculate_batch(df_clean)

    print(f"\n✓ PhenoAge calculated for {len(df_phenoage)} participants")

    # =========================================================================
    # STEP 3: Load Mortality Data
    # =========================================================================
    print("\n" + "#"*70)
    print("# STEP 3/5: Loading Mortality Linkage Data")
    print("#"*70)

    mort_loader = MortalityLoaderV2(
        mortality_file="../bio-age-engine/data/raw/1999-2000/NHANES_1999_2000_MORT_2019_PUBLIC.dat"
    )
    df_mortality = mort_loader.load_mortality()

    print(f"\n✓ Mortality data loaded: {len(df_mortality)} participants")

    # =========================================================================
    # STEP 4: Merge PhenoAge with Mortality
    # =========================================================================
    print("\n" + "#"*70)
    print("# STEP 4/5: Merging PhenoAge with Mortality Outcomes")
    print("#"*70)

    df_final = mort_loader.merge_with_phenoage(df_phenoage, df_mortality)

    print(f"\n✓ Final cohort: {len(df_final)} participants with complete data")

    # =========================================================================
    # STEP 5: Population Validation - Cox Regression & Hazard Ratio
    # =========================================================================
    print("\n" + "#"*70)
    print("# STEP 5/5: Population Validation (Cox Regression)")
    print("#"*70)

    validator = PopulationValidator()
    results = validator.calculate_hazard_ratio(df_final)

    # Generate validation report
    report = validator.generate_validation_report(results)

    # =========================================================================
    # SAVE OUTPUTS
    # =========================================================================
    print("\n" + "#"*70)
    print("# Saving Outputs")
    print("#"*70)

    # Create outputs directory
    Path("outputs").mkdir(exist_ok=True)

    # Save full dataset with PhenoAge
    output_file = "outputs/phenoage_calculations.csv"
    df_final.to_csv(output_file, index=False)
    print(f"\n✓ Saved: {output_file} ({len(df_final)} records)")

    # Save validation report
    report_file = "outputs/population_validation_report.txt"
    with open(report_file, "w") as f:
        f.write(report)
    print(f"✓ Saved: {report_file}")

    # Save quick summary
    summary_file = "outputs/validation_summary.txt"
    with open(summary_file, "w") as f:
        f.write("="*70 + "\n")
        f.write("PHENOAGE VALIDATION SUMMARY\n")
        f.write("="*70 + "\n\n")
        f.write(f"Dataset: NHANES 1999-2000\n")
        f.write(f"Implementation: Version B (WITH unit conversions)\n")
        f.write(f"Participants: {results['n_participants']}\n")
        f.write(f"Deaths: {results['n_deaths']} ({results['n_deaths']/results['n_participants']*100:.1f}%)\n")
        f.write(f"Mean Follow-up: {results['mean_followup']:.1f} years\n\n")
        f.write("-"*70 + "\n")
        f.write("HAZARD RATIO ANALYSIS\n")
        f.write("-"*70 + "\n\n")
        f.write(f"PhenoAge HR: {results['phenoage_hr']:.4f}\n")
        f.write(f"95% CI: ({results['phenoage_ci'][0]:.4f}, {results['phenoage_ci'][1]:.4f})\n")
        f.write(f"P-value: {results['phenoage_p']:.2e}\n")
        f.write(f"C-statistic: {results['phenoage_c_statistic']:.4f}\n\n")
        f.write(f"Levine 2018 Benchmark: {results['benchmark_hr']:.2f}\n")
        f.write(f"Difference: {results['phenoage_hr'] - results['benchmark_hr']:+.4f}\n\n")
        f.write("-"*70 + "\n")
        f.write(f"VALIDATION STATUS: {results['validation_status']}\n")
        f.write("-"*70 + "\n")
    print(f"✓ Saved: {summary_file}")

    # =========================================================================
    # FINAL SUMMARY
    # =========================================================================
    print("\n" + "="*70)
    print("VALIDATION COMPLETE")
    print("="*70)
    print(f"\nDataset: NHANES 1999-2000 ({results['n_participants']} participants)")
    print(f"Deaths: {results['n_deaths']} ({results['n_deaths']/results['n_participants']*100:.1f}%)")
    print(f"\nHazard Ratio: {results['phenoage_hr']:.4f} (95% CI: {results['phenoage_ci'][0]:.4f}-{results['phenoage_ci'][1]:.4f})")
    print(f"Levine 2018:  {results['benchmark_hr']:.2f} (95% CI: {results['benchmark_ci'][0]:.2f}-{results['benchmark_ci'][1]:.2f})")
    print(f"C-statistic:  {results['phenoage_c_statistic']:.4f}")
    print(f"\nValidation Status: {results['validation_status']}")

    if results['validation_status'] == 'PASS':
        print(f"\n{'='*70}")
        print("SUCCESS: Version B (WITH unit conversions) is CORRECT!")
        print("The implementation matches the Levine 2018 benchmark.")
        print("="*70)
    else:
        print(f"\n{'='*70}")
        print("WARNING: Results deviate from Levine 2018 benchmark")
        print("Review implementation for errors")
        print("="*70)

    print(f"\nOutputs saved to:")
    print(f"  - outputs/phenoage_calculations.csv")
    print(f"  - outputs/population_validation_report.txt")
    print(f"  - outputs/validation_summary.txt")
    print("\n")

    return results['validation_status'] == 'PASS'


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n{'='*70}")
        print(f"ERROR: {e}")
        print("="*70)
        import traceback
        traceback.print_exc()
        sys.exit(1)
