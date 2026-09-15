"""Legacy import path; new code should import phenoage_calc."""
from phenoage_calc import PhenoAgeCalculatorV2, calculate_phenoage_single, __version__

__all__ = ['PhenoAgeCalculatorV2', 'calculate_phenoage_single']
