"""
tests/test_specific_locality_mode.py

Sprint: specific_sea_localities

Tests:
  TestSchemaValidation      (5 tests) — SelectedSeaSiteInput schema + OperatorProfileInput
  TestValidateSelectedSites (5 tests) — site_registry.validate_selected_sites()
  TestOperatorBuilderSpecific (6 tests) — operator_builder specific-mode path
  TestMetadataBlock         (4 tests) — MetadataBlock populated correctly in run_feasibility_service
"""

from __future__ import annotations

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# TestSchemaValidation
# ─────────────────────────────────────────────────────────────────────────────

class TestSchemaValidation:
    """Pydantic schema validation for specific-locality mode fields."""

    def test_generic_mode_default(self):
        from backend.schemas import OperatorProfileInput
        p = OperatorProfileInput()
        assert p.site_selection_mode == "generic"
        assert p.selected_sites is None

    def test_selected_sea_site_input_required_fields(self):
        from backend.schemas import SelectedSeaSiteInput
        s = SelectedSeaSiteInput(
            site_id="KH_S01",
            site_name="Kornstad",
            biomass_tonnes=3000,
        )
        assert s.site_id == "KH_S01"
        assert s.biomass_tonnes == 3000
        assert s.biomass_value_nok is None  # optional

    def test_selected_sea_site_with_value(self):
        from backend.schemas import SelectedSeaSiteInput
        s = SelectedSeaSiteInput(
            site_id="KH_S01",
            site_name="Kornstad",
            biomass_tonnes=3000,
            biomass_value_nok=195_000_000,
        )
        assert s.biomass_value_nok == 195_000_000

    def test_operator_profile_with_selected_sites(self):
        from backend.schemas import OperatorProfileInput, SelectedSeaSiteInput
        p = OperatorProfileInput(
            site_selection_mode="specific",
            selected_sites=[
                SelectedSeaSiteInput(
                    site_id="KH_S01", site_name="Kornstad", biomass_tonnes=3000
                ),
                SelectedSeaSiteInput(
                    site_id="KH_S02", site_name="Leite", biomass_tonnes=2500
                ),
            ],
        )
        assert p.site_selection_mode == "specific"
        assert len(p.selected_sites) == 2

    def test_biomass_tonnes_must_be_positive(self):
        from backend.schemas import SelectedSeaSiteInput
        with pytest.raises(Exception):
            SelectedSeaSiteInput(site_id="KH_S01", site_name="Kornstad", biomass_tonnes=-100)


# ─────────────────────────────────────────────────────────────────────────────
# TestValidateSelectedSites
# ─────────────────────────────────────────────────────────────────────────────

class TestValidateSelectedSites:
    """validate_selected_sites() logic."""

    def _make_sel(self, site_id, locality_no=None):
        from backend.schemas import SelectedSeaSiteInput
        return SelectedSeaSiteInput(
            site_id=site_id,
            locality_no=locality_no,
            site_name="Test",
            biomass_tonnes=3000,
        )

    def test_valid_single_site(self):
        from backend.services.site_registry import validate_selected_sites
        errs = validate_selected_sites([self._make_sel("KH_S01")])
        assert errs == []

    def test_valid_multiple_sites(self):
        from backend.services.site_registry import validate_selected_sites
        errs = validate_selected_sites([
            self._make_sel("KH_S01"),
            self._make_sel("KH_S02"),
        ])
        assert errs == []

    def test_unknown_site_id_rejected(self):
        from backend.services.site_registry import validate_selected_sites
        errs = validate_selected_sites([self._make_sel("DOES_NOT_EXIST")])
        assert len(errs) == 1
        assert "not found" in errs[0].lower()

    def test_duplicate_site_id_rejected(self):
        from backend.services.site_registry import validate_selected_sites
        errs = validate_selected_sites([
            self._make_sel("KH_S01"),
            self._make_sel("KH_S01"),
        ])
        assert any("duplicate" in e.lower() for e in errs)

    def test_locality_no_mismatch_rejected(self):
        from backend.services.site_registry import validate_selected_sites
        errs = validate_selected_sites([self._make_sel("KH_S01", locality_no=99999)])
        assert len(errs) == 1
        assert "locality_no" in errs[0].lower() or "does not match" in errs[0].lower()


# ─────────────────────────────────────────────────────────────────────────────
# TestOperatorBuilderSpecific
# ─────────────────────────────────────────────────────────────────────────────

