# phenoage-calc

A focused Python library for **clinical Phenotypic Age**, with single-row and pandas batch calculations. Use [LabAge](https://labage.vercel.app/) for the web interface and its NHANES comparisons.

This library evaluates a published statistical formula. It does not compute DNA methylation PhenoAge, establish individual biological aging rate, or provide a clinical prognosis. No population reference data or patient storage is included.

## Install

Python 3.11 or later:

```sh
git clone https://github.com/aadityageddam-ux/phenoage-calc.git
cd phenoage-calc
python -m pip install .
```

Version 3.0.0 identifies this source cleanup; no PyPI publication is implied.

## Single calculation

```python
from phenoage_calc import calculate_phenoage_single

result = calculate_phenoage_single(
    albumin=4.2, creatinine=0.9, glucose=95, crp=0.1,
    lymphocyte_pct=30, mcv=90, rdw=13, alp=65, wbc=6.5, age=50,
    crp_unit="mg/dL",
)
print(round(result["phenoage"], 4))  # 43.7036
```

This is a synthetic input fixture, not a patient assessment.

| Input | Unit |
| --- | --- |
| albumin | g/dL |
| creatinine, glucose | mg/dL |
| crp | **mg/dL by default**, or explicit `crp_unit="mg/L"` |
| lymphocyte_pct, rdw | % |
| mcv | fL |
| alp | U/L |
| wbc | thousands/µL |
| age | years |

For the same CRP value reported as 1 mg/L, pass `crp=1, crp_unit="mg/L"`. Both routes take the natural logarithm of **0.1 mg/dL**. Units are never inferred from magnitude.

## Batch calculation

```python
import pandas as pd
from phenoage_calc import PhenoAgeCalculator

df = pd.DataFrame([dict(
    albumin=4.2, creatinine=0.9, glucose=95, crp=1,
    lymphocyte_pct=30, mcv=90, rdw=13, alp=65, wbc=6.5, age=50,
)], index=["example-a"])
output = PhenoAgeCalculator().calculate_batch(df, crp_unit="mg/L")
print(output[["phenoage", "delta_age"]])
```

The input is not modified. Index, order and extra columns are preserved. A batch uses one CRP unit for every row; normalize mixed-unit inputs explicitly before calling. Invalid rows reject the whole batch with their position and index. No values are imputed or rows silently discarded.

All inputs must be finite numbers, and CRP must be positive. These are mathematical checks, not clinical reference ranges. Users must establish appropriate populations, assays, units and study design separately.

## Formula and outputs

Coefficients and constants follow [BioAge's original clinical formula](https://github.com/dayoonkwon/BioAge/blob/master/R/phenoage_calc.R), associated with [Levine et al. 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC5940111/). Albumin is multiplied by 10, creatinine by 88.4017, and glucose by 0.0555 before coefficients are applied. CRP is logged in mg/dL.

The age transform uses the 0.090165 denominator and an algebraically equivalent log-hazard expression to avoid saturation. Results are not capped to a plausible age range.

- `phenoage`: calculated clinical Phenotypic Age, in years.
- `delta_age`: raw result minus chronological age; **not residualized age acceleration**.
- `xb`: model linear predictor.
- `mort_score`: historical model intermediate retained for compatibility; not a calibrated individual prognosis. It may round to one at extreme inputs without capping the age result.
- `intermediate_values`: unit conversions and log CRP, for auditing the calculation.

## Migration and scope

The Streamlit app, storage/audit modules, longitudinal views, unverified NHANES loaders, population-validation scripts and obsolete generated specifications were removed from the current tree. They remain in Git history. Existing files outside Git, including any locally stored records, are not migrated or deleted by installing this library.

`core.calculator.PhenoAgeCalculatorV2` and `core.calculator_v2b.PhenoAgeCalculatorV2B` remain compatibility imports. New code should use `phenoage_calc`. The old default CRP input remains mg/dL, but the incorrect ×10-before-log behavior is fixed. Recompute old results; their values will change. Old normal-range flags and claimed validation thresholds were withdrawn.

No license grant is asserted here; this repository currently has no license file.

## Verify

```sh
python -m pip install -e ".[test]"
python -m pytest
python -m build
python examples/single_and_batch.py
```

Tests check independent numerical fixtures, CRP unit equivalence, single/batch agreement, malformed input rejection, row preservation and numerical extremes. They do not establish clinical validity. The optional R script in `tests/reference_formula.R` reproduces the fixed fixtures without importing the Python implementation.
