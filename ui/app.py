"""Native Streamlit TrustSignal application, styled from the supplied design."""

import sys
from pathlib import Path

# Streamlit adds the script's directory (ui/), not necessarily its parent.
# Resolve the UI package from this file for launches from any working directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from trust_signal.application.service import LocalSynchronousApplication
from ui import views
from ui.components import icon

st.set_page_config(page_title="TrustSignal CORE | Entity Intelligence", page_icon="🛡️",
                   layout="wide", initial_sidebar_state="collapsed")

st.html(f"<style>{Path(__file__).with_name('styles.css').read_text()}</style>")

if "trust_signal_app" not in st.session_state:
    st.session_state["trust_signal_app"] = LocalSynchronousApplication()

with st.container(key="header"):
    brand, navigation, account = st.columns([1.3, 4.7, 3], vertical_alignment="center")
    with brand:
        st.html('<div class="ts-brand"><div class="ts-shield">'
                '<span class="material-symbols-outlined">verified_user</span></div>'
                '<div><strong>TrustSignal</strong><span class="ts-core">CORE</span>'
                '<small>ENTITY INTELLIGENCE</small></div></div>')
    with navigation:
        page = st.radio("Workspace", ["Cases / Queue", "Intake & Lookup", "Review & Dossier",
                                      "Sources & Feeds", "Operations & DAG"],
                        index=2, key="navigation", horizontal=True, label_visibility="collapsed")
    with account:
        st.html('<div class="ts-account"><span class="session">'
                '<span class="green">●</span> &nbsp; DESIGN WORKSPACE · SAMPLE DATA</span>'
                '<div class="identity"><b>Pulkit Arora</b><br><small>Lead Compliance Analyst · persona</small></div>'
                '<span class="avatar">PA</span></div>')

with st.container(key="workspace"):
    {"Cases / Queue": views.cases, "Intake & Lookup": views.intake,
     "Review & Dossier": views.review, "Sources & Feeds": views.sources,
     "Operations & DAG": views.operations}[page]()

st.html('<div class="ts-footer"><span>TrustSignal Systems · Forensic Entity Research Workspace</span>'
        f'<span>{icon("verified_user")} Design samples are illustrative; actual research keeps its evidence and coverage.</span></div>')
