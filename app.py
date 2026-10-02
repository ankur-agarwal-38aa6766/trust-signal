"""Streamlit intake and review surface for the local TrustSignal starter."""

from __future__ import annotations

import streamlit as st

from trust_signal.models import CaseRequest, SourceMode
from trust_signal.orchestration.case_graph import run_case

st.set_page_config(page_title="TrustSignal", layout="wide")
st.title("TrustSignal")
st.caption("Legal entity research workspace")

with st.sidebar:
    st.subheader("Case workspace")
    st.markdown("**Local demonstration mode**")
    st.caption("Live GLEIF lookup is available by exact LEI. Snowflake persistence is not connected.")

st.header("Start a case")
with st.form("case_intake"):
    source_mode = st.radio(
        "Research mode",
        options=[SourceMode.DEMO_FIXTURES, SourceMode.GLEIF_LIVE],
        format_func=lambda mode: "Local demo fixtures" if mode == SourceMode.DEMO_FIXTURES else "Live GLEIF LEI lookup",
        horizontal=True,
    )
    legal_name = st.text_input("Legal party name", placeholder="Example Organization Ltd")
    left, right = st.columns(2)
    with left:
        jurisdiction = st.text_input("Jurisdiction code", placeholder="GB")
        registration_id = st.text_input("Registration ID")
    with right:
        lei = st.text_input("LEI")
        website = st.text_input("Website", placeholder="https://example.org")
    submitted = st.form_submit_button("Start research", type="primary")

if submitted:
    if not legal_name.strip():
        st.error("Enter the legal party name to start a case.")
    else:
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

result = st.session_state.get("case_result")
if result:
    st.divider()
    st.subheader(result.party.legal_name)
    st.caption(f"Case {result.case_id} · {result.status.value.replace('_', ' ').title()}")
    if result.status.value == "needs_more_information":
        st.warning("More identity information is needed before research can run.")
        for reason in result.assessment.reasons:
            st.write(reason)
        for branch in result.branches:
            with st.expander(f"{branch.branch_id.title()} lookup evidence"):
                for finding in branch.findings:
                    st.write(finding.claim)
                    if finding.source_url:
                        st.markdown(f"[Open source record]({finding.source_url})")
    else:
        if any(
            finding.evidence_mode.value == "live_source"
            for branch in result.branches
            for finding in branch.findings
        ):
            st.info("GLEIF was queried for the exact LEI. This run only checks the registry identity record.")
        else:
            st.info("Local fixtures only. No external registries, news, sanctions, or legal sources were queried.")
        st.markdown("**Assessment**")
        st.write("Disposition: " + result.assessment.disposition.value.replace("_", " ").title())
        st.write("Score: Not scored · " + result.assessment.score_status.replace("_", " "))
        st.markdown("**Specialist branches**")
        st.dataframe(
            [
                {
                    "Branch": branch.branch_id.replace("_", " ").title(),
                    "Status": branch.status.value,
                    "Findings": len(branch.findings),
                    "Sources checked": "; ".join(branch.sources_checked),
                }
                for branch in result.branches
            ],
            hide_index=True,
            width="stretch",
        )
        st.markdown("**Comparison board**")
        for item in result.comparison_board:
            st.write(f"{item.relation.replace('_', ' ').title()} · {item.summary}")
        with st.expander("Branch limitations and findings"):
            for branch in result.branches:
                st.markdown(f"**{branch.branch_id.title()}**")
                for finding in branch.findings:
                    st.write(f"{finding.claim} ({finding.evidence_mode.value})")
                    if finding.source_url:
                        st.markdown(f"[Open source record]({finding.source_url})")
                    if finding.content_hash:
                        st.caption(f"Response hash: {finding.content_hash}")
                for limitation in branch.limitations:
                    st.caption(limitation)
