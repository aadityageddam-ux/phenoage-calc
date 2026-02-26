"""
Tab 1: Clinical PhenoAge Calculator

Implements the HIPAA-consent-gated biomarker input form, PhenoAge calculation,
encrypted storage, audit logging, and results visualization.

CRITICAL — CRP unit conversion:
  - UI displays CRP in mg/L (clinical standard, spec range 0.1–50.0)
  - Calculator expects CRP in mg/dL (NHANES standard)
  - Conversion applied before calling calculator: crp_nhanes = crp_ui / 10.0
"""

import streamlit as st
import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")  # Non-interactive backend for Streamlit

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BIOMARKER_SPECS = [
    {"key": "albumin",        "label": "Albumin",                      "unit": "g/dL",   "min": 1.0, "max": 7.0,  "step": 0.1, "default": 4.0,  "fmt": "%.1f", "ref": "3.5\u20135.5"},
    {"key": "creatinine",     "label": "Creatinine",                   "unit": "mg/dL",  "min": 0.1, "max": 5.0,  "step": 0.1, "default": 1.0,  "fmt": "%.1f", "ref": "0.7\u20131.3"},
    {"key": "glucose",        "label": "Glucose",                      "unit": "mg/dL",  "min": 50,  "max": 500,  "step": 1,   "default": 90,   "fmt": "%.0f", "ref": "70\u2013100"},
    {"key": "crp",            "label": "C-Reactive Protein",           "unit": "mg/L",   "min": 0.1, "max": 50.0, "step": 0.1, "default": 1.0,  "fmt": "%.1f", "ref": "0.0\u20133.0"},
    {"key": "lymphocyte_pct", "label": "Lymphocyte %",                 "unit": "%",      "min": 5.0, "max": 50.0, "step": 0.5, "default": 30.0, "fmt": "%.1f", "ref": "20\u201340"},
    {"key": "mcv",            "label": "MCV",                          "unit": "fL",     "min": 60,  "max": 120,  "step": 1,   "default": 90,   "fmt": "%.0f", "ref": "80\u2013100"},
    {"key": "rdw",            "label": "RDW",                          "unit": "%",      "min": 10.0, "max": 25.0, "step": 0.1, "default": 13.0, "fmt": "%.1f", "ref": "11.5\u201314.5"},
    {"key": "alp",            "label": "Alkaline Phosphatase (ALP)",   "unit": "U/L",    "min": 10,  "max": 500,  "step": 1,   "default": 70,   "fmt": "%.0f", "ref": "30\u2013120"},
    {"key": "wbc",            "label": "WBC",                          "unit": "10\u00b3/\u03bcL", "min": 1.0, "max": 30.0, "step": 0.1, "default": 7.0,  "fmt": "%.1f", "ref": "4.5\u201311.0"},
]

ACCELERATION_FAST_THRESHOLD = 5.0
ACCELERATION_SLOW_THRESHOLD = -5.0

