"""tests/test_mc_reporter.py — Sprint 8: MCReporter figure and text output tests."""
from __future__ import annotations

import pytest

from core.mc_reporter import MCReporter


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def reporter(simple_mc_library, four_mc_results, tmp_path):
    return MCReporter(
        mc_library=simple_mc_library,
        results=four_mc_results,
        output_dir=tmp_path,
        scenario_name='test_scenario',
    )


# ── render_risk_heatmap ───────────────────────────────────────────────────────

class TestRenderRiskHeatmap:

    def test_file_created(self, reporter, tmp_path):
        path = reporter.render_risk_heatmap()
        assert path.exists()

    def test_file_nonempty(self, reporter, tmp_path):
        path = reporter.render_risk_heatmap()
        assert path.stat().st_size > 10_000   # PNG should be at least 10 KB

    def test_default_filename(self, reporter):
        path = reporter.render_risk_heatmap()
        assert path.name == 'mc_risk_heatmap.png'

    def test_custom_filename(self, reporter, tmp_path):
        path = reporter.render_risk_heatmap(filename='custom_risk.png')
        assert path.name == 'custom_risk.png'


# ── render_transfer_heatmap ───────────────────────────────────────────────────

class TestRenderTransferHeatmap:

    def test_file_created(self, reporter):
        path = reporter.render_transfer_heatmap()
        assert path.exists()
        assert path.stat().st_size > 5_000


# ── render_pair_risk_profiles ─────────────────────────────────────────────────

class TestRenderPairRiskProfiles:

    def test_file_created(self, reporter):
        path = reporter.render_pair_risk_profiles()
        assert path.exists()
        assert path.stat().st_size > 5_000

    def test_empty_results_no_crash(self, simple_mc_library, tmp_path):
        r = MCReporter(simple_mc_library, [], tmp_path / 'empty',
                       scenario_name='empty')
        path = r.render_pair_risk_profiles()
        # Should return path without crashing even with no results
        assert path.name == 'mc_pair_profiles.png'


# ── render_management_summary ─────────────────────────────────────────────────

class TestRenderManagementSummary:

    def test_file_created(self, reporter):
        path = reporter.render_management_summary()
        assert path.exists()

    def test_file_substantial(self, reporter):
        path = reporter.render_management_summary()
        # Dashboard with 6 panels should produce a substantial PNG
        assert path.stat().st_size > 20_000

    def test_default_filename(self, reporter):
        path = reporter.render_management_summary()
        assert path.name == 'mc_management_summary.png'


# ── write_text_summary ────────────────────────────────────────────────────────

class TestWriteTextSummary:

    def test_file_created(self, reporter):
        path = reporter.write_text_summary()
        assert path.exists()

    def test_file_utf8_readable(self, reporter):
        path = reporter.write_text_summary()
        text = path.read_text(encoding='utf-8')
        assert len(text) > 100

    def test_contains_scenario_name(self, reporter):
        path = reporter.write_text_summary()
        text = path.read_text(encoding='utf-8')
        assert 'test_scenario' in text

    def test_contains_red_pairs(self, reporter):
        path = reporter.write_text_summary()
        text = path.read_text(encoding='utf-8')
        assert 'ROD RISIKO' in text

    def test_contains_green_pairs(self, reporter):
        path = reporter.write_text_summary()
        text = path.read_text(encoding='utf-8')
        assert 'GRONN RISIKO' in text

    def test_contains_n_samples(self, reporter):
        path = reporter.write_text_summary()
        text = path.read_text(encoding='utf-8')
        assert '1,000' in text   # n_samples=1000 from fixture

    def test_no_cross_contamination_message(self, reporter):
        """SA->SB and SB->SA are GREEN → no significant cross-contamination."""
        path = reporter.write_text_summary()
        text = path.read_text(encoding='utf-8')
        assert 'krysskontaminering' in text.lower()

    def test_self_infection_mentioned(self, reporter):
        path = reporter.write_text_summary()
        text = path.read_text(encoding='utf-8')
        assert 'egenkontaminering' in text.lower()


# ── render_all ────────────────────────────────────────────────────────────────

class TestRenderAll:

    def test_returns_five_paths(self, reporter):
        paths = reporter.render_all()
        assert len(paths) == 5

    def test_all_paths_exist(self, reporter):
        paths = reporter.render_all()
        for key, path in paths.items():
            assert path.exists(), f"Missing: {key} -> {path}"

    def test_expected_keys(self, reporter):
        paths = reporter.render_all()
        expected_keys = {
            'risk_heatmap', 'transfer_heatmap', 'pair_profiles',
            'management_summary', 'text_summary',
        }
        assert set(paths.keys()) == expected_keys

    def test_log_func_called(self, reporter):
        log_calls = []
        reporter.render_all(log_func=log_calls.append)
        assert len(log_calls) > 0

    def test_png_files_are_valid(self, reporter):
        """PNG files start with the PNG magic bytes."""
        PNG_MAGIC = b'\x89PNG'
        paths = reporter.render_all()
        for key in ('risk_heatmap', 'transfer_heatmap', 'pair_profiles',
                    'management_summary'):
            data = paths[key].read_bytes()
            assert data[:4] == PNG_MAGIC, f"{key} is not a valid PNG"
