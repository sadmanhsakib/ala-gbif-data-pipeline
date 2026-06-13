"""
Methodology & Data — the trust page.

Narrative job: explain how scores are produced, what powers them, and the limits
to keep in mind. Honest caveats are a feature, not an afterthought.
"""
from __future__ import annotations

import streamlit as st

from components import data, theme

TIER_ROWS = [
    ("Critical", "#C02B22", "risk ≥ 0.98 — intervene first"),
    ("High", "#E2702A", "0.90 – 0.98 — strong candidates"),
    ("Moderate", "#E8B43A", "0.70 – 0.90 — monitor"),
    ("Low", "#3F7A53", "below 0.70 — lower priority"),
]


def render() -> None:
    s = data.national_summary()

    theme.page_hero(
        "Methodology & Data",
        "How the risk scores are produced, what powers them, and the limits you "
        "should keep in mind when acting on them.",
        eyebrow="Why you can trust this",
    )

    theme.section_header("The model", eyebrow="Approach")
    st.markdown(
        "Every road segment is scored by a **gradient-boosted tree model "
        "(XGBoost)** that learns the relationship between a segment's ecological "
        "and road-network characteristics and observed wildlife–vehicle collision "
        "risk. Each prediction is paired with **SHAP** (SHapley Additive "
        "exPlanations) values, so we can show — segment by segment — exactly which "
        "factors pushed a score up or down. Scores and explanations are "
        "**pre-computed** and served from disk, which is what keeps the app "
        "responsive on free-tier hardware."
    )

    theme.section_header("What goes into a score", "The model blends three families "
                         "of signal.", eyebrow="Features")
    c1, c2, c3 = st.columns(3)
    c1.markdown(
        "**🦘 Wildlife & ecology**\n\n"
        "- Sighting count\n- Species richness\n- Ecological score\n"
        "- Vegetation (mean NDVI)\n- Body-mass, nocturnal & peak-season weights"
    )
    c2.markdown(
        "**🛣 Road & traffic**\n\n"
        "- Road class\n- Speed limit\n- Traffic proxy\n"
        "- Road-exposure score\n- Distance to road"
    )
    c3.markdown(
        "**🧭 Spatial context**\n\n"
        "- Spatial lag of risk\n- Lagged sightings & richness\n"
        "- Lagged NDVI & traffic\n- Proximity"
    )

    theme.section_header("How to read the scores", "Risk is reported on a 0–1 "
                         "scale and bucketed into four tiers.", eyebrow="Risk tiers")
    chips = "".join(
        f'<span class="rw-chip" style="--chip:{hexc}; margin:0 .4rem .5rem 0;">'
        f'{label}</span><span style="color:#6B6557; font-size:.85rem; '
        f'margin-right:1.2rem;">{desc}</span>'
        for label, hexc, desc in TIER_ROWS
    )
    st.html(f'<div style="line-height:2.2;">{chips}</div>')

    theme.section_header("Data at a glance", eyebrow="Coverage")
    theme.render_metric_band([
        theme.metric_card("Road segments", f"{s['total_segments']:,}", "scored nationally", theme.SAGE),
        theme.metric_card("Wildlife sightings", s["sightings"], "occurrence records", theme.BARK),
        theme.metric_card("Species", str(s["species"]), "native Australian species", theme.SAGE),
        theme.metric_card("States & territories", str(s["states"]), "full coverage", theme.EUCALYPT),
    ])

    theme.section_header("From scores to action", eyebrow="Sign logic")
    st.markdown(
        "The highest-risk segments are promoted to a shortlist of **1,189 "
        "recommended warning-sign sites**. The intent is to put limited signage "
        "budget where the model sees the greatest concentration of collision "
        "risk — see the **Sign Placements** page to map and export them."
    )

    theme.section_header("Limitations & honest caveats", "Please read before acting "
                         "on these recommendations.", eyebrow="Read me")
    st.markdown(
        "- **Scores are pre-computed, not real-time.** They reflect the vintage of "
        "the source occurrence and road datasets.\n"
        "- **Risk is relative and model-based.** A score ranks segments against one "
        "another; it is not a calibrated probability of a collision on a given day.\n"
        "- **Sign effectiveness is not modelled.** We recommend *where* signs would "
        "target the highest-risk locations — we do **not** predict how much a sign "
        "would reduce collisions at that site.\n"
        "- **Correlation is not causation.** Features like traffic proxy and NDVI "
        "are associated with risk in the data; they are not proven causes.\n"
        "- **Coverage gaps exist.** Areas with sparse wildlife reporting may be "
        "under-scored simply because fewer sightings were recorded there."
    )
