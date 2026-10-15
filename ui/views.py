"""Native Streamlit workspaces based on the supplied Precision Blue design."""

from __future__ import annotations

import csv
import io
import json
from html import escape

import streamlit as st

from trust_signal.application.contracts import IdentitySearchCommand, SubmitCaseCommand
from trust_signal.models import SourceMode
from ui.components import badge, eyebrow, go, icon, message, metrics, node, section, title
from ui.design_data import CASES, FINDINGS, SOURCES
from ui.diagrams import TASK_GRAPH


def service():
    return st.session_state["trust_signal_app"]


def set_candidate(name: str, lei: str, jurisdiction: str | None) -> None:
    st.session_state.update(input_legal_name=name, input_lei=lei,
                            input_jurisdiction=jurisdiction or "")
    # Selecting a result must not issue another source search on the next rerender.
    st.session_state["last_search"] = (name, st.session_state.get("research_source_mode"))


def search_candidates() -> None:
    name = st.session_state.get("input_legal_name", "").strip()
    mode = st.session_state.get("research_source_mode", SourceMode.DEMO_FIXTURES)
    query = (name, mode)
    if st.session_state.get("last_search") == query:
        return
    st.session_state["last_search"] = query
    st.session_state["search_result"] = None
    st.session_state.pop("search_error", None)
    if len(name) < 2:
        return
    try:
        st.session_state["search_result"] = service().search_identity(
            IdentitySearchCommand(legal_name=name, source_mode=mode.value))
    except Exception:  # noqa: BLE001 - provider errors may contain credentials
        st.session_state["search_error"] = "Identity search could not be completed. Check the configured source and retry."


def launch_case() -> None:
    name = st.session_state.get("input_legal_name", "").strip()
    if not name:
        st.session_state["intake_error"] = "Please enter a legal party name to dispatch research."
        return
    try:
        receipt = service().submit_case(SubmitCaseCommand(
            legal_name=name, lei=st.session_state.get("input_lei", "").strip(),
            jurisdiction=st.session_state.get("input_jurisdiction", "").strip() or None,
            registration_id=st.session_state.get("input_registration_id", "").strip() or None,
            website=st.session_state.get("input_website", "").strip() or None,
            source_mode=st.session_state.get("research_source_mode", SourceMode.DEMO_FIXTURES).value))
        view = service().get_case(receipt.case_id)
        st.session_state["case_view"] = view
        st.session_state["case_result"] = view.result
        st.session_state["case_mode"] = st.session_state.get("research_source_mode", SourceMode.DEMO_FIXTURES)
        st.session_state.pop("intake_error", None)
        st.session_state["navigation"] = "Review & Dossier"
    except Exception:  # noqa: BLE001 - never display driver exception messages
        st.session_state["intake_error"] = "Error running case: the configured backend could not complete the request. Your inputs have been kept for retry."


def preview_notice(action: str) -> None:
    st.toast(f"{action}: design preview only. No account or research state was changed.", icon="ℹ️")


