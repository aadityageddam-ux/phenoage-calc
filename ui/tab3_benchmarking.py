"""
Population Benchmarking Tab — Individual vs. NHANES Cohort

Compares a patient's PhenoAge acceleration (from Tab 1) against an
age-matched subgroup of the NHANES 1999-2000 population, giving context
on where their biological aging rate falls relative to their peers.

Requires:
    - Tab 1 calculation stored in st.session_state["last_result"]
    - NHANES population cache at nhanes_cache/nhanes_phenoage_processed.parquet
"""

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from scipy import stats

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CACHE_FILE = Path("nhanes_cache") / "nhanes_phenoage_processed.parquet"

# Aging category thresholds (consistent with Tab 1)
ACCELERATED_THRESHOLD = 5.0
DECELERATED_THRESHOLD = -5.0

# Minimum cohort size before falling back to full population
MIN_COHORT_SIZE = 30

# Age band for matching (±2 years)
AGE_BAND = 2


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


@st.cache_data(show_spinner=False)
def _load_population_data() -> pd.DataFrame | None:
    """Load NHANES processed cache (built by Tab 2). Returns None if missing."""
    if not CACHE_FILE.exists():
        return None
    return pd.read_parquet(CACHE_FILE)


# ---------------------------------------------------------------------------
# Benchmarking helpers
# ---------------------------------------------------------------------------


def _get_age_matched_cohort(df: pd.DataFrame, patient_age: float) -> pd.DataFrame:
    """Filter to participants within ±AGE_BAND years of patient_age."""
    cohort = df[df["age"].between(patient_age - AGE_BAND, patient_age + AGE_BAND)].copy()
    if len(cohort) < MIN_COHORT_SIZE:
        # Fall back to full population if cohort is too small
        cohort = df.copy()
    return cohort


def _calculate_percentile(cohort: pd.DataFrame, patient_delta: float) -> float:
    """Percentile rank: fraction of cohort with acceleration LESS than patient's."""
    return stats.percentileofscore(cohort["delta_age"], patient_delta, kind="rank")


def _assign_category(delta_age: float) -> tuple[str, str]:
    """Return (category label, streamlit message type)."""
    if delta_age > ACCELERATED_THRESHOLD:
        return "Accelerated", "warning"
    if delta_age < DECELERATED_THRESHOLD:
        return "Decelerated", "success"
    return "Normal", "info"


def _build_histogram(
    cohort: pd.DataFrame,
    patient_delta: float,
    patient_age: float,
    used_fallback: bool,
) -> go.Figure:
    """Interactive Plotly histogram with KDE, patient marker, and mean marker."""
    cohort_mean = cohort["delta_age"].mean()
    n = len(cohort)

    # KDE line
    kde_x = np.linspace(cohort["delta_age"].min() - 1, cohort["delta_age"].max() + 1, 200)
    kde = stats.gaussian_kde(cohort["delta_age"])
    kde_y = kde(kde_x) * n  # scale density to counts

    if used_fallback:
        title = f"Full Population Distribution (n={n}) — cohort too small for age band"
    else:
        lo = int(patient_age - AGE_BAND)
        hi = int(patient_age + AGE_BAND)
        title = f"Age-Matched Cohort Distribution (Age {lo}–{hi}, n={n})"

    fig = go.Figure()

    # Histogram bars
    fig.add_trace(
        go.Histogram(
            x=cohort["delta_age"],
            nbinsx=30,
            name="Population",
            marker_color="rgba(74, 144, 217, 0.6)",
            marker_line=dict(color="rgba(74, 144, 217, 1)", width=0.5),
        )
    )

    # KDE overlay
    fig.add_trace(
        go.Scatter(
            x=kde_x,
            y=kde_y,
            mode="lines",
            name="KDE",
            line=dict(color="#e05c35", width=2),
        )
    )

    # Patient vertical line
    delta_label = f"You ({patient_delta:+.1f} yrs)"
    fig.add_vline(
        x=patient_delta,
        line=dict(color="red", width=2, dash="dash"),
        annotation_text=delta_label,
        annotation_position="top right",
        annotation_font=dict(color="red", size=13),
    )

    # Mean vertical line
    fig.add_vline(
        x=cohort_mean,
        line=dict(color="green", width=2, dash="dash"),
        annotation_text="Mean",
        annotation_position="top left",
        annotation_font=dict(color="green", size=13),
    )

    fig.update_layout(
        title=title,
        xaxis_title="Age Acceleration (Years)",
        yaxis_title="Count",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        bargap=0.05,
        height=420,
    )

    return fig


def _build_stats_table(
    patient_delta: float,
    cohort: pd.DataFrame,
    percentile: float,
) -> pd.DataFrame:
    """Detailed statistics DataFrame for display."""
    cohort_mean = cohort["delta_age"].mean()
    cohort_std = cohort["delta_age"].std()
    diff_from_mean = patient_delta - cohort_mean
    z_score = diff_from_mean / cohort_std if cohort_std > 0 else 0.0

    data = {
        "Metric": [
            "Patient Acceleration",
            "Cohort Mean",
            "Difference from Mean",
            "Cohort Std Dev",
            "Z-Score",
            "Percentile",
        ],
        "Value": [
            f"{patient_delta:+.2f} years",
            f"{cohort_mean:+.2f} years",
            f"{diff_from_mean:+.2f} years",
            f"{cohort_std:.2f} years",
            f"{z_score:+.2f}",
            f"{percentile:.1f}th",
        ],
    }
    return pd.DataFrame(data)


