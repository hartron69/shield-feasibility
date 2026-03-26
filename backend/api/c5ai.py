"""
C5AI+ API endpoints — freshness gate, pipeline trigger, and BarentsWatch prefetch.

POST /api/c5ai/run
    Trigger the C5AI+ biological forecast pipeline.
    Uses live BarentsWatch data when available (luse/sykdom files in BW_DATA_DIR),
    otherwise falls back to demo data.
    Records run_id and c5ai_vs_static_ratio in in-memory state.

GET /api/c5ai/status
    Return current C5AI+ freshness status (fresh / stale / missing).

POST /api/c5ai/inputs/updated
    Notify the backend that operator inputs have changed since the last run.

POST /api/c5ai/prefetch
    Trigger the BarentsWatch fetcher to refresh luse/sykdom data for the
    configured operator (Kornstad Havbruk AS by default).
    Runs in the background — returns immediately with job metadata.
"""

from __future__ import annotations

import os
import sys
import threading
from typing import Optional

from fastapi import APIRouter, BackgroundTasks

from backend.schemas import C5AIRunResponse, C5AIStatusResponse
from backend.services import c5ai_state

router = APIRouter(prefix="/api/c5ai", tags=["c5ai"])


# ─────────────────────────────────────────────────────────────────────────────
# Biological pipeline (ForecastPipeline)
# ─────────────────────────────────────────────────────────────────────────────

def _build_demo_operator_input():
    """
    Build a minimal C5AIOperatorInput for the three demo sites.
    No historical observations — all forecasters run in prior mode.
    """
    from c5ai_plus.data_models.biological_input import (
        C5AIOperatorInput,
        SiteMetadata,
    )
    sites = [
        SiteMetadata(
            site_id="DEMO_OP_S01",
            site_name="Frohavet North",
            latitude=63.5,
            longitude=8.2,
            species="Atlantic Salmon",
            biomass_tonnes=3200,
            biomass_value_nok=208_000_000,
            fjord_exposure="open_coast",
        ),
        SiteMetadata(
            site_id="DEMO_OP_S02",
            site_name="Sunndalsfjord",
            latitude=62.7,
            longitude=8.6,
            species="Atlantic Salmon",
            biomass_tonnes=3500,
            biomass_value_nok=227_500_000,
            fjord_exposure="semi_exposed",
        ),
        SiteMetadata(
            site_id="DEMO_OP_S03",
            site_name="Storfjorden South",
            latitude=62.1,
            longitude=7.1,
            species="Atlantic Salmon",
            biomass_tonnes=2500,
            biomass_value_nok=162_500_000,
            fjord_exposure="sheltered",
        ),
    ]
    return C5AIOperatorInput(
        operator_id="DEMO_OP",
        operator_name="Nordic Aqua Partners AS",
        sites=sites,
    )


def _run_bio_pipeline(operator_input, static_loss_nok: float = 22_600_000) -> dict:
    """
    Run ForecastPipeline with the given C5AIOperatorInput.
    Returns a metadata dict on success, raises on failure.
    """
    from c5ai_plus.pipeline import ForecastPipeline
    pipeline = ForecastPipeline(verbose=False)
    forecast = pipeline.run(operator_input, static_mean_annual_loss=static_loss_nok)
    agg = forecast.operator_aggregate
    meta = forecast.metadata
    return {
        "site_ids":            [sf.site_id for sf in forecast.site_forecasts],
        "site_names":          [sf.site_name for sf in forecast.site_forecasts],
        "site_count":          len(forecast.site_forecasts),
        "c5ai_vs_static_ratio": round(agg.c5ai_vs_static_ratio, 4),
        "total_expected_annual_loss_nok": round(agg.total_expected_annual_loss, 0),
        "overall_quality":     meta.overall_data_quality,
        "overall_confidence":  meta.overall_confidence,
        "pipeline_ran":        True,
    }