def intake() -> None:
    eyebrow("ENTITY ONBOARDING   ›   AUTONOMOUS RESEARCH DISPATCH   ›   INTAKE & LOOKUP",
            "1  Entity Identity    →    2  Source Scope    →    3  Agent Fan-out")
    title("Initiate Autonomous Entity Investigation",
          "Submit verified legal entity credentials. Cross-reference official registers before orchestrating downstream research and review.",
          "CORTEX AUTOMATED DISPATCH INTAKE")
    left, right = st.columns([7, 5], gap="large")
    with left:
        with st.container(key="card_identity"):
            head, meta = st.columns([3, 1])
            with head:
                section("Entity Identity Baseline", symbol="badge")
            with meta:
                st.html(badge("ISO 17442", "blue"))
            st.html('<div class="ts-divider"></div>')
            st.text_input("Official Registered Legal Entity Name", key="input_legal_name",
                          placeholder="e.g. Acme Sovereign Holdings PLC or Microsoft Corporation",
                          on_change=search_candidates)
            result = st.session_state.get("search_result")
            if st.session_state.get("search_error"):
                st.error(st.session_state["search_error"])
                st.button("Retry identity search", on_click=lambda: (
                    st.session_state.pop("last_search", None), search_candidates()), key="retry_search")
            if result and result.error:
                st.error(result.error)
            elif result and result.candidates:
                with st.container(key="candidate_panel"):
                    st.html('<div class="ts-label">TOP GLEIF MASTER FILE CANDIDATES</div>')
                    for index, candidate in enumerate(result.candidates):
                        info, action = st.columns([4, 1], vertical_alignment="center")
                        with info:
                            st.html(f'<div class="ts-entity-name">{escape(candidate.legal_name)}</div>'
                                    f'<div class="ts-entity-sub ts-mono">LEI: {escape(candidate.lei)} · '
                                    f'{escape(candidate.jurisdiction or "Not stated")}</div>')
                        with action:
                            st.button("Select Match", key=f"cand_box_{candidate.candidate_id}_{index}",
                                      on_click=set_candidate,
                                      args=(candidate.legal_name, candidate.lei, candidate.jurisdiction))
                    st.caption(f"{len(result.candidates)} candidates · {result.coverage}. Selection requires exact identity confirmation.")
            elif result:
                st.info("No registered entity candidates found. Adjust the name or enter a known LEI.")
            first, second = st.columns(2)
            with first:
                st.text_input("Primary Statutory Jurisdiction", key="input_jurisdiction",
                              placeholder="e.g. GB, US-WA, NO")
            with second:
                st.text_input("ISO 17442 LEI (20 Characters)", key="input_lei",
                              placeholder="e.g. INR2EJN1ERAN0W5ZP974", max_chars=20)
            first, second = st.columns(2)
            with first:
                st.text_input("National Registration ID", key="input_registration_id",
                              placeholder="e.g. CRN 09482910")
                st.caption("Registration identifier within the declared jurisdiction")
            with second:
                st.text_input("Statutory Headquarters Address", key="input_address",
                              placeholder="Street, city and postal code")
                st.caption("Supplementary intake context; not an identity confirmation")
            st.multiselect("Known Trading Aliases / Doing Business As (DBA)",
                           ["Acme Corp UK", "Sovereign Capital Ltd", "Acme Global Trust"],
                           accept_new_options=True, key="input_aliases")
            st.caption("Address and aliases are saved in the draft; research support for these fields is pending.")
            with st.container(key="mode_selector"):
                st.radio("Research mode", options=[SourceMode.DEMO_FIXTURES, SourceMode.GLEIF_LIVE],
                         format_func=lambda mode: "Deterministic Fixture" if mode == SourceMode.DEMO_FIXTURES else "Live GLEIF Ingestion",
                         horizontal=True, key="research_source_mode", on_change=search_candidates)
                st.caption("Configure official-source retrieval or deterministic sandbox playback.")
            with st.expander("Additional organization details"):
                st.text_input("Website", key="input_website", placeholder="https://example.org")
            st.html('<div class="ts-divider"></div>')
            save, launch = st.columns([1, 2])
            with save:
                if st.button("Save Draft Intake", icon=":material/bookmark_border:", width="stretch"):
                    st.session_state["saved_draft"] = {key: st.session_state.get(key) for key in (
                        "input_legal_name", "input_jurisdiction", "input_lei", "input_registration_id",
                        "input_address", "input_aliases", "input_website", "research_source_mode")}
                    st.toast("Draft saved for this browser session.", icon="✅")
            with launch:
                st.button("Launch Autonomous Research Pipeline", icon=":material/bolt:",
                          type="primary", width="stretch", key="btn_launch_pipeline", on_click=launch_case)
            if st.session_state.get("intake_error"):
                st.error(st.session_state["intake_error"])
        message("Original responses are retained before verified findings are released. Identity candidates never grant scoring eligibility.", "verified_user")
    with right:
        with st.container(key="card_coverage"):
            section("Pre-Submission Source Coverage", symbol="badge")
            st.caption("Design sample · available connectors do not establish case-specific checked coverage.")
            st.html('<div class="ts-label">SYNCHRONIZED & ACTIVE — DESIGN PREVIEW</div>')
            for pair in [("GLEIF Directory", "OFAC SDN Registry"), ("UK FCDO Sanctions", "World Bank Blacklist"), ("FCA Enforcement", "GDELT Global News")]:
                for col, name in zip(st.columns(2), pair, strict=True):
                    with col:
                        st.html(f'<div class="ts-note"><span class="green">●</span><div><strong>{name}</strong>'
                                '<div class="ts-subtle">Official source adapter</div></div></div>')
            st.html('<div class="ts-label">TRANSPARENT DISCLOSURES & GATED ADAPTERS</div>')
            message("Companies House (UK) Adapter — project verification paused until API access and source policy are approved.", "hourglass_empty")
            message("National Archives: UK Case Law — computational-analysis permission required.", "link_off")
            message("SEC EDGAR cross-match — future source extension; not enabled by this UI.", "upcoming")
        with st.container(key="card_topology"):
            section("Specialist Agent Fan-Out Topology", symbol="account_tree")
            st.caption("Target execution graph after a confirmed legal identity")
            node("1. Identity Confirmation Gate", "Exact record + submitted party consistency", "Required")
            st.html('<div class="ts-stage-arrow">↓</div>')
            for col, (name, desc) in zip(st.columns(2), [
                ("Sanctions", "Official lists"), ("Ownership", "Relationships"),
            ], strict=True):
                with col:
                    node(name, desc, "After identity")
            for col, (name, desc) in zip(st.columns(2), [("Legal", "Primary notices"), ("News", "Metadata discovery")], strict=True):
                with col:
                    node(name, desc, "After identity")
            st.html('<div class="ts-stage-arrow">↓</div>')
            node("3. Discrepancy Matrix Synthesis", "Aggregation → validation → human review", "Unscored by default", "green")


