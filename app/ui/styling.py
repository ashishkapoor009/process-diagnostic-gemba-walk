"""Shared professional blue/white consulting-dashboard styling injected on
every Streamlit page, plus a light/dark mode toggle stored in session state
(Streamlit's native theme is light by default per .streamlit/config.toml;
this CSS overlay provides a dark variant driven entirely client-side).
"""
from __future__ import annotations

import streamlit as st

APP_TITLE = "Process Diagnostic / Gemba Walk Multi-Agent Solution"
APP_SUBTITLE = "Multi-Agent Process Excellence & Lean Six Sigma Diagnostic Platform"

_LIGHT_CSS = """
<style>
:root {
    --pe-blue: #1D4ED8;
    --pe-blue-light: #DBEAFE;
    --pe-blue-dark: #1E3A8A;
    --pe-bg: #FFFFFF;
    --pe-card-bg: #F8FAFC;
    --pe-text: #0F172A;
    --pe-border: #E2E8F0;
}
.pe-card {
    background: var(--pe-card-bg);
    border: 1px solid var(--pe-border);
    border-radius: 12px;
    padding: 1.1rem 1.3rem;
    margin-bottom: 0.8rem;
}
.pe-metric-value { font-size: 1.9rem; font-weight: 700; color: var(--pe-blue-dark); }
.pe-metric-label { font-size: 0.82rem; color: #64748B; text-transform: uppercase; letter-spacing: 0.04em; }
.pe-badge {
    display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 0.75rem;
    font-weight: 600; margin-right: 6px; margin-bottom: 4px;
}
.pe-badge-blue { background: var(--pe-blue-light); color: var(--pe-blue-dark); }
.pe-badge-green { background: #DCFCE7; color: #14532D; }
.pe-badge-red { background: #FEE2E2; color: #7F1D1D; }
.pe-badge-amber { background: #FEF3C7; color: #78350F; }
.pe-badge-purple { background: #EDE9FE; color: #4C1D95; }
.pe-header-banner {
    background: linear-gradient(90deg, #1D4ED8 0%, #2563EB 60%, #3B82F6 100%);
    color: white; padding: 1.4rem 1.8rem; border-radius: 14px; margin-bottom: 1.2rem;
}
.pe-header-banner h1 { color: white; margin: 0; font-size: 1.6rem; }
.pe-header-banner p { color: #DBEAFE; margin: 0.2rem 0 0 0; font-size: 0.95rem; }
[data-testid="stSidebar"] { background-color: #0F172A; }
[data-testid="stSidebar"] * { color: #E2E8F0 !important; }
</style>
"""

_DARK_OVERRIDE_CSS = """
<style>
:root {
    --pe-bg: #0B1220; --pe-card-bg: #111827; --pe-text: #E5E7EB; --pe-border: #1F2937;
}
.stApp { background-color: #0B1220; color: #E5E7EB; }
.pe-card { background: #111827; border-color: #1F2937; }
</style>
"""


def apply_branding(page_icon: str = "🧭") -> None:
    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = False

    st.markdown(_LIGHT_CSS, unsafe_allow_html=True)
    if st.session_state.dark_mode:
        st.markdown(_DARK_OVERRIDE_CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str = "") -> None:
    st.markdown(
        f"""<div class="pe-header-banner"><h1>{title}</h1><p>{subtitle}</p></div>""",
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str, col=None) -> None:
    target = col if col is not None else st
    target.markdown(
        f"""<div class="pe-card"><div class="pe-metric-value">{value}</div>
        <div class="pe-metric-label">{label}</div></div>""",
        unsafe_allow_html=True,
    )


def badge(text: str, color: str = "blue") -> str:
    return f'<span class="pe-badge pe-badge-{color}">{text}</span>'
