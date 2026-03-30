"""
Shield Risk Platform – ScenarioEngine

Runs parametric Monte Carlo scenarios for sea-based and smolt/RAS operators.
Replaces the client-side stub in ScenarioOverridePanel.jsx.

Sprint S6 additions:
- ScenarioParameters: unified parameter struct for sea and smolt scenarios
- ScenarioFacilityResult: per-facility result with loss breakdown
- ScenarioResult: group-level result with narrative
- ScenarioEngine: orchestrates MC runs, compares to baseline

Sea mapping rules
-----------------
lice_pressure_index > 1.5 → +40 % frequency per unit above 1.0
exposure_factor > 1.2     → severity scaled proportionally
operational_factor        → linear frequency scaling
total_biomass_override    → TIV-proportional severity scaling
dissolved_oxygen < 7.0    → +50 % severity (biological domain)

Smolt / RAS mapping rules
--------------------------
ras_failure_multiplier    → frequency multiplied directly
oxygen_level_mg_l < 6.0  → ×3.5 severity + ×2.0 frequency (crisis)
power_backup_hours < 4    → ×1.8 frequency (insufficient backup)
affected_facility_index   → None = all facilities; 0..N-1 = single facility

Diversification (smolt group)
------------------------------
Separate sites have low inter-facility correlation (0.10).  A conservative
17% diversification discount is applied at group level.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from data.input_schema import OperatorInput
from models.monte_carlo import MonteCarloEngine
from models.smolt_loss_categories import SMOLT_LOSS_CATEGORIES
from models.sea_loss_categories import SEA_LOSS_CATEGORIES, get_shares_for_exposure


# ─────────────────────────────────────────────────────────────────────────────
# Parameter and result dataclasses
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ScenarioParameters:
    """
    Unified parameter structure for both facility types.
    Sea operators use biomass/lice/exposure fields.
    Smolt operators use ras/power/oxygen fields.
    Omitted (None) fields leave the baseline unchanged.
    """
    # Sea parameters (existing sliders)
    total_biomass_override:   Optional[float] = None
    dissolved_oxygen_mg_l:    Optional[float] = None
    nitrate_umol_l:           Optional[float] = None
    lice_pressure_index:      Optional[float] = None
    exposure_factor:          Optional[float] = None
    operational_factor:       Optional[float] = None

    # Smolt / RAS parameters (new)
    ras_failure_multiplier:   Optional[float] = None  # 1.0 = baseline
    power_backup_hours:       Optional[float] = None  # available backup hours
    oxygen_level_mg_l:        Optional[float] = None  # actual O₂ level

    # Which facility is affected (0-based index; None = all)
    affected_facility_index:  Optional[int] = None

    # Preset label for logging
    preset_id:    Optional[str] = None
    facility_type: str = "sea"


@dataclass
class ScenarioFacilityResult:
    facility_name:          str
    baseline_expected_loss: float
    scenario_expected_loss: float
    change_pct:             float
    var_99_5_baseline:      float
    var_99_5_scenario:      float
    highest_risk_driver:    str
    loss_by_category:       Dict[str, float] = field(default_factory=dict)


@dataclass
class ScenarioResult:
    preset_id:           str
    facility_type:       str
    # Group level
    baseline_total_loss: float
    scenario_total_loss: float
    total_change_pct:    float
    # Per-facility breakdown
    facility_results:    List[ScenarioFacilityResult]
    # Summary
    highest_risk_driver: str
    narrative:           str


# ─────────────────────────────────────────────────────────────────────────────
# Engine
# ─────────────────────────────────────────────────────────────────────────────

class ScenarioEngine:
    """Runs parametric Monte Carlo scenarios and returns ScenarioResult."""

    DIVERSIFICATION_FACTOR: float = 0.83  # 17% group diversification discount

    def run(
        self,
        base_op_input: OperatorInput,
        params: ScenarioParameters,
        baseline_simulation=None,
        facility_inputs: Optional[List[OperatorInput]] = None,
        site_inputs: Optional[List[OperatorInput]] = None,
    ) -> ScenarioResult:
        """
        Run a scenario and return ScenarioResult.

        Parameters
        ----------
        base_op_input:
            Group-level OperatorInput (always required).
        params:
            Scenario parameters.
        baseline_simulation:
            Pre-computed baseline SimulationResults (optional; re-run if None).
        facility_inputs:
            Per-facility OperatorInput list for smolt multi-facility breakdown.
            Required when params.facility_type == "smolt".
        site_inputs:
            Per-site OperatorInput list for sea multi-site breakdown.
            When provided, enables per-site loss breakdown with diversification.
        """
        if params.facility_type == "smolt":
            return self._run_smolt(base_op_input, params, baseline_simulation, facility_inputs)
        return self._run_sea(base_op_input, params, baseline_simulation, site_inputs=site_inputs)

    # ── Sea ──────────────────────────────────────────────────────────────────

    def _run_sea(self, group_op_input, params, baseline_sim, site_inputs=None):
        """Dispatch to per-site or single-unit sea scenario."""
        if not site_inputs:
            return self._run_sea_single(group_op_input, params, baseline_sim)
        return self._run_sea_multi(group_op_input, params, baseline_sim, site_inputs)

    def _run_sea_single(
        self,
        op_input: OperatorInput,
        params: ScenarioParameters,
        baseline_sim,
    ) -> ScenarioResult:
        """Adjust sea MC parameters and compare to baseline."""
        # Baseline (re-run if not supplied)
        if baseline_sim is None:
            baseline_sim = MonteCarloEngine(op_input).run()
        baseline_loss = baseline_sim.mean_annual_loss

        # Scenario run
        adjusted = self._adjust_sea_params(op_input, params)
        scenario_sim = MonteCarloEngine(adjusted).run()
        scenario_loss = scenario_sim.mean_annual_loss

        change_pct = _pct_change(baseline_loss, scenario_loss)
        driver = self._dominant_sea_driver(params)

        fac_result = ScenarioFacilityResult(
            facility_name          = op_input.name,
            baseline_expected_loss = baseline_loss,
            scenario_expected_loss = scenario_loss,
            change_pct             = change_pct,
            var_99_5_baseline      = baseline_sim.var_995,
            var_99_5_scenario      = scenario_sim.var_995,
            highest_risk_driver    = driver,
            loss_by_category       = {},
        )

        return ScenarioResult(
            preset_id           = params.preset_id or "custom",
            facility_type       = "sea",
            baseline_total_loss = baseline_loss,
            scenario_total_loss = scenario_loss,
            total_change_pct    = change_pct,
            facility_results    = [fac_result],
            highest_risk_driver = driver,
            narrative           = self._build_sea_narrative(params, change_pct, driver),
        )

    def _run_sea_multi(self, group_op_input, params, baseline_sim, site_inputs):
        """
        Sea: run MC per site, sum with sea-level diversification (0.89).
        """
        SEA_DIVERSIFICATION = 0.89

        # Total portfolio biomass — needed to scale total_biomass_override per site
        portfolio_biomass = sum(
            sum(s.biomass_tonnes for s in op.sites)
            for op in site_inputs
        ) or 1.0

        results = []
        total_baseline = 0.0
        total_scenario = 0.0

        for i, site_op in enumerate(site_inputs):
            is_affected = (
                params.affected_facility_index is None
                or params.affected_facility_index == i
            )

            # Use a per-site fixed seed so baseline and scenario draws are identical;
            # any change_pct then reflects only the parametric adjustment, not noise.
            site_seed = 42 + i
            sim_base  = MonteCarloEngine(site_op, seed=site_seed).run()
            base_loss = sim_base.mean_annual_loss

            if is_affected:
                # Scale total_biomass_override from portfolio level to per-site level so
                # that ratio = override_total/baseline_total (not override_total/site_biomass).
                from dataclasses import replace as _dc_replace
                site_biomass = sum(s.biomass_tonnes for s in site_op.sites) or 1.0
                biomass_ratio = (
                    (params.total_biomass_override / portfolio_biomass)
                    if params.total_biomass_override is not None else 1.0
                )
                if params.total_biomass_override is not None:
                    site_override = site_biomass * biomass_ratio
                    site_params = _dc_replace(params, total_biomass_override=site_override)
                else:
                    site_params = params

                # Skip MC re-run when no parameter would actually change the baseline.
                # This avoids deepcopy floating-point drift giving spurious non-zero change.
                effective_change = (
                    (params.lice_pressure_index is not None and params.lice_pressure_index > 1.5) or
                    (params.exposure_factor is not None and params.exposure_factor > 1.2) or
                    (params.operational_factor is not None and abs(params.operational_factor - 1.0) > 0.03) or
                    (params.dissolved_oxygen_mg_l is not None and params.dissolved_oxygen_mg_l < 7.0) or
                    abs(biomass_ratio - 1.0) > 0.001
                )

                if effective_change:
                    adjusted  = self._adjust_sea_params(site_op, site_params)
                    sim_scen  = MonteCarloEngine(adjusted, seed=site_seed).run()
                    scen_loss = sim_scen.mean_annual_loss
                    var_scen  = sim_scen.var_995
                else:
                    scen_loss = base_loss
                    var_scen  = sim_base.var_995
            else:
                scen_loss = base_loss
                var_scen  = sim_base.var_995

            change_pct = _pct_change(base_loss, scen_loss)

            site_profile = getattr(site_op, "site_profile", None)
            exposure     = site_profile.exposure_category if site_profile else "semi_exposed"
            shares       = get_shares_for_exposure(exposure)
            cat_breakdown = {cat: scen_loss * share for cat, share in shares.items()}
            driver        = max(cat_breakdown, key=cat_breakdown.get) if cat_breakdown else "biological"

            results.append(ScenarioFacilityResult(
                facility_name          = site_op.name,
                baseline_expected_loss = base_loss,
                scenario_expected_loss = scen_loss,
                change_pct             = change_pct,
                var_99_5_baseline      = sim_base.var_995,
                var_99_5_scenario      = var_scen,
                highest_risk_driver    = driver,
                loss_by_category       = cat_breakdown,
            ))
            total_baseline += base_loss
            total_scenario += scen_loss

        # Apply diversification symmetrically to both baseline and scenario so that
        # the portfolio-level change_pct is not artificially distorted.
        total_baseline_adj = total_baseline * SEA_DIVERSIFICATION
        total_scenario_adj = total_scenario * SEA_DIVERSIFICATION
        group_change_pct   = _pct_change(total_baseline_adj, total_scenario_adj)

        group_driver = (
            max(results, key=lambda r: r.scenario_expected_loss).highest_risk_driver
            if results else "biological"
        )

        return ScenarioResult(
            preset_id           = params.preset_id or "custom",
            facility_type       = "sea",
            baseline_total_loss = total_baseline_adj,
            scenario_total_loss = total_scenario_adj,
            total_change_pct    = group_change_pct,
            facility_results    = results,
            highest_risk_driver = group_driver,
            narrative           = self._build_sea_narrative(params, group_change_pct, group_driver),
        )

    # ── Smolt ────────────────────────────────────────────────────────────────

    def _run_smolt(
        self,
        group_op_input: OperatorInput,
        params: ScenarioParameters,
        baseline_sim,
        facility_inputs: Optional[List[OperatorInput]],
    ) -> ScenarioResult:
        """
        Run per-facility MC for smolt.  Affected facility gets scenario params;
        others keep their baseline loss.  Group total has diversification applied.
        """
        facilities = facility_inputs or [group_op_input]
        results: List[ScenarioFacilityResult] = []
        total_baseline = 0.0
        total_scenario = 0.0

        for i, fac_input in enumerate(facilities):
            is_affected = (
                params.affected_facility_index is None
                or params.affected_facility_index == i
            )

            # Baseline MC for this facility
            sim_base = MonteCarloEngine(fac_input).run()
            base_loss = sim_base.mean_annual_loss

            if is_affected:
                adjusted = self._adjust_smolt_params(fac_input, params)
                sim_scen = MonteCarloEngine(adjusted).run()
                scen_loss = sim_scen.mean_annual_loss
                var_scen  = sim_scen.var_995
            else:
                scen_loss = base_loss
                var_scen  = sim_base.var_995

            change_pct = _pct_change(base_loss, scen_loss)

            # Category breakdown
            ftype     = getattr(fac_input, "facility_type", "smolt")
            share_key = "share_ras" if "ras" in str(ftype) else "share_flow"
            cat_breakdown = {
                cat_id: scen_loss * cat_data[share_key]
                for cat_id, cat_data in SMOLT_LOSS_CATEGORIES.items()
            }
            driver = max(cat_breakdown, key=cat_breakdown.get) if cat_breakdown else "operational"

            results.append(ScenarioFacilityResult(
                facility_name          = fac_input.name,
                baseline_expected_loss = base_loss,
                scenario_expected_loss = scen_loss,
                change_pct             = change_pct,
                var_99_5_baseline      = sim_base.var_995,
                var_99_5_scenario      = var_scen,
                highest_risk_driver    = driver,
                loss_by_category       = cat_breakdown,
            ))
            total_baseline += base_loss
            total_scenario += scen_loss

        # Apply diversification discount at group level
        total_scenario_adj = total_scenario * self.DIVERSIFICATION_FACTOR
        group_change_pct   = _pct_change(total_baseline, total_scenario_adj)

        group_driver = (
            max(results, key=lambda r: r.scenario_expected_loss).highest_risk_driver
            if results else "operational"
        )

        return ScenarioResult(
            preset_id           = params.preset_id or "custom",
            facility_type       = "smolt",
            baseline_total_loss = total_baseline,
            scenario_total_loss = total_scenario_adj,
            total_change_pct    = group_change_pct,
            facility_results    = results,
            highest_risk_driver = group_driver,
            narrative           = self._build_smolt_narrative(params, results, group_change_pct),
        )

    # ── Parameter adjustment helpers ─────────────────────────────────────────

    def _adjust_sea_params(self, op_input: OperatorInput, params: ScenarioParameters) -> OperatorInput:
        """Return a deepcopy of op_input with risk_params adjusted for sea scenario."""
        adjusted = deepcopy(op_input)
        rp = adjusted.risk_params

        if params.lice_pressure_index is not None and params.lice_pressure_index > 1.5:
            rp.expected_annual_events *= 1.0 + (params.lice_pressure_index - 1.0) * 0.40

        if params.exposure_factor is not None and params.exposure_factor > 1.2:
            rp.mean_loss_severity *= params.exposure_factor

        if params.operational_factor is not None and abs(params.operational_factor - 1.0) > 0.03:
            rp.expected_annual_events *= params.operational_factor

        if params.total_biomass_override is not None:
            baseline_biomass = sum(
                s.biomass_tonnes for s in adjusted.sites
            ) or 1
            ratio = params.total_biomass_override / baseline_biomass
            if abs(ratio - 1.0) > 0.001:  # skip trivial rounding
                rp.mean_loss_severity *= ratio

        if params.dissolved_oxygen_mg_l is not None and params.dissolved_oxygen_mg_l < 7.0:
            rp.mean_loss_severity *= 1.5

        return adjusted

    def _adjust_smolt_params(self, fac_input: OperatorInput, params: ScenarioParameters) -> OperatorInput:
        """Return a deepcopy of fac_input with risk_params adjusted for smolt scenario."""
        adjusted = deepcopy(fac_input)
        rp = adjusted.risk_params

        if params.ras_failure_multiplier is not None:
            rp.expected_annual_events *= params.ras_failure_multiplier

        if params.oxygen_level_mg_l is not None and params.oxygen_level_mg_l < 6.0:
            # Critical O₂ → high severity + elevated frequency
            rp.mean_loss_severity   *= 3.5
            rp.expected_annual_events *= 2.0

        if params.power_backup_hours is not None and params.power_backup_hours < 4:
            # Insufficient backup power → elevated frequency
            rp.expected_annual_events *= 1.8

        return adjusted

    # ── Driver helpers ───────────────────────────────────────────────────────

    def _dominant_sea_driver(self, params: ScenarioParameters) -> str:
        scores: Dict[str, float] = {}
        if params.lice_pressure_index and params.lice_pressure_index > 1.5:
            scores["biological"] = (params.lice_pressure_index - 1.0) * 0.40
        if params.exposure_factor and params.exposure_factor > 1.2:
            scores["structural"] = (params.exposure_factor - 1.0) * 0.30
        if params.operational_factor and params.operational_factor > 1.1:
            scores["operational"] = (params.operational_factor - 1.0) * 0.20
        if params.dissolved_oxygen_mg_l and params.dissolved_oxygen_mg_l < 7.0:
            scores["environmental"] = (7.0 - params.dissolved_oxygen_mg_l) * 0.15
        return max(scores, key=scores.get) if scores else "environmental"

    # ── Narrative helpers ────────────────────────────────────────────────────

    def _build_sea_narrative(
        self, params: ScenarioParameters, change_pct: float, driver: str,
    ) -> str:
        direction = "øker" if change_pct > 0 else "reduseres"
        return (
            f"Scenariet {direction} forventet årlig tap med "
            f"{abs(change_pct):.1f} %. "
            f"Dominerende risikofaktor: {driver}."
        )

    def _build_smolt_narrative(
        self,
        params: ScenarioParameters,
        results: List[ScenarioFacilityResult],
        change_pct: float,
    ) -> str:
        affected = [r for r in results if r.change_pct > 5]
        names = (
            ", ".join(r.facility_name for r in affected)
            if affected else "alle anlegg"
        )
        direction = "øker" if change_pct > 0 else "reduseres"
        return (
            f"Scenariet {direction} konserntapet med {abs(change_pct):.1f} %. "
            f"Berørte anlegg: {names}. "
            f"Diversifiseringsgevinst (separate nedbørsfelt) reduserer konserneksponering."
        )


# ─────────────────────────────────────────────────────────────────────────────
# Utility
# ─────────────────────────────────────────────────────────────────────────────

def _pct_change(baseline: float, scenario: float) -> float:
    if baseline == 0:
        return 0.0
    return round((scenario - baseline) / baseline * 100, 2)
