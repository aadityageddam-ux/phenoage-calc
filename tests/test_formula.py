"""Calculation regression tests; fixtures independently evaluated from BioAge in R."""
import numpy as np
import pandas as pd
import pytest
from core.calculator import PhenoAgeCalculatorV2, calculate_phenoage_single
from core.calculator_v2b import PhenoAgeCalculatorV2B

BASE = dict(albumin=4.2, creatinine=.9, glucose=95, crp=.1,
            lymphocyte_pct=30, mcv=90, rdw=13, alp=65, wbc=6.5, age=50)
OLDER = dict(albumin=3.7, creatinine=1.2, glucose=130, crp=.5,
             lymphocyte_pct=22, mcv=94, rdw=15, alp=95, wbc=8.5, age=70)

@pytest.mark.parametrize('row,expected', [(BASE,43.70363251372635),(OLDER,83.53337985334832)])
def test_independent_reference(row,expected):
    assert calculate_phenoage_single(**row)['phenoage'] == pytest.approx(expected,abs=1e-10)

def test_crp_units_equivalent():
    mgdl = calculate_phenoage_single(**BASE)
    mgl = calculate_phenoage_single(**(BASE | {'crp':1}),crp_unit='mg/L')
    assert mgl == mgdl
    assert mgdl['intermediate_values']['log_crp'] == pytest.approx(np.log(.1))

@pytest.mark.parametrize('change', [{'glucose':None},{'albumin':np.nan},{'crp':0},{'crp':-1},{'age':True},{'mcv':np.inf},{'wbc':'6.5'}])
def test_single_and_batch_reject_same_invalid_inputs(change):
    row=BASE | change
    with pytest.raises(ValueError): calculate_phenoage_single(**row)
    with pytest.raises(ValueError,match='Row 1'):
        PhenoAgeCalculatorV2().calculate_batch(pd.DataFrame([BASE,row]))

def test_batch_preserves_identity_and_does_not_mutate_input():
    df=pd.DataFrame([OLDER,BASE],index=['subject-b','subject-a'])
    original=df.copy(deep=True)
    result=PhenoAgeCalculatorV2().calculate_batch(df)
    pd.testing.assert_frame_equal(df,original)
    assert list(result.index)==list(df.index)
    assert result.phenoage.tolist()==pytest.approx([83.53337985334832,43.70363251372635])
    assert result.delta_age.tolist()==pytest.approx([13.53337985334832,-6.29636748627365])

def test_batch_rejects_missing_columns_and_invalid_unit():
    calc=PhenoAgeCalculatorV2()
    with pytest.raises(ValueError,match='Missing required columns'):
        calc.calculate_batch(pd.DataFrame([BASE]).drop(columns='crp'))
    with pytest.raises(ValueError,match='crp_unit'):
        calc.calculate_batch(pd.DataFrame([BASE]),crp_unit='unknown')

def test_extreme_calculation_is_not_capped():
    a=calculate_phenoage_single(**(BASE | {'rdw':30}))
    b=calculate_phenoage_single(**(BASE | {'rdw':40}))
    assert b['phenoage'] > a['phenoage'] > 100
    assert np.isfinite(b['phenoage'])

def test_alternate_entry_point_uses_same_formula():
    assert PhenoAgeCalculatorV2B().calculate_phenoage(**BASE)==calculate_phenoage_single(**BASE)

def test_empty_batch_has_result_columns():
    result=PhenoAgeCalculatorV2().calculate_batch(pd.DataFrame(columns=BASE))
    assert result.empty and 'phenoage' in result
