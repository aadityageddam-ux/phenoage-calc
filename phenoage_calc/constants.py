"""Full-precision clinical coefficients from BioAge's orig=TRUE formula."""
PHENOAGE_COEFFICIENTS = {
    'intercept': -19.90667, 'albumin': -0.03359355,
    'creatinine': 0.009506491, 'glucose': 0.1953192,
    'crp': 0.09536762, 'lymphocyte_pct': -0.01199984,
    'mcv': 0.02676401, 'rdw': 0.3306156,
    'alp': 0.001868778, 'wbc': 0.05542406, 'age': 0.08035356,
}
REQUIRED_BIOMARKERS = ['albumin', 'creatinine', 'glucose', 'crp',
                       'lymphocyte_pct', 'mcv', 'rdw', 'alp', 'wbc', 'age']
PHENOAGE_INTERCEPT = 141.50225
PHENOAGE_SLOPE = 0.090165
