"""
streamlit_app.py — Shield Risk Platform · Ekstern pilottilgang
https://shieldcaptive.streamlit.app

Streamlit-wrapper rundt eksisterende Python-analysemodeller.
Ingen eksisterende kode er endret — all logikk importeres direkte som
Python-funksjonskall (ingen HTTP, ingen kjørende FastAPI-server nødvendig).

Struktur
--------
  _inject_css()         — Shield-tema og tilpassede kort-stiler
  _sidebar()            — alle inndatakontroller; returnerer (request, run_clicked)
  _show_summary()       — verdict-banner + KPI-rad + mitigerings-delta
  _show_charts()        — base64-PNG-diagrammer fra analyse-pipeline
  _show_criteria()      — utvidet egnethetsanalyse med kriteriedetaljer
  _show_allocation()    — lokalitetsfordeling og biomasseverdikalkulasjon
  _show_loss_analysis() — EAL / SCR per domene og lokalitet
  main()                — sidestruktur og tilstandshåndtering
"""
from __future__ import annotations

import base64
import os
import sys

# ── Ensure repo root is on sys.path (needed on Streamlit Community Cloud) ─────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

# ── Page config (must be the FIRST Streamlit call) ────────────────────────────
st.set_page_config(
    page_title="Shield Risk Platform",
    page_icon="🛡",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": (
            "**Shield Risk Platform v0.5**\n\n"
            "PCC Captive-egnethet og biologisk risikointelligens "
            "for norsk lakseoppdrett.\n\n"
            "Kun for pilottesting — ikke finansiell rådgivning."
        ),
    },
)

# ── Late imports (after sys.path) ─────────────────────────────────────────────
from backend.schemas import (
    FeasibilityRequest,
    MitigationInput,
    ModelSettingsInput,
    OperatorProfileInput,
    StrategySettingsInput,
)
from backend.services.run_analysis import run_feasibility_service
from analysis.mitigation import PREDEFINED_MITIGATIONS

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

_SEA_MITIGATIONS: dict = {
    k: v
    for k, v in PREDEFINED_MITIGATIONS.items()
    if getattr(v, "facility_type", "sea") != "smolt"
}

_STRATEGY_OPTS: dict[str, str] = {
    "pcc_captive":    "PCC Captive Cell (anbefalt for store operatører)",
    "full_insurance": "Full markedsforsikring",
    "hybrid":         "Hybrid — egenandel + markedsforsikring",
    "self_insurance": "Egenforsikring / intern captive",
}

_CORR_OPTS: dict[str, str] = {
    "expert_default": "Ekspert-standard (anbefalt)",
    "independent":    "Uavhengig (konservativt lavt)",
    "low":            "Lav kryss-domenekorrelerasjon",
    "moderate":       "Moderat kryss-domenekorrelerasjon",
}

_MITIGATION_NO: dict[str, str] = {
    "stronger_nets":           "Forsterket notlin",
    "stronger_anchors":        "Forsterket ankring",
    "stronger_moorings":       "Forsterket fortøyning",
    "lice_barriers":           "Lusebarrierer (dypvannsintaksfilter)",
    "environmental_sensors":   "Miljøsensorer (HAB / O₂ / temperatur)",
    "emergency_response_plan": "Beredskapsplan",
    "staff_training_program":  "Opplæringsprogram personell",
    "storm_contingency_plan":  "Stormberedskapsprogram",
    "risk_manager_hire":       "Ansettelse av risikomanager",
    "jellyfish_mitigation":    "Manetmitigation (barrierer + varsling)",
    "deformation_monitoring":  "Deformasjonsovervåkning (strukturell)",
    "ai_early_warning":        "AI-basert tidligvarsling (tverrdomene)",
}

_CHART_LABELS_NO: dict[str, str] = {
    "loss_distribution":   "Tapsdistribusjon",
    "domain_breakdown":    "Domeneinndeling",
    "strategy_comparison": "Strategisammenligning (5-år TCOR)",
    "mitigation_impact":   "Tiltakseffekt",
    "correlation_heatmap": "Domenekorrelasjons-heatmap",
    "scenario_stacks":     "Scenario-stakker (P50 / P95 / P99)",
    "tail_composition":    "Halerisiko — domenebidrag",
    "site_loss":           "EAL fordelt på anlegg",
}

