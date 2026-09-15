"""Clinical Phenotypic Age calculation library."""
from .calculator import PhenoAgeCalculatorV2, calculate_phenoage_single

PhenoAgeCalculator = PhenoAgeCalculatorV2
__version__ = '3.0.0'
__all__ = ['PhenoAgeCalculator', 'PhenoAgeCalculatorV2', 'calculate_phenoage_single']