def _recommendations(category: str) -> str:
    """Return markdown recommendations based on aging category."""
    if category == "Accelerated":
        return (
            "**Your biological age is advancing faster than expected. Consider:**\n\n"
            "- Aerobic exercise ≥ 150 min/week (brisk walking, cycling, swimming)\n"
            "- Mediterranean-style diet (whole grains, vegetables, healthy fats, lean protein)\n"
            "- Sleep hygiene: 7–9 hours of quality sleep per night\n"
            "- Discuss these results with your healthcare provider\n"
            "- Consider retesting biomarkers in **6 months** to track progress"
        )
    if category == "Decelerated":
        return (
            "**Your biological age is advancing more slowly than expected — great work!**\n\n"
            "- Your current lifestyle appears to be working in your favor\n"
            "- Continue your healthy habits: exercise, diet, and sleep\n"
            "- Maintain annual biomarker monitoring to sustain this trajectory"
        )
    return (
        "**Your biological aging rate is within the normal range.**\n\n"
        "- Sustain your current healthy habits\n"
        "- Annual biomarker review is recommended for early detection of changes\n"
        "- Consider targeted lifestyle adjustments if specific biomarkers are borderline"
    )


# ---------------------------------------------------------------------------
# Main render function
# ---------------------------------------------------------------------------


def render_tab3() -> None:
    """Render the Population Benchmarking tab."""
    st.header("Population Benchmarking")
    st.markdown(
        "_See where your biological aging rate falls relative to age-matched peers "
        "in the NHANES 1999-2000 national survey._"
    )
    st.divider()

    # -----------------------------------------------------------------------
    # Guard: require Tab 1 result
    # -----------------------------------------------------------------------
    result = st.session_state.get("last_result")
    if result is None:
        st.warning(
            "No calculation found. Please complete a PhenoAge calculation in the "
            "**Clinical Calculator** tab first."
        )
        return

    patient_delta = result["delta_age"]
    patient_age = result["chronological_age"]
    patient_phenoage = result["phenoage"]

    # -----------------------------------------------------------------------
    # Guard: require NHANES cache
    # -----------------------------------------------------------------------
    with st.spinner("Loading population data…"):
        df = _load_population_data()

    if df is None:
        st.error(
            "Population data not found. Run the **Population Analysis** tab first "
            "to build the NHANES cache, then return here."
        )
        return

    # -----------------------------------------------------------------------
    # Build age-matched cohort
    # -----------------------------------------------------------------------
    cohort_raw = df[df["age"].between(patient_age - AGE_BAND, patient_age + AGE_BAND)]
    used_fallback = len(cohort_raw) < MIN_COHORT_SIZE
    cohort = _get_age_matched_cohort(df, patient_age)

    if used_fallback:
        st.info(
            f"Age-matched cohort (±{AGE_BAND} years) has only {len(cohort_raw)} participants — "
            "using the full population for comparison."
        )

    # -----------------------------------------------------------------------
    # Key metrics row
    # -----------------------------------------------------------------------
    percentile = _calculate_percentile(cohort, patient_delta)
    category, msg_type = _assign_category(patient_delta)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Biological Age", f"{patient_phenoage:.1f} yrs")
    with col2:
        st.metric(
            "Chronological Age",
            f"{patient_age:.0f} yrs",
            delta=f"{patient_delta:+.1f} yrs",
            delta_color="inverse",
        )
    with col3:
        st.metric("Percentile", f"{percentile:.0f}th")

    # Aging category banner
    banner_msg = f"**Aging Category: {category}**"
    if msg_type == "warning":
        st.warning(banner_msg + f" — your acceleration is faster than {percentile:.0f}% of age-matched peers.")
    elif msg_type == "success":
        st.success(banner_msg + f" — your acceleration is slower than {100 - percentile:.0f}% of age-matched peers.")
    else:
        st.info(banner_msg + " — your aging rate is within the typical range.")

    st.divider()

    # -----------------------------------------------------------------------
    # Distribution histogram
    # -----------------------------------------------------------------------
    st.subheader("Population Distribution")
    fig = _build_histogram(cohort, patient_delta, patient_age, used_fallback)
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # -----------------------------------------------------------------------
    # Detailed statistics
    # -----------------------------------------------------------------------
    st.subheader("Detailed Statistics")
    stats_df = _build_stats_table(patient_delta, cohort, percentile)
    st.dataframe(stats_df, hide_index=True, use_container_width=True)

    st.divider()

    # -----------------------------------------------------------------------
    # Recommendations
    # -----------------------------------------------------------------------
    st.subheader("Recommendations")
    st.markdown(_recommendations(category))
