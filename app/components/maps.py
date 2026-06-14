"""
maps.py — pydeck map builders (replaces the folium `map_view.py`).

Why pydeck instead of folium here:
  • Folium renders every feature as DOM; the old code also `deepcopy`-ed a
    cached map on every rerun — expensive on free-tier CPU/RAM.
  • pydeck/deck.gl renders client-side via WebGL, so thousands of segments and
    the 1,189 sign points draw smoothly without server-side work each rerun.

Performance pattern:
  • Heavy GeoJSON view-models are built in @st.cache_data functions with
    PRE-COMPUTED colours, so reruns just re-send cached data — no geometry or
    colour maths repeat.
  • The national/default view is PRE-AGGREGATED (8 state polygons + sign dots),
    never the full 99,739-segment network. Detail appears only when the user
    filters (explorer) or drills into one segment (detail page).
  • Basemap = Carto Positron style JSON → no Mapbox token needed, tiles fetched
    client-side.
"""
from __future__ import annotations

import json

import pandas as pd
import pydeck as pdk
import streamlit as st

from components import data, theme

MAP_STYLE = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"

# Tooltip chrome — matches the eucalyptus/paper system.
TOOLTIP_STYLE = {
    "backgroundColor": theme.EUCALYPT,
    "color": "#F6F4EE",
    "fontFamily": "'IBM Plex Mono', ui-monospace, monospace",
    "fontSize": "12px",
    "borderRadius": "8px",
    "padding": "9px 12px",
    "boxShadow": "0 6px 20px rgba(0,0,0,.28)",
}

_AUS_VIEW = dict(latitude=-25.6, longitude=134.0, zoom=3.3, pitch=0, bearing=0)


# ── Cached view-models ────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def state_choropleth_geojson(metric: str = "critical_segments") -> dict:
    """State polygons coloured by a risk metric (default: critical-segment count).

    Only 8 features — trivially light. Colour is precomputed into each feature's
    `fill_color` property so the map layer is pure render.
    """
    gdf = data.load_boundaries().copy()
    stats = data.state_stats().set_index("state")
    for col in ["total_segments", "critical_segments", "mean_risk", "max_risk"]:
        gdf[col] = gdf["state"].map(stats[col]) if col in stats.columns else 0

    vals = pd.to_numeric(gdf[metric], errors="coerce").fillna(0.0)
    vmax = float(vals.max()) or 1.0
    gdf["fill_color"] = [theme.sequential_risk_rgb(v / vmax, alpha=145) for v in vals]
    gdf["mean_risk_fmt"] = pd.to_numeric(gdf["mean_risk"], errors="coerce").map(
        lambda v: f"{v:.3f}" if pd.notna(v) else "—")
    gdf["max_risk_fmt"] = pd.to_numeric(gdf["max_risk"], errors="coerce").map(
        lambda v: f"{v:.3f}" if pd.notna(v) else "—")
    return json.loads(gdf.to_json())


@st.cache_data(show_spinner="Preparing risk segments…")
def segments_geojson(
    states: tuple[str, ...] = (),
    road_classes: tuple[str, ...] = (),
    min_risk: float = data.CRITICAL_THRESHOLD,
    limit: int = data.EXPLORER_MAX_SEGMENTS,
) -> dict:
    """Filtered high-risk segments as coloured GeoJSON lines (capped at `limit`)."""
    gdf = data.load_segments()
    mask = gdf["predicted_risk"] >= min_risk
    if states:
        mask &= gdf["state"].isin(states)
    if road_classes:
        mask &= gdf["road_class"].astype(str).isin(road_classes)
    sub = (
        gdf.loc[mask]
        .nlargest(limit, "predicted_risk")[
            ["road_segment_id", "predicted_risk", "state", "road_class", "geometry"]
        ]
        .copy()
    )
    sub["color"] = sub["predicted_risk"].map(
        lambda r: theme.sequential_risk_rgb(theme.norm_risk(r), alpha=235))
    sub["risk_fmt"] = sub["predicted_risk"].map(lambda r: f"{r:.4f}")
    return json.loads(sub.to_json())


@st.cache_data(show_spinner=False)
def signs_for_map(state: str | None = None) -> pd.DataFrame:
    """Sign placements with a formatted risk string, optionally state-filtered."""
    df = data.load_signs().copy()
    if state and state != "All states":
        df = df[df["state"] == state]
    df["risk_fmt"] = df["predicted_risk"].map(lambda r: f"{r:.3f}")
    return df


# ── Deck builders ─────────────────────────────────────────────────────────────
def _signs_layer(df: pd.DataFrame, pickable: bool = False) -> pdk.Layer:
    return pdk.Layer(
        "ScatterplotLayer",
        id="signs",
        data=df,
        get_position=["lon", "lat"],
        get_fill_color="color",
        get_radius=2200,
        radius_min_pixels=2.5,
        radius_max_pixels=8,
        stroked=True,
        get_line_color=[255, 255, 255, 210],
        line_width_min_pixels=0.5,
        pickable=pickable,
        auto_highlight=pickable,
    )