def review() -> None:
    view = st.session_state.get("case_view")
    if view is not None:
        actual_review(view)
        return
    eyebrow("Investigations   ›   Queue #UK-9847   ›   Live Review", "DESIGN SAMPLE · NO LIVE ASSESSMENT")
    with st.container(key="card_entity"):
        identity, risk = st.columns([7, 3])
        with identity:
            st.html(f'<div class="ts-inline">{badge("Identity Confirmed", "green")}'
                    f'{badge("GLEIF Active Record")}<span class="ts-subtle">UK Registered Private Limited</span></div>')
            title("ABC Trading Ltd 🇬🇧", "Specialized commodities import-export vehicle based in the City of London. Subject to multi-agent telemetry orchestration for enhanced compliance screening.")
            st.space("medium")
            st.html(f'<div class="ts-inline">{badge("LEI 5493001KJTIIGC8Y1R12")}'
                    f'{badge("UK CRO 0984721")}{badge("London, EC3V 3ND, United Kingdom")}</div>')
        with risk:
            st.html('<div class="ts-risk"><div class="ts-label">RISK ENGINE V2.4 · SAMPLE</div>'
                    '<h3>Cortex Automated Assessment</h3><div class="ts-risk-inner">'
                    '<div class="ts-ring"><strong>68</strong><small>/ 100</small></div>'
                    '<div class="ts-risk-bars"><small>Adverse Media Pressure <b class="red">+45 pts</b></small>'
                    '<div class="ts-risk-bar"><span style="width:90%;background:#dc2626"></span></div>'
                    '<small>PSC Hierarchy Incomplete <b class="purple">+15 pts</b></small>'
                    '<div class="ts-risk-bar"><span style="width:65%;background:#635bff"></span></div>'
                    '<small>Companies House Registered <b class="green">-10 pts</b></small>'
                    '<div class="ts-risk-bar"><span style="width:35%;background:#10b981"></span></div>'
                    '</div></div></div>')
            a, b = st.columns(2)
            a.button("Approve", icon=":material/check_circle:", width="stretch", on_click=preview_notice, args=("Approval",))
            b.button("Flag for Review", icon=":material/flag:", type="primary", width="stretch", on_click=preview_notice, args=("Review action",))
    section("Autonomous Research Pipeline", "Filter matrix findings by selecting an agent")
    agents = [("Registry Specialist", "GLEIF, UK Companies House", "Completed", "100% Verified", "0.42s latency", "green"),
              ("Ownership & PSC Specialist", "Beneficial Owners, Holding Hierarchy", "Coverage Gap", "30% Complete", "View Gap", "purple"),
              ("Legal & Litigation", "High Court Rolls, London Gazette", "Sanctions Clear", "Resolved Petition", "1 Petition (Dismissed)", "blue"),
              ("Adverse Media & News", "Bloomberg, LexisNexis, FT Index", "5 Clustered Alerts", "Financial Misrepresentation", "Flagged", "red")]
    for col, (name, desc, status, percent, timing, tone) in zip(st.columns(4), agents, strict=True):
        with col, st.container(key=f"card_agent_{tone}"):
            symbol = {"green": "fact_check", "purple": "account_tree", "blue": "gavel", "red": "newspaper"}[tone]
            st.html(f'<div class="ts-inline" style="justify-content:space-between"><span class="ts-agent-icon {tone}">{icon(symbol)}</span>{badge(status, tone)}</div>')
            st.html(f'<div class="ts-entity-name">{escape(name)}</div><div class="ts-subtle">{escape(desc)}</div>')
            st.html(f'<div class="ts-inline {tone}" style="justify-content:space-between;font-size:10px"><b>{percent}</b><span class="ts-mono">{timing}</span></div>')
            st.progress(0.3 if tone == "purple" else 0.85 if tone == "red" else 1.0)
            st.button("Filter findings", key=f"filter_{tone}", type="tertiary", on_click=lambda value=name: st.session_state.update(agent_filter=value))
    with st.container(key="card_matrix"):
        heading, filters = st.columns([1, 1.1], vertical_alignment="center")
        with heading:
            section("Cross-Agent Telemetry & Discrepancy Matrix", "Deterministic comparison across official registers, public disclosures, and external intelligence streams.")
        with filters:
            selected = st.segmented_control("Finding category", ["All Findings", "Discrepancies & Conflicts", "Confirmed Matches", "Coverage Gaps"],
                                            default="All Findings", required=True, label_visibility="collapsed", key="finding_category")
        agent_filter = st.session_state.get("agent_filter")
        if agent_filter:
            st.caption(f"Agent filter: {agent_filter}")
            if st.button("Clear agent filter", key="clear_agent"):
                st.session_state.pop("agent_filter", None)
                st.rerun()
        visible = [item for item in FINDINGS if (selected == "All Findings" or item["category"] == selected
                   or (selected == "Discrepancies & Conflicts" and item["tone"] == "purple"))
                   and (not agent_filter or item["agent"] == agent_filter)]
        if not visible:
            st.info("No sample findings match these filters.")
        for index, item in enumerate(visible):
            content, action = st.columns([4, 1.2], vertical_alignment="center")
            with content:
                st.html(f'<div class="ts-finding"><span class="ts-agent-icon {item["tone"]}">{icon(item["icon"])}</span><div><div class="ts-inline">{badge(item["label"], item["tone"])}'
                        f'<span class="ts-subtle">Agent: {escape(item["agent"])} · {escape(item["confidence"])}</span></div>'
                        f'<h3>{escape(item["title"])}</h3><p>{escape(item["detail"])}</p></div></div>')
            with action:
                if st.button(item["action"], key=f"finding_{index}", icon=":material/visibility:", width="stretch"):
                    st.session_state["show_evidence"] = True
            if item != visible[-1]:
                st.html('<div class="ts-divider"></div>')
    with st.container(key="card_evidence"):
        heading, download = st.columns([3, 2])
        with heading:
            section("Audit Provenance & Cortex Observation Hash", symbol="database")
            st.caption("sha256:7f4a9b21804c83e18a994efca0019284cb912ad57088921e102f8374d6e9021a · design example")
        with download:
            st.download_button("Copy Observation JSON / Download", json.dumps({"mode": "design_sample", "entity": "ABC Trading Ltd", "sample_score": 68, "findings": FINDINGS}, indent=2),
                               "trustsignal-design-observation.json", "application/json", icon=":material/data_object:", width="stretch")
            st.button("Download Compliance PDF", icon=":material/download:", disabled=True,
                      help="A verified backend report export is required for a compliance PDF.", width="stretch")
        with st.expander("Grouped Evidence Breakdown: 5 Independent Sources", expanded=st.session_state.get("show_evidence", True)):
            first, second = st.columns(2)
            with first:
                st.markdown("**Financial Times – London Edition** · 28 Nov 2024")
                st.caption('“...inquiries were opened into disputed shipping bills of exchange linked to ABC Trading Ltd’s Thames estuary terminal operations...”')
                st.html(badge("Match Confidence: 96%", "purple"))
            with second:
                st.markdown("**Bloomberg Terminal Wire** · 03 Dec 2024")
                st.caption('“Trade finance intermediaries report temporary settlement halts on transactions originating with ABC Trading Ltd to finalize audit remarks.”')
                st.html(badge("Match Confidence: 92%", "purple"))
            st.caption("Illustrative snippets from the design. These are not retrieved publications.")


