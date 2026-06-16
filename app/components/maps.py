"""
maps.py — folium map builders (replaces the pydeck implementation).

Performance pattern:
  • Heavy GeoJSON view-models are built in @st.cache_data functions with
    PRE-COMPUTED colours, so reruns just re-send cached data.
  • The national/default view is PRE-AGGREGATED (8 state polygons + sign dots),
    never the full 99,739-segment network.
  • Basemap = Carto Positron style -> light basemap.
"""
from __future__ import annotations

import json
import re

import folium
import pandas as pd
import streamlit as st

from components import data, theme

MAP_STYLE = "CartoDB positron"

# ── Cached view-models ────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def state_choropleth_geojson(metric: str = "critical_segments") -> dict:
    """State polygons coloured by a risk metric (default: critical-segment count)."""
    gdf = data.load_boundaries()
    stats = data.state_stats().set_index("state")
    cols_to_add = {}
    for col in ["total_segments", "critical_segments", "mean_risk", "max_risk"]:
        cols_to_add[col] = gdf["state"].map(stats[col]) if col in stats.columns else 0
    gdf = gdf.assign(**cols_to_add)

    vals = pd.to_numeric(gdf[metric], errors="coerce").fillna(0.0)
    vmax = float(vals.max()) or 1.0
    gdf = gdf.assign(
        fill_color=[theme.sequential_risk_hex(v / vmax) for v in vals],
        mean_risk_fmt=pd.to_numeric(gdf["mean_risk"], errors="coerce").map(
            lambda v: f"{v:.3f}" if pd.notna(v) else "—"),
        max_risk_fmt=pd.to_numeric(gdf["max_risk"], errors="coerce").map(
            lambda v: f"{v:.3f}" if pd.notna(v) else "—"),
    )
    return json.loads(gdf.to_json())


@st.cache_data(show_spinner="Preparing risk segments…")
def segments_geojson(
    states: tuple[str, ...] = (),
    road_classes: tuple[str, ...] = (),
    min_risk: float = data.CRITICAL_THRESHOLD,
    limit: int = data.EXPLORER_MAX_SEGMENTS,
) -> dict:
    """Filtered high-risk segments as coloured GeoJSON lines (capped at `limit`)."""
    filtered_df = data.filter_segments(states, road_classes, min_risk, limit)
    if filtered_df.empty:
        return {"type": "FeatureCollection", "features": []}
    ids = set(filtered_df["road_segment_id"].tolist())
    gdf = data.load_segments()
    sub = gdf[gdf["road_segment_id"].isin(ids)][
        ["road_segment_id", "predicted_risk", "state", "road_class", "geometry"]
    ].copy()
    sub["color"] = sub["predicted_risk"].map(
        lambda r: theme.sequential_risk_hex(theme.norm_risk(r)))
    sub["risk_fmt"] = sub["predicted_risk"].map(lambda r: f"{r:.4f}")
    return json.loads(sub.to_json())


@st.cache_data(show_spinner=False)
def signs_for_map(state: str | None = None) -> pd.DataFrame:
    """Sign placements optionally state-filtered. risk_fmt is precomputed."""
    df = data.load_signs()
    if state and state != "All states":
        df = df[df["state"] == state]
    return df


# ── Map builders ──────────────────────────────────────────────────────────────
def _base_map(location=(-25.6, 134.0), zoom_start=4) -> folium.Map:
    m = folium.Map(
        location=location,
        zoom_start=zoom_start,
        tiles=MAP_STYLE,
        control_scale=True,
    )
    return m


def _add_signs(m: folium.Map, df: pd.DataFrame, interactive: bool = False) -> None:
    for idx, row in df.iterrows():
        tooltip = None
        if interactive:
            tooltip = folium.Tooltip(
                f"<b>Recommended sign</b><br/>Segment {row['road_segment_id']}<br/>{row['state']} &middot; risk {row['risk_fmt']}"
            )
        
        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=4,
            color="#FFFFFF",
            weight=1,
            fill=True,
            fill_color=theme.sequential_risk_hex(theme.norm_risk(row["predicted_risk"])),
            fill_opacity=0.8,
            tooltip=tooltip,
        ).add_to(m)


def national_overview_map() -> folium.Map:
    """State risk choropleth + sign-placement context dots. The 'whole network'."""
    m = _base_map()
    states_geo = state_choropleth_geojson()
    
    style_function = lambda feature: {
        'fillColor': feature['properties']['fill_color'],
        'color': '#243B2E',
        'weight': 1,
        'fillOpacity': 0.6,
    }
    
    highlight_function = lambda feature: {
        'fillColor': feature['properties']['fill_color'],
        'color': '#243B2E',
        'weight': 2,
        'fillOpacity': 0.8,
    }
    
    tooltip = folium.GeoJsonTooltip(
        fields=['state', 'critical_segments', 'total_segments', 'mean_risk_fmt', 'max_risk_fmt'],
        aliases=['State:', 'Critical segments:', 'Total segments:', 'Mean risk:', 'Peak risk:'],
        style="background-color: #243B2E; color: #F6F4EE; font-family: monospace; border-radius: 8px; padding: 9px 12px;"
    )
    
    folium.GeoJson(
        states_geo,
        style_function=style_function,
        highlight_function=highlight_function,
        tooltip=tooltip,
        name="States"
    ).add_to(m)
    
    _add_signs(m, signs_for_map(), interactive=False)
    return m