def _run_c5ai_pipeline_safe() -> dict:
    """
    Run the C5AI+ biological pipeline.

    Priority:
      1. BarentsWatch live data  → real luce/sykdom observations, data_mode="real"
      2. Demo SiteMetadata       → prior mode, data_mode="simulated"
      3. Stub fallback           → on any exception, pipeline_ran=False

    Returns a metadata dict consumed by run_c5ai().
    """
    # ── Try BarentsWatch data first ──────────────────────────────────────────
    try:
        from c5ai_plus.Barentswatch.bw_to_c5ai_adapter import (
            bw_data_available,
            bw_data_to_operator_input,
        )
        if bw_data_available():
            op = bw_data_to_operator_input()
            result = _run_bio_pipeline(op)
            result["data_mode"] = "real"
            result["source"] = "barentswatch"
            result["message"] = (
                f"C5AI+ pipeline kjørt med BarentsWatch-data "
                f"({result['site_count']} lokaliteter, "
                f"kvalitet: {result['overall_quality']})"
            )
            return result
    except Exception as bw_exc:
        pass  # fall through to demo

    # ── Demo SiteMetadata (prior mode) ───────────────────────────────────────
    try:
        op = _build_demo_operator_input()
        result = _run_bio_pipeline(op)
        result["data_mode"] = "simulated"
        result["source"] = "demo"
        result["message"] = "C5AI+ pipeline kjørt med demo-data (prior-modus)"
        return result
    except Exception as demo_exc:
        pass  # fall through to stub

    # ── Stub fallback ─────────────────────────────────────────────────────────
    return {
        "site_ids":            ["DEMO_OP_S01", "DEMO_OP_S02", "DEMO_OP_S03"],
        "site_names":          ["Frohavet North", "Sunndalsfjord", "Storfjorden South"],
        "site_count":          3,
        "c5ai_vs_static_ratio": 1.0,
        "total_expected_annual_loss_nok": 0.0,
        "overall_quality":     "POOR",
        "overall_confidence":  "low",
        "pipeline_ran":        False,
        "data_mode":           "simulated",
        "source":              "stub",
        "message":             "C5AI+ pipeline stub — feil i pipeline",
    }


# ─────────────────────────────────────────────────────────────────────────────
# BarentsWatch prefetch
# ─────────────────────────────────────────────────────────────────────────────

# Thread-safe prefetch status
_prefetch_lock = threading.Lock()
_prefetch_status: dict = {"running": False, "last_result": None}


def _run_prefetch_background() -> None:
    """
    Background task: run the BarentsWatch fetcher and save files to BW_DATA_DIR.
    Called from BackgroundTasks — must not raise.
    """
    global _prefetch_status
    with _prefetch_lock:
        _prefetch_status["running"] = True

    try:
        from c5ai_plus.Barentswatch.bw_config import BW_DATA_DIR, FETCHER_PATH
        import subprocess

        env = os.environ.copy()
        env["BW_OUTPUT_DIR"] = str(BW_DATA_DIR)

        proc = subprocess.run(
            [sys.executable, str(FETCHER_PATH)],
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
        )

        from c5ai_plus.Barentswatch.bw_to_c5ai_adapter import bw_quality_summary
        summary = bw_quality_summary()
        result = {
            "ok":        proc.returncode == 0,
            "returncode": proc.returncode,
            "summary":   summary,
            "stderr_tail": proc.stderr[-500:] if proc.stderr else "",
        }
    except Exception as exc:
        result = {"ok": False, "error": str(exc)}
    finally:
        with _prefetch_lock:
            _prefetch_status["running"] = False
            _prefetch_status["last_result"] = result


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/run", response_model=C5AIRunResponse)
def run_c5ai() -> C5AIRunResponse:
    """
    Trigger the C5AI+ analysis pipeline and record the run timestamp.

    Uses live BarentsWatch data when available; falls back to demo prior-mode.
    Stores c5ai_vs_static_ratio in run_extra so feasibility can reference it.
    """
    run_meta = _run_c5ai_pipeline_safe()

    from backend.services.c5ai_state import store_run_extra
    store_run_extra({
        "site_ids":              run_meta["site_ids"],
        "site_names":            run_meta["site_names"],
        "data_mode":             run_meta["data_mode"],
        "source":                run_meta.get("source", "demo"),
        "domains_used":          ["biological", "structural", "environmental", "operational"],
        "risk_type_count":       15,
        "c5ai_vs_static_ratio":  run_meta["c5ai_vs_static_ratio"],
        "overall_quality":       run_meta["overall_quality"],
        "source_labels": (
            [f"BarentsWatch v2/v3 ({run_meta['overall_quality']})"]
            if run_meta.get("source") == "barentswatch"
            else ["Simulert — demo data (prior-modus)"]
        ),
    })

    run_id, run_at = c5ai_state.record_c5ai_run()
    status = c5ai_state.get_status()

    return C5AIRunResponse(
        run_id=run_id,
        generated_at=run_at.isoformat(),
        status="ok" if run_meta["pipeline_ran"] else "stub",
        site_count=run_meta["site_count"],
        domain_count=4,
        risk_type_count=15,
        pipeline_ran=run_meta["pipeline_ran"],
        message=run_meta["message"],
        freshness=status["freshness"],
    )


