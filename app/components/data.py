"""
data.py — Cached data-access layer.

Every disk read lives here behind Streamlit's caching decorators, so the heavy
GeoParquet / GeoJSON loads happen ONCE per session and are reused on every
rerun. On Hugging Face free-tier hardware (CPU-only, limited RAM, cold starts)
this is the single biggest performance lever.

Caching policy:
  • @st.cache_data on every loader/aggregation (results are serialisable data).
  • Loaders read only the columns the UI needs (the parquet has 25 columns;
    we keep ~10) to hold the in-memory GeoDataFrame small.
  • Filtering/aggregation functions take hashable args (tuples, scalars) so
    Streamlit can memoise per distinct filter combination.
"""
from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
import streamlit as st

from components import theme

# ── Paths ─────────────────────────────────────────────────────────────────────
DATA = Path("data")
SEGMENTS_PATH = DATA / "model" / "road_segments_scored.parquet"
SIGNS_PATH = DATA / "model" / "sign_placements.geojson"
BOUNDARIES_PATH = DATA / "processed" / "state_boundaries_simplified.parquet"

# ── Tunables ──────────────────────────────────────────────────────────────────
CRITICAL_THRESHOLD = 0.98          # mirrors the model's original "critical" cut
EXPLORER_MAX_SEGMENTS = 2_000      # hard cap on segments drawn at once (perf)

# Only the columns the front-end uses (of the 25 in the parquet).
SEGMENT_COLUMNS = [
    "road_segment_id", "state", "road_class", "speed_limit",
    "predicted_risk", "sighting_count", "species_richness",
    "traffic_proxy", "mean_ndvi", "geometry",
]

# Network-level facts that are NOT derivable from the segment table (they come
# from the upstream occurrence dataset). Kept explicit + documented, not faked.
TOTAL_WILDLIFE_SIGHTINGS = "413,000+"
SPECIES_COVERED = 11


# ── Raw loaders ───────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Loading road network…")
def load_segments() -> gpd.GeoDataFrame:
    """Scored road segments (geometry kept). Cached once per session."""
    gdf = gpd.read_parquet(SEGMENTS_PATH, columns=SEGMENT_COLUMNS)
    if gdf.crs is None or gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)
    return gdf


@st.cache_data(show_spinner=False)
def load_boundaries() -> gpd.GeoDataFrame:
    """Pre-simplified state polygons (only 8 features — very light)."""
    gdf = gpd.read_parquet(BOUNDARIES_PATH)
    if gdf.crs is None or gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)
    return gdf


@st.cache_data(show_spinner=False)
def load_signs() -> pd.DataFrame:
    """The 1,189 recommended sign placements as a flat DataFrame.

    Pre-computes a per-point RGB colour and formatted risk string from its risk
    tier so the map layer is pure render (no colour or string math on rerun).
    Uses gpd.read_file (C-level GDAL parser) instead of a Python for-loop.
    """
    gdf = gpd.read_file(SIGNS_PATH)
    df = pd.DataFrame({
        "road_segment_id": gdf["road_segment_id"].astype(int),
        "state": gdf["state"].fillna("—"),
        "predicted_risk": gdf["predicted_risk"].astype(float),
        "lon": gdf.geometry.x.astype(float),
        "lat": gdf.geometry.y.astype(float),
    })
    df["color"] = df["predicted_risk"].map(
        lambda r: theme.sequential_risk_rgb(theme.norm_risk(r), alpha=235))
    df["risk_fmt"] = df["predicted_risk"].map(lambda r: f"{r:.3f}")
    return df