def actual_review(view) -> None:
    eyebrow(f"Investigations   ›   {view.case_id}   ›   Research Result", "APPLICATION RESULT")
    with st.container(key="card_actual_identity"):
        title(view.legal_name, f"Case {view.case_id} · {view.status.value.replace('_', ' ').title()}")
        st.html(badge(view.status.value.replace("_", " ").title(), "blue"))
        if view.lei:
            st.caption(f"LEI: {view.lei}")
        mode = st.session_state.get("case_mode")
        if mode == SourceMode.DEMO_FIXTURES:
            st.info("Local fixtures only. No external registries, news, sanctions, or legal sources were queried.")
        else:
            st.info("Live source mode. Only the checked sources and retained evidence below establish coverage.")
        if view.error:
            st.error("The case could not be loaded from the configured backend.")
        if view.status.value == "needs_more_information":
            st.warning("More identity information is needed before research can run.")
        for reason in view.reasons:
            st.markdown(f"- {reason}")
        result = view.result
        if result is not None:
            st.metric("Assessment", result.assessment.score_status.replace("_", " ").title())
        st.button("Return to Intake", on_click=go, args=("Intake & Lookup",), icon=":material/arrow_back:")
    section("Research Pipeline", "Actual branch status; skipped or failed research is an explicit gap.")
    if view.branches:
        for col, branch in zip(st.columns(min(len(view.branches), 4)), view.branches[:4], strict=True):
            with col, st.container(key=f"card_actual_{branch['branch_id']}"):
                section(branch["branch_id"].replace("_", " ").title())
                st.html(badge(branch["status"].replace("_", " ").title()))
    with st.container(key="card_actual_findings"):
        section("Findings & Comparison", symbol="compare_arrows")
        if view.comparison_board:
            for item in view.comparison_board:
                st.markdown(f"**{item['relation'].replace('_', ' ').title()}**")
                st.write(item["summary"])
        else:
            st.info("No comparison findings were produced. This does not establish a clean risk assessment.")
        if result is not None:
            with st.expander("Full observation and case JSON"):
                st.json(result.model_dump(mode="json"))
            st.download_button("Download Case JSON", result.model_dump_json(indent=2),
                               f"{view.case_id}.json", "application/json", icon=":material/download:")


