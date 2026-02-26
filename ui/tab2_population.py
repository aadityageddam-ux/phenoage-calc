"""
Population Analysis Tab — NHANES 1999-2000 Cohort Validation

Validates the PhenoAge implementation against Levine 2018 using the full
NHANES dataset. Runs Cox proportional hazards regression and confirms
the engine reproduces the published Hazard Ratio (HR ≈ 1.08).

Scientific Reference:
    Levine ME, et al. (2018). Aging, 10(4):573-591. PMID: 29676998
"""

import os
import traceback
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend required for Streamlit
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import streamlit as st

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NHANES_DIR = Path("nhanes_data")
CACHE_DIR = Path("nhanes_cache")
CACHE_FILE = CACHE_DIR / "nhanes_phenoage_processed.parquet"

MORTALITY_FILE = NHANES_DIR / "NHANES_1999_2000_MORT_2019_PUBLIC.dat"

REQUIRED_XPT_FILES = {
    "DEMO.xpt": "Demographics",
    "LAB18.xpt": "Albumin / Glucose / Creatinine / ALP",
    "LAB11.xpt": "C-Reactive Protein",
    "LAB25.xpt": "WBC / Lymphocyte% / MCV / RDW",
}

VALIDATION_HR_MIN = 1.04
VALIDATION_HR_MAX = 1.12
VALIDATION_P_MAX = 0.001
VALIDATION_C_MIN = 0.70


# ---------------------------------------------------------------------------
# Helper: file status check
# ---------------------------------------------------------------------------

def _check_data_files() -> dict:
    """Return dict of {filename: bool} for each required file."""
    status = {}
    for fname in REQUIRED_XPT_FILES:
        status[fname] = (NHANES_DIR / fname).exists()
    status["NHANES_1999_2000_MORT_2019_PUBLIC.dat"] = MORTALITY_FILE.exists()
    return status


def _all_files_present(status: dict) -> bool:
    return all(status.values())


# ---------------------------------------------------------------------------
# Helper: run full NHANES pipeline
# ---------------------------------------------------------------------------

def _run_pipeline() -> pd.DataFrame:
    """
    Load NHANES data, compute PhenoAge for each participant, merge mortality.

    Returns:
        DataFrame with columns: seqn, age, phenoage, delta_age, deceased, followup_years
    """
    from core.calculator import PhenoAgeCalculatorV2
    from data.nhanes_loader import NHANESLoaderV2
    from data.mortality_loader import MortalityLoaderV2

    # Step 1: Load and clean NHANES biomarker data
    loader = NHANESLoaderV2(str(NHANES_DIR))
    df_raw = loader.load_and_merge()
    df_clean = loader.clean_data(df_raw)

    # Step 2: Calculate PhenoAge for all participants
    calculator = PhenoAgeCalculatorV2()
    df_pheno = calculator.calculate_batch(df_clean)

    # Step 3: Load mortality linkage
    mort_loader = MortalityLoaderV2(str(MORTALITY_FILE))
    df_mort = mort_loader.load_mortality()

    # Step 4: Merge
    df_merged = mort_loader.merge_with_phenoage(df_pheno, df_mort)

    return df_merged


# ---------------------------------------------------------------------------
# Helper: load or build cached DataFrame
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def _load_population_data() -> pd.DataFrame:
    """Load from Parquet cache if available, otherwise run full pipeline."""
    if CACHE_FILE.exists():
        return pd.read_parquet(CACHE_FILE)

    df = _run_pipeline()
    CACHE_DIR.mkdir(exist_ok=True)
    df.to_parquet(CACHE_FILE, index=False)
    return df


# ---------------------------------------------------------------------------
# Helper: run Cox regression
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def _run_cox(cache_mtime: float) -> dict:
    """Run Cox model on the population DataFrame. Cached by Parquet file mtime."""
    df = pd.read_parquet(CACHE_FILE)
    from analysis.population_validation import PopulationValidator
    validator = PopulationValidator()
    return validator.calculate_hazard_ratio(df)


# ---------------------------------------------------------------------------
# Visualizations
# ---------------------------------------------------------------------------

def _plot_acceleration_histogram(df: pd.DataFrame) -> plt.Figure:
    """Histogram of PhenoAge acceleration with KDE overlay."""
    fig, ax = plt.subplots(figsize=(9, 4))

    sns.histplot(
        df["delta_age"],
        bins=30,
        color="#4a90d9",
        alpha=0.6,
        stat="density",
        ax=ax,
        label="Distribution",
    )
    sns.kdeplot(
        df["delta_age"],
        color="#e05c35",
        linewidth=2,
        ax=ax,
        label="KDE",
    )

    ax.axvline(0, color="#555555", linestyle="--", linewidth=1.2, label="No acceleration")
    ax.set_xlabel("PhenoAge Acceleration (years)", fontsize=12)
    ax.set_ylabel("Density", fontsize=12)
    ax.set_title("Population Distribution of PhenoAge Acceleration", fontsize=13)
    ax.legend()
    fig.tight_layout()
    return fig


