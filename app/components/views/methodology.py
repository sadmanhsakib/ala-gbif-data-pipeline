"""
Methodology & Data: the trust page.

Narrative job: explain the hard problem, why a proxy label was necessary, how
scores are produced, how they were validated, and the limits to keep in mind.
Curated for a technically literate reviewer: honest caveats are a feature.
"""
from __future__ import annotations

import streamlit as st

from components import data, theme

# ── Risk tier reference ───────────────────────────────────────────────────────
TIER_ROWS = [
    ("Critical", "#C02B22", "risk ≥ 0.98: intervene first"),
    ("High", "#E2702A", "0.90 – 0.98: strong candidates"),
    ("Moderate", "#E8B43A", "0.70 – 0.90: monitor"),
    ("Low", "#3F7A53", "below 0.70: lower priority"),
]

# ── Validation metrics (from Optuna-optimised model) ──────────────────────────
VALIDATION = {
    "cv_r2": "0.9743",
    "cv_r2_sd": "±0.0002",
    "cv_mae": "0.0337",
    "cv_mae_sd": "±0.0007",
    "tas_ceiling": "0.3001",
    "tas_model": "0.2922",
    "tas_pct": "97.4%",
    "tas_direct": "0.9835",
    "moran_target": "0.4117",
    "moran_resid": "0.3081",
    "moran_explained": "25.2%",
}