def cases() -> None:
    eyebrow("CASES   ›   Cases / Queue", "42 Total Entities Tracked    ·    5 Action Required    ·    8 In Review    ·    29 Cleared")
    text, buttons = st.columns([3, 1.8], vertical_alignment="bottom")
    with text:
        title("Entity Investigations Queue", "Real-time graph orchestration, identity verification, and adverse intelligence consensus.")
    with buttons:
        rescan, create = st.columns([1, 1.3])
        rescan.button("Trigger Rescan", icon=":material/sync:", on_click=preview_notice,
                      args=("Rescan",), width="stretch")
        create.button("New Investigation", type="primary", icon=":material/add:", width="stretch", on_click=go, args=("Intake & Lookup",))
    with st.container(key="card_queue_filters"):
        search, risk, jurisdiction = st.columns([3, 1.1, 2.1], vertical_alignment="bottom")
        query = search.text_input("Search investigations", placeholder="Search entity name, LEI, Reg No, or jurisdiction…", label_visibility="collapsed", icon=":material/search:")
        tier = risk.selectbox("Risk tier", ["All Tiers", "High Risk", "Review Required", "Low Risk"], label_visibility="collapsed")
        region = jurisdiction.segmented_control("Jurisdiction", ["All", "UK", "US", "EU", "Norway", "APAC"], default="All", required=True, label_visibility="collapsed")
    metrics([("HIGH RISK", "5 Entities", "Immediate review required · +2 today", "warning", "red"),
             ("AUTONOMOUS AGENT PROCESSING", "8 Active", "Avg latency: 1.4s / DAG task", "neurology", "purple"),
             ("COVERAGE GAPS", "4 Entities", "Missing UBO or PSC node · Actionable", "pie_chart", "orange"),
             ("AUTO-SCORED & VERIFIED", "29 Cleared", "99.4% confidence average · Zero gaps", "verified", "green")])
    rows = [item for item in CASES if query.casefold() in json.dumps(item).casefold()
            and (region == "All" or item["jurisdiction"] == region)
            and (tier == "All Tiers" or (tier == "High Risk" and item["score"] >= 75)
                 or (tier == "Review Required" and 40 <= item["score"] < 75)
                 or (tier == "Low Risk" and item["score"] < 40))]
    widths = [2.4, 1.2, 1.7, 2.5, .7, 1.1]
    with st.container(key="card_queue"):
        with st.container(key="qhead"):
            label, sort = st.columns([4, 1.5], vertical_alignment="center")
            with label:
                section("Queue Ledger", f"{len(rows)} sample items shown")
            order = sort.selectbox("Sort", ["Risk Descending", "Risk Ascending", "Entity Name"], label_visibility="collapsed")
        rows = sorted(rows, key=(lambda x: x["name"]) if order == "Entity Name" else lambda x: x["score"], reverse=order == "Risk Descending")
        with st.container(key="qcolumns"):
            for col, heading in zip(st.columns(widths), ["ENTITY & LEGAL FORM", "RISK SCORE", "AGENT DAG VERIFICATION", "KEY FINDINGS / DISCREPANCY", "SYNC AGE", "ACTION"], strict=True):
                col.html(f'<div class="ts-label">{heading}</div>')
        for item in rows:
            with st.container(key=f"qrow_{item['id']}"):
                entity, score, agents, finding, age, action = st.columns(widths, vertical_alignment="center")
                entity.html(f'<div class="ts-entity-name">{item["flag"]}　{escape(item["name"])}</div><div class="ts-entity-sub"><b class="ts-mono">{escape(item["id"])}</b>　{escape(item["form"])}</div>')
                score.html(f'<span class="ts-score-small {item["tone"]}">{item["score"]}</span><span style="font-size:9px;font-weight:700" class="{item["tone"]}">{item["status"]}</span>')
                agents.html(f'<div class="ts-inline">{badge("Reg ✓", "green")}{badge("UBO ×" if item["score"] > 80 else "UBO ✓", "red" if item["score"] > 80 else "green")}{badge("Lit ✓")}{badge("Media !" if item["score"] > 50 else "Media ✓", item["tone"])}</div>')
                finding.html(f'<div style="font-size:12px" class="{item["tone"]}">{escape(item["finding"])}</div><div class="ts-entity-sub">{escape(item["detail"])}</div>')
                age.html(f'<span class="ts-mono">{item["age"]}</span>')
                action.button(item["action"], key=f"open_{item['id']}", width="stretch", on_click=open_sample, args=(item,))
        if not rows:
            st.info("No sample investigations match your filters.")
        with st.container(key="qfooter"):
            count, download, sync, pagination = st.columns([2, 1.4, 1.8, 1.2], vertical_alignment="center")
            count.caption(f"Showing {len(rows)} of {len(CASES)} sample entities")
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=list(CASES[0]))
            writer.writeheader()
            writer.writerows(rows)
            download.download_button("Export Forensic Audit CSV", output.getvalue(), "sample-queue.csv", "text/csv", icon=":material/download:", width="stretch")
            sync.button("Sync with Snowflake Warehouse", icon=":material/cloud_sync:", on_click=preview_notice, args=("Warehouse sync",), width="stretch")
            with pagination:
                previous, current, following = st.columns(3, gap="small")
                previous.button("‹", disabled=True, help="First sample page", key="previous_page")
                current.button("1", type="primary", disabled=True, help="Five sample records on one page", key="current_page")
                following.button("›", disabled=True, help="No additional sample records", key="next_page")
    with st.container(key="card_queue_dag"):
        a, b = st.columns([4, 1], vertical_alignment="center")
        with a:
            section("Auto-Orchestration DAG Pipeline", "Sample queue reflects the supplied design; full managed execution remains an integration gate.", "hub")
        b.button("View DAG graph →", on_click=go, args=("Operations & DAG",), width="stretch")


