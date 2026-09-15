"""Synthetic inputs demonstrating equivalent mg/dL and mg/L CRP routes."""
import pandas as pd
from phenoage_calc import PhenoAgeCalculator, calculate_phenoage_single

row = dict(albumin=4.2, creatinine=.9, glucose=95, crp=.1,
           lymphocyte_pct=30, mcv=90, rdw=13, alp=65, wbc=6.5, age=50)
single = calculate_phenoage_single(**row)
batch = PhenoAgeCalculator().calculate_batch(
    pd.DataFrame([row | {'crp': 1}], index=['example-a']), crp_unit='mg/L')
assert abs(single['phenoage'] - 43.70363251372635) < 1e-10
assert abs(batch.loc['example-a', 'phenoage'] - single['phenoage']) < 1e-10
print(batch[['phenoage', 'delta_age']])