HIPAA_CONSENT_TEXT = """
## Informed Consent — PhenoAge Biological Age Assessment

### What is this test?
This tool estimates your **biological age** (PhenoAge) from 9 standard laboratory
values using the Levine 2018 algorithm. Biological age reflects physiological
aging independent of calendar age.

### What data is collected?
- An anonymous numeric patient ID (hashed with SHA-256 before storage)
- Your chronological age
- 9 biomarker values from a standard CMP + CBC panel
- Date and time of assessment

### How is my data protected?
- All clinical data is encrypted with **AES-256** (Fernet) before being written to disk
- Patient identifiers are hashed — the original ID is never stored in plain text
- Audit logs record only timestamps and hashed IDs — **no clinical values appear in logs**
- Data is stored locally on this system only

### Important limitations
- ⚠️ This is **NOT** a clinical diagnostic tool
- Results should be discussed with a qualified healthcare provider
- PhenoAge is one metric; it does not capture all aspects of health
- This tool is **NOT** FDA-approved

### Your rights
- You may decline at any time
- You may request deletion of your records
- You may request access to audit logs for your records
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_tab1(calculator, storage, audit, storage_available: bool) -> None:
    """Top-level entry point called from app.py. Orchestrates consent gate and main UI."""
    st.header("PhenoAge Clinical Calculator")
    st.caption("Levine 2018 biological age algorithm — Levine ME et al., *Aging*, 2018")

    if st.session_state.get("consent_dismissed"):
        st.info("You declined the consent form. Refresh the page to start over.")
        return

    if not st.session_state.get("consent_given"):
        _render_consent_gate()
    else:
        _render_calculator_ui(calculator, storage, audit, storage_available)


# ---------------------------------------------------------------------------
# Consent gate
# ---------------------------------------------------------------------------

def _render_consent_gate() -> None:
    """Renders HIPAA consent section. Updates session state on user action."""
    st.markdown(HIPAA_CONSENT_TEXT)
    st.divider()

    cb1 = st.checkbox("I have read and understood this information", key="consent_cb1")
    cb2 = st.checkbox("I consent to secure data storage", key="consent_cb2")
    cb3 = st.checkbox("I understand this is not a diagnostic test", key="consent_cb3")

    all_checked = cb1 and cb2 and cb3

    col_accept, col_decline, _ = st.columns([2, 2, 8])
    with col_accept:
        if st.button("Accept and Continue", disabled=not all_checked, type="primary"):
            st.session_state["consent_given"] = True
            st.rerun()
    with col_decline:
        if st.button("Decline"):
            st.session_state["consent_dismissed"] = True
            st.rerun()


# ---------------------------------------------------------------------------
# Calculator UI (shown after consent)
# ---------------------------------------------------------------------------

def _render_calculator_ui(calculator, storage, audit, storage_available: bool) -> None:
    """Renders biomarker input form, handles calculation, and displays results."""
    with st.form("biomarker_form"):
        patient_id, age, ui_biomarkers = _render_input_form()
        submitted = st.form_submit_button("Calculate PhenoAge", type="primary")

    if submitted:
        nhanes_biomarkers = _convert_crp_to_nhanes(ui_biomarkers)
        result = _run_calculation(calculator, nhanes_biomarkers, age)
        if result is not None:
            st.session_state["last_result"] = result
            st.session_state["last_biomarkers"] = ui_biomarkers
            st.session_state["last_patient_id"] = patient_id
            _save_and_audit(storage, audit, patient_id, nhanes_biomarkers, result, storage_available)

    # Show storage status feedback
    save_status = st.session_state.get("storage_save_status")
    if save_status == "success":
        st.success("Results saved securely to encrypted storage.")
    elif save_status == "error":
        st.warning(f"Could not save results: {st.session_state.get('storage_error_msg')}")

    # Always show last results if available (persists across reruns)
    if st.session_state.get("last_result") is not None:
        st.divider()
        _render_results(st.session_state["last_result"])


def _render_input_form():
    """Renders all input widgets. Returns (patient_id, age, ui_biomarkers)."""
    st.subheader("Patient Information")
    col_pid, col_age, _ = st.columns([2, 2, 6])
    with col_pid:
        patient_id = st.number_input("Patient ID", min_value=1, value=1, step=1,
                                     help="Local identifier only \u2014 stored as SHA-256 hash")
    with col_age:
        age = st.number_input("Chronological Age (years)", min_value=20, max_value=90,
                              value=50, step=1)

    st.subheader("Laboratory Values")
    st.caption("Enter values from a recent CMP + CBC panel")

    ui_biomarkers = {}
    cols = st.columns(3)
    for i, spec in enumerate(BIOMARKER_SPECS):
        with cols[i % 3]:
            val = st.number_input(
                f"{spec['label']} ({spec['unit']})",
                min_value=float(spec["min"]),
                max_value=float(spec["max"]),
                value=float(spec["default"]),
                step=float(spec["step"]),
                format=spec["fmt"],
                key=f"input_{spec['key']}",
                help=f"Normal range: {spec['ref']} {spec['unit']}",
            )
            ui_biomarkers[spec["key"]] = val

    return int(patient_id), int(age), ui_biomarkers


# ---------------------------------------------------------------------------
# Unit conversion
# ---------------------------------------------------------------------------

def _convert_crp_to_nhanes(ui_biomarkers: dict) -> dict:
    """Convert CRP from mg/L (UI) to mg/dL (NHANES) for the calculator."""
    nhanes = dict(ui_biomarkers)
    nhanes["crp"] = ui_biomarkers["crp"] / 10.0
    return nhanes


# ---------------------------------------------------------------------------
# Calculation
# ---------------------------------------------------------------------------

def _run_calculation(calculator, nhanes_biomarkers: dict, age: int):
    """Call calculate_phenoage(). Returns result dict or None on error."""
    try:
        return calculator.calculate_phenoage(
            albumin=nhanes_biomarkers["albumin"],
            creatinine=nhanes_biomarkers["creatinine"],
            glucose=nhanes_biomarkers["glucose"],
            crp=nhanes_biomarkers["crp"],
            lymphocyte_pct=nhanes_biomarkers["lymphocyte_pct"],
            mcv=nhanes_biomarkers["mcv"],
            rdw=nhanes_biomarkers["rdw"],
            alp=nhanes_biomarkers["alp"],
            wbc=nhanes_biomarkers["wbc"],
            age=float(age),
        )
    except ValueError as exc:
        st.error(f"Calculation error: {exc}")
        return None
    except Exception:
        st.error("Unexpected error during calculation. Please check your input values.")
        return None


# ---------------------------------------------------------------------------
# Storage + audit
# ---------------------------------------------------------------------------

def _save_and_audit(storage, audit, patient_id: int, nhanes_biomarkers: dict,
                    result: dict, storage_available: bool) -> None:
    """Save encrypted record and write audit log entry."""
    # Reset status
    st.session_state["storage_save_status"] = None
    st.session_state["storage_error_msg"] = None

    if not storage_available:
        st.session_state["storage_save_status"] = "error"
        st.session_state["storage_error_msg"] = "Encryption key not configured (see sidebar)"
        return

    try:
        storage.save_patient_data(
            patient_id=int(patient_id),
            biomarkers=nhanes_biomarkers,
            results=result,
            metadata={"crp_ui_unit": "mg/L", "crp_stored_unit": "mg/dL"},
        )
        audit.log_calculation(
            patient_id=int(patient_id),
            chronological_age=result["chronological_age"],
        )
        st.session_state["storage_save_status"] = "success"
    except Exception as exc:
        st.session_state["storage_save_status"] = "error"
        st.session_state["storage_error_msg"] = str(exc)


# ---------------------------------------------------------------------------
# Results display
# ---------------------------------------------------------------------------

def _render_results(result: dict) -> None:
    """Render 3-column metrics, bar chart, and interpretation."""
    st.subheader("Your Results")
    _render_metrics(result)
    st.divider()
    _render_age_chart(result)
    st.divider()
    _render_interpretation(result["delta_age"])

    # New calculation button
    if st.button("New Calculation"):
        st.session_state["last_result"] = None
        st.session_state["last_biomarkers"] = None
        st.session_state["last_patient_id"] = None
        st.session_state["storage_save_status"] = None
        st.rerun()


def _render_metrics(result: dict) -> None:
    """Three-column st.metric display."""
    phenoage = result["phenoage"]
    chron_age = result["chronological_age"]
    delta_age = result["delta_age"]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Biological Age", f"{phenoage:.1f} yrs")
    with col2:
        st.metric("Chronological Age", f"{chron_age:.1f} yrs")
    with col3:
        # delta_color="inverse": positive → red (aging faster = bad),
        # negative → green (aging slower = good)
        st.metric(
            "Age Acceleration",
            f"{delta_age:+.1f} yrs",
            delta=f"{delta_age:.1f}",
            delta_color="inverse",
        )


def _render_age_chart(result: dict) -> None:
    """Horizontal bar chart comparing chronological vs biological age."""
    phenoage = result["phenoage"]
    chron_age = result["chronological_age"]
    delta_age = result["delta_age"]

    phenoage_color = "#d62728" if delta_age > 0 else "#2ca02c"

    fig, ax = plt.subplots(figsize=(8, 2))
    ax.barh(
        ["Chronological Age", "Biological Age (PhenoAge)"],
        [chron_age, phenoage],
        color=["#1f77b4", phenoage_color],
        height=0.5,
    )
    ax.set_xlabel("Age (years)")
    x_max = max(phenoage, chron_age) * 1.2
    ax.set_xlim(0, x_max)
    ax.set_title("Age Comparison")

    # Annotate bars with values
    ax.text(chron_age + x_max * 0.01, 0, f"{chron_age:.0f} yrs", va="center", fontsize=11)
    ax.text(phenoage + x_max * 0.01, 1, f"{phenoage:.1f} yrs", va="center", fontsize=11)

    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)  # Prevent memory accumulation in long-running sessions


def _render_interpretation(delta_age: float) -> None:
    """Display interpretation message based on age acceleration thresholds."""
    if delta_age > ACCELERATION_FAST_THRESHOLD:
        st.warning(
            f"Your biological age is **{delta_age:.1f} years OLDER** than your chronological age. "
            "This suggests accelerated aging, which is associated with higher disease risk. "
            "Consider discussing these results with your healthcare provider."
        )
    elif delta_age < ACCELERATION_SLOW_THRESHOLD:
        st.success(
            f"Your biological age is **{abs(delta_age):.1f} years YOUNGER** than your chronological age. "
            "This suggests healthy, decelerated aging."
        )
    else:
        st.info(
            f"Your biological age is within **{abs(delta_age):.1f} years** of your chronological age. "
            "This is consistent with normal aging."
        )
