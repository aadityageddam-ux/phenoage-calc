"""
Quick Test - PhenoAge Calculator V2
Tests the correct implementation with a sample calculation
"""

import sys
sys.path.insert(0, '.')

from core import PhenoAgeCalculatorV2

def test_healthy_adult():
    """Test typical healthy 35-year-old"""
    calc = PhenoAgeCalculatorV2()

    result = calc.calculate_phenoage(
        albumin=4.5,          # g/dL (optimal)
        creatinine=1.0,       # mg/dL (normal)
        glucose=90,           # mg/dL (optimal fasting)
        crp=0.1,             # mg/dL (low inflammation)
        lymphocyte_pct=32,    # % (normal)
        mcv=88,              # fL (normal)
        rdw=12.5,            # % (normal)
        alp=65,              # U/L (normal)
        wbc=6.5,             # 1000 cells/μL (normal)
        age=35               # years
    )

    print("="*70)
    print("QUICK TEST: Healthy 35-Year-Old")
    print("="*70)
    print(f"Chronological Age: {result['chronological_age']:.1f} years")
    print(f"PhenoAge:          {result['phenoage']:.1f} years")
    print(f"Age Acceleration:  {result['delta_age']:+.1f} years")
    print(f"Mortality Score:   {result['mort_score']:.4f} (10-year)")
    print(f"Linear Predictor:  {result['xb']:.4f}")
    print(f"\nIntermediate Values:")
    print(f"  CRP (mg/L):      {result['intermediate_values']['crp_mg_L']:.2f}")
    print(f"  ln(CRP):         {result['intermediate_values']['log_crp']:.4f}")
    print("="*70)

    # Assertions
    assert result['phenoage'] > 0, "PhenoAge should be positive"
    assert -20 < result['delta_age'] < 20, "Delta age should be reasonable"
    assert 0 <= result['mort_score'] <= 1, "Mortality score should be between 0 and 1"

    print("\n✓ All tests passed!")
    return result

if __name__ == "__main__":
    test_healthy_adult()