_DOMAIN_NO: dict[str, str] = {
    "biological":    "Biologisk",
    "structural":    "Strukturell",
    "environmental": "Miljø",
    "operational":   "Operasjonell",
}

# ─────────────────────────────────────────────────────────────────────────────
# Utility helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fmt(v: float | None, decimals: int = 1) -> str:
    """Format a NOK value to a compact, readable string."""
    if v is None:
        return "—"
    sign = "-" if v < 0 else ""
    a = abs(v)
    if a >= 1_000_000_000:
        return f"{sign}NOK {a / 1e9:.{decimals}f} mrd"
    if a >= 1_000_000:
        return f"{sign}NOK {a / 1e6:.{decimals}f}M"
    if a >= 1_000:
        return f"{sign}NOK {a / 1_000:.0f}k"
    return f"{sign}NOK {a:.0f}"


def _pct(v: float | None) -> str:
    if v is None:
        return "—"
    return f"{v:.1f}%"


def _suggested_biomass(ref_price: float, realisation: float, haircut: float) -> float:
    return ref_price * 1_000.0 * realisation * (1.0 - haircut)


def _decode_chart(b64: str) -> bytes:
    return base64.b64decode(b64)


# ─────────────────────────────────────────────────────────────────────────────
# CSS + branding injection
# ─────────────────────────────────────────────────────────────────────────────

