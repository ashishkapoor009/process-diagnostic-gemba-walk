"""Renders Mermaid diagram text inside Streamlit via an embedded HTML
component (mermaid.js from CDN), since Streamlit has no native Mermaid
renderer. The Mermaid source is also shown in an expander so it can be
copy-pasted into Visio/Lucidchart/draw.io per the spec's portability requirement.
"""
from __future__ import annotations

import html

import streamlit as st
import streamlit.components.v1 as components


def render_mermaid(code: str, height: int = 480, key: str = "") -> None:
    if not code or not code.strip():
        st.info("No diagram available yet.")
        return

    escaped = html.escape(code)
    components.html(
        f"""
        <div class="mermaid" style="background:white;padding:12px;border-radius:10px;">{escaped}</div>
        <script type="module">
            import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs";
            mermaid.initialize({{ startOnLoad: true, theme: "default", securityLevel: "loose" }});
        </script>
        """,
        height=height,
        scrolling=True,
    )
    with st.expander("View / copy Mermaid source"):
        st.code(code, language="text")
