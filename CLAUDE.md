# Project guidance

This repository is a calculation library. LabAge is the web interface.
Do not restore patient storage, aging-rate interpretations or population-validation claims.

- Use the full-precision clinical formula reproduced by BioAge, not an old generated specification.
- CRP defaults to mg/dL; accept mg/L only with the explicit unit argument. Log CRP in mg/dL.
- Require all ten numeric inputs. Reject nonfinite values and nonpositive CRP; do not impute or add an epsilon.
- Single and batch paths must share one implementation and preserve batch row order.
- Test numerical agreement independently. Plausible output ranges or a target hazard ratio do not prove correctness.
- Run `python -m pytest` and `python -m build`; check installation of the built wheel outside the checkout.