def _build_quartile_table(df: pd.DataFrame) -> pd.DataFrame:
    """Build mortality rate table by acceleration quartile."""
    df = df.copy()
    df["quartile"] = pd.qcut(
        df["delta_age"], q=4, labels=["Q1 (Slowest)", "Q2", "Q3", "Q4 (Fastest)"]
    )
    result = (
        df.groupby("quartile", observed=True)
        .agg(
            N=("deceased", "count"),
            Deaths=("deceased", "sum"),
        )
        .reset_index()
    )
    result["Mortality Rate"] = (result["Deaths"] / result["N"] * 100).round(1).astype(str) + "%"
    result.columns = ["Quartile (Acceleration)", "N", "Deaths", "Mortality Rate"]
    return result


# ---------------------------------------------------------------------------
# Main render function
# ---------------------------------------------------------------------------

def render_tab2() -> None:
    """Render the Population Analysis tab."""
    st.header("Population Analysis & Mortality Validation")
    st.markdown(
        "_Validates this PhenoAge implementation against the Levine 2018 NHANES cohort. "
        "The Cox model should reproduce HR ≈ 1.08 per 1-year increase in PhenoAge._"
    )
    st.divider()

    # -----------------------------------------------------------------------
    # A. Data Status Panel
    # -----------------------------------------------------------------------
    st.subheader("Data Status")

    file_status = _check_data_files()
    all_present = _all_files_present(file_status)
    cache_exists = CACHE_FILE.exists()

    col_files, col_cache = st.columns([3, 1])

    with col_files:
        st.markdown("**Required NHANES files** (place in `nhanes_data/`):")
        for fname, description in REQUIRED_XPT_FILES.items():
            icon = "✅" if file_status[fname] else "❌"
            st.markdown(f"{icon} `{fname}` — {description}")
        mort_icon = "✅" if file_status["NHANES_1999_2000_MORT_2019_PUBLIC.dat"] else "❌"
        st.markdown(f"{mort_icon} `NHANES_1999_2000_MORT_2019_PUBLIC.dat` — Mortality linkage (2019)")

    with col_cache:
        st.markdown("**Cache:**")
        if cache_exists:
            cache_size = CACHE_FILE.stat().st_size // 1024
            st.success(f"Parquet cached\n({cache_size} KB)")
            if st.button("Clear Cache"):
                CACHE_FILE.unlink()
                st.cache_data.clear()
                st.rerun()
        else:
            st.info("No cache\n(will be built on first run)")

    if not all_present and not cache_exists:
        st.warning(
            "Missing required data files. Download NHANES 1999-2000 XPT files and "
            "the mortality linkage file, then place them in the `nhanes_data/` directory."
        )
        st.markdown(
            "**Download from CDC:**  \n"
            "[NHANES 1999-2000 Data Files](https://wwwn.cdc.gov/nchs/nhanes/continuousnhanes/default.aspx?BeginYear=1999)  \n"
            "[Mortality Linkage Files](https://www.cdc.gov/nchs/data-linkage/mortality-public.htm)"
        )
        st.stop()

    st.divider()

    # -----------------------------------------------------------------------
    # B. Load & Analyze trigger
    # -----------------------------------------------------------------------
    if not cache_exists:
        st.info("All required files detected. Click below to process the population data.")
        if not st.button("Load & Analyze Population Data", type="primary"):
            st.stop()

    # -----------------------------------------------------------------------
    # C. Load data (from cache or pipeline)
    # -----------------------------------------------------------------------
    try:
        if cache_exists:
            df = pd.read_parquet(CACHE_FILE)
        else:
            with st.spinner("Processing NHANES pipeline — this may take ~30 seconds..."):
                df = _load_population_data()
    except Exception as exc:
        st.error(f"Failed to load population data: {exc}")
        with st.expander("Error details"):
            st.code(traceback.format_exc())
        st.stop()

    # Validate required columns
    required_cols = {"phenoage", "age", "delta_age", "deceased", "followup_years"}
    if not required_cols.issubset(df.columns):
        missing = required_cols - set(df.columns)
        st.error(f"Processed data is missing columns: {missing}. Clear cache and re-run.")
        st.stop()

    # -----------------------------------------------------------------------
    # D. Summary Metrics
    # -----------------------------------------------------------------------
    st.subheader("Cohort Summary")

    n_total = len(df)
    n_deaths = int(df["deceased"].sum())
    mortality_pct = n_deaths / n_total * 100
    mean_followup = df["followup_years"].mean()

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Participants", f"{n_total:,}")
    m2.metric("Deaths During Follow-up", f"{n_deaths:,}", f"{mortality_pct:.1f}%")
    m3.metric("Mean Follow-up", f"{mean_followup:.1f} yrs")

    st.divider()

    # -----------------------------------------------------------------------
    # E. Age Acceleration Distribution
    # -----------------------------------------------------------------------
    st.subheader("PhenoAge Acceleration Distribution")

    fig = _plot_acceleration_histogram(df)
    st.pyplot(fig)
    plt.close(fig)

    st.divider()

    # -----------------------------------------------------------------------
    # F. Mortality Rate by Acceleration Quartile
    # -----------------------------------------------------------------------
    st.subheader("Mortality Rate by Acceleration Quartile")

    quartile_df = _build_quartile_table(df)
    st.dataframe(quartile_df, use_container_width=True, hide_index=True)

    st.divider()

    # -----------------------------------------------------------------------
    # G. Cox Regression Results
    # -----------------------------------------------------------------------
    st.subheader("Cox Proportional Hazards Regression")

    try:
        with st.spinner("Fitting Cox model..."):
            cox_results = _run_cox(CACHE_FILE.stat().st_mtime)
    except Exception as exc:
        st.error(f"Cox regression failed: {exc}")
        with st.expander("Error details"):
            st.code(traceback.format_exc())
        st.stop()

    col_pheno, col_age = st.columns(2)

    with col_pheno:
        st.markdown("**PhenoAge (Primary Predictor)**")
        hr = cox_results["phenoage_hr"]
        ci_lo, ci_hi = cox_results["phenoage_ci"]
        pval = cox_results["phenoage_p"]
        c_stat = cox_results["phenoage_c_statistic"]

        st.metric("Hazard Ratio", f"{hr:.4f}")
        st.caption(f"95% CI: ({ci_lo:.4f}, {ci_hi:.4f})")
        st.metric("P-value", f"{pval:.2e}")
        st.metric("C-statistic", f"{c_stat:.4f}")
        st.caption(
            f"Each 1-year increase in PhenoAge → "
            f"{(hr - 1) * 100:.1f}% higher mortality risk"
        )

    with col_age:
        st.markdown("**Chronological Age (Baseline)**")
        age_hr = cox_results["age_hr"]
        age_ci_lo, age_ci_hi = cox_results["age_ci"]
        age_p = cox_results["age_p"]

        st.metric("Hazard Ratio", f"{age_hr:.4f}")
        st.caption(f"95% CI: ({age_ci_lo:.4f}, {age_ci_hi:.4f})")
        st.metric("P-value", f"{age_p:.2e}")
        st.caption("Comparison baseline — chronological age only")

    st.divider()

    # -----------------------------------------------------------------------
    # H. Levine 2018 Consistency Check
    # -----------------------------------------------------------------------
    st.subheader("Levine 2018 Consistency Check")
    st.markdown(
        f"_Benchmark: HR ≈ 1.08 (95% CI: 1.06–1.10), C-statistic 0.73–0.82_"
    )

    hr_pass = VALIDATION_HR_MIN <= hr <= VALIDATION_HR_MAX
    p_pass = pval < VALIDATION_P_MAX
    c_pass = c_stat > VALIDATION_C_MIN
    all_pass = hr_pass and p_pass and c_pass

    check_col1, check_col2, check_col3 = st.columns(3)

    with check_col1:
        label = "PASS" if hr_pass else "FAIL"
        icon = "✅" if hr_pass else "❌"
        st.markdown(f"**HR in [{VALIDATION_HR_MIN}, {VALIDATION_HR_MAX}]**")
        if hr_pass:
            st.success(f"{icon} {label}  (HR = {hr:.4f})")
        else:
            st.error(f"{icon} {label}  (HR = {hr:.4f})")

    with check_col2:
        label = "PASS" if p_pass else "FAIL"
        icon = "✅" if p_pass else "❌"
        st.markdown(f"**P-value < {VALIDATION_P_MAX}**")
        if p_pass:
            st.success(f"{icon} {label}  (p = {pval:.2e})")
        else:
            st.error(f"{icon} {label}  (p = {pval:.2e})")

    with check_col3:
        label = "PASS" if c_pass else "FAIL"
        icon = "✅" if c_pass else "❌"
        st.markdown(f"**C-statistic > {VALIDATION_C_MIN}**")
        if c_pass:
            st.success(f"{icon} {label}  (C = {c_stat:.4f})")
        else:
            st.error(f"{icon} {label}  (C = {c_stat:.4f})")

    st.divider()

    if all_pass:
        st.success(
            "### ✓ OVERALL: PASS\n"
            "This implementation reproduces the Levine 2018 benchmark. "
            "The PhenoAge formula, unit conversions, and coefficients are scientifically validated."
        )
    else:
        st.error(
            "### ✗ OVERALL: FAIL\n"
            "One or more validation criteria not met. "
            "Review formula, coefficients, and unit conversions."
        )
