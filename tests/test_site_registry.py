"""
tests/test_site_registry.py

20 tests for backend/services/site_registry.py.

Groups:
  TestSiteRegistryLookup        (6 tests) — basic get_* and list helpers
  TestResolveBarentswatchRecord (8 tests) — resolve_barentswatch_record logic
  TestSiteRecordFields          (3 tests) — SiteRecord dataclass integrity
  TestRegistryAPIEndpoint       (3 tests) — GET /api/c5ai/site-registry via TestClient
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# TestSiteRegistryLookup
# ---------------------------------------------------------------------------

class TestSiteRegistryLookup:
    """Basic registry lookup helpers."""

    def test_get_site_by_locality_no_found(self):
        from backend.services.site_registry import get_site_by_locality_no
        # 12855 is Kornstad (KH_S01) in bw_config.py
        rec = get_site_by_locality_no(12855)
        assert rec is not None
        assert rec.site_id == "KH_S01"

    def test_get_site_by_locality_no_not_found(self):
        from backend.services.site_registry import get_site_by_locality_no
        rec = get_site_by_locality_no(99999)
        assert rec is None

    def test_get_site_by_site_id_found(self):
        from backend.services.site_registry import get_site_by_site_id
        rec = get_site_by_site_id("KH_S02")
        assert rec is not None
        assert rec.locality_no == 12870

    def test_get_site_by_site_id_not_found(self):
        from backend.services.site_registry import get_site_by_site_id
        rec = get_site_by_site_id("DOES_NOT_EXIST")
        assert rec is None

    def test_list_all_sites_returns_all(self):
        from backend.services.site_registry import list_all_sites
        from c5ai_plus.Barentswatch.bw_config import OPERATOR_LOCALITIES
        expected = sum(len(op["localities"]) for op in OPERATOR_LOCALITIES)
        sites = list_all_sites()
        assert len(sites) == expected

    def test_get_registry_summary_has_correct_keys(self):
        from backend.services.site_registry import get_registry_summary
        summary = get_registry_summary()
        assert "site_count" in summary
        assert "operator_count" in summary
        assert "operators" in summary
        assert "sites" in summary
        assert summary["site_count"] == len(summary["sites"])


# ---------------------------------------------------------------------------
# TestResolveBarentswatchRecord
# ---------------------------------------------------------------------------

class TestResolveBarentswatchRecord:
    """resolve_barentswatch_record matching logic."""

    def test_found_by_locality_no(self):
        from backend.services.site_registry import resolve_barentswatch_record
        rec, warn = resolve_barentswatch_record(12855)
        assert rec is not None
        assert rec.site_id == "KH_S01"
        assert warn is None

    def test_not_found_by_locality_no(self):
        from backend.services.site_registry import resolve_barentswatch_record
        rec, warn = resolve_barentswatch_record(99999)
        assert rec is None
        assert warn is not None
        assert "99999" in warn

    def test_found_by_name(self):
        from backend.services.site_registry import resolve_barentswatch_record
        rec, warn = resolve_barentswatch_record(None, bw_name="Kornstad")
        assert rec is not None
        assert rec.site_id == "KH_S01"
        assert warn is not None
        assert "WARNING" in warn
        assert "locality_no missing" in warn

    def test_not_found_by_name(self):
        from backend.services.site_registry import resolve_barentswatch_record
        rec, warn = resolve_barentswatch_record(None, bw_name="Uknown Site XYZ")
        assert rec is None
        assert warn is not None
        assert "WARNING" in warn

    def test_ambiguous_name_returns_none(self):
        """
        Inject two sites with the same name into a temporary registry to verify
        that ambiguous name matches return (None, warning).
        """
        from backend.services import site_registry as reg_mod
        from backend.services.site_registry import SiteRecord

        orig_by_locality = reg_mod._BY_LOCALITY_NO.copy()
        orig_by_site_id  = reg_mod._BY_SITE_ID.copy()

        dup_a = SiteRecord(
            site_id="DUP_A", locality_no=88881, site_name="DupSite",
            bw_locality_name="DupSite", operator_id="OP", operator_name="Op",
            lat=0.0, lon=0.0,
        )
        dup_b = SiteRecord(
            site_id="DUP_B", locality_no=88882, site_name="DupSite",
            bw_locality_name="DupSite", operator_id="OP", operator_name="Op",
            lat=0.0, lon=0.0,
        )

        reg_mod._BY_LOCALITY_NO[88881] = dup_a
        reg_mod._BY_LOCALITY_NO[88882] = dup_b
        reg_mod._BY_SITE_ID["DUP_A"]  = dup_a
        reg_mod._BY_SITE_ID["DUP_B"]  = dup_b

        try:
            rec, warn = reg_mod.resolve_barentswatch_record(None, bw_name="DupSite")
            assert rec is None
            assert warn is not None
            assert "WARNING" in warn
        finally:
            # Restore original registry state
            reg_mod._BY_LOCALITY_NO.clear()
            reg_mod._BY_LOCALITY_NO.update(orig_by_locality)
            reg_mod._BY_SITE_ID.clear()
            reg_mod._BY_SITE_ID.update(orig_by_site_id)

    def test_both_none_returns_warning(self):
        from backend.services.site_registry import resolve_barentswatch_record
        rec, warn = resolve_barentswatch_record(None, bw_name=None)
        assert rec is None
        assert warn is not None
        assert "WARNING" in warn

    def test_locality_no_takes_priority_over_name(self):
        """locality_no path should be used even when bw_name is also provided."""
        from backend.services.site_registry import resolve_barentswatch_record
        rec, warn = resolve_barentswatch_record(12855, bw_name="SomeOtherName")
        assert rec is not None
        assert rec.site_id == "KH_S01"
        assert warn is None

    def test_returns_none_warning_on_miss(self):
        """A locality_no miss gives (None, non-empty string)."""
        from backend.services.site_registry import resolve_barentswatch_record
        rec, warn = resolve_barentswatch_record(1)
        assert rec is None
        assert isinstance(warn, str)
        assert len(warn) > 0


# ---------------------------------------------------------------------------
# TestSiteRecordFields
# ---------------------------------------------------------------------------

class TestSiteRecordFields:
    """SiteRecord dataclass integrity."""

    def _first_site(self):
        from backend.services.site_registry import list_all_sites
        return list_all_sites()[0]

    def test_site_record_has_required_fields(self):
        rec = self._first_site()
        for attr in ("site_id", "locality_no", "site_name", "lat", "lon",
                     "operator_id", "operator_name", "facility_type"):
            assert hasattr(rec, attr), f"Missing field: {attr}"

    def test_operator_name_populated(self):
        rec = self._first_site()
        assert isinstance(rec.operator_name, str)
        assert len(rec.operator_name) > 0

    def test_facility_type_default(self):
        """Default facility_type is 'sea_cage' when not overridden in bw_config."""
        rec = self._first_site()
        # bw_config.py does not set facility_type, so the default is used
        assert rec.facility_type == "sea_cage"


# ---------------------------------------------------------------------------
# TestRegistryAPIEndpoint
# ---------------------------------------------------------------------------

class TestRegistryAPIEndpoint:
    """Integration tests for GET /api/c5ai/site-registry."""

    @pytest.fixture(scope="class")
    def client(self):
        from fastapi.testclient import TestClient
        from backend.main import app
        return TestClient(app)

    def test_site_registry_returns_200(self, client):
        resp = client.get("/api/c5ai/site-registry")
        assert resp.status_code == 200

    def test_site_registry_has_sites_key(self, client):
        resp = client.get("/api/c5ai/site-registry")
        data = resp.json()
        assert "sites" in data
        assert isinstance(data["sites"], list)
        assert len(data["sites"]) > 0

    def test_each_site_has_locality_no(self, client):
        resp = client.get("/api/c5ai/site-registry")
        data = resp.json()
        for site in data["sites"]:
            assert "locality_no" in site
            assert isinstance(site["locality_no"], int)
