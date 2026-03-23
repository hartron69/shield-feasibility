"""
Input Data Audit API — GET /api/inputs/audit

Returns a structured JSON audit report covering:
  - C5AI+ freshness and data mode
  - Domain coverage (which domains are C5AI+-informed vs. stub-estimated)
  - Per-site completeness, confidence flags, and missing field inventory
  - Portfolio-level summary and model limitation disclosures

Data sources
------------
C5AI+ status     : backend.services.c5ai_state (live, in-memory)
Per-site quality : Three demo sites (DEMO_OP_S01–S03) — same as mockInputsData.js.
                   Consistent with frontend mock so report and UI match.
Model limitations: Hardcoded — reflects known stub-model gaps documented in
                   docs/sprints/sprint_c5ai_traceability_refinement/02_architecture.md
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/inputs", tags=["inputs"])


# ─────────────────────────────────────────────────────────────────────────────
# Response models
# ─────────────────────────────────────────────────────────────────────────────

class RiskTypeAudit(BaseModel):
    source: str                          # "real" | "simulated" | "estimated"
    completeness: float                  # 0.0–1.0
    confidence: str                      # "high" | "medium" | "low"
    flag: str                            # "SUFFICIENT" | "LIMITED" | "POOR"
    n_obs: int
    missing_fields: List[str] = Field(default_factory=list)


class SiteAudit(BaseModel):
    site_id: str
    site_name: str
    fjord_exposure: str
    overall_completeness: float
    overall_confidence: str
    risk_types: Dict[str, RiskTypeAudit]


class DomainCoverage(BaseModel):
    source: str       # "c5ai_plus" | "estimated"
    model: str        # "C5AI+ MultiDomainEngine" | "Stub-modell (ekspertprioritet)"
    note: str


class AuditSummary(BaseModel):
    total_sites: int
    total_risk_types_assessed: int
    sufficient_count: int
    limited_count: int
    poor_count: int
    total_missing_fields: int
    portfolio_completeness: float    # weighted average
    portfolio_confidence: str


class C5AIStatusSnap(BaseModel):
    freshness: str
    last_run_at: Optional[str] = None
    data_mode: str
    pipeline_ran: bool


class InputsAuditReport(BaseModel):
    report_type: str = "input_data_audit"
    generated_at: str
    operator: str
    c5ai_status: C5AIStatusSnap
    domain_coverage: Dict[str, DomainCoverage]
    sites: List[SiteAudit]
    summary: AuditSummary
    model_limitations: List[str]


# ─────────────────────────────────────────────────────────────────────────────
# Per-site quality data (demo — mirrors mockInputsData.js MOCK_DATA_QUALITY)
# ─────────────────────────────────────────────────────────────────────────────

_SITE_QUALITY: List[dict] = [
    {
        "site_id": "DEMO_OP_S01",
        "site_name": "Frohavet North",
        "fjord_exposure": "open_coast",
        "overall_completeness": 0.61,
        "overall_confidence": "medium",
        "risk_types": {
            "hab":                  {"source":"simulated","completeness":0.72,"confidence":"medium","flag":"LIMITED",   "n_obs":12,"missing_fields":["chlorophyll_history","algae_species"]},
            "lice":                 {"source":"simulated","completeness":0.85,"confidence":"high",  "flag":"SUFFICIENT","n_obs":15,"missing_fields":[]},
            "jellyfish":            {"source":"simulated","completeness":0.45,"confidence":"low",   "flag":"POOR",      "n_obs": 8,"missing_fields":["current_data","bloom_index","species_id"]},
            "pathogen":             {"source":"simulated","completeness":0.61,"confidence":"medium","flag":"LIMITED",   "n_obs":11,"missing_fields":["pcr_results","mortality_records"]},
            "mooring_failure":      {"source":"real",     "completeness":0.58,"confidence":"medium","flag":"LIMITED",   "n_obs": 9,"missing_fields":["anchor_tensile_test","corrosion_survey"]},
            "net_integrity":        {"source":"real",     "completeness":0.80,"confidence":"high",  "flag":"SUFFICIENT","n_obs":14,"missing_fields":[]},
            "cage_structural":      {"source":"estimated","completeness":0.42,"confidence":"low",   "flag":"POOR",      "n_obs": 6,"missing_fields":["deformation_log","load_cell_data"]},
            "deformation":          {"source":"estimated","completeness":0.45,"confidence":"low",   "flag":"POOR",      "n_obs": 7,"missing_fields":["load_cell_data","deformation_log"]},
            "anchor_deterioration": {"source":"real",     "completeness":0.55,"confidence":"medium","flag":"LIMITED",   "n_obs": 8,"missing_fields":["tensile_test"]},
            "oxygen_stress":        {"source":"real",     "completeness":0.78,"confidence":"high",  "flag":"SUFFICIENT","n_obs":18,"missing_fields":[]},
            "temperature_extreme":  {"source":"simulated","completeness":0.88,"confidence":"high",  "flag":"SUFFICIENT","n_obs":20,"missing_fields":[]},
            "current_storm":        {"source":"real",     "completeness":0.65,"confidence":"medium","flag":"LIMITED",   "n_obs":10,"missing_fields":["wave_buoy_data"]},
            "ice":                  {"source":"estimated","completeness":0.40,"confidence":"low",   "flag":"POOR",      "n_obs": 5,"missing_fields":["sea_level_gauge","ice_forecast"]},
            "exposure_anomaly":     {"source":"estimated","completeness":0.38,"confidence":"low",   "flag":"POOR",      "n_obs": 4,"missing_fields":["current_meter","exposure_model"]},
            "human_error":          {"source":"estimated","completeness":0.45,"confidence":"low",   "flag":"POOR",      "n_obs": 5,"missing_fields":["incident_reports","training_records"]},
            "procedure_failure":    {"source":"estimated","completeness":0.50,"confidence":"medium","flag":"LIMITED",   "n_obs": 7,"missing_fields":["procedure_audit_log"]},
            "equipment_failure":    {"source":"estimated","completeness":0.55,"confidence":"medium","flag":"LIMITED",   "n_obs": 8,"missing_fields":["maintenance_log","failure_history"]},
            "incident":             {"source":"estimated","completeness":0.52,"confidence":"medium","flag":"LIMITED",   "n_obs": 8,"missing_fields":["near_miss_reports"]},
            "maintenance_backlog":  {"source":"real",     "completeness":0.72,"confidence":"medium","flag":"SUFFICIENT","n_obs":12,"missing_fields":[]},
        },
    },
    {
        "site_id": "DEMO_OP_S02",
        "site_name": "Sunndalsfjord",
        "fjord_exposure": "semi_exposed",
        "overall_completeness": 0.74,
        "overall_confidence": "medium",
        "risk_types": {
            "hab":                  {"source":"simulated","completeness":0.78,"confidence":"high",  "flag":"SUFFICIENT","n_obs":14,"missing_fields":["algae_species"]},
            "lice":                 {"source":"simulated","completeness":0.88,"confidence":"high",  "flag":"SUFFICIENT","n_obs":16,"missing_fields":[]},
            "jellyfish":            {"source":"simulated","completeness":0.42,"confidence":"low",   "flag":"POOR",      "n_obs": 7,"missing_fields":["current_data","bloom_index","species_id"]},
            "pathogen":             {"source":"simulated","completeness":0.65,"confidence":"medium","flag":"LIMITED",   "n_obs":12,"missing_fields":["pcr_results"]},
            "mooring_failure":      {"source":"real",     "completeness":0.78,"confidence":"high",  "flag":"SUFFICIENT","n_obs":14,"missing_fields":[]},
            "net_integrity":        {"source":"real",     "completeness":0.90,"confidence":"high",  "flag":"SUFFICIENT","n_obs":18,"missing_fields":[]},
            "cage_structural":      {"source":"real",     "completeness":0.72,"confidence":"medium","flag":"SUFFICIENT","n_obs":12,"missing_fields":["load_cell_data"]},
            "deformation":          {"source":"real",     "completeness":0.75,"confidence":"high",  "flag":"SUFFICIENT","n_obs":13,"missing_fields":[]},
            "anchor_deterioration": {"source":"real",     "completeness":0.80,"confidence":"high",  "flag":"SUFFICIENT","n_obs":15,"missing_fields":[]},
            "oxygen_stress":        {"source":"simulated","completeness":0.82,"confidence":"high",  "flag":"SUFFICIENT","n_obs":18,"missing_fields":[]},
            "temperature_extreme":  {"source":"simulated","completeness":0.85,"confidence":"high",  "flag":"SUFFICIENT","n_obs":18,"missing_fields":[]},
            "current_storm":        {"source":"simulated","completeness":0.70,"confidence":"medium","flag":"SUFFICIENT","n_obs":12,"missing_fields":[]},
            "ice":                  {"source":"estimated","completeness":0.62,"confidence":"medium","flag":"LIMITED",   "n_obs": 9,"missing_fields":["ice_forecast"]},
            "exposure_anomaly":     {"source":"estimated","completeness":0.58,"confidence":"medium","flag":"LIMITED",   "n_obs": 8,"missing_fields":["current_meter"]},
            "human_error":          {"source":"real",     "completeness":0.75,"confidence":"medium","flag":"SUFFICIENT","n_obs":13,"missing_fields":["training_records"]},
            "procedure_failure":    {"source":"real",     "completeness":0.78,"confidence":"high",  "flag":"SUFFICIENT","n_obs":14,"missing_fields":[]},
            "equipment_failure":    {"source":"real",     "completeness":0.80,"confidence":"high",  "flag":"SUFFICIENT","n_obs":15,"missing_fields":[]},
            "incident":             {"source":"real",     "completeness":0.78,"confidence":"high",  "flag":"SUFFICIENT","n_obs":14,"missing_fields":[]},
            "maintenance_backlog":  {"source":"real",     "completeness":0.82,"confidence":"high",  "flag":"SUFFICIENT","n_obs":16,"missing_fields":[]},
        },
    },
    {
        "site_id": "DEMO_OP_S03",
        "site_name": "Storfjorden South",
        "fjord_exposure": "sheltered",
        "overall_completeness": 0.83,
        "overall_confidence": "high",
        "risk_types": {
            "hab":                  {"source":"simulated","completeness":0.82,"confidence":"high",  "flag":"SUFFICIENT","n_obs":15,"missing_fields":[]},
            "lice":                 {"source":"simulated","completeness":0.90,"confidence":"high",  "flag":"SUFFICIENT","n_obs":17,"missing_fields":[]},
            "jellyfish":            {"source":"simulated","completeness":0.48,"confidence":"low",   "flag":"POOR",      "n_obs": 9,"missing_fields":["bloom_index","species_id"]},
            "pathogen":             {"source":"simulated","completeness":0.70,"confidence":"medium","flag":"LIMITED",   "n_obs":13,"missing_fields":["pcr_results"]},
            "mooring_failure":      {"source":"real",     "completeness":0.92,"confidence":"high",  "flag":"SUFFICIENT","n_obs":18,"missing_fields":[]},
            "net_integrity":        {"source":"real",     "completeness":0.95,"confidence":"high",  "flag":"SUFFICIENT","n_obs":20,"missing_fields":[]},
            "cage_structural":      {"source":"real",     "completeness":0.88,"confidence":"high",  "flag":"SUFFICIENT","n_obs":16,"missing_fields":[]},
            "deformation":          {"source":"real",     "completeness":0.88,"confidence":"high",  "flag":"SUFFICIENT","n_obs":16,"missing_fields":[]},
            "anchor_deterioration": {"source":"real",     "completeness":0.90,"confidence":"high",  "flag":"SUFFICIENT","n_obs":18,"missing_fields":[]},
            "oxygen_stress":        {"source":"real",     "completeness":0.92,"confidence":"high",  "flag":"SUFFICIENT","n_obs":22,"missing_fields":[]},
            "temperature_extreme":  {"source":"real",     "completeness":0.90,"confidence":"high",  "flag":"SUFFICIENT","n_obs":22,"missing_fields":[]},
            "current_storm":        {"source":"real",     "completeness":0.80,"confidence":"high",  "flag":"SUFFICIENT","n_obs":15,"missing_fields":[]},
            "ice":                  {"source":"estimated","completeness":0.72,"confidence":"medium","flag":"SUFFICIENT","n_obs":12,"missing_fields":[]},
            "exposure_anomaly":     {"source":"estimated","completeness":0.68,"confidence":"medium","flag":"LIMITED",   "n_obs":10,"missing_fields":["current_meter"]},
            "human_error":          {"source":"real",     "completeness":0.88,"confidence":"high",  "flag":"SUFFICIENT","n_obs":16,"missing_fields":[]},
            "procedure_failure":    {"source":"real",     "completeness":0.90,"confidence":"high",  "flag":"SUFFICIENT","n_obs":18,"missing_fields":[]},
            "equipment_failure":    {"source":"real",     "completeness":0.92,"confidence":"high",  "flag":"SUFFICIENT","n_obs":18,"missing_fields":[]},
            "incident":             {"source":"real",     "completeness":0.88,"confidence":"high",  "flag":"SUFFICIENT","n_obs":16,"missing_fields":[]},
            "maintenance_backlog":  {"source":"real",     "completeness":0.90,"confidence":"high",  "flag":"SUFFICIENT","n_obs":18,"missing_fields":[]},
        },
    },
]


_DOMAIN_COVERAGE: Dict[str, dict] = {
    "biological": {
        "source": "c5ai_plus",
        "model": "C5AI+ MultiDomainEngine (biologisk domain)",
        "note": (
            "Biologisk domene er informert av C5AI+-prognose når C5AI+ er kjørt og "
            "frisk. Risikotyper: HAB, lakselus, manet, patogen."
        ),
    },
    "structural": {
        "source": "estimated",
        "model": "Stub-modell (ekspertprioritet)",
        "note": (
            "Strukturell domene bruker hardkodede subfraksjoner basert på ekspertvurdering. "
            "Ingen live-datamodell. Risikotyper: mooring_failure (35%), net_integrity (30%), "
            "cage_structural (25%), feed_system (10%)."
        ),
    },
    "environmental": {
        "source": "estimated",
        "model": "Stub-modell (ekspertprioritet)",
        "note": (
            "Miljødomene bruker hardkodede subfraksjoner. Risikotyper: oxygen_stress, "
            "temperature_extreme, current_storm, ice, exposure_anomaly."
        ),
    },
    "operational": {
        "source": "estimated",
        "model": "Stub-modell (ekspertprioritet)",
        "note": (
            "Operasjonelt domene bruker hardkodede subfraksjoner. Risikotyper: "
            "human_error, procedure_failure, equipment_failure, incident, maintenance_backlog."
        ),
    },
}


_MODEL_LIMITATIONS: List[str] = [
    "Kun biologisk domene er C5AI+-informert. Strukturell, miljø og operasjonell bruker "
    "stub-estimater basert på ekspertprioritet — ikke kalibrert mot anleggsdata.",
    "Per-anlegg domenebryting er porteføljebasert (proporsjonal approksimering). "
    "Faktisk domeneprofil per anlegg kan avvike, særlig for åpen kyst vs. skjermet fjord.",
    "SCR-bidrag per anlegg er proporsjonal allokering av portefølje-SCR — ikke et "
    "selvstendig anleggsspesifikt SCR-estimat.",
    "Risikoparametere (frekvens, alvorlighetsgrad) er skalert fra template-data "
    "(Nordic Aqua Partners AS). Operatørspesifikke faktorer er ikke fullt ut kalibrert.",
    "C5AI+-prognose dekker kun sjøanlegg. Settefisk-lokaliteter har ingen C5AI+-modell.",
    "Alle data i denne rapporten er simulert demodata. Faktiske verdier krever "
    "integrasjon mot BarentsWatch, Seacloud eller operatørens egne sensordata.",
]


# ─────────────────────────────────────────────────────────────────────────────
# Endpoint
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/audit", response_model=InputsAuditReport)
def get_inputs_audit() -> InputsAuditReport:
    """
    Return the Input Data Audit Report.

    Combines live C5AI+ freshness state with per-site quality metrics
    for the three demo operator sites.
    """
    from backend.services import c5ai_state
    from backend.services.c5ai_state import get_run_extra

    state = c5ai_state.get_status()
    extra = get_run_extra()

    c5ai_snap = C5AIStatusSnap(
        freshness=state.get("freshness", "missing"),
        last_run_at=state.get("c5ai_last_run_at"),
        data_mode=extra.get("data_mode", "simulated"),
        pipeline_ran=bool(extra),
    )

    # Update biological domain source based on live C5AI+ freshness
    domain_coverage = {}
    for domain, cfg in _DOMAIN_COVERAGE.items():
        source = cfg["source"]
        if domain == "biological" and state.get("freshness") == "missing":
            source = "estimated"
        domain_coverage[domain] = DomainCoverage(
            source=source,
            model=cfg["model"],
            note=cfg["note"],
        )

    # Build site audit entries
    sites: List[SiteAudit] = []
    all_flags: List[str] = []
    all_missing: List[str] = []
    completeness_values: List[float] = []

    for sq in _SITE_QUALITY:
        rt_map: Dict[str, RiskTypeAudit] = {}
        for rt_key, rt in sq["risk_types"].items():
            rt_map[rt_key] = RiskTypeAudit(**rt)
            all_flags.append(rt["flag"])
            all_missing.extend(rt["missing_fields"])

        sites.append(SiteAudit(
            site_id=sq["site_id"],
            site_name=sq["site_name"],
            fjord_exposure=sq["fjord_exposure"],
            overall_completeness=sq["overall_completeness"],
            overall_confidence=sq["overall_confidence"],
            risk_types=rt_map,
        ))
        completeness_values.append(sq["overall_completeness"])

    summary = AuditSummary(
        total_sites=len(sites),
        total_risk_types_assessed=len(all_flags),
        sufficient_count=all_flags.count("SUFFICIENT"),
        limited_count=all_flags.count("LIMITED"),
        poor_count=all_flags.count("POOR"),
        total_missing_fields=len(all_missing),
        portfolio_completeness=round(sum(completeness_values) / len(completeness_values), 3),
        portfolio_confidence="medium",
    )

    return InputsAuditReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        operator="Nordic Aqua Partners AS (demo)",
        c5ai_status=c5ai_snap,
        domain_coverage=domain_coverage,
        sites=sites,
        summary=summary,
        model_limitations=_MODEL_LIMITATIONS,
    )
