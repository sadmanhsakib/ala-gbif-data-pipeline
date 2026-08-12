"""
Sign Placements: the "what should I do about it?" page.

Narrative job: turn risk scores into action. The model flags 1,189 segments
where a wildlife warning sign would target the highest-risk locations; this page
maps them, breaks them down by state, and exports the list.

Note: we deliberately do NOT show a modelled "risk after sign": sign
effectiveness is not part of the dataset (see Methodology → Limitations). We
recommend WHERE to act, not a predicted collision reduction.
"""
from __future__ import annotations

import streamlit as st

from components import data, maps, theme, ui

SIGN_HEX = "#E2702A"
CRITICAL_HEX = "#C02B22"


def render() -> None:
    theme.page_hero(
        "Sign Placements",
        "The bottom line: 1,189 segments where a wildlife warning sign targets the "
        "highest-risk locations. Here is exactly where: ready to map, break down, "
        "and export.",
        eyebrow="What to do",
    )

    signs = data.load_signs()
    by_state = signs.groupby("state").size().sort_values(ascending=False)
    top_state = by_state.index[0] if len(by_state) else "—"

    theme.render_metric_band([
        theme.metric_card("Recommended signs", f"{len(signs):,}",
                          "priority placements", SIGN_HEX),
        theme.metric_card("States covered", f"{signs['state'].nunique()}",
                          "national reach", theme.EUCALYPT),
        theme.metric_card("Mean risk at sites", f"{signs['predicted_risk'].mean():.3f}",
                          "across all recommended sites", CRITICAL_HEX),
        theme.metric_card("Busiest state", str(top_state),
                          f"{int(by_state.iloc[0]):,} signs" if len(by_state) else "",
                          theme.BARK),
    ])

    theme.section_header("Signs by state:", "How the recommended placements are "
                         "distributed across the country.", eyebrow="Breakdown")
    breakdown = by_state.rename("signs").reset_index()
    st.dataframe(
        breakdown, width='stretch', hide_index=True,
        column_config={
            "state": st.column_config.TextColumn("State / territory"),
            "signs": st.column_config.NumberColumn("Recommended signs", format="%d"),
        },
    )

    st.download_button(
        "⬇  Download full placement list (CSV)",
        signs.drop(columns=["color"]).to_csv(index=False).encode("utf-8"),
        file_name="recommended_sign_placements.csv",
        mime="text/csv",
    )

    theme.section_header(
        "Recommended sign network:",
        "Every dot is a proposed sign site, colour-graded by segment risk. Filter "
        "by state, hover for detail, or click a site to open its full analysis.",
        eyebrow="Where to act",
    )
    state = st.selectbox(
        "State / territory",
        ["All states"] + sorted(signs["state"].dropna().unique().tolist()),
    )
    df = maps.signs_for_map(state)
    geojson_data = maps.signs_geojson(state)
    event = ui.select_on_map(maps.signs_map(df, geojson_data), key="signs_map")
    clicked = maps.parse_selection(event)
    if clicked:
        ui.goto("detail", clicked)
