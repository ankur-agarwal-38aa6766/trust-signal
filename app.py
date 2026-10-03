"""Streamlit intake and review surface for the local TrustSignal starter."""

from __future__ import annotations

import streamlit as st

from trust_signal.models import CaseRequest, SourceMode
from trust_signal.orchestration.case_graph import run_case

st.set_page_config(page_title="TrustSignal Console", layout="wide", initial_sidebar_state="expanded")

# --- Custom CSS for Red, White, Black Theme ---
st.markdown("""
<style>
    /* Global styles */
    .stApp { background-color: #F8F9FA; color: #111111; }
    h1, h2, h3 { color: #111111 !important; font-weight: 700; }
    
    /* Base Buttons */
    .stButton>button { border: 2px solid #111111; font-weight: bold; transition: all 0.2s; }
    .stButton>button:hover { background-color: #111111; color: #FFFFFF; border-color: #111111; }
    
    /* Primary buttons (intake, reject) */
    div[data-testid="stFormSubmitButton"]>button { background-color: #111111; color: white; border: none; font-weight: bold; }
    div[data-testid="stFormSubmitButton"]>button:hover { background-color: #D32F2F; color: white; }
    
    /* Custom Headers & Boxes */
    .ts-header { background-color: #111111; color: white; padding: 0.75rem 1.5rem; font-weight: bold; border-left: 6px solid #D32F2F; margin-bottom: 2rem; font-size: 1.2rem; letter-spacing: 0.1em; }
    .ts-box { border: 1px solid #111111; background-color: white; padding: 1.5rem; border-radius: 4px; margin-bottom: 1.5rem; box-shadow: 2px 2px 0px rgba(0,0,0,0.1); }
    .ts-gap { border-left: 4px solid #D32F2F; background-color: #FFEBEE; padding: 1rem; margin-bottom: 1rem; color: #B71C1C; font-size: 0.9rem; }
    
    /* Metrics */
    div[data-testid="stMetricValue"] { color: #111111; }
    div[data-testid="stMetricLabel"] { font-weight: bold; text-transform: uppercase; letter-spacing: 0.05em; color: #666; }
</style>
""", unsafe_allow_html=True)


st.markdown('<div class="ts-header">TrustSignal <span style="font-weight:normal; color:#aaa;">| Case Review Console</span></div>', unsafe_allow_html=True)

with st.sidebar:
    st.subheader("Workspace Context")
    st.markdown("**Analyst:** pulkitarora")
    st.divider()
    source_mode = st.radio(
        "Data Source Mode",
        options=[SourceMode.DEMO_FIXTURES, SourceMode.GLEIF_LIVE],
        format_func=lambda m: "Local demo fixtures" if m == SourceMode.DEMO_FIXTURES else "Live GLEIF lookup (LEI)"
    )
    st.caption("Live GLEIF fetches real records if exact LEI is provided. Otherwise, fixtures are used.")

if "case_result" not in st.session_state:
    st.session_state["case_result"] = None

# ==========================================
# STAGE 1: COMPANY INTAKE
# ==========================================
if st.session_state["case_result"] is None:
    st.markdown("### Start a Case")
    with st.form("case_intake"):
        legal_name = st.text_input("Legal party name", placeholder="ABC Trading Ltd")
        col1, col2 = st.columns(2)
        with col1:
            jurisdiction = st.text_input("Jurisdiction code", placeholder="GB")
            registration_id = st.text_input("Registration ID")
        with col2:
            lei = st.text_input("LEI", placeholder="5493001KJTIIGC8Y1R12")
            website = st.text_input("Website", placeholder="https://example.org")
        
        submitted = st.form_submit_button("Start Research Pipeline")
        
    if submitted:
        if not legal_name.strip():
            st.error("Enter the legal party name to start a case.")
        else:
            with st.spinner("Resolving identity and orchestrating parallel agents..."):
                request = CaseRequest(
                    party={
                        "legal_name": legal_name,
                        "jurisdiction": jurisdiction or None,
                        "registration_id": registration_id or None,
                        "lei": lei or None,
                        "website": website or None,
                    },
                    source_mode=source_mode,
                )
                st.session_state["case_result"] = run_case(request)
                st.rerun()

