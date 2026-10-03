"""Analyst UI deployed as Streamlit in Snowflake.

The application submits durable case requests and reads only serving views.
The orchestration worker claims requests and writes case outcomes separately.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

import streamlit as st
from snowflake.snowpark.context import get_active_session

session = get_active_session()
st.set_page_config(page_title="TrustSignal", layout="wide")
st.title("TrustSignal")
st.caption("Evidence-led legal entity research")

# Single-tenant demo scaffolding. Replace with authenticated server-side tenancy
# plus Snowflake row-access policies before granting access to multiple tenants.
DEMO_TENANT_ID = "hackathon_demo"


def query(sql: str, params: list | None = None):
    return session.sql(sql, params=params or []).to_pandas()


def submit_case(
    legal_name: str,
    jurisdiction: str | None,
    registration_id: str | None,
    lei: str | None,
):
    case_id = f"case_{uuid4().hex}"
    request_id = f"request_{uuid4().hex}"
    tenant_id = DEMO_TENANT_ID
    requested_by = session.sql("SELECT CURRENT_USER()").collect()[0][0]
    requested_at = datetime.now(UTC)
    payload = {
        "schema_version": "1",
        "party": {
            "legal_name": legal_name,
            "jurisdiction": jurisdiction,
            "registration_id": registration_id,
            "lei": lei,
        },
        "source_mode": "configured_sources",
    }
    idempotency_key = f"ui:{requested_by}:{legal_name.casefold()}:{lei or registration_id or ''}"
    session.sql(
        """
        INSERT INTO TRUST_SIGNAL_CORE.CASE_REQUESTS (
          REQUEST_ID, CASE_ID, TENANT_ID, REQUEST_STATUS, IDEMPOTENCY_KEY,
          REQUESTED_BY, REQUESTED_AT, REQUEST_PAYLOAD
        )
        SELECT ?, ?, ?, 'queued', ?, ?, ?, PARSE_JSON(?)
        """,
        params=[
            request_id,
            case_id,
            tenant_id,
            idempotency_key,
            requested_by,
            requested_at.isoformat(),
            json.dumps(payload),
        ],
    ).collect()
    return case_id


intake, queue, sources = st.tabs(["New case", "Review queue", "Source coverage"])

with intake:
    st.caption("Hackathon demo tenant. Bind tenant identity to authenticated context before multi-tenant use.")
    with st.form("case_intake"):
        legal_name = st.text_input("Legal party name")
        first, second, third = st.columns(3)
        with first:
            jurisdiction = st.text_input("Jurisdiction", placeholder="GB")
        with second:
            registration_id = st.text_input("Registration ID")
        with third:
            lei = st.text_input("LEI")
        submitted = st.form_submit_button("Start research", type="primary")
    if submitted:
        if not legal_name.strip():
            st.error("Legal party name is required.")
        elif not (jurisdiction or registration_id or lei):
            st.error("Provide a jurisdiction, registration ID, or LEI to resolve the legal party.")
        else:
            case_id = submit_case(legal_name, jurisdiction or None, registration_id or None, lei or None)
            st.success(f"Case {case_id} was queued for research.")

with queue:
    cases = query(
        """
        SELECT CASE_ID, CASE_STATUS, IDENTITY_STATUS, LEGAL_NAME, JURISDICTION,
               LEI, RISK_SCORE, SCORE_STATUS, DISPOSITION, UPDATED_AT
        FROM TRUST_SIGNAL_SERVE.V_CASE_SUMMARY
        WHERE TENANT_ID = ?
        ORDER BY UPDATED_AT DESC
        LIMIT 100
        """,
        params=[DEMO_TENANT_ID],
    )
    st.dataframe(cases, width="stretch", hide_index=True)
    selected_case = st.text_input("Case ID to inspect", key="selected_case")
    if selected_case:
        findings = query(
            """
            SELECT BRANCH_ID, BRANCH_STATUS, CLAIM_TYPE, CLAIM, SUBJECT, SOURCE_ID,
                   SOURCE_RECORD_ID, CANONICAL_URL, OBSERVED_AT, VERIFICATION_STATUS,
                   PROCEDURAL_STATUS, LIMITATIONS
            FROM TRUST_SIGNAL_SERVE.V_CASE_FINDINGS
            WHERE CASE_ID = ? AND TENANT_ID = ?
            ORDER BY OBSERVED_AT DESC
            """,
            params=[selected_case, DEMO_TENANT_ID],
        )
        st.subheader("Evidence and findings")
        st.dataframe(findings, width="stretch", hide_index=True)

with sources:
    health = query(
        """
        SELECT SOURCE_ID, SOURCE_NAME, SOURCE_CLASS, JURISDICTIONS, ACCESS_METHOD,
               CATALOG_STATUS, EXPECTED_FRESHNESS_MINUTES, LAST_RUN_STATUS,
               LAST_RUN_COMPLETED_AT, MINUTES_SINCE_LAST_RUN, LAST_ERROR_CATEGORY
        FROM TRUST_SIGNAL_SERVE.V_SOURCE_HEALTH
        ORDER BY SOURCE_ID
        """
    )
    st.dataframe(health, width="stretch", hide_index=True)
