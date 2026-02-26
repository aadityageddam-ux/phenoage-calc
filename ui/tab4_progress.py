"""
Tab 4: Your Progress — Longitudinal Aging Trajectory

Visualizes a patient's biological age trajectory over multiple measurements,
showing how PhenoAge has changed relative to chronological age over time.

Requires:
    - st.session_state["last_patient_id"] set by Tab 1 after a save
    - st.session_state["storage"] (SecureStorage instance)
    - st.session_state["storage_available"] == True
"""

from datetime import datetime

import plotly.graph_objects as go
import streamlit as st

# Minimum elapsed time (in years) to compute a meaningful Rate of Aging.
# Records saved within the same session will have near-zero elapsed time.
_MIN_YEARS_FOR_RATE = 1 / 365  # ~1 day


def _years_between(ts_early: str, ts_late: str) -> float:
    """Return fractional years between two ISO 8601 timestamp strings."""
    dt_early = datetime.fromisoformat(ts_early)
    dt_late = datetime.fromisoformat(ts_late)
    delta_seconds = (dt_late - dt_early).total_seconds()
    return delta_seconds / (365.25 * 24 * 3600)


def _fmt_rate(rate: float) -> str:
    """Format Rate of Aging for display, guarding against nan/inf."""
    try:
        if rate != rate or abs(rate) == float("inf"):  # nan or inf check
            return "N/A"
        return f"{rate:.2f} bio-yrs/yr"
    except Exception:
        return "N/A"


def render_tab4() -> None:
    """Render the longitudinal trajectory tab."""
    st.header("Your Progress")
    st.caption("Track how your biological age changes over time.")

    # Guard: storage must be available
    if not st.session_state.get("storage_available"):
        st.info("Secure storage is not configured. Enable it to track longitudinal progress.")
        return

    patient_id = st.session_state.get("last_patient_id")
    if patient_id is None:
        st.info(
            "No patient loaded. Run a calculation in **Clinical Calculator** and save it "
            "to begin tracking your trajectory."
        )
        return

    storage = st.session_state["storage"]
    history = storage.load_patient_history(patient_id)

    if len(history) < 2:
        st.info(
            f"Only **{len(history)}** record(s) found for Patient ID **{patient_id}**. "
            "Submit a second calculation using the same Patient ID in the **Clinical Calculator** "
            "tab to enable trajectory tracking."
        )
        return

    # Build trajectory data (already sorted oldest→newest by load_patient_history)
    records = []
    for rec in history:
        cr = rec["calculation_results"]
        records.append({
            "timestamp": rec["timestamp"],
            "chronological_age": cr["chronological_age"],
            "phenoage": cr["phenoage"],
            "delta_age": cr["delta_age"],
        })

    timestamps = [r["timestamp"] for r in records]
    chron_ages = [r["chronological_age"] for r in records]
    phenoages = [r["phenoage"] for r in records]
    delta_ages = [r["delta_age"] for r in records]

    # Compute Rate of Aging using actual calendar time from timestamps
    elapsed_years = _years_between(timestamps[0], timestamps[-1])
    if elapsed_years >= _MIN_YEARS_FOR_RATE:
        rate_of_aging = (phenoages[-1] - phenoages[0]) / elapsed_years
    else:
        rate_of_aging = float("nan")  # same-session records — not meaningful

    # Intervention Net Benefit: Pre_delta - Post_delta
    # Positive value = improvement (age acceleration decreased)
    net_benefit = delta_ages[0] - delta_ages[-1]

    # Format dates for display (date portion only)
    display_dates = [ts[:10] for ts in timestamps]

    # Metrics row
    col1, col2, col3 = st.columns(3)
    col1.metric("Measurements", len(records))

    if elapsed_years < _MIN_YEARS_FOR_RATE:
        col2.metric(
            "Rate of Aging",
            "Insufficient Data",
            help="Records were saved in the same session. Take a follow-up measurement later.",
        )
    else:
        col2.metric(
            "Rate of Aging",
            _fmt_rate(rate_of_aging),
            help="Biological years elapsed per calendar year (<1 = aging slower than average).",
        )

    col3.metric(
        "Intervention Net Benefit",
        f"{net_benefit:+.1f} yrs",
        delta=f"{net_benefit:+.1f} yrs",
        delta_color="normal",  # positive (improvement) renders green
        help="Pre − Post age acceleration. Positive = PhenoAge improved relative to chronological age.",
    )

    st.divider()

    # Plotly trajectory chart — X-axis is measurement date
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=display_dates,
            y=chron_ages,
            mode="lines+markers",
            name="Chronological Age",
            line=dict(color="#4a90d9", width=2, dash="dot"),
            marker=dict(size=6),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=display_dates,
            y=phenoages,
            mode="lines+markers",
            name="PhenoAge (Biological)",
            line=dict(color="#e05c35", width=2),
            marker=dict(size=8, symbol="circle"),
        )
    )

    fig.update_layout(
        title="Biological Age Trajectory",
        xaxis_title="Measurement Date",
        yaxis_title="Age (years)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=420,
        hovermode="x unified",
    )

    st.plotly_chart(fig, use_container_width=True)
