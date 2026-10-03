"""Streamlit intake and review surface for the local TrustSignal starter."""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from trust_signal.models import CaseRequest, SourceMode
from trust_signal.orchestration.case_graph import run_case

st.set_page_config(
    page_title="TrustSignal Entity Intelligence",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS to minimize Streamlit chrome and let the enterprise dashboard shine
st.markdown("""
<style>
    /* Base container sizing */
    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 1rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
        max-width: 100% !important;
    }
    header[data-testid="stHeader"] {
        display: none !important;
    }
    iframe {
        width: 100% !important;
        border: none !important;
    }
    
    /* Expander card container */
    div[data-testid="stExpander"] {
        border: 1px solid #E2E8F0 !important;
        background-color: #FFFFFF !important;
        margin: 0.75rem 1.5rem 0.75rem 1.5rem !important;
        border-radius: 12px !important;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05) !important;
        overflow: hidden !important;
    }
    
    /* Expander summary/header bar */
    div[data-testid="stExpander"] > details > summary {
        background-color: #F8FAFC !important;
        color: #0F172A !important;
        font-weight: 600 !important;
        font-size: 0.875rem !important;
        padding: 0.75rem 1.25rem !important;
        border-bottom: 1px solid #E2E8F0 !important;
        transition: background-color 0.2s ease !important;
    }
    div[data-testid="stExpander"] > details > summary:hover {
        background-color: #F1F5F9 !important;
        color: #4F46E5 !important;
    }
    div[data-testid="stExpander"] > details > summary svg {
        fill: #64748B !important;
    }
    
    /* Inner form container */
    div[data-testid="stExpander"] > details > div {
        background-color: #FFFFFF !important;
        padding: 1.25rem !important;
    }
    div[data-testid="stForm"] {
        border: none !important;
        padding: 0 !important;
    }
    
    /* All labels inside the form */
    div[data-testid="stExpander"] label,
    div[data-testid="stExpander"] label p,
    div[data-testid="stExpander"] .stWidgetLabel p {
        color: #1E293B !important;
        font-weight: 600 !important;
        font-size: 0.825rem !important;
        letter-spacing: -0.01em !important;
    }

    /* Radio button options */
    div[data-testid="stRadio"] div[role="radiogroup"] label {
        color: #334155 !important;
        font-weight: 500 !important;
        font-size: 0.85rem !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label p {
        color: #334155 !important;
        font-weight: 500 !important;
    }
    
    /* Inputs: background, border, text */
    div[data-testid="stExpander"] input[type="text"] {
        background-color: #F8FAFC !important;
        color: #0F172A !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 8px !important;
        font-size: 0.875rem !important;
        padding: 0.5rem 0.75rem !important;
        transition: border-color 0.2s, box-shadow 0.2s !important;
    }
    div[data-testid="stExpander"] input[type="text"]:focus {
        background-color: #FFFFFF !important;
        border-color: #4F46E5 !important;
        box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1) !important;
        outline: none !important;
    }
    div[data-testid="stExpander"] input::placeholder {
        color: #94A3B8 !important;
    }
    
    /* Submit button */
    div[data-testid="stFormSubmitButton"] > button {
        background-color: #0F172A !important;
        color: #FFFFFF !important;
        border: 1px solid #0F172A !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        padding: 0.55rem 1.5rem !important;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05) !important;
        transition: all 0.2s ease !important;
    }
    div[data-testid="stFormSubmitButton"] > button:hover {
        background-color: #4F46E5 !important;
        border-color: #4F46E5 !important;
        color: #FFFFFF !important;
        box-shadow: 0 4px 6px -1px rgba(79, 70, 229, 0.2) !important;
    }
</style>
""", unsafe_allow_html=True)

# Collapsible Intake Drawer for triggering new investigations or automated testing
with st.expander("🔍 Investigation Intake & Source Dispatch (Click to Expand)", expanded=False), st.form("case_intake"):
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
# 100% COMPLETE & UNCOMPROMISED RECREATION OF THE TEAM'S ENTERPRISE SAAS DESIGN IMAGE
# -------------------------------------------------------------------------------------------------
html_ui = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    body { font-family: 'Inter', sans-serif; }
    .donut-gauge {
      background: conic-gradient(#4F46E5 0% 68%, #E2E8F0 68% 100%);
    }
  </style>
</head>
<body class="bg-[#F8FAFC] text-[#0F172A] antialiased min-h-screen pb-12">

  <!-- 1. TOP NAVIGATION BAR -->
  <nav class="bg-white border-b border-[#E2E8F0] px-6 py-2.5 flex items-center justify-between sticky top-0 z-50 shadow-sm">
    <div class="flex items-center space-x-6">
      <div class="flex items-center space-x-2">
        <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-[#4F46E5] to-[#7C3AED] flex items-center justify-center text-white shadow-sm font-bold text-sm">
          TS
        </div>
        <div>
          <span class="font-bold text-base tracking-tight text-[#0F172A]">TrustSignal</span>
          <span class="text-[10px] block font-semibold text-[#64748B] tracking-wider uppercase -mt-1">Entity Intelligence</span>
        </div>
      </div>
      
      <div class="hidden md:flex items-center space-x-1 pl-4 text-xs font-medium text-[#475569]">
        <button class="px-3 py-1.5 rounded-md hover:bg-[#F1F5F9] transition">Investigations / Queue</button>
        <button class="px-3 py-1.5 rounded-md bg-[#F1F5F9] text-[#0F172A] font-semibold">Live Entity Review</button>
        <button class="px-3 py-1.5 rounded-md hover:bg-[#F1F5F9] transition">New Investigation</button>
        <button class="px-3 py-1.5 rounded-md hover:bg-[#F1F5F9] transition">Source Feeds</button>
      </div>
    </div>

    <div class="flex items-center space-x-4">
      <div class="flex items-center bg-[#F8FAFC] border border-[#E2E8F0] rounded-full px-2.5 py-1 text-[11px] font-medium text-[#475569] space-x-2">
        <span class="flex items-center space-x-1.5">
          <span class="w-2 h-2 rounded-full bg-[#10B981] animate-pulse"></span>
          <span>Live Sync</span>
        </span>
        <span class="text-gray-300">|</span>
        <span>Snowflake Cortex</span>
      </div>
      
      <button class="text-[#64748B] hover:text-[#0F172A] p-1.5 rounded-full hover:bg-[#F1F5F9] transition relative">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"></path></svg>
        <span class="absolute top-1 right-1 w-1.5 h-1.5 bg-[#EF4444] rounded-full"></span>
      </button>

      <div class="flex items-center space-x-2 border-l border-[#E2E8F0] pl-4">
        <div class="w-7 h-7 rounded-full bg-[#0F172A] text-white flex items-center justify-center font-bold text-xs">
          PA
        </div>
        <div class="text-left text-xs">
          <span class="font-semibold block text-[#0F172A] leading-tight">Pulkit Arora</span>
          <span class="text-[10px] text-[#64748B]">Lead Analyst</span>
        </div>
      </div>
    </div>
  </nav>

  <!-- 2. BREADCRUMBS & TELEMETRY BAR -->
  <div class="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between text-xs text-[#64748B]">
    <div class="flex items-center space-x-2">
      <span class="hover:text-[#0F172A] cursor-pointer">Investigations</span>
      <span>›</span>
      <span class="hover:text-[#0F172A] cursor-pointer">Queue #UK-9847</span>
      <span>›</span>
      <span class="text-[#4F46E5] font-semibold">Live Review</span>
    </div>

    <div class="flex items-center space-x-4 text-[11px]">
      <div class="flex items-center space-x-1.5">
        <span class="w-1.5 h-1.5 rounded-full bg-[#4F46E5]"></span>
        <span>Snowflake Cortex Cluster: <code class="font-mono text-[#0F172A] bg-white px-1.5 py-0.5 rounded border border-[#E2E8F0]">eu-west-1.cortex-agent-04</code></span>
      </div>
      <span>Session TTL: <strong class="text-[#0F172A]">42m remaining</strong></span>
    </div>
  </div>

  <div class="max-w-7xl mx-auto px-6 space-y-6">

    <!-- 3. TOP ROW: ENTITY IDENTITY & RISK ENGINE -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      
      <!-- Left 2 Cols: Entity Header Card -->
      <div class="lg:col-span-2 bg-white rounded-xl border border-[#E2E8F0] p-6 shadow-sm flex flex-col justify-between">
        <div>
          <!-- Badges -->
          <div class="flex flex-wrap items-center gap-2 mb-3">
            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-[#ECFDF5] text-[#059669] border border-[#A7F3D0]">
              <svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path></svg>
              Identity Confirmed
            </span>
            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-[#F0FDF4] text-[#16A34A] border border-[#BBF7D0]">
              <span class="w-1.5 h-1.5 rounded-full bg-[#16A34A] mr-1.5"></span>
              GLEIF Active Record
            </span>
            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-[#F1F5F9] text-[#475569] border border-[#E2E8F0]">
              UK Registered Private Limited
            </span>
          </div>

          <!-- Entity Name & Flag -->
          <div class="flex items-center space-x-3 mb-2">
            <h1 class="text-2xl font-bold tracking-tight text-[#0F172A]">ABC Trading Ltd</h1>
            <span class="text-xl" title="United Kingdom">🇬🇧</span>
          </div>

          <!-- Description -->
          <p class="text-xs text-[#64748B] leading-relaxed max-w-2xl mb-6">
            Specialized commodities import-export vehicle based in the City of London. Subject to multi-agent telemetry orchestration for enhanced compliance screening.
          </p>
        </div>

        <!-- Identifiers Pills -->
        <div class="flex flex-wrap items-center gap-3 pt-4 border-t border-[#F1F5F9] text-xs">
          <div class="flex items-center space-x-1.5 bg-[#F8FAFC] border border-[#E2E8F0] px-3 py-1.5 rounded-lg text-[#334155]">
            <span class="font-bold text-[#64748B] text-[10px] tracking-wide">LEI</span>
            <span class="font-mono font-medium">5493001KJTIIGC8Y1R12</span>
            <button onclick="copyToClipboard('5493001KJTIIGC8Y1R12')" class="text-[#94A3B8] hover:text-[#0F172A] ml-1" title="Copy LEI">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>
            </button>
          </div>

          <div class="flex items-center space-x-1.5 bg-[#F8FAFC] border border-[#E2E8F0] px-3 py-1.5 rounded-lg text-[#334155]">
            <span class="font-bold text-[#64748B] text-[10px] tracking-wide">UK CRO</span>
            <span class="font-mono font-medium">0984721</span>
            <button onclick="copyToClipboard('0984721')" class="text-[#94A3B8] hover:text-[#0F172A] ml-1" title="Copy CRO">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>
            </button>
          </div>

          <div class="flex items-center space-x-1.5 bg-[#F8FAFC] border border-[#E2E8F0] px-3 py-1.5 rounded-lg text-[#334155]">
            <svg class="w-3.5 h-3.5 text-[#64748B]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
            <span class="font-medium text-[#475569]">London, EC3V 3ND, United Kingdom</span>
          </div>
        </div>
      </div>

      <!-- Right 1 Col: Risk Engine Card -->
      <div class="bg-white rounded-xl border border-[#E2E8F0] p-6 shadow-sm flex flex-col justify-between">
        <div>
          <div class="flex items-center justify-between mb-1">
            <span class="text-[10px] font-bold text-[#64748B] tracking-wider uppercase">RISK ENGINE V2.4</span>
            <span class="px-2 py-0.5 rounded-md text-[10px] font-bold bg-[#FEE2E2] text-[#DC2626] border border-[#FCA5A5]">
              Review Required
            </span>
          </div>
          <h2 class="text-sm font-bold text-[#0F172A] mb-4">Cortex Automated Assessment</h2>

          <!-- Donut Score and Breakdown -->
          <div class="flex items-center space-x-4 mb-4">
            <!-- Circular Gauge -->
            <div class="relative w-20 h-20 rounded-full donut-gauge flex items-center justify-center p-2 flex-shrink-0 shadow-inner">
              <div class="w-16 h-16 rounded-full bg-white flex flex-col items-center justify-center shadow-sm">
                <span class="text-xl font-extrabold text-[#0F172A] leading-none">68</span>
                <span class="text-[9px] font-semibold text-[#64748B]">/ 100</span>
              </div>
            </div>

            <!-- Score Contributors -->
            <div class="space-y-1.5 flex-1 text-xs">
              <div class="flex justify-between items-center text-[11px]">
                <span class="text-[#475569] truncate">Adverse Media Pressure</span>
                <span class="font-bold text-[#EF4444] ml-1">+45 pts</span>
              </div>
              <div class="w-full bg-[#F1F5F9] rounded-full h-1"><div class="bg-[#EF4444] h-1 rounded-full w-[45%]"></div></div>

              <div class="flex justify-between items-center text-[11px]">
                <span class="text-[#475569] truncate">PSC Hierarchy Incomplete</span>
                <span class="font-bold text-[#6366F1] ml-1">+15 pts</span>
              </div>
              <div class="w-full bg-[#F1F5F9] rounded-full h-1"><div class="bg-[#6366F1] h-1 rounded-full w-[25%]"></div></div>

              <div class="flex justify-between items-center text-[11px]">
                <span class="text-[#475569] truncate">Companies House Registered</span>
                <span class="font-bold text-[#10B981] ml-1">-10 pts</span>
              </div>
              <div class="w-full bg-[#F1F5F9] rounded-full h-1"><div class="bg-[#10B981] h-1 rounded-full w-[15%]"></div></div>
            </div>
          </div>
        </div>

        <!-- Decision Buttons -->
        <div class="flex items-center space-x-2 pt-3 border-t border-[#F1F5F9]">
          <button onclick="recordAction('Approve')" class="flex-1 inline-flex items-center justify-center px-3 py-2 border border-[#E2E8F0] rounded-lg text-xs font-semibold text-[#334155] bg-white hover:bg-[#F8FAFC] transition">
            <svg class="w-3.5 h-3.5 mr-1.5 text-[#10B981]" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path></svg>
            Approve
          </button>
          <button onclick="recordAction('Flag for Review')" class="flex-[1.5] inline-flex items-center justify-center px-3 py-2 bg-[#4F46E5] text-white rounded-lg text-xs font-semibold hover:bg-[#4338CA] shadow-sm transition">
            <svg class="w-3.5 h-3.5 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 1H21l-3 6 3 6h-8.5l-1-1H5a2 2 0 00-2 2zm9-13.5V9"></path></svg>
            Flag for Review
          </button>
          <button onclick="recordAction('Reject')" class="p-2 border border-[#E2E8F0] rounded-lg text-[#64748B] hover:text-[#EF4444] hover:bg-[#F8FAFC] transition" title="Dismiss / Reject">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
          </button>
        </div>
      </div>

    </div>

    <!-- 4. AUTONOMOUS RESEARCH PIPELINE (4 CARDS) -->
    <div>
      <div class="flex items-center justify-between mb-3">
        <div class="flex items-center space-x-2">
          <span class="w-2.5 h-2.5 rounded-full bg-[#4F46E5]"></span>
          <h2 class="text-sm font-bold text-[#0F172A]">Autonomous Research Pipeline</h2>
          <span class="text-[11px] font-medium text-[#64748B] bg-[#F1F5F9] px-2 py-0.5 rounded border border-[#E2E8F0]">
            Snowflake Cortex Engine (4 Agents)
          </span>
        </div>
        <span class="text-xs text-[#64748B]">Filter matrix findings by selecting an agent</span>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        
        <!-- Card 1: Registry Specialist -->
        <div class="bg-white rounded-xl border border-[#E2E8F0] p-4 shadow-sm hover:border-[#CBD5E1] transition flex flex-col justify-between">
          <div>
            <div class="flex items-center justify-between mb-2">
              <div class="w-8 h-8 rounded-lg bg-[#F0FDF4] border border-[#DCFCE7] flex items-center justify-center text-[#16A34A]">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
              </div>
              <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-[#DCFCE7] text-[#15803D]">
                <svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path></svg>
                Completed
              </span>
            </div>
            <h3 class="font-bold text-sm text-[#0F172A]">Registry Specialist</h3>
            <p class="text-[11px] text-[#64748B] mb-4">GLEIF, UK Companies House</p>
          </div>
          <div>
            <div class="flex justify-between items-center text-[11px] font-semibold text-[#334155] mb-1.5">
              <span>100% Verified</span>
              <span class="text-[#64748B] font-normal">0.42s latency</span>
            </div>
            <div class="w-full bg-[#DCFCE7] h-1.5 rounded-full"><div class="bg-[#16A34A] h-1.5 rounded-full w-full"></div></div>
          </div>
        </div>

        <!-- Card 2: Ownership & PSC Specialist -->
        <div class="bg-white rounded-xl border border-[#E2E8F0] p-4 shadow-sm hover:border-[#CBD5E1] transition flex flex-col justify-between">
          <div>
            <div class="flex items-center justify-between mb-2">
              <div class="w-8 h-8 rounded-lg bg-[#EFF6FF] border border-[#DBEAFE] flex items-center justify-center text-[#2563EB]">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 11.5V14m0-2.5v-6a1.5 1.5 0 113 0m-3 6a1.5 1.5 0 00-3 0v2a7.5 7.5 0 0015 0v-5a1.5 1.5 0 00-3 0m-6-3V11m0-5.5v-1a1.5 1.5 0 013 0v1m0 0V11m0-5.5a1.5 1.5 0 013 0v3m0 0V11"></path></svg>
              </div>
              <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-[#FEF3C7] text-[#D97706]">
                <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
                Coverage Gap
              </span>
            </div>
            <h3 class="font-bold text-sm text-[#0F172A]">Ownership & PSC Specialist</h3>
            <p class="text-[11px] text-[#64748B] mb-4">Beneficial Owners, Holding Hierarchy</p>
          </div>
          <div>
            <div class="flex justify-between items-center text-[11px] font-semibold text-[#334155] mb-1.5">
              <span>30% Complete</span>
              <a href="#matrix-ownership" class="text-[#2563EB] hover:underline font-medium">View Gap</a>
            </div>
            <div class="w-full bg-[#E0E7FF] h-1.5 rounded-full"><div class="bg-[#4F46E5] h-1.5 rounded-full w-[30%]"></div></div>
          </div>
        </div>

        <!-- Card 3: Legal & Litigation -->
        <div class="bg-white rounded-xl border border-[#E2E8F0] p-4 shadow-sm hover:border-[#CBD5E1] transition flex flex-col justify-between">
          <div>
            <div class="flex items-center justify-between mb-2">
              <div class="w-8 h-8 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0] flex items-center justify-center text-[#475569]">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3"></path></svg>
              </div>
              <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-[#EFF6FF] text-[#1D4ED8]">
                <svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M2.166 4.999A11.954 11.954 0 0010 1.944 11.954 11.954 0 0017.834 5c.11.65.166 1.32.166 2.001 0 5.225-3.34 9.67-8 11.317C5.34 16.67 2 12.225 2 7c0-.682.057-1.35.166-2.001zm11.541 3.708a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path></svg>
                Sanctions Clear
              </span>
            </div>
            <h3 class="font-bold text-sm text-[#0F172A]">Legal & Litigation</h3>
            <p class="text-[11px] text-[#64748B] mb-4">High Court Rolls, London Gazette</p>
          </div>
          <div>
            <div class="flex justify-between items-center text-[11px] font-semibold text-[#334155] mb-1.5">
              <span>Resolved Petition</span>
              <span class="text-[#64748B] font-normal">1 Petition (Dismissed)</span>
            </div>
            <div class="w-full bg-[#E2E8F0] h-1.5 rounded-full"><div class="bg-[#0284C7] h-1.5 rounded-full w-full"></div></div>
          </div>
        </div>

        <!-- Card 4: Adverse Media & News -->
        <div class="bg-white rounded-xl border border-[#FCA5A5] p-4 shadow-sm hover:border-[#EF4444] transition flex flex-col justify-between relative overflow-hidden">
          <div class="absolute top-0 right-0 w-16 h-16 bg-[#FEE2E2] rounded-bl-full -z-0 opacity-40"></div>
          <div class="relative z-10">
            <div class="flex items-center justify-between mb-2">
              <div class="w-8 h-8 rounded-lg bg-[#FEF2F2] border border-[#FECACA] flex items-center justify-center text-[#DC2626]">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z"></path></svg>
              </div>
              <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-[#FFEDD5] text-[#C2410C]">
                5 Clustered Alerts
              </span>
            </div>
            <h3 class="font-bold text-sm text-[#0F172A]">Adverse Media & News</h3>
            <p class="text-[11px] text-[#64748B] mb-4">Bloomberg, LexisNexis, FT Index</p>
          </div>
          <div class="relative z-10">
            <div class="flex justify-between items-center text-[11px] font-bold text-[#DC2626] mb-1.5">
              <span>Financial Misrepresentation</span>
              <span>Flagged</span>
            </div>
            <div class="w-full bg-[#FEE2E2] h-1.5 rounded-full"><div class="bg-[#EF4444] h-1.5 rounded-full w-full"></div></div>
          </div>
        </div>

      </div>
    </div>

    <!-- 5. CROSS-AGENT TELEMETRY & DISCREPANCY MATRIX -->
    <div class="bg-white rounded-xl border border-[#E2E8F0] shadow-sm p-6">
      <div class="mb-4">
        <h2 class="text-base font-bold text-[#0F172A]">Cross-Agent Telemetry & Discrepancy Matrix</h2>
        <p class="text-xs text-[#64748B]">Deterministic comparison across official registers, public disclosures, and external intelligence streams.</p>
      </div>

      <!-- Filter Tabs -->
      <div class="flex flex-wrap items-center gap-2 mb-6 border-b border-[#F1F5F9] pb-4">
        <button onclick="filterMatrix('all')" id="tab-all" class="matrix-tab px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-[#0F172A] text-white">
          All Findings (4)
        </button>
        <button onclick="filterMatrix('conflict')" id="tab-conflict" class="matrix-tab px-3.5 py-1.5 rounded-lg text-xs font-medium text-[#64748B] hover:bg-[#F1F5F9] transition">
          Discrepancies & Conflicts (2)
        </button>
        <button onclick="filterMatrix('match')" id="tab-match" class="matrix-tab px-3.5 py-1.5 rounded-lg text-xs font-medium text-[#64748B] hover:bg-[#F1F5F9] transition">
          Confirmed Matches (1)
        </button>
        <button onclick="filterMatrix('gap')" id="tab-gap" class="matrix-tab px-3.5 py-1.5 rounded-lg text-xs font-medium text-[#64748B] hover:bg-[#F1F5F9] transition">
          Coverage Gaps (1)
        </button>
      </div>

      <!-- Matrix Rows -->
      <div class="space-y-4">

        <!-- Row 1: Media Conflict -->
        <div class="matrix-item p-4 rounded-xl border border-[#E2E8F0] hover:border-[#CBD5E1] transition bg-white flex flex-col md:flex-row md:items-center justify-between gap-4" data-category="conflict">
          <div class="flex items-start space-x-3.5">
            <div class="w-9 h-9 rounded-lg bg-[#FEE2E2] flex items-center justify-center text-[#DC2626] flex-shrink-0 mt-0.5">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5.882V19.24a1.76 1.76 0 01-3.417.592l-2.147-6.15M18 13a3 3 0 100-6M5.436 13.683A4.001 4.001 0 017 6h1.832c4.1 0 7.625-1.234 9.168-3v14c-1.543-1.766-5.067-3-9.168-3H7a3.988 3.988 0 01-1.564-.317z"></path></svg>
            </div>
            <div>
              <div class="flex flex-wrap items-center gap-2 mb-1.5">
                <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-[#FEE2E2] text-[#DC2626]">MEDIA CONFLICT</span>
                <span class="text-[11px] text-[#64748B]">Agent: <strong class="text-[#334155]">Adverse Media Specialist</strong></span>
                <span class="text-gray-300">•</span>
                <span class="text-[11px] text-[#64748B]">Confidence: <strong class="text-[#0F172A]">94%</strong></span>
              </div>
              <h4 class="font-bold text-sm text-[#0F172A] mb-1">5 Clustered Publications Alleging Supplier Invoicing Misrepresentation</h4>
              <p class="text-xs text-[#64748B] max-w-3xl leading-relaxed">
                LexisNexis & Bloomberg flagged multiple independent reports published between Nov 12, 2024 and Dec 04, 2024 detailing disputed letters of credit issued to overseas grain suppliers totaling £4.2M.
              </p>
            </div>
          </div>
          <div class="flex items-center space-x-2 flex-shrink-0">
            <button onclick="scrollToProvenance()" class="inline-flex items-center px-3.5 py-2 rounded-lg text-xs font-semibold bg-[#EEF2FF] text-[#4F46E5] hover:bg-[#E0E7FF] transition">
              <svg class="w-3.5 h-3.5 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path></svg>
              Inspect Grouped Evidence (5 Sources)
            </button>
            <button class="p-2 text-[#94A3B8] hover:text-[#0F172A] rounded-lg">
              <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z"></path></svg>
            </button>
          </div>
        </div>

        <!-- Row 2: Ownership Mismatch / Gap -->
        <div id="matrix-ownership" class="matrix-item p-4 rounded-xl border border-[#E2E8F0] hover:border-[#CBD5E1] transition bg-white flex flex-col md:flex-row md:items-center justify-between gap-4" data-category="gap">
          <div class="flex items-start space-x-3.5">
            <div class="w-9 h-9 rounded-lg bg-[#EFF6FF] flex items-center justify-center text-[#2563EB] flex-shrink-0 mt-0.5">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 11.5V14m0-2.5v-6a1.5 1.5 0 113 0m-3 6a1.5 1.5 0 00-3 0v2a7.5 7.5 0 0015 0v-5a1.5 1.5 0 00-3 0m-6-3V11m0-5.5v-1a1.5 1.5 0 013 0v1m0 0V11m0-5.5a1.5 1.5 0 013 0v3m0 0V11"></path></svg>
            </div>
            <div>
              <div class="flex flex-wrap items-center gap-2 mb-1.5">
                <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-[#DBEAFE] text-[#1E40AF]">OWNERSHIP MISMATCH / GAP</span>
                <span class="text-[11px] text-[#64748B]">Agent: <strong class="text-[#334155]">Ownership & PSC Specialist</strong></span>
                <span class="text-gray-300">•</span>
                <span class="text-[11px] text-[#64748B]">Confidence: <strong class="text-[#0F172A]">81%</strong></span>
              </div>
              <h4 class="font-bold text-sm text-[#0F172A] mb-1">Secondary Holding Entity Unindexed in UK Ultimate Beneficial Register</h4>
              <p class="text-xs text-[#64748B] max-w-3xl leading-relaxed">
                Companies House filing lists <strong>Aura Capital HoldCo (75%)</strong> as majority PSC. However, self-declaration onboarding dossier references <strong>ABC Group Overseas Corp (Cayman)</strong>. 25% voting stake ownership remains unaccounted for.
              </p>
            </div>
          </div>
          <div class="flex items-center space-x-3 flex-shrink-0 text-right">
            <div>
              <span class="text-[11px] font-bold text-[#64748B] block">Coverage: 30%</span>
              <button onclick="alert('PSC Declaration request triggered via compliance worker.')" class="text-xs font-semibold text-[#2563EB] hover:underline">Request PSC Declaration</button>
            </div>
            <button class="p-2 text-[#94A3B8] hover:text-[#0F172A]">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"></path></svg>
            </button>
          </div>
        </div>

        <!-- Row 3: Legal / Benign -->
        <div class="matrix-item p-4 rounded-xl border border-[#E2E8F0] hover:border-[#CBD5E1] transition bg-white flex flex-col md:flex-row md:items-center justify-between gap-4" data-category="conflict">
          <div class="flex items-start space-x-3.5">
            <div class="w-9 h-9 rounded-lg bg-[#ECFDF5] flex items-center justify-center text-[#059669] flex-shrink-0 mt-0.5">
              <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path></svg>
            </div>
            <div>
              <div class="flex flex-wrap items-center gap-2 mb-1.5">
                <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-[#D1FAE5] text-[#047857]">RESOLVED / BENIGN</span>
                <span class="text-[11px] text-[#64748B]">Agent: <strong class="text-[#334155]">Legal & Litigation Specialist</strong></span>
                <span class="text-gray-300">•</span>
                <span class="text-[11px] text-[#059669] font-medium">Official Court Order Verified</span>
              </div>
              <h4 class="font-bold text-sm text-[#0F172A] mb-1">London Gazette Winding-Up Petition (CR-2024-00192) Formally Dismissed</h4>
              <p class="text-xs text-[#64748B] max-w-3xl leading-relaxed">
                A creditor petition filed in September 2024 by an equipment lessor was struck out by the High Court of Justice (Companies Court) on January 14, 2025. Costs paid in full; legal status remains in Good Standing.
              </p>
            </div>
          </div>
          <div class="flex items-center space-x-2 flex-shrink-0">
            <button class="inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-medium text-[#475569] bg-[#F1F5F9] hover:bg-[#E2E8F0] transition">
              <svg class="w-3.5 h-3.5 mr-1.5 text-[#64748B]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
              Gazette Doc #49281
            </button>
            <button class="p-2 text-[#94A3B8] hover:text-[#0F172A]">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
            </button>
          </div>
        </div>

        <!-- Row 4: Sanctions Clean -->
        <div class="matrix-item p-4 rounded-xl border border-[#E2E8F0] hover:border-[#CBD5E1] transition bg-white flex flex-col md:flex-row md:items-center justify-between gap-4" data-category="match">
          <div class="flex items-start space-x-3.5">
            <div class="w-9 h-9 rounded-lg bg-[#ECFDF5] flex items-center justify-center text-[#059669] flex-shrink-0 mt-0.5">
              <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M2.166 4.999A11.954 11.954 0 0010 1.944 11.954 11.954 0 0017.834 5c.11.65.166 1.32.166 2.001 0 5.225-3.34 9.67-8 11.317C5.34 16.67 2 12.225 2 7c0-.682.057-1.35.166-2.001zm11.541 3.708a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path></svg>
            </div>
            <div>
              <div class="flex flex-wrap items-center gap-2 mb-1.5">
                <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-[#DCFCE7] text-[#15803D]">CONFIRMED CLEAR</span>
                <span class="text-[11px] text-[#64748B]">Agent: <strong class="text-[#334155]">Sanctions Watchdog</strong></span>
                <span class="text-gray-300">•</span>
                <span class="text-[11px] text-[#64748B]">32 Lists Ingested</span>
              </div>
              <h4 class="font-bold text-sm text-[#0F172A] mb-1">OFAC SDN, UK FCDO, EU Consolidated & UN Sanctions Screen: 0 Direct Matches</h4>
              <p class="text-xs text-[#64748B] max-w-3xl leading-relaxed">
                Full phonetic, semantic, and fuzzy matching executed against directors (Mr. Alistair Vance, Ms. Elena Rostova). All primary officers verified unlisted. PEP check negative.
              </p>
            </div>
          </div>
          <div class="flex items-center space-x-2 flex-shrink-0">
            <span class="inline-flex items-center text-xs font-semibold text-[#10B981]">
              <svg class="w-3.5 h-3.5 mr-1" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path></svg>
              Zero Hits
            </span>
          </div>
        </div>

      </div>
    </div>

    <!-- 6. AUDIT PROVENANCE & CORTEX OBSERVATION HASH DRAWER -->
    <div id="provenance-section" class="bg-white rounded-xl border border-[#E2E8F0] shadow-sm p-6">
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-[#F1F5F9] mb-4">
        <div class="flex items-center space-x-3">
          <div class="w-8 h-8 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0] flex items-center justify-center text-[#475569]">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"></path></svg>
          </div>
          <div>
            <div class="flex items-center space-x-2">
              <h3 class="text-sm font-bold text-[#0F172A]">Audit Provenance & Cortex Observation Hash</h3>
              <span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-[#ECFDF5] text-[#059669]">Cryptographically Signed</span>
            </div>
            <div class="flex items-center space-x-2 mt-0.5 text-xs">
              <code class="font-mono text-[#64748B] text-[11px]">sha256:7f4a9b21884c03e18a994efca0019284cb912ad57088921e102f8374d6e9021a</code>
              <button onclick="copyToClipboard('7f4a9b21884c03e18a994efca0019284cb912ad57088921e102f8374d6e9021a')" class="text-[#94A3B8] hover:text-[#0F172A]" title="Copy Hash">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>
              </button>
            </div>
          </div>
        </div>

        <div class="flex items-center space-x-2">
          <button onclick="copyRawObservationJSON()" class="inline-flex items-center px-3 py-1.5 border border-[#E2E8F0] rounded-lg text-xs font-semibold text-[#334155] bg-white hover:bg-[#F8FAFC] transition">
            <svg class="w-3.5 h-3.5 mr-1.5 text-[#64748B]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"></path></svg>
            Copy Observation JSON
          </button>
          <button onclick="alert('Exporting complete Compliance Audit Package (JSON & Metadata Bundle)...')" class="inline-flex items-center px-3 py-1.5 bg-[#0F172A] text-white rounded-lg text-xs font-semibold hover:bg-[#1E293B] shadow-sm transition">
            <svg class="w-3.5 h-3.5 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
            Download Compliance PDF
          </button>
        </div>
      </div>

      <!-- Grouped Evidence Breakdown -->
      <div class="bg-[#F8FAFC] rounded-xl border border-[#E2E8F0] p-4">
        <div class="flex items-center justify-between mb-3 text-xs">
          <span class="font-bold text-[#DC2626] flex items-center">
            <svg class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
            Grouped Evidence Breakdown: 5 Independent Sources
          </span>
          <span class="text-[#64748B] font-mono text-[11px]">
            Clustered via Cortex Vector Similarity (&gt;=0.88 Cosine)
          </span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- Citation 1 -->
          <div class="bg-white p-3.5 rounded-lg border border-[#E2E8F0] text-xs space-y-2">
            <div class="flex justify-between items-start">
              <span class="font-bold text-[#0F172A]">Financial Times - London Edition</span>
              <span class="text-[#64748B] text-[11px]">28 Nov 2024</span>
            </div>
            <p class="text-[#475569] italic bg-[#F8FAFC] p-2 rounded border-l-2 border-[#4F46E5] text-[11px]">
              "...inquiries were opened into disputed shipping bills of exchange linked to ABC Trading Ltd's Thames estuary terminal operations..."
            </p>
            <div class="flex justify-between items-center pt-1 text-[11px]">
              <span class="text-[#4F46E5] font-semibold">Match Confidence: 96%</span>
              <a href="#" onclick="alert('Navigating to stored observation archive in Snowflake...')" class="text-[#2563EB] hover:underline font-medium inline-flex items-center">
                Source URL
                <svg class="w-3 h-3 ml-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
              </a>
            </div>
          </div>

          <!-- Citation 2 -->
          <div class="bg-white p-3.5 rounded-lg border border-[#E2E8F0] text-xs space-y-2">
            <div class="flex justify-between items-start">
              <span class="font-bold text-[#0F172A]">Bloomberg Terminal Wire</span>
              <span class="text-[#64748B] text-[11px]">03 Dec 2024</span>
            </div>
            <p class="text-[#475569] italic bg-[#F8FAFC] p-2 rounded border-l-2 border-[#4F46E5] text-[11px]">
              "Trade finance intermediaries report temporary settlement halts on transactions originating with ABC Trading Ltd following audit remarks."
            </p>
            <div class="flex justify-between items-center pt-1 text-[11px]">
              <span class="text-[#4F46E5] font-semibold">Match Confidence: 92%</span>
              <a href="#" onclick="alert('Navigating to stored observation archive in Snowflake...')" class="text-[#2563EB] hover:underline font-medium inline-flex items-center">
                Source URL
                <svg class="w-3 h-3 ml-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>

  </div>

  <script>
    function copyToClipboard(text) {
      navigator.clipboard.writeText(text);
      alert('Copied to clipboard: ' + text);
    }

    function copyRawObservationJSON() {
      const payload = {
        "case_id": "case_uk_9847_abc",
        "entity": {
          "legal_name": "ABC Trading Ltd",
          "lei": "5493001KJTIIGC8Y1R12",
          "cro": "0984721",
          "jurisdiction": "GB"
        },
        "cortex_assessment": {
          "score": 68,
          "disposition": "review_required",
          "reasons": [
            "Adverse Media Pressure (+45 pts)",
            "PSC Hierarchy Incomplete (+15 pts)",
            "Companies House Registered (-10 pts)"
          ]
        },
        "observation_hash": "sha256:7f4a9b21884c03e18a994efca0019284cb912ad57088921e102f8374d6e9021a",
        "storage_plane": "SNOWFLAKE_RAW.OBSERVATIONS"
      };
      navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
      alert('Copied Snowflake Observation JSON to clipboard!');
    }

    function scrollToProvenance() {
      const el = document.getElementById('provenance-section');
      if (el) el.scrollIntoView({ behavior: 'smooth' });
    }

    function recordAction(action) {
      const note = prompt('Enter Analyst Reviewer Rationale for [' + action + ']:', 'Screened against Companies House & Gazette filings. Escalated media cluster to Senior Reviewer.');
      if (note) {
        alert('Action locked to Snowflake TRUSTSIGNAL_OPS:\\nActor: Pulkit Arora\\nAction: ' + action + '\\nRationale: ' + note);
      }
    }

    function filterMatrix(category) {
      const items = document.querySelectorAll('.matrix-item');
      const tabs = document.querySelectorAll('.matrix-tab');
      
      tabs.forEach(t => {
        t.className = "matrix-tab px-3.5 py-1.5 rounded-lg text-xs font-medium text-[#64748B] hover:bg-[#F1F5F9] transition";
      });
      const activeTab = document.getElementById('tab-' + category);
      if (activeTab) {
        activeTab.className = "matrix-tab px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-[#0F172A] text-white";
      }

      items.forEach(item => {
        if (category === 'all') {
          item.style.display = 'flex';
        } else if (category === 'conflict' && (item.dataset.category === 'conflict')) {
          item.style.display = 'flex';
        } else if (category === 'match' && item.dataset.category === 'match') {
          item.style.display = 'flex';
        } else if (category === 'gap' && item.dataset.category === 'gap') {
          item.style.display = 'flex';
        } else {
          item.style.display = 'none';
        }
      });
    }
  </script>
</body>
</html>
"""

components.html(html_ui, height=1400, scrolling=True)