def explorer_map(geojson: dict, show_signs: bool = False) -> folium.Map:
    """Filtered risk segments (lines). Clicking a segment can drive selection."""
    m = _base_map()
    
    if geojson and geojson.get("features"):
        style_function = lambda feature: {
            'color': feature['properties']['color'],
            'weight': 3,
            'opacity': 0.8
        }
        
        highlight_function = lambda feature: {
            'color': feature['properties']['color'],
            'weight': 5,
            'opacity': 1.0
        }
        
        tooltip = folium.GeoJsonTooltip(
            fields=['road_segment_id', 'risk_fmt', 'state', 'road_class'],
            aliases=['Segment:', 'Risk:', 'State:', 'Class:'],
            style="background-color: #243B2E; color: #F6F4EE; font-family: monospace; border-radius: 8px; padding: 9px 12px;"
        )
        
        segments_layer = folium.GeoJson(
            geojson,
            style_function=style_function,
            highlight_function=highlight_function,
            tooltip=tooltip,
            name="Segments"
        )
        segments_layer.add_to(m)
        
        # Fit bounds
        m.fit_bounds(segments_layer.get_bounds())

    if show_signs:
        _add_signs(m, signs_for_map(), interactive=False)
        
    return m


def signs_map(df: pd.DataFrame) -> folium.Map:
    """All (or state-filtered) recommended sign placements — the 'where to act' map."""
    m = _base_map()
    
    _add_signs(m, df, interactive=True)
    
    if not df.empty:
        sw = [df['lat'].min(), df['lon'].min()]
        ne = [df['lat'].max(), df['lon'].max()]
        m.fit_bounds([sw, ne])
        
    return m


def segment_locator_map(seg_geojson: dict, lat: float, lon: float,
                         sign_row: dict | None = None) -> folium.Map:
    """Zoomed-in locator for a single segment (detail page)."""
    m = _base_map(location=(lat, lon), zoom_start=14)
    
    if seg_geojson and seg_geojson.get("features"):
        folium.GeoJson(
            seg_geojson,
            style_function=lambda x: {'color': '#C02B22', 'weight': 5, 'opacity': 0.9},
            name="Segment"
        ).add_to(m)
        
    if sign_row is not None:
        folium.CircleMarker(
            location=[sign_row["lat"], sign_row["lon"]],
            radius=6,
            color="#243B2E",
            weight=1.5,
            fill=True,
            fill_color="#E8B43A",
            fill_opacity=1.0,
        ).add_to(m)
        
    return m


# ── Cached HTML Builders for Performance ──────────────────────────────────────
@st.cache_data(show_spinner=False)
def get_national_overview_html() -> str:
    """Pre-render and cache the HTML string for the overview map. Zero CPU on reruns."""
    return national_overview_map()._repr_html_()

@st.cache_data(show_spinner=False)
def get_segment_locator_html(segment_id: int) -> str | None:
    """Pre-render and cache the HTML string for a segment locator map."""
    row = data.get_segment_row(segment_id)
    if not row:
        return None
    lat, lon = float(row["lat"]), float(row["lon"])
    
    signs = signs_for_map()
    has_sign = segment_id in set(signs["road_segment_id"])
    sign_row = None
    if has_sign:
        r = signs[signs["road_segment_id"] == segment_id].iloc[0]
        sign_row = {"lon": float(r["lon"]), "lat": float(r["lat"])}
        
    seg_geojson = data.segment_geojson(segment_id)
    return segment_locator_map(seg_geojson, lat, lon, sign_row)._repr_html_()


# ── Selection parsing (map click → segment id), version-tolerant ──────────────
def parse_selection(event) -> int | None:
    """Extract a road_segment_id from an st_folium return dict."""
    if not event:
        return None
        
    # Check if a GeoJson feature was clicked
    drawing = event.get("last_active_drawing")
    if drawing and isinstance(drawing, dict):
        props = drawing.get("properties")
        if props and "road_segment_id" in props:
            return int(props["road_segment_id"])
            
    # Check if a CircleMarker was clicked by parsing its tooltip
    tooltip = event.get("last_object_clicked_tooltip")
    if tooltip and "Segment" in tooltip:
        m = re.search(r"Segment\s+(\d+)", tooltip)
        if m:
            return int(m.group(1))

    return None
