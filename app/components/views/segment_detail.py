"""
Segment Detail — the "why is this spot dangerous?" deep dive.

Narrative job: for a single segment, show its risk, the factors behind it
(SHAP), where it is, and whether a warning sign is recommended.
"""
from __future__ import annotations

import streamlit as st

from components import data, maps, theme, ui


def _picker() -> None:
    st.info("No segment selected yet. Pick one in the **Risk Explorer**, click a "
            "site on the **Sign Placements** map, or enter an ID below.")
    c1, c2 = st.columns([1, 3])
    sid_in = c1.number_input("Segment ID", min_value=0, step=1, value=0)
    if c1.button("Analyse segment", type="primary") and sid_in:
        ui.goto("detail", int(sid_in))
        st.rerun()


def render() -> None:
    theme.page_hero(
        "Segment Detail",
        "Everything the model knows about one road segment — its risk, the "
        "factors driving it, and whether a warning sign is recommended.",
        eyebrow="Why this segment",
    )

    sid = st.session_state.get("selected_segment")
    if not sid:
        _picker()
        return

    row = data.get_segment_row(int(sid))
    if row is None:
        st.warning(f"Segment {sid} was not found in the dataset.")
        if st.button("← Back to Risk Explorer"):
            ui.goto("explorer")
        return

    risk = float(row["predicted_risk"])
    tier, hexc, _ = theme.risk_tier(risk)

    theme.render_metric_band([
        theme.metric_card("Predicted risk", f"{risk:.4f}", f"{tier} risk", hexc),
        theme.metric_card("Wildlife sightings", f"{int(row['sighting_count']):,}",
                          "recorded on this segment", theme.BARK),
        theme.metric_card("Species richness", f"{int(row['species_richness'])}",
                          "distinct species", theme.SAGE),
        theme.metric_card("Speed limit", f"{int(row['speed_limit'])}", "km/h", theme.EUCALYPT),
        theme.metric_card("Road class", f"{row['road_class']}", "segment type", theme.SAGE),
    ])

    signs = maps.signs_for_map()
    has_sign = int(sid) in set(signs["road_segment_id"])
    if has_sign:
        st.success("✓  A wildlife warning sign is recommended here — this segment "
                   "is among the 1,189 priority placements.")
    else:
        st.info("No warning sign is currently recommended for this segment.")

    left, right = st.columns([1, 1], gap="large")
    with left:
        theme.section_header("Location:", "Zoom and pan to see the segment in context.",
                             eyebrow="Where")
        geojson = data.segment_geojson(int(sid))
        sign_row = None
        if has_sign:
            r = signs[signs["road_segment_id"] == int(sid)].iloc[0]
            sign_row = {"lon": float(r["lon"]), "lat": float(r["lat"])}
        if geojson:
            st.pydeck_chart(
                maps.segment_locator_deck(geojson, float(row["lat"]),
                                          float(row["lon"]), sign_row),
                width='stretch',
            )
        else:
            st.caption("No geometry available for this segment.")

    with right:
        theme.section_header("Risk attribution", "Which factors pushed this "
                             "segment's score up or down.", eyebrow="Why")
        from components import shap_panel
        shap_panel.render_shap_panel(int(sid))

    st.write("")
    cols = st.columns([1, 1, 4])
    if cols[0].button("← Back to Explorer"):
        ui.goto("explorer")
    if cols[1].button("View all sign sites"):
        ui.goto("signs")