def render() -> None:
    s = data.national_summary()

    theme.page_hero(
        "Methodology & Data",
        "How the risk scores are produced: and, just as importantly, what they "
        "cannot tell you. This page documents the research design, validation "
        "strategy, and known limitations behind every number in this tool.",
        eyebrow="Why you can trust this",
    )

    # ── 1. The hard problem ───────────────────────────────────────────────────
    theme.section_header(
        "Why this is a hard problem?",
        eyebrow="Problem framing",
    )
    st.markdown(
        "~10 million animals die on Australian roads annually, yet the most "
        "comprehensive open citizen-science platform: iNaturalist: contains "
        "only **~15,000 confirmed roadkill observations** across 570+ species "
        "over five years. That is a detection rate of roughly **0.03%**.\n\n"
        "This sparsity is structural: roadkill events are transient, dispersed "
        "across 900,000+ km of road network, and entirely dependent on "
        "opportunistic observer presence. No national standardised roadkill "
        "monitoring programme exists in Australia. Direct supervised learning "
        "— predicting collision counts from road and ecological features: is "
        "therefore **infeasible**. The ground truth does not exist at the "
        "required spatial resolution."
    )

    # ── 2. The proxy label approach ───────────────────────────────────────────
    theme.section_header(
        "The proxy label approach:",
        "Without ground truth, we construct a surrogate risk score from "
        "observable correlates of collision risk and train a model to predict it.",
        eyebrow="Design decision",
    )
    st.markdown(
        "Three methodologically legitimate options exist:\n\n"
        "1. **Proxy label construction**: derive a surrogate risk score from "
        "wildlife presence, road danger, and habitat quality; train a model to "
        "predict that surrogate.\n"
        "2. **Unsupervised clustering**: group segments by feature similarity. "
        "Produces clusters, not risk scores.\n"
        "3. **Expert rule systems**: hard-coded thresholds. Not generalisable, "
        "not updatable from new data.\n\n"
        "This project uses approach 1. The proxy label is designed to be "
        "**ecologically principled**, **spatially coherent**, and **partially "
        "non-recoverable by formula**: the three properties required for a "
        "proxy label to support genuine model generalisation rather than "
        "formula memorisation."
    )

    # ── 3. Label construction ─────────────────────────────────────────────────
    theme.section_header(
        "How the proxy label is built?",
        "Four steps transform raw data into a 0–1 risk ranking.",
        eyebrow="Label design",
    )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            "**Step 1 · Ecological score** (weighted sum)\n\n"
            "| Component | Weight | Rationale |\n"
            "|---|---|---|\n"
            "| Sighting count | 0.30 | Most direct observational evidence |\n"
            "| Mean NDVI | 0.20 | Habitat quality: sustained presence |\n"
            "| Species richness | 0.15 | Biodiversity breadth |\n"
            "| Peak season weight | 0.15 | Seasonal risk character |\n"
            "| Nocturnal weight | 0.10 | Visibility risk modifier |\n"
            "| Body mass weight | 0.10 | Collision severity modifier |"
        )
    with c2:
        st.markdown(
            "**Step 2 · Road exposure score** (weighted sum)\n\n"
            "| Component | Weight | Rationale |\n"
            "|---|---|---|\n"
            "| Speed limit | 0.35 | Kinetic energy at impact |\n"
            "| Proximity | 0.35 | Wildlife approach distance |\n"
            "| Traffic proxy | 0.30 | Lower weight: imputed, not measured |"
        )
    st.markdown(
        "**Step 3 · Multiplicative combination:** "
        "`raw_risk = ecological_score × road_exposure_score`\n\n"
        "The multiplicative form enforces a logical AND: risk is only non-zero "
        "where wildlife presence **and** road danger co-occur. An additive "
        "combination would let a high-speed motorway with no wildlife "
        "score moderately: that does not reflect genuine collision risk.\n\n"
        "**Step 4 · Spatial lag blending + rank normalisation:**\n\n"
        "`blended_risk = 0.7 × raw_risk + 0.3 × spatial_lag(k=5)`  →  "
        "`proxy_risk = percentile_rank(blended_risk)`\n\n"
        "The 30% spatial lag injects neighbourhood context: wildlife movement "
        "corridors do not respect road segment boundaries. Percentile rank "
        "removes the arbitrary magnitude of blended scores and produces a "
        "uniform [0, 1] distribution that is robust to outliers. The result "
        "encodes **relative risk ranking**, not absolute collision probability."
    )

    # ── 4. Data sources ───────────────────────────────────────────────────────
    theme.section_header(
        "Data sources & coverage:",
        eyebrow="What powers the scores",
    )
    theme.render_metric_band([
        theme.metric_card(
            "Road segments", f"{s['total_segments']:,}",
            "scored nationally", theme.SAGE),
        theme.metric_card(
            "Wildlife sightings", s["sightings"],
            "ALA + GBIF, 2020–2026", theme.BARK),
        theme.metric_card(
            "Species", str(s["species"]),
            "native Australian collision-risk fauna", theme.SAGE),
        theme.metric_card(
            "States & territories", str(s["states"]),
            "full national coverage", theme.EUCALYPT),
    ])
    st.markdown(
        "**ALA + GBIF dual ingestion:** The two databases have structurally "
        "different observer networks. ALA specialises in Australian citizen "
        "science; GBIF aggregates museum specimens, research surveys, and "
        "international programmes. Taking the deduplicated union achieves "
        "greater spatial coverage than either alone: particularly for remote "
        "regions underrepresented in citizen science.\n\n"
        "**NDVI:** MODIS MOD13A3 monthly composites at 1 km resolution, "
        "median-composited across 72 months (2020–2026) to suppress fire "
        "scar artefacts and cloud contamination.\n\n"
        "**Road network:** OpenStreetMap via GeoFabrik: the only nationally "
        "complete, openly licensed, machine-readable road network for Australia."
    )

    # ── 5. Feature engineering highlights ─────────────────────────────────────
    theme.section_header(
        "What goes into a prediction?",
        "The model blends three families of signal: plus spatial lags for "
        "features where neighbourhood context carries independent predictive "
        "information.",
        eyebrow="Features",
    )
    c1, c2, c3 = st.columns(3)
    c1.markdown(
        "**🦘 Wildlife & ecology**\n\n"
        "- Sighting count\n- Species richness\n- Ecological score\n"
        "- Vegetation (mean NDVI)\n- Body-mass, nocturnal & peak-season weights"
    )
    c2.markdown(
        "**🛣 Road & traffic**\n\n"
        "- Speed limit\n- Traffic proxy\n"
        "- Road-exposure score\n- Distance to road / proximity"
    )
    c3.markdown(
        "**🧭 Spatial context**\n\n"
        "- Spatial lag of sighting count\n- Lagged species richness\n"
        "- Lagged NDVI & traffic proxy\n"
        "- *Road class excluded*: its signal is already captured by "
        "speed limit & traffic proxy"
    )

    # ── 6. Model choice ──────────────────────────────────────────────────────
    theme.section_header(
        "Why XGBoost?",
        eyebrow="Model selection",
    )
    st.markdown(
        "Every road segment is scored by a **gradient-boosted tree model "
        "(XGBoost)** optimised via 50-trial Bayesian search (Optuna, TPE "
        "sampler). Each prediction is paired with **exact SHAP values**: "
        "not kernel approximations: computed by traversing the tree structure."
    )
    st.markdown(
        "| Alternative | Why rejected |\n"
        "|---|---|\n"
        "| Random Forest | Less sample-efficient on 99k segments; no native "
        "learning rate shrinkage to control overfitting on a noisy proxy label |\n"
        "| Linear Regression | Cannot capture non-linear interactions "
        "(e.g. high sightings near a slow road ≠ same count near a motorway) |\n"
        "| Neural Network | SHAP would require kernel approximations: "
        "per-segment attributions would be estimated, not exact. "
        "Exact SHAP is non-negotiable for the explainability panel |\n"
        "| Gaussian Process | O(n³) complexity: infeasible for 99k segments "
        "without sparse approximations beyond project scope |"
    )

    # ── 7. Validation ─────────────────────────────────────────────────────────
    theme.section_header(
        "Validation strategy:",
        "Three complementary tests: because any single metric can be gamed "
        "by spatial autocorrelation.",
        eyebrow="How we know it works",
    )

    st.markdown("##### Spatial block cross-validation")
    st.markdown(
        "Random CV is **methodologically incorrect** for spatially "
        "autocorrelated data: a test segment 50 m from its training neighbours "
        "is not a test of generalisation. We use **jittered 50 km spatial "
        "blocks** (±15 km boundary offset per fold) so the model must predict "
        "risk in geographic regions it has never seen."
    )
    theme.render_metric_band([
        theme.metric_card(
            "Spatial CV R²", VALIDATION["cv_r2"],
            VALIDATION["cv_r2_sd"], theme.SAGE),
        theme.metric_card(
            "Spatial CV MAE", VALIDATION["cv_mae"],
            VALIDATION["cv_mae_sd"], theme.SAGE),
    ])

    st.markdown("##### Tasmania geographic holdout")
    st.markdown(
        "Tasmania is **geographically isolated** (Bass Strait), has **distinct "
        "fauna** composition, yet costs only 2.4% of training data. The model "
        "was never trained on any Tasmanian segment."
    )
    theme.render_metric_band([
        theme.metric_card(
            "Ceiling (proxy vs sightings)",
            VALIDATION["tas_ceiling"],
            "maximum achievable: by construction", theme.BARK),
        theme.metric_card(
            "Model (predicted vs sightings)",
            VALIDATION["tas_model"],
            f"{VALIDATION['tas_pct']} of ceiling achieved", theme.SAGE),
        theme.metric_card(
            "Direct (predicted vs proxy)",
            VALIDATION["tas_direct"],
            "Spearman ρ on unseen state", theme.EUCALYPT),
    ])

    st.markdown("##### Moran's I on residuals")
    st.markdown(
        "R² cannot distinguish whether the model learned *why* risk is high "
        "(feature relationships) or *where* it is high (geographic proximity). "
        "Moran's I on residuals provides the diagnostic: spatially random "
        "residuals (I ≈ 0) mean the model captured structure through features, "
        "not memorised locations."
    )
    theme.render_metric_band([
        theme.metric_card(
            "Target Moran's I", VALIDATION["moran_target"],
            "spatial structure in proxy_risk", theme.BARK),
        theme.metric_card(
            "Residual Moran's I", VALIDATION["moran_resid"],
            "remaining after model", theme.SAGE),
        theme.metric_card(
            "Spatial structure explained",
            VALIDATION["moran_explained"],
            "absorbed via tabular features alone", theme.EUCALYPT),
    ])

    # ── 8. Risk tiers ─────────────────────────────────────────────────────────
    theme.section_header(
        "How to read the scores?",
        "Risk is reported on a 0–1 scale and bucketed into four tiers.",
        eyebrow="Risk tiers",
    )
    chips = "".join(
        f'<span class="rw-chip" style="--chip:{hexc}; margin:0 .4rem .5rem 0;">'
        f'{label}</span><span style="color:#6B6557; font-size:.85rem; '
        f'margin-right:1.2rem;">{desc}</span>'
        for label, hexc, desc in TIER_ROWS
    )
    st.html(f'<div style="line-height:2.2;">{chips}</div>')

    # ── 9. Sign placement logic ───────────────────────────────────────────────
    theme.section_header("From scores to action:", eyebrow="Sign logic")
    st.markdown(
        "The highest-risk segments are promoted to a shortlist of **1,189 "
        "recommended warning-sign sites** (threshold: `predicted_risk ≥ 0.98`, "
        "spatially deduplicated with 2 km minimum separation). The intent is "
        "to put limited signage budget where the model sees the greatest "
        "concentration of collision risk."
    )
    st.markdown(
        "| State | Recommended signs |\n|---|---|\n"
        "| NSW | 831 |\n| VIC | 166 |\n| QLD | 120 |\n"
        "| TAS | 57 |\n| ACT | 16 |\n| SA | 12 |\n| WA | 5 |\n\n"
        "This distribution reflects the geographic concentration of sighting "
        "records, not the true national distribution of collision risk. "
        "Recommendations in **NSW, VIC, QLD, TAS, and ACT** are grounded in "
        "dense training signal: **high confidence**. SA and WA are "
        "extrapolations into data-sparse regions."
    )

    # ── 10. Limitations ───────────────────────────────────────────────────────
    theme.section_header(
        "Limitations & honest caveats:",
        "Please read before acting on these recommendations.",
        eyebrow="Read me",
    )
    st.markdown(
        "- **Proxy label circularity.** The label is derived from the same "
        "feature space the model uses. High CV R² partially reflects formula "
        "recovery, not only genuine generalisation. Two design decisions "
        "partially break this: spatial lag blending injects neighbourhood "
        "context the model cannot directly access from its own inputs, and "
        "the Tasmania holdout (r = 0.9835) demonstrates generalisation "
        "inconsistent with pure memorisation. **Full resolution requires real "
        "collision ground truth data**, which does not exist.\n"
        "- **Observation bias.** ALA and GBIF records are citizen-science "
        "observations concentrated near populated areas and roads. The model "
        "cannot distinguish observer density from wildlife density: an "
        "unresolved limitation of occurrence-based risk modelling.\n"
        "- **Imputed road attributes.** Speed limit and traffic proxy are "
        "imputed from road class for the majority of segments. Real values "
        "vary by state, urban/rural context, and time of day.\n"
        "- **Static temporal snapshot.** Scores reflect 2020–2026 data. "
        "They will become stale as land use changes, roads are upgraded, "
        "and species distributions shift under climate change.\n"
        "- **Residual spatial autocorrelation.** Moran's I on residuals "
        "(0.3081) indicates unobserved landscape covariates: terrain "
        "complexity, fencing density, seasonal migration corridors: that no "
        "available open dataset can supply. This represents the **ceiling of "
        "what is achievable with open data at national scale**.\n"
        "- **Sign effectiveness is not modelled.** We recommend *where* signs "
        "would target the highest-risk locations: we do **not** predict how "
        "much a sign would reduce collisions at that site."
    )