def _inject_css() -> None:
    st.markdown(
        """
        <style>
        /* ── Header ──────────────────────────────────────────────── */
        .sh-header        { display:flex; align-items:baseline; gap:10px;
                            border-bottom:3px solid #C9A84C; padding-bottom:0.6rem;
                            margin-bottom:0.4rem; }
        .sh-title         { font-size:2rem; font-weight:800; color:#1B2B4B; }
        .sh-gold          { color:#C9A84C; }
        .sh-sub           { font-size:0.85rem; color:#6B7280; }

        /* ── Verdict banners ─────────────────────────────────────── */
        .verdict-strong   { background:#DCFCE7; border-left:5px solid #16A34A;
                            padding:1rem 1.3rem; border-radius:8px; margin-bottom:1rem; }
        .verdict-rec      { background:#D1FAE5; border-left:5px solid #059669;
                            padding:1rem 1.3rem; border-radius:8px; margin-bottom:1rem; }
        .verdict-maybe    { background:#FEF9C3; border-left:5px solid #CA8A04;
                            padding:1rem 1.3rem; border-radius:8px; margin-bottom:1rem; }
        .verdict-no       { background:#FEE2E2; border-left:5px solid #DC2626;
                            padding:1rem 1.3rem; border-radius:8px; margin-bottom:1rem; }
        .vt               { font-size:1.15rem; font-weight:700; margin-bottom:3px; }
        .vs               { font-size:0.82rem; color:#374151; }

        /* ── KPI cards ───────────────────────────────────────────── */
        .kpi              { background:#F8FAFC; border:1px solid #E2E8F0;
                            border-radius:10px; padding:1rem 0.8rem; text-align:center; }
        .kpi-lbl          { font-size:0.68rem; text-transform:uppercase;
                            letter-spacing:0.06em; color:#64748B; margin-bottom:5px; }
        .kpi-val          { font-size:1.5rem; font-weight:700; color:#1B2B4B; }
        .kpi-sub          { font-size:0.7rem; color:#94A3B8; margin-top:3px; }

        /* ── Score bar ───────────────────────────────────────────── */
        .score-bg         { background:#E5E7EB; border-radius:6px;
                            height:10px; overflow:hidden; margin:6px 0 2px; }
        .score-fill       { height:100%; border-radius:6px; }

        /* ── Criterion row ───────────────────────────────────────── */
        .crit-name        { font-weight:600; font-size:0.88rem; color:#1B2B4B; }
        .crit-weight      { font-size:0.75rem; color:#9CA3AF; }
        .crit-finding     { font-size:0.8rem; color:#4B5563; margin-top:2px; }

        /* ── Sidebar section labels ──────────────────────────────── */
        .ss-lbl           { font-size:0.68rem; font-weight:700; text-transform:uppercase;
                            letter-spacing:0.07em; color:#9CA3AF; margin:0.9rem 0 0.2rem; }

        /* ── Welcome ─────────────────────────────────────────────── */
        .welcome          { max-width:680px; margin:3rem auto; text-align:center; }
        .welcome-box      { background:#F8FAFC; border:1px solid #E2E8F0;
                            border-radius:12px; padding:2rem; text-align:left; margin-top:1.5rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar — all input controls
# ─────────────────────────────────────────────────────────────────────────────

_EXAMPLE: dict = {
    "_name":        "Nordic Aqua Partners AS",
    "_n_sites":     3,
    "_biomass":     9_200.0,
    "_ref_price":   80,
    "_realisation": 90,
    "_haircut":     10,
    "_revenue":     897.0,
    "_premium":     19.5,
}


def _sidebar():  # -> tuple[FeasibilityRequest, bool]
    with st.sidebar:
        st.markdown(
            '<div style="margin-bottom:0.25rem">'
            '<span style="font-size:1.7rem;font-weight:800;color:#1B2B4B;">'
            '🛡 <span style="color:#C9A84C;">Shield</span></span></div>'
            '<div style="font-size:0.8rem;color:#6B7280;">Risk Platform · Pilotversjon</div>',
            unsafe_allow_html=True,
        )
        st.divider()

        # ── Example loader ────────────────────────────────────────────────────
        if st.button("📥 Last inn eksempeldata", use_container_width=True,
                     help="Nordic Aqua Partners AS — realistisk norsk oppdrettsoperatør"):
            st.session_state.update(_EXAMPLE)
            st.rerun()

        # ── Operator profile ──────────────────────────────────────────────────
        st.markdown('<div class="ss-lbl">Operatørprofil</div>', unsafe_allow_html=True)

        name = st.text_input(
            "Operatørnavn",
            key="_name",
            placeholder="Min Oppdrettsbedrift AS",
        )
        n_sites = st.slider(
            "Antall lokaliteter", min_value=1, max_value=20,
            key="_n_sites",
        )
        biomass = st.number_input(
            "Total biomasse (tonn)",
            min_value=500.0, max_value=100_000.0, step=500.0,
            format="%.0f",
            key="_biomass",
        )

        # ── Biomass valuation ─────────────────────────────────────────────────
        st.markdown('<div class="ss-lbl">Biomasseverdiberegning</div>', unsafe_allow_html=True)

        ref_price = st.slider(
            "Referansepris (NOK/kg)", min_value=50, max_value=130, step=5,
            key="_ref_price",
        )
        realisation_pct = st.slider(
            "Realiseringsgrad (%)", min_value=50, max_value=120, step=5,
            key="_realisation",
        )
        haircut_pct = st.slider(
            "Forsiktighetsfradrag (%)", min_value=0, max_value=30, step=5,
            key="_haircut",
        )

        realisation = realisation_pct / 100.0
        haircut     = haircut_pct / 100.0
        sugg_nok_t  = _suggested_biomass(ref_price, realisation, haircut)
        sugg_total  = sugg_nok_t * (biomass or 0)

        st.caption(
            f"Beregnet verdi: **{sugg_nok_t:,.0f} NOK/t** "
            f"· Totalverdi: **{_fmt(sugg_total)}**"
        )

        # ── Insurance ─────────────────────────────────────────────────────────
        st.markdown('<div class="ss-lbl">Forsikring</div>', unsafe_allow_html=True)

        revenue = st.number_input(
            "Årsomsetning (NOK M)",
            min_value=50.0, max_value=20_000.0, step=50.0,
            format="%.0f",
            key="_revenue",
        )
        premium = st.number_input(
            "Nåværende premie (NOK M)",
            min_value=0.5, max_value=500.0, step=0.5,
            format="%.1f",
            key="_premium",
        )

        # ── Analysis settings ─────────────────────────────────────────────────
        st.markdown('<div class="ss-lbl">Analyseinnstillinger</div>', unsafe_allow_html=True)

        strategy_key = st.selectbox(
            "Strategi",
            options=list(_STRATEGY_OPTS.keys()),
            format_func=lambda k: _STRATEGY_OPTS[k],
            key="_strategy",
        )
        corr_key = st.selectbox(
            "Domenekorrelerasjon",
            options=list(_CORR_OPTS.keys()),
            format_func=lambda k: _CORR_OPTS[k],
            key="_corr",
        )
        n_sims = st.select_slider(
            "Monte Carlo-simuleringer",
            options=[1_000, 2_500, 5_000, 10_000],
            value=st.session_state.get("_nsims", 5_000),
            key="_nsims",
        )

        # ── Mitigations (collapsed by default) ───────────────────────────────
        with st.expander("Risikoreduserende tiltak", expanded=False):
            st.caption(
                "Tiltak som er implementert vil redusere sannsynlighet og/eller "
                "alvorlighetsgrad i simuleringsmodellen."
            )
            selected_actions: list[str] = st.multiselect(
                "Velg aktive tiltak",
                options=list(_MITIGATION_NO.keys()),
                format_func=lambda k: _MITIGATION_NO.get(k, k),
                default=[],
                key="_mitigations",
                label_visibility="collapsed",
            )
            if selected_actions:
                total_cost = sum(
                    getattr(PREDEFINED_MITIGATIONS.get(k), "annual_cost_nok", 0)
                    for k in selected_actions
                )
                st.caption(f"Estimert tiltakskostnad: **{_fmt(total_cost)}/år**")

        st.divider()

        run_clicked = st.button(
            "▶  Kjør analyse",
            use_container_width=True,
            type="primary",
            help=f"Kjører {n_sims:,} Monte Carlo-simuleringer (~5–15 sek)",
        )

    # ── Build FeasibilityRequest ───────────────────────────────────────────────
    profile = OperatorProfileInput(
        name=name or "Ukjent operatør",
        n_sites=int(n_sites),
        total_biomass_tonnes=float(biomass or 1_000),
        reference_price_per_kg=float(ref_price),
        realisation_factor=realisation,
        prudence_haircut=haircut,
        biomass_value_per_tonne=sugg_nok_t,
        annual_revenue_nok=float(revenue or 100) * 1_000_000,
        annual_premium_nok=float(premium or 5) * 1_000_000,
    )
    model    = ModelSettingsInput(
        n_simulations=int(n_sims),
        domain_correlation=corr_key,
        generate_pdf=False,          # Ingen PDF-fil på cloud
    )
    strategy = StrategySettingsInput(strategy=strategy_key)
    mitigation = MitigationInput(selected_actions=selected_actions)

    request = FeasibilityRequest(
        operator_profile=profile,
        model_settings=model,
        strategy_settings=strategy,
        mitigation=mitigation,
    )
    return request, run_clicked


# ─────────────────────────────────────────────────────────────────────────────
# Display helpers
# ─────────────────────────────────────────────────────────────────────────────

def _verdict_html(verdict: str, score: float, strategy_key: str) -> str:
    if "STRONGLY" in verdict:
        css = "verdict-strong"
    elif "RECOMMENDED" in verdict and "NOT" not in verdict:
        css = "verdict-rec"
    elif "POTENTIALLY" in verdict:
        css = "verdict-maybe"
    else:
        css = "verdict-no"
    strat_label = _STRATEGY_OPTS.get(strategy_key, strategy_key)
    return (
        f'<div class="{css}">'
        f'<div class="vt">{verdict}</div>'
        f'<div class="vs">Egnethetsscore: <strong>{score:.0f} / 100</strong>'
        f' &nbsp;·&nbsp; Strategi: {strat_label}</div>'
        f'</div>'
    )


def _score_bar_html(score: float) -> str:
    pct = min(max(score, 0), 100)
    color = "#16A34A" if pct >= 70 else "#CA8A04" if pct >= 45 else "#DC2626"
    return (
        f'<div class="score-bg">'
        f'<div class="score-fill" style="width:{pct:.0f}%;background:{color};"></div>'
        f'</div>'
    )


def _show_summary(result, strategy_key: str) -> None:
    s = result.baseline.summary

    # Verdict banner
    st.markdown(_verdict_html(s.verdict, s.composite_score, strategy_key),
                unsafe_allow_html=True)

    # KPI row — 4 equal columns
    c1, c2, c3, c4 = st.columns(4)
    kpis = [
        (c1, "Forventet årstap",   _fmt(s.expected_annual_loss), "E[tap/år] — Monte Carlo snitt"),
        (c2, "P95 årstap",         _fmt(s.p95_loss),             "95-persentil årstap"),
        (c3, "P99 årstap",         _fmt(s.p99_loss),             "99-persentil årstap"),
        (c4, "SCR (99,5%)",        _fmt(s.scr),                  "Solvenskapital etter RI"),
    ]
    for col, lbl, val, sub in kpis:
        with col:
            st.markdown(
                f'<div class="kpi"><div class="kpi-lbl">{lbl}</div>'
                f'<div class="kpi-val">{val}</div>'
                f'<div class="kpi-sub">{sub}</div></div>',
                unsafe_allow_html=True,
            )

    # Composite score progress bar
    st.markdown("")
    sc1, sc2 = st.columns([5, 1])
    with sc1:
        st.markdown(
            f"**Samlet egnethetsscore: {s.composite_score:.0f} / 100**",
        )
        st.markdown(_score_bar_html(s.composite_score), unsafe_allow_html=True)
    with sc2:
        st.caption(f"Konfidens: {s.confidence_level}")

    # Mitigation delta block
    if result.mitigated is not None and result.comparison is not None:
        st.markdown("---")
        st.markdown("#### Effekt av risikoreduserende tiltak")
        comp = result.comparison
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric(
                "Forventet årstap (m/ tiltak)",
                _fmt(result.mitigated.summary.expected_annual_loss),
                delta=f"{_fmt(comp.expected_loss_delta)} ({comp.expected_loss_delta_pct:.1f}%)",
                delta_color="inverse",
                help="Negativt delta = lavere tap = bedre",
            )
        with m2:
            st.metric(
                "P95 (m/ tiltak)",
                _fmt(result.mitigated.summary.p95_loss),
                delta=_fmt(comp.p95_delta),
                delta_color="inverse",
            )
        with m3:
            st.metric(
                "SCR (m/ tiltak)",
                _fmt(result.mitigated.summary.scr),
                delta=_fmt(comp.scr_delta),
                delta_color="inverse",
            )
        with m4:
            st.metric(
                "Kostnadsbesparelse/år",
                _fmt(comp.annual_cost_saving),
                help="Reduksjon i netto forventet tapskostnad per år",
            )

        if comp.narrative:
            st.info(comp.narrative)

        if comp.top_benefit_domains:
            domains_str = " · ".join(
                _DOMAIN_NO.get(d, d) for d in comp.top_benefit_domains
            )
            st.caption(f"Største tiltakseffekt i domenene: **{domains_str}**")


def _show_charts(result) -> None:
    charts = result.baseline.charts
    if not charts:
        st.info("Ingen diagrammer i denne kjøringen.")
        return

    items = list(charts.items())
    for i in range(0, len(items), 2):
        cols = st.columns(2)
        for j, (key, b64) in enumerate(items[i : i + 2]):
            with cols[j]:
                label = _CHART_LABELS_NO.get(key, key.replace("_", " ").title())
                st.markdown(f"**{label}**")
                try:
                    st.image(_decode_chart(b64), use_container_width=True)
                except Exception:
                    st.warning(f"Kunne ikke vise diagram: {key}")


def _show_criteria(result) -> None:
    scores = result.baseline.criterion_scores
    if not scores:
        st.info("Ingen kriteriedata tilgjengelig.")
        return

    st.markdown(
        "Samlet egnethetsscore er et vektet gjennomsnitt av kriteriene nedenfor. "
        "Hvert kriterie måler én dimensjon av PCC-egnethet (0–100)."
    )
    st.markdown("---")

    for crit in scores:
        name    = crit.get("name", "—")
        raw     = float(crit.get("raw_score", 0))
        weight  = float(crit.get("weight", 0))
        finding = crit.get("finding", "")

        col_info, col_score = st.columns([4, 1])

        with col_info:
            st.markdown(
                f'<span class="crit-name">{name}</span> '
                f'<span class="crit-weight">vekt {weight:.0%}</span>',
                unsafe_allow_html=True,
            )
            st.markdown(_score_bar_html(raw), unsafe_allow_html=True)
            if finding:
                st.markdown(
                    f'<div class="crit-finding">{finding}</div>',
                    unsafe_allow_html=True,
                )

        with col_score:
            color = "#16A34A" if raw >= 70 else "#CA8A04" if raw >= 45 else "#DC2626"
            st.markdown(
                f'<div style="text-align:right;padding-top:4px;">'
                f'<span style="font-size:1.4rem;font-weight:700;color:{color}">'
                f'{raw:.0f}</span>'
                f'<span style="color:#9CA3AF;font-size:0.78rem">/100</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.markdown("")  # spacing


def _show_allocation(result) -> None:
    alloc = result.allocation
    if alloc is None:
        st.info("Allokeringsdata ikke tilgjengelig.")
        return

    # Scaling metrics
    s1, s2, s3, s4 = st.columns(4)
    with s1:
        st.metric("TIV-ratio", f"{alloc.tiv_ratio:.2f}×",
                  help="Operatørens totaleksponering vs. referansemal (NOK 662M)")
    with s2:
        st.metric("Skaleringsf. alvorlighetsgrad", f"{alloc.risk_severity_scaled:.2f}×",
                  help="Tapsalvorlighetsgrad skalert fra TIV-ratio")
    with s3:
        st.metric("Skaleringsf. hendelseshyppighet", f"{alloc.risk_events_scaled:.2f}×",
                  help="Forventede hendelser/år skalert med √(n_lokaliteter)")
    with s4:
        if alloc.calibration_active:
            st.metric("Kalibrering", alloc.calibration_mode,
                      help="Historiske tapsdata brukt til å kalibrere parametre")
        else:
            st.metric("Kalibrering", "Mal-basert",
                      help="Ingen historiske data — mal-skalering brukt")

    # Per-site table
    if alloc.sites:
        st.markdown("#### Lokalitetsfordeling")
        import pandas as pd
        rows = [
            {
                "Lokalitet":    s.name,
                "Biomasse (t)": f"{s.biomass_tonnes:,}",
                "Biomasseverdi": _fmt(s.biomass_value_nok),
                "Utstyr":       _fmt(s.equipment_value_nok),
                "Infrastruktur": _fmt(s.infrastructure_value_nok),
                "TIV":          _fmt(s.tiv_nok),
                "Andel":        _pct(s.weight_pct),
            }
            for s in alloc.sites
        ]
        st.dataframe(
            pd.DataFrame(rows),
            hide_index=True,
            use_container_width=True,
        )

    # Biomass valuation detail
    if alloc.biomass_valuation:
        bv = alloc.biomass_valuation
        st.markdown("#### Biomasseverdiberegning")
        b1, b2, b3, b4, b5 = st.columns(5)
        with b1: st.metric("Referansepris", f"{bv.reference_price_per_kg:.0f} NOK/kg")
        with b2: st.metric("Realiseringsgrad", f"{bv.realisation_factor:.0%}")
        with b3: st.metric("Forsiktighetsfradrag", f"{bv.prudence_haircut:.0%}")
        with b4: st.metric("Foreslått (NOK/t)", f"{bv.suggested_biomass_value_per_tonne:,.0f}")
        with b5:
            applied_lbl = "Anvendt (NOK/t)"
            if bv.user_overridden:
                applied_lbl += " ⚠"
            st.metric(applied_lbl, f"{bv.applied_biomass_value_per_tonne:,.0f}",
                      help="⚠ = manuell overstyring aktiv" if bv.user_overridden else "")

    # Financial ratios
    if alloc.financial_ratios:
        st.markdown("#### Avledede finansielle parametre")
        fr = alloc.financial_ratios
        fcols = st.columns(len(fr))
        label_map = {
            "ebitda":  "EBITDA",
            "equity":  "Egenkapital",
            "fcf":     "Fri kontantstrøm",
            "assets":  "Totalaktiva",
        }
        for col, (k, v) in zip(fcols, fr.items()):
            with col:
                st.metric(label_map.get(k, k), _fmt(v))

    # Warnings
    for w in alloc.warnings or []:
        st.warning(w)


def _show_loss_analysis(result) -> None:
    la = result.loss_analysis
    if la is None:
        st.info("Tapsanalysedata ikke tilgjengelig.")
        return

    # Domain breakdown
    if la.per_domain:
        st.markdown("#### EAL fordelt på risikodomene")
        import pandas as pd

        domain_rows = [
            {
                "Domene":       _DOMAIN_NO.get(d, d),
                "Forventet årstap": _fmt(v),
                "Andel":        _pct(v / sum(la.per_domain.values()) * 100)
                                if sum(la.per_domain.values()) > 0 else "—",
            }
            for d, v in sorted(la.per_domain.items(), key=lambda x: x[1], reverse=True)
        ]
        st.dataframe(pd.DataFrame(domain_rows), hide_index=True, use_container_width=True)

    # Per-site breakdown
    if la.per_site:
        st.markdown("#### EAL og SCR-bidrag per lokalitet")
        import pandas as pd

        site_rows = [
            {
                "Lokalitet":        s.site_name,
                "ID":               s.site_id,
                "EAL/år (eksakt)":  _fmt(s.expected_annual_loss_nok),
                "SCR-bidrag (ca.)": _fmt(s.scr_contribution_nok),
                "SCR-andel":        _pct(s.scr_share_pct),
                "Toppdomene":       _DOMAIN_NO.get(s.dominant_domain, s.dominant_domain),
            }
            for s in sorted(la.per_site, key=lambda x: x.expected_annual_loss_nok, reverse=True)
        ]
        st.dataframe(pd.DataFrame(site_rows), hide_index=True, use_container_width=True)
        st.caption(
            "EAL er eksakt (Monte Carlo, TIV-vektet). "
            "SCR-bidrag er proporsjonal approksimering av portefølje-SCR."
        )

    # Top risk drivers
    if la.top_drivers:
        st.markdown("#### Topp risikodrivere")
        import pandas as pd

        driver_rows = [
            {
                "Driver":       d.label,
                "Domene":       _DOMAIN_NO.get(d.domain, d.domain),
                "Tapsimpact":   _fmt(d.impact_nok),
                "Andel av EAL": _pct(d.impact_share_pct),
            }
            for d in la.top_drivers[:8]
        ]
        st.dataframe(pd.DataFrame(driver_rows), hide_index=True, use_container_width=True)

    if la.method_note:
        st.caption(la.method_note)


# ─────────────────────────────────────────────────────────────────────────────
# Welcome screen (no result yet)
# ─────────────────────────────────────────────────────────────────────────────

def _welcome() -> None:
    st.markdown(
        """
        <div class="welcome">
          <div style="font-size:3.5rem">🛡</div>
          <h1 style="color:#1B2B4B;margin:0.3rem 0 0.6rem;">
            Shield Risk Platform
          </h1>
          <p style="color:#6B7280;font-size:1rem;margin-bottom:1.5rem;">
            PCC Captive-egnethet og biologisk risikointelligens
            for norsk lakseoppdrett.
          </p>
          <div class="welcome-box">
            <h3 style="color:#1B2B4B;margin-top:0;">Slik bruker du verktøyet</h3>
            <ol style="color:#374151;line-height:2.1;">
              <li>Fyll inn operatørprofil i sidepanelet til venstre</li>
              <li>Velg strategi og analyseinnstillinger</li>
              <li>Trykk <strong>▶ Kjør analyse</strong> — resultater vises innen 15 sekunder</li>
            </ol>
            <hr style="border:none;border-top:1px solid #E2E8F0;margin:1rem 0;">
            <p style="color:#6B7280;font-size:0.85rem;margin:0;">
              Vil du teste med realistiske data?
              Trykk <strong>📥 Last inn eksempeldata</strong> øverst i sidepanelet
              for å laste Nordic Aqua Partners AS — en typisk norsk lakseoppdrettsoperatør
              med tre lokaliteter i Møre og Romsdal.
            </p>
          </div>
          <p style="color:#9CA3AF;font-size:0.75rem;margin-top:1.5rem;">
            Modellen benytter Compound Poisson-LogNormal Monte Carlo (5 000 scenarier),
            4-domene risikokorrelerasjon og PCC Captive-kalibrering mot markedspremsdata.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    _inject_css()

    # Page header
    st.markdown(
        '<div class="sh-header">'
        '<span class="sh-title">🛡 <span class="sh-gold">Shield</span> Risk Platform</span>'
        '</div>'
        '<div class="sh-sub" style="margin-bottom:1.2rem;">'
        'PCC Captive-egnethet &nbsp;·&nbsp; Biologisk risikointelligens '
        '&nbsp;·&nbsp; Stokastisk tapssimulering &nbsp;·&nbsp; '
        '<em>Kun for pilottesting</em></div>',
        unsafe_allow_html=True,
    )

    # Sidebar returns the request and whether "Kjør analyse" was clicked
    request, run_clicked = _sidebar()

    # Session state initialisation
    if "result" not in st.session_state:
        st.session_state["result"] = None
    if "strategy_key" not in st.session_state:
        st.session_state["strategy_key"] = "pcc_captive"

    # Run analysis when button clicked
    if run_clicked:
        spinner_msg = (
            f"Kjører {request.model_settings.n_simulations:,} Monte Carlo-simuleringer "
            f"for {request.operator_profile.name}…"
        )
        with st.spinner(spinner_msg):
            try:
                result = run_feasibility_service(request)
                st.session_state["result"] = result
                st.session_state["strategy_key"] = request.strategy_settings.strategy
            except Exception as exc:
                st.error(f"Analyse feilet: {exc}")
                import traceback
                with st.expander("Teknisk feilmelding"):
                    st.code(traceback.format_exc())
                st.session_state["result"] = None

    result = st.session_state.get("result")

    if result is None:
        _welcome()
        return

    strategy_key = st.session_state.get("strategy_key", "pcc_captive")

    # ── Result tabs ───────────────────────────────────────────────────────────
    tab_sum, tab_charts, tab_crit, tab_alloc, tab_loss = st.tabs([
        "📊 Sammendrag",
        "📈 Risikodiagrammer",
        "✅ Egnethetsanalyse",
        "🏭 Allokering",
        "📉 Tapsanalyse",
    ])

    with tab_sum:
        _show_summary(result, strategy_key)

    with tab_charts:
        _show_charts(result)

    with tab_crit:
        _show_criteria(result)

    with tab_alloc:
        _show_allocation(result)

    with tab_loss:
        _show_loss_analysis(result)

    # ── Footer ────────────────────────────────────────────────────────────────
    st.divider()
    op_name = st.session_state.get("_name", "—")
    st.caption(
        f"Shield Risk Platform v0.5 &nbsp;·&nbsp; "
        f"Operatør: {op_name} &nbsp;·&nbsp; "
        f"Analyse kjørt med {result.metadata.n_simulations:,} simuleringer &nbsp;·&nbsp; "
        "Alle beregninger er veiledende og utgjør ikke finansiell rådgivning."
    )


if __name__ == "__main__":
    main()
