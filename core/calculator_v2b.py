"""
PhenoAge Calculator V2B - WITH Unit Conversions (Like Bio-Age-Engine)
Testing alternative interpretation: coefficients calibrated on CONVERTED units

This tests the hypothesis that Levine coefficients were fit on:
- Albumin in g/L (not g/dL)  - Creatinine in μmol/L (not mg/dL)
- Glucose in mmol/L (not mg/dL)
"""

import numpy as np
import pandas as pd
from typing import Dict
from core.constants import PHENOAGE_COEFFICIENTS, PHENOAGE_INTERCEPT, PHENOAGE_SLOPE, PHENOAGE_MORTALITY_CONSTANT, MORTALITY_GAMMA, MORTALITY_TIME_MONTHS, CRP_CONVERSION_FACTOR

class PhenoAgeCalculatorV2B:
    """Version B: WITH unit conversions (testing alternative hypothesis)"""
    
    def __init__(self):
        self.coef = PHENOAGE_COEFFICIENTS
        self.intercept = PHENOAGE_INTERCEPT
        self.slope = PHENOAGE_SLOPE
        self.mort_constant = PHENOAGE_MORTALITY_CONSTANT
        self.gamma = MORTALITY_GAMMA
        self.time_months = MORTALITY_TIME_MONTHS
    
    def calculate_phenoage(self, albumin: float, creatinine: float, glucose: float,
                          crp: float, lymphocyte_pct: float, mcv: float,
                          rdw: float, alp: float, wbc: float, age: float) -> Dict[str, float]:
        """Calculate PhenoAge WITH unit conversions"""
        
        # Convert units (like bio-age-engine)
        albumin_g_L = albumin * 10  # g/dL → g/L
        creatinine_umol_L = creatinine * 88.4  # mg/dL → μmol/L
        glucose_mmol_L = glucose * 0.0555  # mg/dL → mmol/L
        crp_mg_L = crp * 10.0  # mg/dL → mg/L
        
        if crp_mg_L <= 0:
            raise ValueError(f"CRP must be > 0. Got {crp} mg/dL")
        
        log_crp = np.log(crp_mg_L)
        
        # Calculate xb with CONVERTED values
        xb = (
            self.coef['intercept'] +
            self.coef['albumin'] * albumin_g_L +
            self.coef['creatinine'] * creatinine_umol_L +
            self.coef['glucose'] * glucose_mmol_L +
            self.coef['crp'] * log_crp +
            self.coef['lymphocyte_pct'] * lymphocyte_pct +
            self.coef['mcv'] * mcv +
            self.coef['rdw'] * rdw +
            self.coef['alp'] * alp +
            self.coef['wbc'] * wbc +
            self.coef['age'] * age
        )
        
        # Calculate mortality and PhenoAge
        mort_score = 1 - np.exp(-np.exp(xb) * (np.exp(self.gamma * self.time_months) - 1) / self.gamma)
        mort_score = min(mort_score, 0.9999)
        
        phenoage = self.intercept + np.log(self.mort_constant * np.log(1 - mort_score)) / self.slope
        delta_age = phenoage - age
        
        return {
            'phenoage': float(phenoage),
            'chronological_age': float(age),
            'delta_age': float(delta_age),
            'xb': float(xb),
            'mort_score': float(mort_score)
        }