def open_sample(item: dict) -> None:
    if item["name"] == "ABC Trading Ltd":
        st.session_state.pop("case_view", None)
        st.session_state.pop("case_result", None)
        go("Review & Dossier")
    else:
        set_candidate(item["name"], item["id"] if len(item["id"]) == 20 else "", {"UK": "GB", "Norway": "NO", "EU": "DE", "US": "US-WA"}.get(item["jurisdiction"]))
        go("Intake & Lookup")


def sources() -> None:
    eyebrow("System Administration   ›   Source Catalog & Integration Health", "INGESTION_FABRIC · DESIGN SAMPLE")
    text, action = st.columns([3, 1.8], vertical_alignment="bottom")
    with text:
        title("Authoritative Sources & Intelligence Connectors", "Telemetry ingestion pipelines, national company registers, sanctions watchlists, and court record daemons mapped to the evidence warehouse.", "FEDERATED CONNECTORS")
    with action:
        poll, provision = st.columns(2)
        poll.button("Poll Source Health Now", icon=":material/sync:", width="stretch", on_click=preview_notice, args=("Source-health poll",))
        provision.button("Provision Adapter", icon=":material/add_link:", type="primary", width="stretch",
                         on_click=preview_notice, args=("Adapter provisioning",))
    metrics([("TOTAL CONNECTORS", "14", "Enterprise Registry Mesh · v4.19 Spec", "hub", "blue"),
             ("HEALTHY PIPELINES", "9", "99.8% Uptime · < 350ms avg", "check_circle", "green"),
             ("RATE-LIMITED / CACHED", "2", "Companies House, GDELT · Snapshot fallback", "speed", "blue"),
             ("GATED / ACTION REQD", "1", "UK Find Case Law · Contract pending", "lock", "red")])
    with st.container(key="card_source_filters"):
        filters, search = st.columns([3, 1])
        category = filters.segmented_control("Source category", ["All", "Official Registries", "Sanctions & Debarment", "Litigation & Court", "Adverse Media & News"], default="All", required=True, label_visibility="collapsed")
        query = search.text_input("Filter sources", placeholder="Filter sources by name or ID…", icon=":material/search:", label_visibility="collapsed")
    items = [item for item in SOURCES if (category == "All" or item["category"] == category)
             and query.casefold() in json.dumps(item).casefold()]
    if not items:
        st.info("No connectors match these filters.")
    for offset in range(0, len(items), 3):
        for col, item in zip(st.columns(3), items[offset:offset + 3], strict=False):
            with col, st.container(key=f"card_source_{item['short']}"):
                name, status = st.columns([3, 1.2])
                name.html(f'<div class="ts-source-heading"><span class="ts-initial">{item["short"]}</span><div><strong>{escape(item["name"])}</strong><small>{escape(item["authority"])}</small></div></div>')
                status.html(badge(item["status"], item["tone"]))
                st.html(f'<p class="ts-subtle" style="min-height:54px">{escape(item["description"])}</p>')
                if item.get("warning"):
                    message(item["warning"], "warning")
                st.html(f'<div class="ts-source-details"><div><small>{item["label"]}</small><strong class="{item["tone"]}">{escape(item["metric"])}</strong></div>'
                        f'<div><small>ADAPTER / SYNC</small><strong>{escape(item["version"])}</strong></div>'
                        f'<div class="table"><small>STORAGE TABLE · DESIGN</small><strong>{escape(item["table"])}</strong></div></div>')
                with st.expander("Inspect Schema →"):
                    st.json({"source": item["name"], "category": item["category"], "sample_storage_table": item["table"], "status_is_sample": True,
                             "evidence_fields": ["source_id", "source_record_id", "observed_at", "content_hash", "connector_version"]})
    with st.container(key="card_governance"):
        section("Snowflake Ingestion Governance & Boundary Contract", "FORENSIC EPISTEMIC SEPARATION PROTOCOL · ARCHITECTURE STANDARD 2.4", "policy")
        message("Evidentiary Boundary: Source Presence ≠ Legal Proof. Ingestion records source observations. Legal identity, claim review, scoring and business decisions remain separate gates.", "info")
        for col, (heading, body) in zip(st.columns(3), [("SOURCE WORKER", "Fetch → retain → verify → release"), ("CRYPTOGRAPHIC PROVENANCE", "SHA-256 of original retained bytes"), ("FAILURE POLICY", "Explicit blocked, partial or failed coverage")], strict=True):
            with col:
                node(heading, body, "Contract boundary")


