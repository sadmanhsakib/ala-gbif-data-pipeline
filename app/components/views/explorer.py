"""
Risk Explorer — the decision-support workhorse.

Narrative job: "Find the segments that need action." Filter by state, road class,
and risk; see them on the map; rank them in a sortable table; send any one to
detailed analysis or export the list.

Performance: the map and table are both driven by cached, capped queries
(`data.filter_segments` / `maps.segments_geojson`, max 2,000 segments) so we
never push the full network to the browser.
"""
from __future__ import annotations

import streamlit as st

from components import data, maps, theme, ui


def render() -> None:
    theme.page_hero(
        "Risk Explorer",
        "Filter the national network down to the segments that matter, rank them "
        "by risk, and send any one straight to detailed analysis.",
        eyebrow="Find where to act",
    )

    opts = data.filter_options()
    with st.container(border=True):
        c1, c2, c3 = st.columns([1.2, 1.2, 1.6])
        states = c1.multiselect("State / territory", opts["states"],
                                placeholder="All states")
        classes = c2.multiselect("Road class", opts["road_classes"],
                                 placeholder="All road types")
        min_risk = c3.slider("Minimum predicted risk", 0.50, 1.0, 0.90, 0.005)
        show_signs = st.checkbox("Overlay recommended sign sites on the map",
                                 value=False)

    df = data.filter_segments(tuple(states), tuple(classes), min_risk)

    if df.empty:
        st.warning("No segments match these filters. Try lowering the minimum risk "
                   "or clearing a filter.")
        return

    st.caption(
        f"Showing the **{len(df):,}** highest-risk segments at or above risk "
        f"**{min_risk:.3f}** (capped at {data.EXPLORER_MAX_SEGMENTS:,} for "
        f"performance)."
    )

    theme.section_header("Risk map:", "Lines are coloured by risk — deeper red is "
                         "higher. Hover for detail; click a segment to inspect it.",
                         eyebrow="Filtered view")
    geojson = maps.segments_geojson(tuple(states), tuple(classes), min_risk)
    event = ui.select_on_map(maps.explorer_map(geojson, show_signs), key="explorer_map")
    clicked = maps.parse_selection(event)
    if clicked:
        ui.goto("detail", clicked)

    theme.section_header("Ranked segments:", "Sort by any column. Select a row to "
                         "open its full analysis, or export the list below.",
                         eyebrow="Priority table")
    table = df[["road_segment_id", "state", "road_class", "speed_limit",
                "predicted_risk", "sighting_count", "species_richness", "risk_tier"]]
    selected = ui.select_row(
        table, key="explorer_table", height=420,
        column_config={
            "road_segment_id": st.column_config.NumberColumn("Segment", format="%d"),
            "state": st.column_config.TextColumn("State"),
            "road_class": st.column_config.TextColumn("Road class"),
            "speed_limit": st.column_config.NumberColumn("Speed", format="%d km/h"),
            "predicted_risk": st.column_config.ProgressColumn(
                "Predicted risk", format="%.4f", min_value=min_risk, max_value=1.0),
            "sighting_count": st.column_config.NumberColumn("Sightings", format="%d"),
            "species_richness": st.column_config.NumberColumn("Species", format="%d"),
            "risk_tier": st.column_config.TextColumn("Tier"),
        },
    )
    if selected is not None:
        ui.goto("detail", int(selected["road_segment_id"]))

    st.download_button(
        "⬇  Download this list (CSV)",
        df.to_csv(index=False).encode("utf-8"),
        file_name="high_risk_segments.csv",
        mime="text/csv",
    )
