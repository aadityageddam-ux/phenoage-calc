"""
PhenoAge Engine — Streamlit Application

Entry point for the clinical biological age calculator UI.

Usage:
    streamlit run app.py
"""

import logging
import streamlit as st

# Silence batch-processing debug output in the terminal
logging.basicConfig(level=logging.WARNING)

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
    st.subheader("Delete My Data")
    with st.expander("Right to deletion (HIPAA § 164.526)"):
        del_patient_id = st.number_input(
            "Patient ID to delete", min_value=1, value=1, step=1,
            key="del_patient_id",
        )
        del_confirm = st.checkbox(
            "I confirm I want to permanently delete all records for this Patient ID",
            key="del_confirm",
        )
        if st.button(
            "Delete My Data",
            disabled=not del_confirm or not st.session_state["storage_available"],
            type="secondary",
        ):
            try:
                # Load age before deletion so audit log is meaningful
                age_for_audit = 0.0
                record = st.session_state["storage"].load_patient_data(int(del_patient_id))
                if record is not None:
                    age_for_audit = record.get("calculation_results", {}).get(
                        "chronological_age", 0.0
                    )

                deleted = st.session_state["storage"].delete_patient_data(int(del_patient_id))
                if deleted:
                    st.session_state["audit"].log_deletion(
                        patient_id=int(del_patient_id),
                        age=age_for_audit,
                    )
                    st.success(f"All records for patient {int(del_patient_id)} deleted.")
                else:
                    st.warning(f"No records found for patient {int(del_patient_id)}.")
            except Exception as exc:
                st.error(f"Deletion failed: {exc}")

    st.divider()
    st.caption("Results are stored in `patient_data/` (encrypted Excel + audit log).")

# ---------------------------------------------------------------------------
# Main tab layout
# ---------------------------------------------------------------------------

tab1, tab2, tab3, tab4 = st.tabs(["Clinical Calculator", "Population Analysis", "Benchmarking", "Your Progress"])

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

with tab3:
    from ui.tab3_benchmarking import render_tab3
    render_tab3()

with tab4:
    from ui.tab4_progress import render_tab4
    render_tab4()