@router.get("/status", response_model=C5AIStatusResponse)
def get_c5ai_status() -> C5AIStatusResponse:
    """Return the current C5AI+ freshness status."""
    s = c5ai_state.get_status()
    return C5AIStatusResponse(
        run_id=s["run_id"],
        c5ai_last_run_at=s["c5ai_last_run_at"],
        inputs_last_updated_at=s["inputs_last_updated_at"],
        is_fresh=s["is_fresh"],
        freshness=s["freshness"],
    )


@router.post("/inputs/updated")
def inputs_updated() -> dict:
    """
    Notify the backend that operator inputs have changed.
    Marks the C5AI+ analysis as stale if it has not been re-run since.
    """
    ts = c5ai_state.mark_inputs_updated()
    status = c5ai_state.get_status()
    return {
        "inputs_last_updated_at": ts.isoformat(),
        "freshness": status["freshness"],
    }


@router.post("/prefetch")
def prefetch_barentswatch(background_tasks: BackgroundTasks) -> dict:
    """
    Trigger a background BarentsWatch data fetch for the configured operator.

    Runs the fetcher script (barentswatch_c5ai_fetcher_2.0.py) as a subprocess
    with BW_OUTPUT_DIR pointing to BW_DATA_DIR.  Returns immediately — the
    actual download takes ~60–120 s depending on API response times.

    Requires BW_CLIENT_SECRET to be set as an environment variable.
    """
    with _prefetch_lock:
        if _prefetch_status["running"]:
            return {
                "status": "already_running",
                "message": "En henting kjører allerede. Prøv igjen om litt.",
            }

    if not os.getenv("BW_CLIENT_SECRET"):
        return {
            "status": "error",
            "message": "BW_CLIENT_SECRET miljøvariabel er ikke satt. Sett den og prøv igjen.",
        }

    background_tasks.add_task(_run_prefetch_background)

    from c5ai_plus.Barentswatch.bw_config import DEFAULT_OPERATOR_CFG
    return {
        "status":    "started",
        "message":   (
            f"Henter data fra BarentsWatch for "
            f"{DEFAULT_OPERATOR_CFG['operator_name']} "
            f"({len(DEFAULT_OPERATOR_CFG['localities'])} lokaliteter). "
            "Kjør POST /api/c5ai/run etter at hentingen er ferdig."
        ),
        "operator":  DEFAULT_OPERATOR_CFG["operator_id"],
        "localities": [
            loc["localityNo"] for loc in DEFAULT_OPERATOR_CFG["localities"]
        ],
    }


@router.get("/prefetch/status")
def prefetch_status() -> dict:
    """Return the status of the last (or ongoing) BarentsWatch prefetch."""
    with _prefetch_lock:
        return {
            "running":     _prefetch_status["running"],
            "last_result": _prefetch_status["last_result"],
        }


@router.get("/site-registry")
def site_registry_endpoint() -> dict:
    """Return the full BW locality <-> Shield site_id mapping with BW coverage info."""
    from backend.services.site_registry import get_registry_summary
    summary = get_registry_summary()
    try:
        from c5ai_plus.Barentswatch.bw_to_c5ai_adapter import bw_quality_summary
        quality = bw_quality_summary()
        quality_by_site = {s["site_id"]: s for s in quality.get("sites", [])}
        for site in summary["sites"]:
            sid = site["site_id"]
            if sid in quality_by_site:
                q = quality_by_site[sid]
                site["bw_data_quality"] = q.get("data_quality_flag", "UNKNOWN")
                site["bw_reported_weeks"] = q.get("reported_weeks", 0)
                site["bw_c5ai_scale"] = q.get("c5ai_scale")
            else:
                site["bw_data_quality"] = "NO_DATA"
                site["bw_reported_weeks"] = 0
                site["bw_c5ai_scale"] = None
    except Exception:
        pass
    return summary


@router.get("/bw/data-status")
def bw_data_status() -> dict:
    """Return a quality summary of the current BarentsWatch data files."""
    try:
        from c5ai_plus.Barentswatch.bw_to_c5ai_adapter import (
            bw_data_available,
            bw_quality_summary,
        )
        available = bw_data_available()
        if not available:
            return {"available": False, "message": "Ingen BarentsWatch-data funnet i data-katalogen."}
        return {"available": True, **bw_quality_summary()}
    except Exception as exc:
        return {"available": False, "error": str(exc)}
