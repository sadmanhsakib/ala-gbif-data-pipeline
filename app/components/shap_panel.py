"""
shap_panel.py — "Why is this segment risky?" feature-attribution panel.

Unchanged engine, restyled output:
  • Precomputed SHAP values are loaded once (@st.cache_data) and the Matplotlib
    waterfall is rendered on the non-interactive 'Agg' backend, cached PER
    SEGMENT — so re-selecting a segment is instant and never recomputes.
  • The plot is recoloured into the app's risk language (orange = pushes risk
    up, green = pulls it down) and the surrounding card uses the new palette.
"""
from __future__ import annotations

import io

import joblib
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import shap
import streamlit as st

from components import data, theme

matplotlib.use("Agg")  # headless, faster on CPU-only hardware

_UP = "#E2702A"    # contribution increasing risk  (high/orange)
_DOWN = "#3F7A53"  # contribution decreasing risk  (low/green)


@st.cache_data(show_spinner=False)
def load_feature_columns(path: str = "data/model/feature_cols.pkl") -> list[str]:
    return list(joblib.load(path))


@st.cache_data(show_spinner=False)
def load_shap_values(path: str = "data/model/shap_values.parquet") -> pd.DataFrame:
    df = pd.read_parquet(path)
    return df.set_index("road_segment_id", drop=False)


@st.cache_data(show_spinner=False)
def load_feature_values(path: str = "data/model/road_segments_scored.parquet") -> pd.DataFrame:
    feature_cols = load_feature_columns()
    df = pd.read_parquet(path, columns=["road_segment_id"] + feature_cols)
    return df.set_index("road_segment_id", drop=False)


@st.cache_data(show_spinner="Explaining this segment…")
def generate_waterfall_plot(segment_id: int) -> bytes:
    """Render a SHAP waterfall for one segment as PNG bytes (cached per id)."""
    shap_df = load_shap_values()
    feature_df = load_feature_values()

    exclude = ["road_segment_id", "expected_value"]
    feature_cols = [c for c in shap_df.columns if c not in exclude]

    explanation = shap.Explanation(
        values=shap_df.loc[segment_id, feature_cols].values,
        base_values=float(shap_df.loc[segment_id, "expected_value"]),
        data=feature_df.loc[segment_id, feature_cols].values,
        feature_names=feature_cols,
    )

    fig, ax = plt.subplots(figsize=(8, 5))
    shap.plots.waterfall(explanation, show=False)
    fig.patch.set_facecolor("white")

    # Recolour SHAP's default crimson/blue bars into the risk ramp. Wrapped in a
    # try so a SHAP internals change can never break the panel.
    try:
        for patch in plt.gca().patches:
            r, g, b, _ = patch.get_facecolor()
            patch.set_facecolor(_UP if r >= b else _DOWN)
    except Exception:
        pass

    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=100, bbox_inches="tight")
    plt.close(fig)
    return buffer.getvalue()


def _empty_state() -> None:
    st.html(
        f"""
        <div style="text-align:center; padding:2.4rem 1rem; color:{theme.INK_3};">
          <div style="font-size:2.2rem; line-height:1; margin-bottom:.6rem;">🔍</div>
          <p style="font-weight:600; color:{theme.INK_2}; margin:0;">No segment selected</p>
          <p style="font-size:.85rem; margin:.4rem 0 0; line-height:1.5;">
            Pick a segment in the Risk Explorer (or click one on the map) to see
            exactly which factors drove its risk score.
          </p>
        </div>
        """
    )


def render_shap_panel(segment_id: int | None = None) -> None:
    """Render the attribution panel for `segment_id`, or an empty state."""
    if segment_id is None:
        _empty_state()
        return

    segment_id = int(segment_id)
    shap_df = load_shap_values()
    if segment_id not in shap_df.index:
        st.warning(f"No SHAP data available for segment {segment_id}.")
        return

    # Prefer the model's predicted_risk for the headline number (consistent with
    # the rest of the app); fall back to the SHAP-row sum if the row is missing.
    row = data.get_segment_row(segment_id)
    if row is not None:
        risk = float(row["predicted_risk"])
        context = f"{row.get('state', '—')} · {row.get('road_class', '—')}"
    else:
        risk = float(shap_df.loc[segment_id].drop(labels=["road_segment_id"]).sum())
        context = "—"
    _, hexc, _ = theme.risk_tier(risk)

    st.html(
        f"""
        <div style="background:{theme.PAPER}; border:1px solid {theme.BORDER};
                    border-left:4px solid {hexc}; border-radius:12px;
                    padding:1rem 1.1rem; margin-bottom:1rem;">
          <div style="font-family:'IBM Plex Mono',monospace; font-size:.68rem;
                      letter-spacing:.12em; text-transform:uppercase; color:{theme.BARK};">
            Segment Analysis
          </div>
          <div style="font-family:'IBM Plex Mono',monospace; font-size:1.5rem;
                      font-weight:600; color:{theme.INK}; margin:.15rem 0;">#{segment_id}</div>
          <div style="font-size:.85rem; color:{theme.INK_2};">{context}</div>
          <div style="margin-top:.55rem;">{theme.risk_chip(risk)}</div>
        </div>
        """
    )
    st.caption("Bars in red push this segment's risk **up**; blue bars pull it **down**.")
    st.image(generate_waterfall_plot(segment_id), width='stretch')