# ── Derived tables / aggregates ───────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def segment_table() -> pd.DataFrame:
    """Flat, geometry-free table for sortable explorer + leaderboards.

    Adds a centroid lon/lat so the detail view can zoom to a segment
    without re-touching the (heavy) geometry column. Uses centroid (fast)
    instead of representative_point (expensive GEOS op on ~99K geometries).
    """
    gdf = load_segments()
    centroids = gdf.to_crs(epsg=3857).geometry.centroid
    df = pd.DataFrame({
        "road_segment_id": gdf["road_segment_id"].astype(int),
        "state": gdf["state"],
        "road_class": gdf["road_class"],
        "speed_limit": gdf["speed_limit"],
        "predicted_risk": gdf["predicted_risk"].astype(float),
        "sighting_count": gdf["sighting_count"],
        "species_richness": gdf["species_richness"],
        "traffic_proxy": gdf["traffic_proxy"],
        "lon": centroids.x.astype(float),
        "lat": centroids.y.astype(float),
    })
    df["risk_tier"] = df["predicted_risk"].map(lambda s: theme.risk_tier(s)[0])
    return df


@st.cache_data(show_spinner=False)
def national_summary() -> dict:
    """Hero metrics for the overview band (computed from data where truthful)."""
    df = segment_table()
    return {
        "total_segments": int(len(df)),
        "critical_segments": int((df["predicted_risk"] >= CRITICAL_THRESHOLD).sum()),
        "states": int(df["state"].nunique()),
        "mean_risk": float(df["predicted_risk"].mean()),
        "sightings": TOTAL_WILDLIFE_SIGHTINGS,   # from source occurrence data
        "species": SPECIES_COVERED,              # from source occurrence data
    }


@st.cache_data(show_spinner=False)
def state_stats() -> pd.DataFrame:
    """Per-state aggregates, ranked by critical-segment count."""
    df = segment_table()
    out = (
        df.groupby("state")
        .agg(
            total_segments=("road_segment_id", "size"),
            critical_segments=("predicted_risk", lambda s: int((s >= CRITICAL_THRESHOLD).sum())),
            mean_risk=("predicted_risk", "mean"),
            max_risk=("predicted_risk", "max"),
        )
        .reset_index()
        .sort_values("critical_segments", ascending=False)
    )
    return out


@st.cache_data(show_spinner=False)
def top_hotspots(n: int = 10) -> pd.DataFrame:
    """Highest-risk segments nationally — the overview leaderboard."""
    return segment_table().nlargest(n, "predicted_risk").reset_index(drop=True)


@st.cache_data(show_spinner=False)
def filter_options() -> dict:
    """Distinct values that populate the explorer's filter controls."""
    df = segment_table()
    return {
        "states": sorted(df["state"].dropna().unique().tolist()),
        "road_classes": sorted(df["road_class"].dropna().astype(str).unique().tolist()),
        "risk_min": float(df["predicted_risk"].min()),
        "risk_max": float(df["predicted_risk"].max()),
    }


@st.cache_data(show_spinner="Filtering segments…")
def filter_segments(
    states: tuple[str, ...] = (),
    road_classes: tuple[str, ...] = (),
    min_risk: float = CRITICAL_THRESHOLD,
    limit: int = EXPLORER_MAX_SEGMENTS,
) -> pd.DataFrame:
    """Filtered, geometry-free slice for the explorer table.

    Args are tuples/scalars so each distinct filter set is memoised. Result is
    capped at `limit` (highest-risk first) so we never push tens of thousands
    of rows/segments to the client at once.
    """
    df = segment_table()
    mask = df["predicted_risk"] >= min_risk
    if states:
        mask &= df["state"].isin(states)
    if road_classes:
        mask &= df["road_class"].astype(str).isin(road_classes)
    return df.loc[mask].nlargest(limit, "predicted_risk").reset_index(drop=True)


# ── Single-segment lookups (for the detail page) ──────────────────────────────
@st.cache_data(show_spinner=False)
def get_segment_row(segment_id: int) -> dict | None:
    df = segment_table()
    sel = df[df["road_segment_id"] == int(segment_id)]
    return None if sel.empty else sel.iloc[0].to_dict()


@st.cache_data(show_spinner=False)
def segment_geojson(segment_id: int) -> dict | None:
    """GeoJSON for a single segment's geometry (locator map on the detail page)."""
    gdf = load_segments()
    sel = gdf[gdf["road_segment_id"] == int(segment_id)]
    if sel.empty:
        return None
    cols = ["road_segment_id", "predicted_risk", "state", "road_class", "geometry"]
    return json.loads(sel[cols].to_json())
