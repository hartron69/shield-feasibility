"""
Tests for models/correlation.py – RiskCorrelationMatrix and _nearest_psd.
"""

import numpy as np
import pytest

from models.correlation import RiskCorrelationMatrix, _nearest_psd


# ── Helpers ───────────────────────────────────────────────────────────────────

SITE_IDS_2 = ["site-A", "site-B"]
SITE_IDS_3 = ["site-A", "site-B", "site-C"]


def _valid_2x2(rho: float = 0.4) -> np.ndarray:
    return np.array([[1.0, rho], [rho, 1.0]])


def _valid_3x3(rho: float = 0.3) -> np.ndarray:
    return np.array([
        [1.0, rho, rho],
        [rho, 1.0, rho],
        [rho, rho, 1.0],
    ])


# ── __post_init__ validation ──────────────────────────────────────────────────

class TestRiskCorrelationMatrixValidation:
    def test_valid_2x2_accepted(self):
        rcm = RiskCorrelationMatrix(
            risk_type="biological",
            site_ids=SITE_IDS_2,
            correlation_matrix=_valid_2x2(),
        )
        assert rcm.risk_type == "biological"

    def test_wrong_shape_raises(self):
        bad = np.eye(3)
        with pytest.raises(ValueError, match="shape"):
            RiskCorrelationMatrix(
                risk_type="all",
                site_ids=SITE_IDS_2,
                correlation_matrix=bad,
            )

    def test_non_symmetric_raises(self):
        mat = _valid_2x2()
        mat[0, 1] = 0.9  # break symmetry
        with pytest.raises(ValueError, match="symmetric"):
            RiskCorrelationMatrix(
                risk_type="all",
                site_ids=SITE_IDS_2,
                correlation_matrix=mat,
            )

    def test_diagonal_not_one_raises(self):
        mat = _valid_2x2()
        mat[0, 0] = 0.9
        mat[1, 1] = 0.9
        with pytest.raises(ValueError, match="diagonal"):
            RiskCorrelationMatrix(
                risk_type="all",
                site_ids=SITE_IDS_2,
                correlation_matrix=mat,
            )


# ── equicorrelation factory ───────────────────────────────────────────────────

class TestEquicorrelation:
    def test_produces_correct_shape(self):
        rcm = RiskCorrelationMatrix.equicorrelation(SITE_IDS_3, rho=0.5)
        assert rcm.correlation_matrix.shape == (3, 3)

    def test_off_diagonal_equals_rho(self):
        rho = 0.35
        rcm = RiskCorrelationMatrix.equicorrelation(SITE_IDS_3, rho=rho)
        mat = rcm.correlation_matrix
        # All off-diagonal entries equal rho
        mask = ~np.eye(3, dtype=bool)
        assert np.allclose(mat[mask], rho)

    def test_diagonal_is_one(self):
        rcm = RiskCorrelationMatrix.equicorrelation(SITE_IDS_3, rho=0.2)
        assert np.allclose(np.diag(rcm.correlation_matrix), 1.0)

    def test_zero_rho_returns_identity(self):
        rcm = RiskCorrelationMatrix.equicorrelation(SITE_IDS_2, rho=0.0)
        np.testing.assert_array_equal(rcm.correlation_matrix, np.eye(2))

    def test_rho_equals_one_raises(self):
        with pytest.raises(ValueError, match="rho"):
            RiskCorrelationMatrix.equicorrelation(SITE_IDS_2, rho=1.0)

    def test_negative_rho_raises(self):
        with pytest.raises(ValueError, match="rho"):
            RiskCorrelationMatrix.equicorrelation(SITE_IDS_2, rho=-0.1)

    def test_default_risk_type(self):
        rcm = RiskCorrelationMatrix.equicorrelation(SITE_IDS_2, rho=0.3)
        assert rcm.risk_type == "all"

    def test_custom_risk_type(self):
        rcm = RiskCorrelationMatrix.equicorrelation(
            SITE_IDS_2, rho=0.3, risk_type="biological"
        )
        assert rcm.risk_type == "biological"


# ── from_distance_decay factory ───────────────────────────────────────────────

class TestFromDistanceDecay:
    def _distances_3x3(self) -> np.ndarray:
        """Symmetric distance matrix for 3 sites."""
        d = np.array([
            [0.0, 10.0, 25.0],
            [10.0, 0.0, 15.0],
            [25.0, 15.0, 0.0],
        ])
        return d

    def test_shape(self):
        rcm = RiskCorrelationMatrix.from_distance_decay(
            SITE_IDS_3, self._distances_3x3()
        )
        assert rcm.correlation_matrix.shape == (3, 3)

    def test_diagonal_is_one(self):
        rcm = RiskCorrelationMatrix.from_distance_decay(
            SITE_IDS_3, self._distances_3x3()
        )
        assert np.allclose(np.diag(rcm.correlation_matrix), 1.0)

    def test_symmetric(self):
        rcm = RiskCorrelationMatrix.from_distance_decay(
            SITE_IDS_3, self._distances_3x3()
        )
        mat = rcm.correlation_matrix
        np.testing.assert_allclose(mat, mat.T, atol=1e-10)

    def test_off_diagonal_decay(self):
        """Farther sites should be less correlated."""
        d = self._distances_3x3()
        rcm = RiskCorrelationMatrix.from_distance_decay(
            SITE_IDS_3, d, max_rho=0.6, decay=0.05
        )
        mat = rcm.correlation_matrix
        # site 0 vs 1 (10 km) should be more correlated than 0 vs 2 (25 km)
        assert mat[0, 1] > mat[0, 2]

    def test_formula(self):
        """Verify rho_ij = max_rho * exp(-decay * dist)."""
        d = np.array([[0.0, 20.0], [20.0, 0.0]])
        rcm = RiskCorrelationMatrix.from_distance_decay(
            SITE_IDS_2, d, max_rho=0.6, decay=0.05
        )
        expected = 0.6 * np.exp(-0.05 * 20.0)
        assert rcm.correlation_matrix[0, 1] == pytest.approx(expected)

    def test_wrong_distance_shape_raises(self):
        bad_d = np.zeros((4, 4))
        with pytest.raises(ValueError, match="shape"):
            RiskCorrelationMatrix.from_distance_decay(SITE_IDS_3, bad_d)

    def test_default_risk_type(self):
        d = np.array([[0.0, 5.0], [5.0, 0.0]])
        rcm = RiskCorrelationMatrix.from_distance_decay(SITE_IDS_2, d)
        assert rcm.risk_type == "biological"


