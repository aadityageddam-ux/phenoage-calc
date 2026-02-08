"""Quick validation script without Unicode issues"""
import sys, os
# Force UTF-8 encoding
if os.name == 'nt':  # Windows
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from core import PhenoAgeCalculatorV2
from data.nhanes_loader import NHANESLoaderV2
from data.mortality_loader import MortalityLoaderV2
from analysis.population_validation import PopulationValidator

def main():
    print("\n" + "="*70)
    print("PHENOAGE VALIDATION - Version B (WITH unit conversions)")
    print("="*70 + "\n")

    # Load NHANES
    print("[1/5] Loading NHANES data...")
    loader = NHANESLoaderV2(data_dir="../bio-age-engine/data/raw/1999-2000")
    df = loader.load_and_merge()
    df_clean = loader.clean_data(df)
    print(f"OK: {len(df_clean)} participants\n")

    # Calculate PhenoAge
    print("[2/5] Calculating PhenoAge...")
    calc = PhenoAgeCalculatorV2()
    df_phenoage = calc.calculate_batch(df_clean)
    print(f"OK: PhenoAge calculated\n")

    # Load mortality
    print("[3/5] Loading mortality data...")
    mort_loader = MortalityLoaderV2(
        mortality_file="../bio-age-engine/data/raw/1999-2000/NHANES_1999_2000_MORT_2019_PUBLIC.dat"
    )
    df_mortality = mort_loader.load_mortality()
    print(f"OK: Mortality data loaded\n")

    # Merge
    print("[4/5] Merging data...")
    df_final = mort_loader.merge_with_phenoage(df_phenoage, df_mortality)
    print(f"OK: {len(df_final)} participants with complete data\n")

    # Validate
    print("[5/5] Running Cox regression validation...")
    validator = PopulationValidator()
    results = validator.calculate_hazard_ratio(df_final)

    # Save outputs
    Path("outputs").mkdir(exist_ok=True)
    df_final.to_csv("outputs/phenoage_calculations.csv", index=False)
    
    report = validator.generate_validation_report(results)
    with open("outputs/population_validation_report.txt", "w", encoding='utf-8') as f:
        f.write(report)

    print("\n" + "="*70)
    print("VALIDATION RESULTS")
    print("="*70)
    print(f"Participants: {results['n_participants']}")
    print(f"Deaths: {results['n_deaths']} ({results['n_deaths']/results['n_participants']*100:.1f}%)")
    print(f"\nHazard Ratio: {results['phenoage_hr']:.4f}")
    print(f"95% CI: ({results['phenoage_ci'][0]:.4f}, {results['phenoage_ci'][1]:.4f})")
    print(f"P-value: {results['phenoage_p']:.2e}")
    print(f"C-statistic: {results['phenoage_c_statistic']:.4f}")
    print(f"\nLevine 2018 Benchmark: {results['benchmark_hr']:.2f}")
    print(f"Difference: {results['phenoage_hr'] - results['benchmark_hr']:+.4f}")
    print(f"\nValidation Status: {results['validation_status']}")
    print("="*70)

    return results['validation_status'] == 'PASS'

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