class TestOperatorBuilderSpecific:
    """operator_builder.build_operator_input() specific-locality mode."""

    def _make_profile(self, sites):
        from backend.schemas import OperatorProfileInput, SelectedSeaSiteInput
        return OperatorProfileInput(
            name="Test Operator",
            n_sites=len(sites),
            site_selection_mode="specific",
            selected_sites=[
                SelectedSeaSiteInput(**s) for s in sites
            ],
            biomass_value_per_tonne=65_000,
        )

    def test_specific_mode_site_count(self):
        from backend.services.operator_builder import build_operator_input
        profile = self._make_profile([
            {"site_id": "KH_S01", "site_name": "Kornstad", "biomass_tonnes": 3000},
            {"site_id": "KH_S02", "site_name": "Leite",    "biomass_tonnes": 2500},
        ])
        op, alloc = build_operator_input(profile)
        assert len(op.sites) == 2

    def test_specific_mode_biomass_preserved(self):
        from backend.services.operator_builder import build_operator_input
        profile = self._make_profile([
            {"site_id": "KH_S01", "site_name": "Kornstad", "biomass_tonnes": 3200},
        ])
        op, alloc = build_operator_input(profile)
        assert op.sites[0].biomass_tonnes == 3200

    def test_specific_mode_allocation_summary(self):
        from backend.services.operator_builder import build_operator_input
        profile = self._make_profile([
            {"site_id": "KH_S01", "site_name": "Kornstad", "biomass_tonnes": 3000},
        ])
        _, alloc = build_operator_input(profile)
        assert alloc.site_selection_mode == "specific"

    def test_specific_mode_locality_numbers(self):
        from backend.services.operator_builder import build_operator_input
        profile = self._make_profile([
            {"site_id": "KH_S01", "site_name": "Kornstad", "biomass_tonnes": 3000},
            {"site_id": "KH_S02", "site_name": "Leite",    "biomass_tonnes": 2500},
        ])
        _, alloc = build_operator_input(profile)
        # KH_S01=12855, KH_S02=12870
        assert 12855 in alloc.selected_locality_numbers
        assert 12870 in alloc.selected_locality_numbers

    def test_specific_mode_auto_value_warning(self):
        from backend.services.operator_builder import build_operator_input
        profile = self._make_profile([
            {"site_id": "KH_S01", "site_name": "Kornstad", "biomass_tonnes": 3000},
        ])
        _, alloc = build_operator_input(profile)
        # biomass_value_nok not set → auto-derived → warning emitted
        assert any("auto" in w.lower() or "auto-beregnet" in w.lower()
                   for w in alloc.warnings)

    def test_specific_mode_explicit_value_no_warning(self):
        from backend.services.operator_builder import build_operator_input
        from backend.schemas import OperatorProfileInput, SelectedSeaSiteInput
        profile = OperatorProfileInput(
            name="Test Operator",
            n_sites=1,
            site_selection_mode="specific",
            biomass_value_per_tonne=65_000,
            selected_sites=[
                SelectedSeaSiteInput(
                    site_id="KH_S01",
                    site_name="Kornstad",
                    biomass_tonnes=3000,
                    biomass_value_nok=195_000_000,
                )
            ],
        )
        _, alloc = build_operator_input(profile)
        # Explicit value set → no auto-derived warning for this site
        auto_warnings = [w for w in alloc.warnings if "auto-beregnet" in w.lower()]
        assert len(auto_warnings) == 0


# ─────────────────────────────────────────────────────────────────────────────
# TestMetadataBlock
# ─────────────────────────────────────────────────────────────────────────────

class TestMetadataBlock:
    """MetadataBlock populated correctly in run_feasibility_service via TestClient."""

    def _client(self):
        from fastapi.testclient import TestClient
        from backend.main import app
        return TestClient(app)

    def test_generic_mode_metadata_defaults(self):
        client = self._client()
        payload = {
            "operator_profile": {
                "n_sites": 2,
                "total_biomass_tonnes": 6000,
                "biomass_value_per_tonne": 64800,
            },
            "model_settings": {"n_simulations": 200, "generate_pdf": False},
        }
        res = client.post("/api/feasibility/run", json=payload)
        assert res.status_code == 200
        meta = res.json()["metadata"]
        assert meta["site_selection_mode"] == "generic"
        assert meta["selected_site_count"] == 0
        assert meta["selected_locality_numbers"] == []

    def test_specific_mode_metadata_populated(self):
        client = self._client()
        payload = {
            "operator_profile": {
                "n_sites": 2,
                "total_biomass_tonnes": 5500,
                "biomass_value_per_tonne": 65000,
                "site_selection_mode": "specific",
                "selected_sites": [
                    {"site_id": "KH_S01", "site_name": "Kornstad", "biomass_tonnes": 3000},
                    {"site_id": "KH_S02", "site_name": "Leite",    "biomass_tonnes": 2500},
                ],
            },
            "model_settings": {"n_simulations": 200, "generate_pdf": False},
        }
        res = client.post("/api/feasibility/run", json=payload)
        assert res.status_code == 200
        meta = res.json()["metadata"]
        assert meta["site_selection_mode"] == "specific"
        assert meta["selected_site_count"] == 2
        assert 12855 in meta["selected_locality_numbers"]
        assert 12870 in meta["selected_locality_numbers"]

    def test_invalid_site_id_returns_422(self):
        client = self._client()
        payload = {
            "operator_profile": {
                "n_sites": 1,
                "total_biomass_tonnes": 3000,
                "biomass_value_per_tonne": 65000,
                "site_selection_mode": "specific",
                "selected_sites": [
                    {"site_id": "DOES_NOT_EXIST", "site_name": "Ghost", "biomass_tonnes": 3000},
                ],
            },
            "model_settings": {"n_simulations": 200, "generate_pdf": False},
        }
        res = client.post("/api/feasibility/run", json=payload)
        assert res.status_code == 422

    def test_duplicate_site_returns_422(self):
        client = self._client()
        payload = {
            "operator_profile": {
                "n_sites": 2,
                "total_biomass_tonnes": 6000,
                "biomass_value_per_tonne": 65000,
                "site_selection_mode": "specific",
                "selected_sites": [
                    {"site_id": "KH_S01", "site_name": "Kornstad", "biomass_tonnes": 3000},
                    {"site_id": "KH_S01", "site_name": "Kornstad", "biomass_tonnes": 3000},
                ],
            },
            "model_settings": {"n_simulations": 200, "generate_pdf": False},
        }
        res = client.post("/api/feasibility/run", json=payload)
        assert res.status_code == 422
