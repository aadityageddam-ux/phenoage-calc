"""Clinical Phenotypic Age calculations; numerical outputs, not a prognosis.

The default CRP input is mg/dL for compatibility with this repository's API.
Pass crp_unit='mg/L' explicitly for laboratories reporting mg/L. Both paths
log CRP in mg/dL. No missing values are imputed or rows silently dropped.
"""
from numbers import Real
import math
import numpy as np
import pandas as pd
from phenoage_calc.constants import PHENOAGE_COEFFICIENTS, REQUIRED_BIOMARKERS


class PhenoAgeCalculatorV2:
    """Evaluate the original clinical formula reproduced by BioAge.

    Units: albumin g/dL, creatinine and glucose mg/dL, lymphocytes/RDW %, MCV
    fL, ALP U/L, WBC thousands/µL, age years. CRP defaults to mg/dL, with an
    explicit mg/L option. All ten inputs must be finite numbers; CRP > 0.
    """

    def calculate_phenoage(self, albumin, creatinine, glucose, crp,
                           lymphocyte_pct, mcv, rdw, alp, wbc, age, *, crp_unit='mg/dL'):
        values = dict(albumin=albumin, creatinine=creatinine, glucose=glucose,
                      crp=crp, lymphocyte_pct=lymphocyte_pct, mcv=mcv,
                      rdw=rdw, alp=alp, wbc=wbc, age=age)
        for name, value in values.items():
            if value is None:
                raise ValueError(f'Missing required biomarker: {name}')
            if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real) or not math.isfinite(value):
                raise ValueError(f'{name} must be a finite number.')
        if crp_unit not in ('mg/dL', 'mg/L'):
            raise ValueError("crp_unit must be 'mg/dL' or 'mg/L'.")
        if crp <= 0:
            raise ValueError('crp must be strictly positive; zero is not replaced with an epsilon.')
        converted = dict(values)
        converted['albumin'] = albumin * 10.0
        converted['creatinine'] = creatinine * 88.4017
        converted['glucose'] = glucose * 0.0555
        crp_mg_dl = crp / 10.0 if crp_unit == 'mg/L' else crp
        converted['crp'] = math.log(crp_mg_dl)
        xb = PHENOAGE_COEFFICIENTS['intercept'] + sum(
            PHENOAGE_COEFFICIENTS[name] * converted[name] for name in REQUIRED_BIOMARKERS)
        log_hazard = math.log(1.51714 / 0.007692696) + xb
        phenoage = 141.50225 + (math.log(0.0055305) + log_hazard) / 0.090165
        if not math.isfinite(phenoage):
            raise ValueError('Inputs exceed the supported numerical range.')
        # This intermediate can round to 1; age is computed independently above.
        mort_score = 1.0 if log_hazard > 7 else -math.expm1(-math.exp(log_hazard))
        return {
            'phenoage': float(phenoage), 'chronological_age': float(age),
            'delta_age': float(phenoage-age), 'xb': float(xb),
            'mort_score': float(mort_score),
            'intermediate_values': {
                'albumin_g_L': float(converted['albumin']),
                'creatinine_umol_L': float(converted['creatinine']),
                'glucose_mmol_L': float(converted['glucose']),
                'crp_mg_dL': float(crp_mg_dl),
                'crp_mg_L': float(crp_mg_dl*10),
                'log_crp': float(converted['crp']),
            },
        }

    def calculate_batch(self, df, *, crp_unit='mg/dL'):
        """Return a copy with calculation columns, preserving index/order.

        Reject the whole batch if any row is invalid. Error messages identify
        row position and index without printing laboratory values.
        """
        if not isinstance(df, pd.DataFrame) or not df.columns.is_unique:
            raise ValueError('Provide a DataFrame with unique column names.')
        missing = set(REQUIRED_BIOMARKERS) - set(df.columns)
        if missing:
            raise ValueError(f'Missing required columns: {sorted(missing)}')
        if crp_unit not in ('mg/dL', 'mg/L'):
            raise ValueError("crp_unit must be 'mg/dL' or 'mg/L'.")
        records = []
        for position, (index, row) in enumerate(zip(df.index, df[REQUIRED_BIOMARKERS].to_dict('records'))):
            try:
                value = self.calculate_phenoage(**row, crp_unit=crp_unit)
            except ValueError as error:
                raise ValueError(f'Row {position} (index {index!r}): {error}') from error
            records.append({key: value[key] for key in ('phenoage','delta_age','xb','mort_score')} | value['intermediate_values'])
        output = df.copy()
        columns = ['phenoage','delta_age','xb','mort_score','albumin_g_L','creatinine_umol_L','glucose_mmol_L','crp_mg_dL','crp_mg_L','log_crp']
        for column in columns:
            output[column] = [record[column] for record in records]
        return output



def calculate_phenoage_single(albumin, creatinine, glucose, crp, lymphocyte_pct,
                              mcv, rdw, alp, wbc, age, *, crp_unit='mg/dL'):
    """Convenience wrapper using the same validation and units as batch."""
    return PhenoAgeCalculatorV2().calculate_phenoage(
        albumin, creatinine, glucose, crp, lymphocyte_pct, mcv, rdw, alp, wbc, age,
        crp_unit=crp_unit)