def operations() -> None:
    eyebrow("Telemetry Operations   ›   Snowflake Cortex Orchestrator   ›   DAG Task Graph Telemetry", "OPERATOR PRIVILEGED CONSOLE · SAMPLE")
    text, warehouse = st.columns([3, 1.3], vertical_alignment="bottom")
    with text:
        title("Orchestration DAG & Compute Telemetry", "Snowpark Engine v4.19 · Region: eu-west-1 (Frankfurt Primary)", "SNOWPARK ENGINE V4.19")
    warehouse.segmented_control("Warehouse", ["DEV_WH  XS", "STAGE_WH  S", "PROD_READONLY  L"], default="DEV_WH  XS", required=True, label_visibility="collapsed")
    metrics([("WAREHOUSE UTILIZATION", "18%", "DEV_WH (XS) · Idle capacity reserved: 82%", "memory", "purple"),
             ("TERMINAL GATES INTERCEPTED", "14 Runs Halting", "+82% compute saved before specialist fan-out", "shield", "green"),
             ("PIPELINE P95 LATENCY", "1.34s", "Snowpark Cortex LLM orchestration average", "speed", "purple"),
             ("QUARANTINE / PAUSED RUNS", "1 Active Quarantine", "Awaiting operator audit · reconciliation lock active", "lock", "red")])
    with st.container(key="card_dag"):
        a, b = st.columns([3, 1.4], vertical_alignment="center")
        with a:
            section("Snowflake Cortex Task Graph", "Interactive fan-out stage view with deterministic circuit-breakers and branch execution telemetry", "account_tree")
        mode = b.segmented_control("View Mode", ["Logical Flow", "Resource Pool"], default="Logical Flow", required=True, label_visibility="collapsed")
        st.space("small")
        if mode == "Logical Flow":
            st.graphviz_chart(TASK_GRAPH, width="stretch", height=350)
        else:
            st.dataframe([{"Worker": f"worker-{i:02}", "Warehouse": "DEV_WH", "State": "Reserved" if i == 8 else "Ready", "Slots": 1} for i in range(1, 9)], hide_index=True, width="stretch")
        message("Automatic Pre-Emptive Pruning: if TS_IDENTITY fails, specialist branches stay blocked. Diagram timings and scores are sample design values.", "info")
    recent, quarantine = st.columns([5, 7])
    with recent, st.container(key="card_recent_runs"):
        section("Recent Execution Runs", "Sample execution history", "history")
        for name, run, status, tone in [("ABC Trading Ltd", "run_c91a78e", "Cleared (94/100)", "green"),
                                        ("Apex Global Logistics", "run_b44f21d", "Halted at Gate", "red"),
                                        ("Microsoft Corp", "run_8812a4f", "Cleared (99/100)", "green"),
                                        ("Sterling Pacific Shipping", "run_0f84be1", "Completed (72/100)", "blue")]:
            st.html(f'<div class="ts-note" style="justify-content:space-between"><div><b>{escape(name)}</b><div class="ts-mono">{run}</div></div>{badge(status, tone)}</div>')
        st.caption("Showing latest 4 of 1,280 sample runs")
        st.button("View History →", on_click=preview_notice, args=("Run history",))
    with quarantine, st.container(key="card_quarantine"):
        st.html(f'<div class="ts-inline">{badge("QUARANTINE RECORD", "red")}<span class="ts-mono">RUN_ID: run_b44f21d</span></div>')
        section("Apex Global Logistics Inc.", "GATE STATUS: INTERCEPTED (CODE_409)")
        message("Conflicting Entity Registry Hashes Detected — the Companies House hash contradicts the European registry hash. Sample worker lock: QUIESCED.", "report")
        for col, heading, value in zip(st.columns(3), ["CREDITS CONSUMED", "CREDITS AVOIDED", "WORKER LOCK"], ["0.00042 CR", "0.01890 CR", "QUIESCED"], strict=True):
            with col:
                node(heading, value, "Design sample")
        st.space("medium")
        left, right = st.columns(2)
        left.button("Quiesce & Reconcile", icon=":material/pause_circle:", width="stretch", on_click=preview_notice, args=("Reconciliation",))
        right.button("Authorized Requeue", type="primary", icon=":material/replay:", width="stretch", on_click=preview_notice, args=("Requeue",))
        st.caption("Operator controls are previews; they do not mutate a cloud account.")
    with st.container(key="card_task_root"):
        section("Snowflake Cortex Task Root & Cryptographic Provenance", "Design reference · not an applied task definition", "terminal")
        st.code("""-- DESIGN EXAMPLE ONLY
CREATE OR REPLACE TASK ts_dag_orch_v2
  WAREHOUSE = 'DEV_WH'
  SCHEDULE = 'USING CRON 0/1 * * * * UTC'
  USER_TASK_TIMEOUT_MS = 15000
  SUSPEND_TASK_AFTER_NUM_FAILURES = 2
AS
  CALL SYSTEM$CORTEX_ORCHESTRATE_DISCREPANCY_MATRIX(
    'graph_ref' => 'urn:trustsignal:cortex:dag:0x93FA',
    'enable_terminal_gates' => TRUE,
    'merkle_provenance_audit' => 'SHA256_ACTIVE'
  );""", language="sql")
        st.caption("Worker pool status: 8 threads ready (1 reserved for emergency quarantine dispatch) · sample telemetry")
