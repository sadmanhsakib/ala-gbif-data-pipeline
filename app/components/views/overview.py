"""
National Overview: the landing page.

Narrative job: "Here is the whole road network, and here is where the danger
concentrates." Pre-aggregated state choropleth (8 polygons) + a priority queue
of the top hotspots. Light by design: nothing here renders the full network.
"""
from __future__ import annotations

import streamlit as st

from components import data, maps, theme, ui

CRITICAL_HEX = "#C02B22"


def render() -> None:
    s = data.national_summary()

    theme.page_hero(
        "National Overview",
        "We score every road segment in Australia for wildlife–vehicle collision "
        "risk. This is the whole network at a glance: and where the danger "
        "concentrates, so you know where to look first.",
        eyebrow="The whole picture",
    )

    theme.render_metric_band([
        theme.metric_card("Road segments analysed", f"{s['total_segments']:,}",
                          "across the national network", theme.SAGE),
        theme.metric_card("Wildlife sightings", s["sightings"],
                          "verified occurrence records", theme.BARK),
        theme.metric_card("Critical segments", f"{s['critical_segments']:,}",
                          "risk ≥ 0.98: act first", CRITICAL_HEX),
        theme.metric_card("Species covered", str(s["species"]),
                          "native Australian species", theme.SAGE),
        theme.metric_card("States & territories", str(s["states"]),
                          "national coverage", theme.EUCALYPT),
    ])

    theme.section_header(
        "Top 10 hotspots:",
        "The single highest-risk segments in the country: your first places to "
        "act. Select any row to open its full risk analysis.",
        eyebrow="Priority queue",
    )
    top = data.top_hotspots(10)[
        ["road_segment_id", "state", "road_class", "predicted_risk",
         "sighting_count", "species_richness"]
    ]
    selected = ui.select_row(
        top, key="overview_hotspots", height=390,
        column_config={
            "road_segment_id": st.column_config.NumberColumn("Segment", format="%d"),
            "state": st.column_config.TextColumn("State"),
            "road_class": st.column_config.TextColumn("Road class"),
            "predicted_risk": st.column_config.ProgressColumn(
                "Predicted risk", format="%.4f", min_value=0.9, max_value=1.0),
            "sighting_count": st.column_config.NumberColumn("Sightings", format="%d"),
            "species_richness": st.column_config.NumberColumn("Species", format="%d"),
        },
    )
    if selected is not None:
        ui.goto("detail", int(selected["road_segment_id"]))
    
    theme.section_header(
        "Where risk concentrates?",
        "Each state is shaded by its number of critical segments; amber dots mark "
        "recommended sign sites. Hover any state for its risk profile.",
        eyebrow="National map",
    )
    with st.spinner("Rendering national map…"):
        html = maps.get_national_overview_html()
        ui.render_static_map(html, height=520)
    
    st.write("")
    if st.button("Explore all high-risk segments →", type="primary"):
        ui.goto("explorer")
