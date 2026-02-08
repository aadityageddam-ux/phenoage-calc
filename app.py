"""
PhenoAge Engine — Streamlit Application

Entry point for the clinical biological age calculator UI.

Usage:
    streamlit run app.py
"""

import streamlit as st

# ---------------------------------------------------------------------------
# Page configuration (must be first Streamlit call)
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="PhenoAge Engine",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Session state initialization (runs once per browser session)
# ---------------------------------------------------------------------------

if "initialized" not in st.session_state:
    from core import PhenoAgeCalculatorV2
    from storage import SecureStorage, AuditLogger

    # Consent flow
    st.session_state["consent_given"] = False
    st.session_state["consent_dismissed"] = False

    # Calculation results
    st.session_state["last_result"] = None
    st.session_state["last_biomarkers"] = None
    st.session_state["last_patient_id"] = None

    # Storage feedback
    st.session_state["storage_save_status"] = None
    st.session_state["storage_error_msg"] = None

    # Core objects
    st.session_state["calculator"] = PhenoAgeCalculatorV2()

    # Storage — auto-create .env with fresh key if missing, then initialize
    from storage import setup_env_file
    setup_env_file()  # no-op if .env already exists; safe to call unconditionally
    try:
        st.session_state["storage"] = SecureStorage()
        st.session_state["audit"] = AuditLogger()
        st.session_state["storage_available"] = True
    except (ValueError, Exception) as exc:
        st.session_state["storage"] = None
        st.session_state["audit"] = None
        st.session_state["storage_available"] = False
        st.session_state["storage_init_error"] = str(exc)

    st.session_state["initialized"] = True

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("PhenoAge Engine")
    st.markdown("*Levine 2018 Biological Age Calculator*")
    st.divider()

    if not st.session_state["storage_available"]:
        st.warning(
            "Secure storage disabled — encryption key not configured.\n\n"
            "Add `PHENOAGE_ENCRYPTION_KEY` to `.env` to enable encrypted storage."
        )
        st.caption(f"Reason: {st.session_state.get('storage_init_error', 'Unknown')}")
    else:
        st.success("Secure storage active")

    st.divider()
    st.caption("Results are stored in `patient_data/` (encrypted Excel + audit log).")

# ---------------------------------------------------------------------------
# Main tab layout
# ---------------------------------------------------------------------------

tab1, tab2 = st.tabs(["Clinical Calculator", "Population Analysis"])

with tab1:
    from ui.tab1_calculator import render_tab1
    render_tab1(
        calculator=st.session_state["calculator"],
        storage=st.session_state["storage"],
        audit=st.session_state["audit"],
        storage_available=st.session_state["storage_available"],
    )

with tab2:
    from ui.tab2_population import render_tab2
    render_tab2()
