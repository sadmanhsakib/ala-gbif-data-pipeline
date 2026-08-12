"""
theme.py: Design tokens + reusable UI fragments for the "Bushland & Hazard"
visual system used across the Wildlife Collision Risk platform.

This module is deliberately light: palette constants, the shared *risk colour
language*, and small HTML builders so every page speaks the same visual
language. It performs NO disk access: data.py imports it purely for colour
mapping, which avoids a circular dependency (theme never imports data).

Design intent (per brief):
  • Earth-tone conservation chrome  → eucalyptus green + bark brown on warm paper
  • A disciplined warning spectrum  → amber → orange → red, reserved ONLY for risk
    so brand colour and risk colour never compete for meaning.
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

# ── Brand / earth palette ─────────────────────────────────────────────────────
PAPER = "#F6F4EE"      # warm field-guide canvas (not stark white)
SURFACE = "#FFFFFF"    # cards / panels
EUCALYPT = "#243B2E"   # primary brand: nav, headers
EUCALYPT_2 = "#33503F"
SAGE = "#5A7A5E"       # secondary green accent
BARK = "#6F5439"       # earth brown
OCHRE = "#C57B3C"      # Australian-soil highlight (used sparingly)
INK = "#221F1A"        # primary text (warm charcoal, not pure black)
INK_2 = "#6B6557"      # secondary text
INK_3 = "#9B9485"      # tertiary text
BORDER = "#E5E0D5"     # warm hairline

# ── Risk colour language ──────────────────────────────────────────────────────
# Continuous ramp stops: (position 0–1, hex, rgb). Reserved for risk only.
RISK_STOPS = [
    (0.00, "#3F7A53", (63, 122, 83)),    # low     : green
    (0.45, "#E8B43A", (232, 180, 58)),   # moderate: amber
    (0.75, "#E2702A", (226, 112, 42)),   # high    : orange
    (1.00, "#C02B22", (192, 43, 34)),    # critical: red
]

# Categorical tiers: (min_score, label, hex, rgb). Thresholds are tunable: the
# 0.98 "critical" cut mirrors the model's original HIGHRISK_THRESHOLD.
TIERS = [
    (0.98, "Critical", "#C02B22", [192, 43, 34]),
    (0.90, "High", "#E2702A", [226, 112, 42]),
    (0.70, "Moderate", "#E8B43A", [232, 180, 58]),
    (0.00, "Low", "#3F7A53", [63, 122, 83]),
]


def risk_tier(score: float) -> tuple[str, str, list[int]]:
    """Map a 0–1 risk score to (tier_label, hex, rgb)."""
    for lo, label, hexc, rgb in TIERS:
        if score >= lo:
            return label, hexc, rgb
    return "Low", "#3F7A53", [63, 122, 83]


def norm_risk(score: float, lo: float = 0.70, hi: float = 1.0) -> float:
    """Normalise a score into [0,1] across the *meaningful* high-risk window.

    Predicted risk clusters near 1.0 on the segments we surface, so spreading
    the colour ramp over 0.70–1.0 (rather than 0–1) makes differences legible.
    """
    if hi <= lo:
        return 1.0
    return max(0.0, min(1.0, (score - lo) / (hi - lo)))


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def sequential_risk_rgb(t: float, alpha: int = 220) -> list[int]:
    """Interpolate the risk ramp at position t∈[0,1] → [r,g,b,alpha] for pydeck."""
    t = max(0.0, min(1.0, t))
    for i in range(len(RISK_STOPS) - 1):
        p0, _, c0 = RISK_STOPS[i]
        p1, _, c1 = RISK_STOPS[i + 1]
        if p0 <= t <= p1:
            f = 0.0 if p1 == p0 else (t - p0) / (p1 - p0)
            return [int(_lerp(c0[j], c1[j], f)) for j in range(3)] + [alpha]
    return list(RISK_STOPS[-1][2]) + [alpha]


def sequential_risk_hex(t: float) -> str:
    """Interpolate the risk ramp at position t∈[0,1] → #RRGGBB hex for folium."""
    rgb = sequential_risk_rgb(t, alpha=255)
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}".upper()


# ── CSS injection (cached so the file is read once per session) ───────────────
@st.cache_data
def _css(path: str = "app/assets/style.css") -> str:
    return f"<style>{Path(path).read_text(encoding='utf-8')}</style>"


def inject_css() -> None:
    """Inject the global stylesheet. Cheap on reruns: the file read is cached."""
    st.html(_css())


# ── Reusable HTML fragments ───────────────────────────────────────────────────
def brand_mark() -> None:
    """Render the sidebar brand lockup."""
    st.sidebar.html(
        """
        <div class="rw-brand">
          <div class="rw-brand-mark">▲</div>
          <div class="rw-brand-text">
            <div class="rw-brand-name">Wildlife Collision Risk</div>
            <div class="rw-brand-sub">Australia · National Road Network</div>
          </div>
        </div>
        """
    )


def page_hero(title: str, subtitle: str, eyebrow: str = "") -> None:
    """Page-level hero: eyebrow + title + the always-present 'why this matters' line."""
    st.html(
        f"""
        <header class="rw-hero">
          <div class="rw-eyebrow">{eyebrow}</div>
          <h1 class="rw-hero-title">{title}</h1>
          <p class="rw-hero-sub">{subtitle}</p>
        </header>
        """
    )


def section_header(title: str, desc: str = "", eyebrow: str = "") -> None:
    st.html(
        f"""
        <div class="rw-section">
          <div class="rw-eyebrow">{eyebrow}</div>
          <h2 class="rw-section-title">{title}</h2>
          <p class="rw-section-desc">{desc}</p>
        </div>
        """
    )


def risk_chip(score: float) -> str:
    """Inline pill (HTML string): colour-coded by tier. Use inside st.html blocks."""
    label, hexc, _ = risk_tier(score)
    return f'<span class="rw-chip" style="--chip:{hexc}">{label} · {score:.3f}</span>'


def metric_card(label: str, value: str, sub: str = "", accent: str = INK) -> str:
    """Return the HTML for one hero metric card (value set in Plex Mono)."""
    return f"""
    <div class="rw-metric" style="--accent:{accent}">
      <div class="rw-metric-label">{label}</div>
      <div class="rw-metric-value">{value}</div>
      <div class="rw-metric-sub">{sub}</div>
    </div>
    """


def render_metric_band(cards: list[str]) -> None:
    """Render a responsive grid of metric cards in a single HTML block.

    NOTE: one st.html call instead of N st.columns/st.metric widgets: fewer
    DOM nodes and no per-card Streamlit overhead, which matters on cold starts.
    """
    st.html('<div class="rw-metric-band">' + "".join(cards) + "</div>")


def footer() -> None:
    st.html(
        """
        <div class="rw-footer">
          <span><strong>Australian Wildlife Roadkill Risk Mapper</strong>
         : a decision-support tool for road safety &amp; wildlife conservation.</span>
          <a class="rw-footer-link"
             href="https://github.com/sadmanhsakib/aus-wildlife-roadkill-risk-mapper"
             target="_blank" rel="noopener">View on GitHub →</a>
        </div>
        """
    )