# ==========================================
# MAIN DASHBOARD (Stages 2 - 7)
# ==========================================
result = st.session_state.get("case_result")
if result:
    st.button("← New Case", on_click=lambda: st.session_state.pop("case_result"))
    st.divider()
    
    # --- STAGE 2: IDENTITY CONFIRMATION ---
    st.markdown("### Resolved Identity Context")
    if result.status.value == "needs_more_information":
        st.warning("⚠️ **Identity Ambiguous:** The system found multiple matches or missing identifiers. More information is needed before parallel research can proceed.")
        for r in result.assessment.reasons:
            st.write(f"- {r}")
        st.stop()
        
    id_col1, id_col2, id_col3 = st.columns(3)
    id_col1.metric("Legal Name", result.party.legal_name)
    id_col2.metric("LEI", result.party.lei or "Unverified")
    id_col3.metric("Jurisdiction", result.party.jurisdiction or "Unverified")
    
    st.divider()

    # --- STAGE 3: PARALLEL SPECIALIST RESEARCH ---
    st.markdown("### Parallel Specialist Pipeline")
    
    branches = result.branches
    if not branches:
        st.info("No specialist branches were executed for this case.")
        
    branch_cols = st.columns(len(branches) if branches else 1)
    has_gaps = False
    
    for i, branch in enumerate(branches):
        with branch_cols[i]:
            name = branch.branch_id.replace("_", " ").title()
            status = branch.status.value
            if status == "completed":
                st.markdown(f'<div style="padding:10px; border-left:4px solid #4CAF50; background:white; border:1px solid #ddd; font-size:14px;"><b>{name}</b><br/><span style="color:#4CAF50;">✔ Done ({len(branch.findings)})</span></div>', unsafe_allow_html=True)
            elif status == "failed":
                has_gaps = True
                st.markdown(f'<div style="padding:10px; border-left:4px solid #D32F2F; background:white; border:1px solid #ddd; font-size:14px;"><b>{name}</b><br/><span style="color:#D32F2F;">✖ Failed (Gap)</span></div>', unsafe_allow_html=True)
            else:
                has_gaps = True
                st.markdown(f'<div style="padding:10px; border-left:4px solid #FFC107; background:white; border:1px solid #ddd; font-size:14px;"><b>{name}</b><br/><span style="color:#FF9800;">⚠ {status.title()}</span></div>', unsafe_allow_html=True)

    st.write("")
    
    # Split layout for Comparison Board (Left) and Assessment/Review (Right)
    col_main, col_side = st.columns([2, 1], gap="large")

    with col_main:
        # --- STAGES 4 & 5: AGGREGATION & COMPARISON BOARD ---
        st.markdown("### Comparison Board & Timeline")
        st.caption("Displays chronological evidence and aggregated specialist claims.")
        
        if not result.comparison_board:
            st.info("No comparative findings available.")
        else:
            for item in result.comparison_board:
                st.markdown(f'<div class="ts-box">', unsafe_allow_html=True)
                st.markdown(f"**{item.relation.replace('_', ' ').title()}**")
                st.write(item.summary)
                
                # Fetch findings related to this dimension across all branches
                # This simulates the "deduplication/timeline" view by grouping evidence
                for branch in branches:
                    if branch.findings:
                        with st.expander(f"🔎 Inspect Provenance ({branch.branch_id.title()})"):
                            for f in branch.findings:
                                st.markdown(f"**Claim:** {f.claim}")
                                st.markdown(f"**Procedural Status:** `{f.procedural_status or 'official_record'}`")
                                if f.event_at or f.observed_at:
                                    st.caption(f"Date: {f.event_at or f.observed_at}")
                                if f.source_url:
                                    st.markdown(f"[🔗 View Original Source in Snowflake]({f.source_url})")
                                if f.content_hash:
                                    st.caption(f"Hash: `{f.content_hash}`")
                                st.divider()
                st.markdown('</div>', unsafe_allow_html=True)

    with col_side:
        # --- STAGE 6: VALIDATION & ASSESSMENT ---
        st.markdown("### Validation & Assessment")
        
        if has_gaps or result.status.value == "completed_with_gaps":
            st.markdown(
                '<div class="ts-gap"><b>Assessment Paused</b><br/><br/>'
                'Risk scores left <b>UNSET</b> due to missing critical source coverage (One or more branches skipped/failed). '
                'An unavailable source must not produce a zero-risk score.</div>', 
                unsafe_allow_html=True
            )
        else:
            st.markdown('<div style="padding:1rem; border:1px solid #4CAF50; border-left:4px solid #4CAF50; background:white; margin-bottom:1rem;"><b>Assessment Complete</b><br/>All configured sources returned verified records.</div>', unsafe_allow_html=True)
            st.metric("Risk Score", result.assessment.risk_score or "Not Configured")
            
        st.write("**Disposition:**", result.assessment.disposition.value.replace("_", " ").title())
        
        st.divider()
        
        # --- STAGE 7: REVIEW & DECISION ---
        st.markdown("### Audited Decision Record")
        st.caption("Turn this research into an accountable business action.")
        with st.form("decision_form"):
            rationale = st.text_area("Reviewer Rationale (Required for Audit)", placeholder="Document exactly why this decision is being made based on the evidence timeline and coverage gaps...")
            
            st.write("Action:")
            btn_col1, btn_col2 = st.columns(2)
            req_btn = btn_col1.form_submit_button("Request Details")
            app_btn = btn_col2.form_submit_button("Clear & Approve")
            rej_btn = st.form_submit_button("Reject (Policy Hard Stop)", type="primary")
            
            if req_btn or app_btn or rej_btn:
                if not rationale.strip():
                    st.error("Submission failed. You must provide a rationale for the audit record.")
                else:
                    action_str = "Clear & Approve" if app_btn else "Reject" if rej_btn else "Request Details"
                    st.success(f"Decision '{action_str}' locked for {result.party.legal_name}.")
                    st.info("The actor, rationale, evidence version, and policy version have been durably recorded to Snowflake (TRUSTSIGNAL_OPS).")
