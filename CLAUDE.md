# PhenoAge Engine — Project Constitution

## Identity
This is the **PhenoAge Engine**, implementing the Levine 2018 biological age algorithm.
- Target Hazard Ratio: **~1.08** per year of phenotypic age acceleration
- Reference: Levine ME et al. (2018) *Aging Cell*

## Mathematical Ground Truth

### Model Intercept
```
intercept = -19.907
```

### CRP Handling (CRITICAL)
- Input unit: mg/dL or mg/L — **must be converted to mg/L**
- **Must apply Natural Log (ln) transformation**: `np.log(crp_mg_l + 0.001)`
- The `+ 0.001` epsilon prevents `log(0)` crashes on zero-valued inputs

### Biomarker Coefficients (all 9 required)
| Biomarker | Unit | Coefficient |
|-----------|------|-------------|
| Albumin | g/L | -0.0336 |
| Creatinine | μmol/L | 0.0095 |
| Glucose | mmol/L | 0.1953 |
| CRP (ln) | ln(mg/L) | 0.0954 |
| Lymphocyte % | % | -0.0120 |
| MCV | fL | 0.0268 |
| RDW | % | 0.3306 |
| Alkaline Phosphatase | U/L | 0.00188 |
| WBC | 10³/μL | 0.0554 |

## Security Standards

### Encryption
- All patient data **MUST** be AES-256 encrypted using the key in `.env`
- Key variable: `PHENOAGE_ENCRYPTION_KEY`
- Storage backend: `storage/secure_storage.py` (Fernet symmetric encryption)

### Patient Identity
- Patient IDs are **deterministic SHA-256 hashes** — never store raw PII
- This enables longitudinal lookup without exposing identifying information
- Implementation: `storage/secure_storage.py`

## Clinical Guardrails

### Completeness
- All 9 biomarkers are **required**
- Raise `ValueError` on any missing or None input — never impute silently

### Numerical Safety
```python
np.log(crp + 0.001)  # epsilon prevents log(0) crash
```

## Architecture
```
core/calculator.py        # PhenoAgeCalculatorV2 — Levine algorithm + unit conversions
storage/secure_storage.py # Fernet encryption + SHA-256 patient ID hashing + Excel I/O
storage/audit_logger.py   # PHI-free CSV audit log (HIPAA compliance)
app.py                    # Streamlit UI entry point
tests/                    # pytest test suite
```

## Build & Test Commands
```bash
# Run the application
streamlit run app.py

# Run all tests
pytest tests/

# System integrity check
python check_integrity.py
```