def national_overview_deck() -> pdk.Deck:
    """State risk choropleth + sign-placement context dots. The 'whole network'."""
    states = state_choropleth_geojson()
    signs = signs_for_map()
    choropleth = pdk.Layer(
        "GeoJsonLayer",
        id="states",
        data=states,
        stroked=True,
        filled=True,
        get_fill_color="properties.fill_color",
        get_line_color=[36, 59, 46, 170],
        line_width_min_pixels=1,
        pickable=True,
        auto_highlight=True,
        highlight_color=[90, 122, 94, 90],
    )
    tooltip = {
        "html": (
            "<b>{state}</b>"
            "<br/>Critical segments: <b>{critical_segments}</b>"
            "<br/>Total segments: {total_segments}"
            "<br/>Mean risk {mean_risk_fmt} · Peak {max_risk_fmt}"
        ),
        "style": TOOLTIP_STYLE,
    }
    return pdk.Deck(
        layers=[choropleth, _signs_layer(signs, pickable=False)],
        initial_view_state=pdk.ViewState(**_AUS_VIEW),
        map_style=MAP_STYLE,
        tooltip=tooltip,
        height=520,
    )


def explorer_deck(geojson: dict, show_signs: bool = False) -> pdk.Deck:
    """Filtered risk segments (lines). Clicking a segment can drive selection."""
    segs = pdk.Layer(
        "GeoJsonLayer",
        id="segments",
        data=geojson,
        stroked=True,
        filled=False,
        get_line_color="properties.color",
        line_width_min_pixels=2.2,
        line_width_max_pixels=6,
        pickable=True,
        auto_highlight=True,
        highlight_color=[36, 59, 46, 160],
    )
    layers = [segs]
    if show_signs:
        layers.append(_signs_layer(signs_for_map(), pickable=False))
    tooltip = {
        "html": (
            "<b>Segment {road_segment_id}</b>"
            "<br/>Risk <b>{risk_fmt}</b>"
            "<br/>{state} · {road_class}"
        ),
        "style": TOOLTIP_STYLE,
    }
    return pdk.Deck(
        layers=layers,
        initial_view_state=pdk.ViewState(**_AUS_VIEW),
        map_style=MAP_STYLE,
        tooltip=tooltip,
        height=460,
    )


def signs_deck(df: pd.DataFrame) -> pdk.Deck:
    """All (or state-filtered) recommended sign placements — the 'where to act' map."""
    tooltip = {
        "html": (
            "<b>Recommended sign</b>"
            "<br/>Segment {road_segment_id}"
            "<br/>{state} · risk {risk_fmt}"
        ),
        "style": TOOLTIP_STYLE,
    }
    return pdk.Deck(
        layers=[_signs_layer(df, pickable=True)],
        initial_view_state=pdk.ViewState(**_AUS_VIEW),
        map_style=MAP_STYLE,
        tooltip=tooltip,
        height=540,
    )


def segment_locator_deck(seg_geojson: dict, lat: float, lon: float,
                         sign_row: dict | None = None) -> pdk.Deck:
    """Zoomed-in locator for a single segment (detail page)."""
    layers = [
        pdk.Layer(
            "GeoJsonLayer",
            id="segment",
            data=seg_geojson,
            stroked=True,
            filled=False,
            get_line_color=[192, 43, 34, 240],
            line_width_min_pixels=4,
            pickable=False,
        )
    ]
    if sign_row is not None:
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                id="sign",
                data=[sign_row],
                get_position=["lon", "lat"],
                get_fill_color=[232, 180, 58, 255],
                get_radius=60,
                radius_min_pixels=6,
                stroked=True,
                get_line_color=[36, 59, 46, 255],
                line_width_min_pixels=1.5,
            )
        )
    return pdk.Deck(
        layers=layers,
        initial_view_state=pdk.ViewState(latitude=lat, longitude=lon, zoom=12.5, pitch=0),
        map_style=MAP_STYLE,
        height=380,
    )


# ── Selection parsing (map click → segment id), version-tolerant ──────────────
def parse_selection(event) -> int | None:
    """Extract a road_segment_id from an st.pydeck_chart(on_select=...) event.

    Handles both the object-style return (event.selection.objects) and a plain
    dict, and both flat (scatter) and nested (GeoJSON feature) object shapes.
    Returns None if nothing actionable was clicked.
    """
    if not event:
        return None
    selection = getattr(event, "selection", None)
    if selection is None and isinstance(event, dict):
        selection = event.get("selection")
    if not selection:
        return None
    objects = selection.get("objects") if isinstance(selection, dict) else getattr(selection, "objects", None)
    if not objects:
        return None
    for _layer_id, items in objects.items():
        if not items:
            continue
        obj = items[0]
        if isinstance(obj, dict):
            if "road_segment_id" in obj:
                return int(obj["road_segment_id"])
            props = obj.get("properties") or {}
            if "road_segment_id" in props:
                return int(props["road_segment_id"])
    return None