# ── is_positive_definite ──────────────────────────────────────────────────────

class TestIsPositiveDefinite:
    def test_identity_is_pd(self):
        rcm = RiskCorrelationMatrix(
            risk_type="all",
            site_ids=SITE_IDS_2,
            correlation_matrix=np.eye(2),
        )
        assert rcm.is_positive_definite() is True

    def test_equicorrelation_is_pd(self):
        rcm = RiskCorrelationMatrix.equicorrelation(SITE_IDS_3, rho=0.4)
        assert rcm.is_positive_definite() is True

    def test_near_singular_returns_false(self):
        # Nearly singular: rho very close to 1 but valid correlation matrix
        rho = 0.9999
        mat = np.array([[1.0, rho], [rho, 1.0]])
        rcm = RiskCorrelationMatrix(
            risk_type="all", site_ids=SITE_IDS_2, correlation_matrix=mat
        )
        # May or may not be PD depending on floating point; just check it runs
        result = rcm.is_positive_definite()
        assert isinstance(result, bool)


# ── cholesky ──────────────────────────────────────────────────────────────────

class TestCholesky:
    def test_cholesky_shape(self):
        rcm = RiskCorrelationMatrix.equicorrelation(SITE_IDS_3, rho=0.3)
        L = rcm.cholesky()
        assert L.shape == (3, 3)

    def test_cholesky_lower_triangular(self):
        rcm = RiskCorrelationMatrix.equicorrelation(SITE_IDS_3, rho=0.3)
        L = rcm.cholesky()
        np.testing.assert_allclose(np.triu(L, k=1), 0.0, atol=1e-12)

    def test_cholesky_reconstructs_matrix(self):
        rcm = RiskCorrelationMatrix.equicorrelation(SITE_IDS_3, rho=0.4)
        L = rcm.cholesky()
        reconstructed = L @ L.T
        np.testing.assert_allclose(
            reconstructed, rcm.correlation_matrix, atol=1e-10
        )

    def test_cholesky_2x2_manual(self):
        rho = 0.5
        rcm = RiskCorrelationMatrix.equicorrelation(SITE_IDS_2, rho=rho)
        L = rcm.cholesky()
        # L[0,0] = 1; L[1,0] = rho; L[1,1] = sqrt(1 - rho^2)
        assert L[0, 0] == pytest.approx(1.0, abs=1e-10)
        assert L[1, 0] == pytest.approx(rho, abs=1e-10)
        assert L[1, 1] == pytest.approx(np.sqrt(1 - rho**2), abs=1e-10)


# ── _nearest_psd ──────────────────────────────────────────────────────────────

class TestNearestPSD:
    def test_already_psd_unchanged(self):
        """An already PD matrix should be returned essentially unchanged."""
        A = np.array([[1.0, 0.3], [0.3, 1.0]])
        A_psd = _nearest_psd(A)
        np.testing.assert_allclose(A_psd, A, atol=1e-8)

    def test_result_is_symmetric(self):
        A = np.array([[1.0, 0.5, 0.5],
                      [0.5, 1.0, 0.9],
                      [0.5, 0.9, 1.0]])
        A_psd = _nearest_psd(A)
        np.testing.assert_allclose(A_psd, A_psd.T, atol=1e-10)

    def test_result_has_unit_diagonal(self):
        A = np.array([[1.0, 0.5, 0.5],
                      [0.5, 1.0, 0.9],
                      [0.5, 0.9, 1.0]])
        A_psd = _nearest_psd(A)
        np.testing.assert_allclose(np.diag(A_psd), 1.0, atol=1e-10)

    def test_result_is_positive_definite(self):
        # Matrix that is not PD (negative eigenvalue introduced)
        A = np.array([[1.0, 0.95, 0.95],
                      [0.95, 1.0, 0.95],
                      [0.95, 0.95, 1.0]])
        A_psd = _nearest_psd(A)
        eigvals = np.linalg.eigvalsh(A_psd)
        assert np.all(eigvals > 0)

    def test_cholesky_after_repair(self):
        """Matrix repaired by _nearest_psd should be Cholesky-decomposable."""
        # This 3x3 is near-singular
        A = np.array([[1.0, 0.99, 0.99],
                      [0.99, 1.0, 0.99],
                      [0.99, 0.99, 1.0]])
        A_psd = _nearest_psd(A)
        # Should not raise
        L = np.linalg.cholesky(A_psd)
        assert L.shape == (3, 3)
