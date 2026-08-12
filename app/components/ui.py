"""
ui.py: small interaction helpers shared across the page views.

The selection APIs (st.dataframe / st.pydeck_chart `on_select`) require recent
Streamlit (dataframe ≥1.35, pydeck ≥1.38). Each helper degrades gracefully on
older versions so the app stays usable: the table falls back to a selectbox and
the map simply renders without click-to-select.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st


def select_row(df: pd.DataFrame, key: str, column_config: dict | None = None,
               height: int = 340) -> pd.Series | None:
    """Sortable single-row-selectable table. Returns the selected row or None."""
    try:
        event = st.dataframe(
            df, key=key, on_select="rerun", selection_mode="single-row",
            width='stretch', hide_index=True, height=height,
            column_config=column_config,
        )
        sel = getattr(event, "selection", None)
        rows = (sel.get("rows", []) if isinstance(sel, dict)
                else getattr(sel, "rows", [])) if sel is not None else []
        return df.iloc[rows[0]] if rows else None
    except TypeError:
        # Streamlit too old for dataframe selection: render + selectbox fallback.
        st.dataframe(df, width='stretch', hide_index=True,
                     height=height, column_config=column_config)
        id_col = df.columns[0]
        choice = st.selectbox(f"Select by {id_col}", ["—"] + df[id_col].tolist(), key=f"{key}_sb")
        return df[df[id_col] == choice].iloc[0] if choice != "—" else None


def select_on_map(map_obj, key: str, height: int = 460):
    """Render a folium map with object selection; returns the event or None."""
    from streamlit_folium import st_folium
    try:
        return st_folium(
            map_obj,
            width='100%',
            height=height,
            returned_objects=["last_active_drawing", "last_object_clicked", "last_object_clicked_tooltip"],
            key=key,
        )
    except Exception:
        # Fallback if there are issues
        from streamlit_folium import folium_static
        folium_static(map_obj, width=700, height=height)
        return None


def render_static_map(html_str: str, height: int = 460):
    """Render a pre-computed HTML map extremely fast without any callbacks."""
    import streamlit as st
    st.iframe(html_str, height=height)


def goto(page_key: str, segment_id: int | None = None) -> None:
    """Navigate to another page (by key in st.session_state['_pages']),
    optionally setting the active segment first."""
    if segment_id is not None:
        st.session_state.selected_segment = int(segment_id)
    pages = st.session_state.get("_pages", {})
    if page_key in pages:
        st.switch_page(pages[page_key])
