"""
Traceability Service — builds the TraceabilityBlock for FeasibilityResponse.

Captures exactly what risk data drove the feasibility run:
  - Whether a C5AI+ forecast was loaded or a static model was used
  - Which sites, domains, and risk types were included
  - Scale factor if C5AI+ enrichment was applied
  - Site-level attribution (EAL + SCR) from the loss analysis
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional

from backend.schemas import TraceabilityBlock, TraceabilitySiteTrace


_STATIC_MODEL_NOTE = (
    "Denne gjennomførbarhetsanalysen bruker en statisk Compound Poisson-LogNormal-modell "
    "kalibrert mot operatørens TIV og risikoparametre. "
    "Ingen live C5AI+-prognose ble lastet i denne kjøringen — "
    "modellparametrene (forventet antall hendelser, alvorlighetsgrad, CV) er skalert fra "
    "template-data basert på operatørens eksponering. "
    "Domenene (biologisk, strukturell, miljø, operasjonell) beregnes via DomainLossBreakdown "
    "med stub-baserte fraksjoner for ikke-biologiske domener. "
    "Per-anlegg EAL er eksakt (TIV-vektet Gaussian copula). "
    "SCR-bidrag per anlegg er en proporsjonal tilnærming. "
    "Når C5AI+ er koblet live, vil scale_factor og loss_fractions justere Monte Carlo direkte."
)

_C5AI_ENRICHED_NOTE = (
    "C5AI+-prognosen ble lastet og brukt til å skalere det stokastiske tapsgrunnlaget. "
    "Biologiske risikotyper (HAB, lakselus, manet, patogen) er hentet fra prognosens "
    "loss_fractions og scale_factor. Øvrige domener (strukturell, miljø, operasjonell) "
    "bruker stub-baserte fraksjoner. Per-anlegg EAL er eksakt. SCR-bidrag er proporsjonal tilnærming."
)


def build_traceability_block(
    sim: Any,
    op: Any,
    selected_mitigations: List[str],
    loss_analysis_block: Optional[Any] = None,
) -> TraceabilityBlock:
    """Build a TraceabilityBlock from a completed simulation run."""

    c5ai_enriched: bool = bool(getattr(sim, "c5ai_enriched", False))
    c5ai_scale: Optional[float] = getattr(sim, "c5ai_scale_factor", None)
    sim_mitigated: bool = bool(getattr(sim, "mitigated", False))
    mitigation_names: List[str] = list(getattr(sim, "mitigation_summary", None) or [])

    if c5ai_enriched and sim_mitigated:
        source = "c5ai_plus_mitigated"
        data_mode = "c5ai_forecast_mitigated"
    elif c5ai_enriched:
        source = "c5ai_plus"
        data_mode = "c5ai_forecast"
    else:
        source = "static_model"
        data_mode = "static_model"

    mapping_note = _C5AI_ENRICHED_NOTE if c5ai_enriched else _STATIC_MODEL_NOTE

    # Site universe — prefer loss_analysis site names (most visible to user)
    site_ids: List[str] = []
    if loss_analysis_block is not None:
        for s in getattr(loss_analysis_block, "per_site", []):
            site_ids.append(s.site_id)

    if not site_ids:
        # Fall back to operator sites
        for s in getattr(op, "sites", []) or []:
            sid = getattr(s, "site_id", None) or getattr(s, "name", "unknown")
            site_ids.append(str(sid))

    if not site_ids:
        sld = getattr(sim, "site_loss_distribution", None) or {}
        site_ids = list(sld.keys())

    # Domain + risk type universe
    dld = getattr(sim, "domain_loss_breakdown", None)
    domains_used: List[str] = []
    risk_types_used: List[str] = []

    if dld is not None:
        try:
            dom_totals = dld.domain_totals()
            domains_used = [d for d, arr in dom_totals.items() if arr.size > 0 and float(arr.mean()) > 0]
        except Exception:
            pass
        try:
            all_sub = dld.all_subtypes() if hasattr(dld, "all_subtypes") else {}
            risk_types_used = [k for k, arr in all_sub.items() if arr.size > 0 and float(arr.mean()) > 0]
        except Exception:
            pass

    if not domains_used:
        domains_used = ["biological", "structural", "environmental", "operational"]

    # Site trace from loss_analysis
    site_trace: List[TraceabilitySiteTrace] = []
    if loss_analysis_block is not None:
        for s in getattr(loss_analysis_block, "per_site", []):
            dom_bd = s.domain_breakdown if hasattr(s, "domain_breakdown") else {}
            top_domains = sorted(dom_bd.keys(), key=lambda d: dom_bd.get(d, 0), reverse=True)[:2] if dom_bd else [getattr(s, "dominant_domain", "biological")]
            site_trace.append(
                TraceabilitySiteTrace(
                    site_id=s.site_id,
                    site_name=s.site_name,
                    eal_nok=float(s.expected_annual_loss_nok),
                    scr_contribution_nok=float(s.scr_contribution_nok),
                    top_domains=top_domains,
                )
            )

    applied = list(selected_mitigations) or mitigation_names

    return TraceabilityBlock(
        analysis_id=uuid.uuid4().hex[:12],
        generated_at=datetime.now(timezone.utc).isoformat(),
        source=source,
        c5ai_enriched=c5ai_enriched,
        c5ai_scale_factor=float(c5ai_scale) if c5ai_scale is not None else None,
        site_count=len(site_ids),
        domain_count=len(domains_used),
        risk_type_count=len(risk_types_used),
        site_ids=site_ids,
        domains_used=domains_used,
        risk_types_used=risk_types_used,
        data_mode=data_mode,
        mitigated_forecast_used=sim_mitigated,
        applied_mitigations=applied,
        mapping_note=mapping_note,
        site_trace=site_trace,
    )
