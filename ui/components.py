"""Small presentational helpers; all application controls are Streamlit widgets."""

from html import escape

import streamlit as st


def icon(name: str) -> str:
    return f'<span class="material-symbols-outlined" aria-hidden="true">{escape(name)}</span>'


def badge(label: str, tone: str = "blue") -> str:
    return f'<span class="ts-badge {escape(tone)}">{escape(label)}</span>'


def eyebrow(text: str, right: str = "") -> None:
    st.html(f'<div class="ts-breadcrumb"><span>{escape(text)}</span>'
            f'<span class="ts-mono">{escape(right)}</span></div>')


def title(heading: str, description: str, kicker: str = "") -> None:
    st.html(f'<div class="ts-page-title"><div class="ts-kicker">{escape(kicker)}</div>'
            f'<h1>{escape(heading)}</h1><p>{escape(description)}</p></div>')


def section(heading: str, description: str = "", symbol: str = "") -> None:
    st.html(f'<div class="ts-section-title">{icon(symbol) if symbol else ""}'
            f'<div><h2>{escape(heading)}</h2>'
            f'{f"<p>{escape(description)}</p>" if description else ""}</div></div>')


def metrics(items: list[tuple[str, str, str, str, str]]) -> None:
    for column, (label, value, detail, symbol, tone) in zip(st.columns(len(items)), items, strict=True):
        with column:
            st.html(f'<div class="ts-metric {escape(tone)}">'
                    f'<div class="ts-metric-label">{escape(label)}{icon(symbol)}</div>'
                    f'<div class="ts-metric-value">{escape(value)}</div>'
                    f'<div class="ts-metric-detail">{escape(detail)}</div></div>')


def node(name: str, description: str, status: str, tone: str = "blue") -> None:
    st.html(f'<div class="ts-node {escape(tone)}"><strong>{escape(name)}</strong>'
            f'<p>{escape(description)}</p>{badge(status, tone)}</div>')


def go(page: str) -> None:
    st.session_state["navigation"] = page


def message(text: str, symbol: str = "info") -> None:
    st.html(f'<div class="ts-note">{icon(symbol)}<span>{escape(text)}</span></div>')
