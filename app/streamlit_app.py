"""
streamlit_app.py — entry point & multipage shell.

Wires the five views into a branded sidebar navigation and renders the shared
chrome (global CSS, brand lockup, footer) once around every page. Run with:

    streamlit run streamlit_app.py
"""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="Wildlife Collision Risk · Australia",
    page_icon="🦘",
    layout="wide",
    initial_sidebar_state="expanded",
)

from components import theme  # noqa: E402  (after set_page_config, by design)
from components.views import (  # noqa: E402
    explorer,
    methodology,
    overview,
    segment_detail,
    sign_placements,
)

# ── Session defaults ──────────────────────────────────────────────────────────
st.session_state.setdefault("selected_segment", None)

# ── Shared chrome ─────────────────────────────────────────────────────────────
theme.inject_css()
theme.brand_mark()

# ── Pages ─────────────────────────────────────────────────────────────────────
pages = {
    "overview": st.Page(
        overview.render,
        title="National Overview",
        icon="🗺️",
        url_path="overview",
        default=True,
    ),
    "explorer": st.Page(
        explorer.render, title="Risk Explorer", icon="🔎", url_path="explorer"
    ),
    "detail": st.Page(
        segment_detail.render, title="Segment Detail", icon="📈", url_path="segment"
    ),
    "signs": st.Page(
        sign_placements.render, title="Sign Placements", icon="🚸", url_path="signs"
    ),
    "method": st.Page(
        methodology.render,
        title="Methodology & Data",
        icon="📚",
        url_path="methodology",
    ),
}
# Stored so any view can navigate programmatically (see components/ui.goto).
st.session_state["_pages"] = pages

pg = st.navigation(list(pages.values()))
pg.run()

theme.footer()
