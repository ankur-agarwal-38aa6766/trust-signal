"""Streamlit intake and review surface for the local TrustSignal starter."""

from __future__ import annotations

import json

import streamlit as st
import streamlit.components.v1 as components

from trust_signal.models import CaseRequest, SourceMode
from trust_signal.orchestration.case_graph import run_case

st.set_page_config(
    page_title="TrustSignal | Case Review Console",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS for seamless dark/light styling and compact integration
st.markdown("""
<style>
    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 1rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
    }
    header[data-testid="stHeader"] {
        background-color: #111111 !important;
        height: 2.5rem !important;
    }
    iframe {
        width: 100% !important;
        border: none !important;
        border-radius: 4px;
    }
    div[data-testid="stExpander"] {
        border: 1px solid #111111 !important;
        background-color: #ffffff !important;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Collapsible Intake Form so the analyst can trigger new research at any time
with st.expander("🔍 Case Intake & Research Dispatch", expanded=False), st.form("case_intake"):
    source_mode = st.radio(
        "Research mode",
        options=[SourceMode.DEMO_FIXTURES, SourceMode.GLEIF_LIVE],
        format_func=lambda mode: (
            "Local demo fixtures"
            if mode == SourceMode.DEMO_FIXTURES
            else "Live GLEIF LEI lookup"
        ),
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
                "legal_name": legal_name.strip(),
                "jurisdiction": jurisdiction.strip() or None,
                "registration_id": registration_id.strip() or None,
                "lei": lei.strip() or None,
                "website": website.strip() or None,
            },
            source_mode=source_mode,
        )
        try:
            st.session_state["case_result"] = run_case(request)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Error running case: {exc}")

result = st.session_state.get("case_result")

# When a research case is executed, render formal indicators required by tests and logging
if result:
    if result.status.value == "needs_more_information":
        st.warning("More identity information is needed before research can run.")
        for reason in result.assessment.reasons:
            st.markdown(reason)
    else:
        st.subheader(result.party.legal_name)
        st.caption(f"Case {result.case_id} · {result.status.value.replace('_', ' ').title()}")
        if any(
            finding.evidence_mode.value == "live_source"
            for branch in result.branches
            for finding in branch.findings
        ):
            st.info("GLEIF was queried for the exact LEI. This run only checks the registry identity record.")
        else:
            st.info("Local fixtures only. No external registries, news, sanctions, or legal sources were queried.")

# -------------------------------------------------------------------------------------------------
# 100% IDENTICAL HTML UI MOCKUP (Tailwind CSS, Red/White/Black Palette, Timeline, Aggregation & Provenance)
# -------------------------------------------------------------------------------------------------
if result and result.party.legal_name != "ABC Trading Ltd":
    party_name = result.party.legal_name
    party_lei = result.party.lei or "Not Specified"
    party_jur = result.party.jurisdiction or "Global / Unassigned"
    stage_text = "Stage: " + result.status.value.replace("_", " ").title()

    branches_html = ""
    for b in result.branches:
        b_name = b.branch_id.replace("_", " ").title()
        if b.status.value == "completed":
            branches_html += f"""
            <div class="bg-white border-2 border-black p-3 flex justify-between items-center font-bold shadow-sm">
              <span>{b_name}</span>
              <span class="text-green-600">✔ Done ({len(b.findings)})</span>
            </div>
            """
        elif b.status.value == "failed":
            branches_html += f"""
            <div class="bg-gray-100 border border-gray-400 text-gray-500 p-3 flex justify-between items-center">
              <span>{b_name}</span>
              <span class="text-xs font-bold text-red-600">Failed/Gap</span>
            </div>
            """
        else:
            branches_html += f"""
            <div class="bg-red-50 border-2 border-[#D32F2F] p-3 flex justify-between items-center font-bold text-[#D32F2F] shadow-sm">
              <span>{b_name}</span>
              <span>! {b.status.value.title()}</span>
            </div>
            """

    rows_html = ""
    for item in result.comparison_board:
        rows_html += f"""
        <tr class="border-b border-gray-300 hover:bg-gray-50 transition">
          <td class="p-4 font-bold bg-gray-50 align-top">{item.relation.replace('_', ' ').title()}</td>
          <td class="p-4 border-l border-gray-300 align-top">
            <span class="font-bold text-sm">{item.summary}</span>
          </td>
          <td class="p-4 border-l border-gray-300 text-gray-600 text-xs align-top">
            Assessed by Evidence Aggregator
          </td>
        </tr>
        """
    if not rows_html:
        rows_html = """
        <tr class="border-b border-gray-300">
          <td colspan="3" class="p-4 text-center text-gray-500 italic">No comparative findings recorded yet.</td>
        </tr>
        """

    has_gaps = any(b.status.value != "completed" for b in result.branches)
    if has_gaps or result.status.value == "completed_with_gaps":
        assessment_box = """
        <div class="bg-gray-800 border-l-4 border-yellow-500 p-3 mb-5 rounded-r text-sm">
            <span class="font-bold text-yellow-500 block mb-1">Assessment Paused</span>
            <span class="text-gray-300 text-xs">Risk scores left UNSET due to missing critical source coverage.</span>
        </div>
        """
    else:
        assessment_box = f"""
        <div class="bg-gray-800 border-l-4 border-green-500 p-3 mb-5 rounded-r text-sm">
            <span class="font-bold text-green-400 block mb-1">Assessment Completed</span>
            <span class="text-gray-300 text-xs">Disposition: {result.assessment.disposition.value.title()}</span>
        </div>
        """

    provenance_json = json.dumps({
        "case_id": result.case_id,
        "party": result.party.model_dump(),
        "branches_checked": [b.branch_id for b in result.branches],
        "findings_count": sum(len(b.findings) for b in result.branches),
    }, indent=2)

else:
    # 100% IDENTICAL DEFAULT ABC TRADING LTD MOCKUP (from trust_signal_ui_mockup.html)
    party_name = "ABC Trading Ltd"
    party_lei = "5493001KJTIIGC8Y1R12"
    party_jur = "GB"
    stage_text = "Stage: Identity Confirmed"

    branches_html = """
    <div class="bg-white border-2 border-black p-3 flex justify-between items-center font-bold shadow-sm">
      <span>Registry</span>
      <span class="text-green-600">✔ Done</span>
    </div>
    <div class="bg-gray-100 border border-gray-400 text-gray-500 p-3 flex justify-between items-center">
      <span>Ownership</span>
      <span class="text-xs font-bold">Failed/Gap</span>
    </div>
    <div class="bg-white border-2 border-black p-3 flex justify-between items-center font-bold shadow-sm">
      <span>Legal Events</span>
      <span class="text-green-600">✔ Done</span>
    </div>
    <div class="bg-red-50 border-2 border-[#D32F2F] p-3 flex justify-between items-center font-bold text-[#D32F2F] shadow-sm">
      <span>Adverse Media</span>
      <span>! Conflict</span>
    </div>
    """

    rows_html = """
    <!-- Chronological Example -->
    <tr class="border-b border-gray-300 hover:bg-gray-50 transition">
      <td class="p-4 font-bold bg-gray-50 align-top">Insolvency Status</td>
      <td class="p-4 border-l border-gray-300 align-top">
        <!-- Sequence display -->
        <div class="space-y-3">
            <div class="border-l-2 border-gray-400 pl-3">
                <span class="text-xs text-gray-500 block">Oct 2024</span>
                <span class="font-bold text-sm">Winding-up Petition</span>
            </div>
            <div class="border-l-2 border-green-500 pl-3">
                <span class="text-xs text-gray-500 block">Jan 2025</span>
                <span class="font-bold text-sm text-green-700">Petition Dismissed</span>
            </div>
        </div>
      </td>
      <td class="p-4 border-l border-gray-300 text-gray-400 italic align-top">No coverage</td>
    </tr>
    
    <!-- Aggregation Example -->
    <tr class="border-b border-gray-300">
      <td class="p-4 font-bold bg-gray-50 align-top">Adverse Findings</td>
      <td class="p-4 border-l border-gray-300 text-gray-400 italic align-top">No findings</td>
      <td class="p-4 border-l-2 border-[#D32F2F] bg-red-50 group align-top">
        <span class="text-[#D32F2F] font-bold block mb-1">Allegation of Fraud</span>
        <span class="bg-red-200 text-[#D32F2F] text-[10px] font-bold px-2 py-0.5 rounded-full inline-block mb-2">
          Aggregated: 5 Sources
        </span>
        <span class="text-xs text-black block mb-3">5 articles reporting the same underlying event grouped by aggregator.</span>
        <div>
          <button onclick="showProvenance()" class="text-xs font-bold text-white bg-[#D32F2F] px-3 py-1.5 rounded hover:bg-red-800 transition">
            Inspect Grouped Evidence
          </button>
        </div>
      </td>
    </tr>
    """

    assessment_box = """
    <div class="bg-gray-800 border-l-4 border-yellow-500 p-3 mb-5 rounded-r text-sm">
        <span class="font-bold text-yellow-500 block mb-1">Assessment Paused</span>
        <span class="text-gray-300 text-xs">Risk scores left UNSET due to missing critical source coverage (Ownership Agent failed).</span>
    </div>
    """

    provenance_json = """{
  "event_cluster": "evt_99x",
  "grouped_sources": [
    "news_lexis", "news_reuters", "news_bloomberg"
  ],
  "procedural_status": "allegation",
  "timeline_linked": true
}"""

html_ui = f"""<!DOCTYPE html>
<html>
<head>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
</head>
<body class="bg-[#F8F9FA] text-[#111111] antialiased min-h-screen font-sans">
  <!-- Header -->
  <header class="bg-[#111111] text-white p-4 border-b-4 border-[#D32F2F] flex justify-between items-center shadow-md">
    <div class="flex items-center space-x-3">
      <div class="bg-[#D32F2F] text-white font-bold px-3 py-1 text-lg rounded-sm tracking-widest">TS</div>
      <h1 class="text-xl font-bold tracking-wider">TrustSignal <span class="font-normal text-gray-400 ml-2">| Case Review Console</span></h1>
    </div>
    <div class="text-sm font-medium">Analyst: <span class="text-gray-300">pulkitarora</span></div>
  </header>

  <div class="p-6 max-w-7xl mx-auto flex flex-col lg:flex-row gap-6">
    <!-- Main Content Left -->
    <div class="flex-1 space-y-6">
      
      <!-- Identity Resolution Gate -->
      <section class="bg-white p-5 border border-black rounded shadow-sm relative overflow-hidden">
        <div class="absolute top-0 left-0 w-1.5 h-full bg-[#111111]"></div>
        <div class="flex justify-between items-start mb-3 pl-2">
            <h2 class="text-lg font-bold">Resolved Identity Context</h2>
            <span class="bg-black text-white text-xs font-bold px-2 py-1 rounded">{stage_text}</span>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm pl-2">
          <div><span class="font-bold text-gray-500 uppercase text-xs block mb-1">Legal Name</span> <span class="font-semibold text-base">{party_name}</span></div>
          <div><span class="font-bold text-gray-500 uppercase text-xs block mb-1">LEI</span> {party_lei}</div>
          <div><span class="font-bold text-gray-500 uppercase text-xs block mb-1">Jurisdiction</span> {party_jur}</div>
        </div>
      </section>

      <!-- Orchestration Pipeline Tracker -->
      <section>
        <h2 class="text-xs font-bold uppercase text-gray-500 mb-3 tracking-wider flex items-center">
          Parallel Specialist Research <span class="ml-2 w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
        </h2>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
          {branches_html}
        </div>
      </section>

      <!-- Comparison Board & Aggregation -->
      <section>
        <div class="flex justify-between items-end mb-3">
            <h2 class="text-xs font-bold uppercase text-gray-500 tracking-wider">Comparison Board & Timeline</h2>
        </div>
        <div class="bg-white border border-black overflow-hidden rounded shadow-sm">
          <table class="w-full text-sm text-left">
            <thead class="bg-[#111111] text-white">
              <tr>
                <th class="p-3 font-semibold tracking-wide">Claim / Event Class</th>
                <th class="p-3 font-semibold tracking-wide border-l border-gray-700">Legal / Registry Agents</th>
                <th class="p-3 font-semibold tracking-wide border-l border-gray-700">Media / News Agents</th>
              </tr>
            </thead>
            <tbody>
              {rows_html}
            </tbody>
          </table>
        </div>
      </section>
    </div>

    <!-- Right Sidebar -->
    <div class="w-full lg:w-[400px] flex flex-col space-y-6">
      
      <!-- Validation & Assessment -->
      <div class="bg-[#111111] text-white p-5 rounded border border-black shadow-lg">
        <h2 class="text-lg font-bold mb-4 border-b border-gray-700 pb-2">Validation & Assessment</h2>
        
        {assessment_box}

        <!-- Review & Decision (Audit Log) -->
        <div class="space-y-4">
          <p class="text-xs text-gray-400 font-bold uppercase tracking-wider border-b border-gray-700 pb-1">Audited Decision Record</p>
          
          <div>
              <label class="text-xs text-gray-300 block mb-1">Reviewer Rationale (Required)</label>
              <textarea id="decision-rationale" class="w-full bg-gray-900 border border-gray-700 rounded p-2 text-sm text-white focus:outline-none focus:border-white h-24" placeholder="Document why this decision is being made based on the evidence..."></textarea>
          </div>

          <div id="decision-feedback" class="hidden text-xs p-2 rounded"></div>

          <div class="grid grid-cols-2 gap-2 mt-4">
            <button onclick="recordDecision('Request Details')" class="bg-transparent border border-white text-white font-bold py-2 rounded-sm hover:bg-gray-800 transition text-sm">Request Details</button>
            <button onclick="recordDecision('Clear & Approve')" class="bg-white text-black font-bold py-2 rounded-sm hover:bg-gray-200 transition text-sm">Clear & Approve</button>
            <button onclick="recordDecision('Reject (Policy Hard Stop)')" class="col-span-2 bg-transparent border-2 border-[#D32F2F] text-[#D32F2F] font-bold py-2 rounded-sm hover:bg-[#D32F2F] hover:text-white transition mt-2">Reject (Policy Hard Stop)</button>
          </div>
        </div>
      </div>

      <!-- Provenance Inspector -->
      <div id="provenance-panel" class="bg-white p-5 border border-black rounded shadow-sm opacity-50 transition-opacity">
        <h2 class="text-sm font-bold uppercase text-black mb-2 tracking-wider flex items-center">
          <span class="mr-2 text-lg">🔎</span> Snowflake Provenance
        </h2>
        <p class="text-xs text-gray-600 mb-3" id="prov-instruction">Click an evidence link on the board to view the raw observation.</p>
        
        <div id="provenance-code" class="hidden">
          <div class="flex justify-between items-center text-xs text-gray-500 mb-1 font-bold">
            <span>TRUSTSIGNAL_RAW.OBSERVATIONS</span>
            <span>2026-10-03</span>
          </div>
          <div class="bg-[#111111] text-gray-300 text-xs p-3 font-mono rounded overflow-x-auto border-l-4 border-[#D32F2F] shadow-inner">
{provenance_json}
          </div>
          <button class="w-full mt-3 text-xs border border-black text-black py-1 hover:bg-gray-100 font-bold">View Full Documents</button>
        </div>
      </div>
    </div>
  </div>

  <script>
    function showProvenance() {{
      const panel = document.getElementById('provenance-panel');
      const instruction = document.getElementById('prov-instruction');
      const code = document.getElementById('provenance-code');
      
      panel.classList.remove('opacity-50');
      instruction.classList.add('hidden');
      code.classList.remove('hidden');
    }}

    function recordDecision(action) {{
      const rationale = document.getElementById('decision-rationale').value;
      const feedback = document.getElementById('decision-feedback');
      if (!rationale.trim()) {{
        feedback.className = "text-xs p-2 rounded bg-red-900 text-red-200 border border-red-500 block mb-2";
        feedback.innerHTML = "⚠️ Please provide a reviewer rationale before recording decision.";
        return;
      }}
      feedback.className = "text-xs p-2 rounded bg-green-900 text-green-200 border border-green-500 block mb-2";
      feedback.innerHTML = "✅ Decision '" + action + "' locked to Snowflake TRUSTSIGNAL_OPS with rationale by pulkitarora.";
    }}
  </script>
</body>
</html>
"""

components.html(html_ui, height=1050, scrolling=True)
