"""
Tests for Sprint 7 – DomainCorrelationMatrix.

Covers:
- Dataclass validation (__post_init__)
- equicorrelation factory
- expert_default factory
- from_dict factory
- sub_matrix extraction
- is_positive_definite / cholesky
- _perturb_domain_weights helper
"""

import numpy as np
import pytest

from models.domain_correlation import (
    DOMAIN_ORDER,
    DomainCorrelationMatrix,
    PREDEFINED_DOMAIN_CORRELATIONS,
)
from models.domain_loss_breakdown import _perturb_domain_weights


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _rng(seed=42):
    return np.random.default_rng(seed)


def _valid_4x4():
    """Return a valid symmetric unit-diagonal 4×4 matrix."""
    mat = np.array([
        [1.00, 0.20, 0.30, 0.10],
        [0.20, 1.00, 0.40, 0.25],
        [0.30, 0.40, 1.00, 0.15],
        [0.10, 0.25, 0.15, 1.00],
    ], dtype=float)
    return mat


# ─────────────────────────────────────────────────────────────────────────────
# TestDomainCorrelationMatrixValidation  (6 tests)
# ─────────────────────────────────────────────────────────────────────────────

class TestDomainCorrelationMatrixValidation:
    def test_accepts_valid_expert_default(self):
        dcm = DomainCorrelationMatrix.expert_default()
        assert dcm.domains == DOMAIN_ORDER
        assert dcm.correlation_matrix.shape == (4, 4)
        assert dcm.perturbation_strength == 0.20

    def test_rejects_non_square_shape(self):
        with pytest.raises(ValueError, match="shape"):
            DomainCorrelationMatrix(
                domains=["biological", "structural"],
                correlation_matrix=np.eye(3),
            )

    def test_rejects_asymmetric_matrix(self):
        mat = _valid_4x4()
        mat[0, 1] = 0.99   # break symmetry
        with pytest.raises(ValueError, match="symmetric"):
            DomainCorrelationMatrix(domains=list(DOMAIN_ORDER), correlation_matrix=mat)

    def test_rejects_non_unit_diagonal(self):
        mat = _valid_4x4()
        mat[0, 0] = 0.5
        with pytest.raises(ValueError, match="diagonal"):
            DomainCorrelationMatrix(domains=list(DOMAIN_ORDER), correlation_matrix=mat)

    def test_rejects_unknown_domain_name(self):
        mat = np.eye(2)
        with pytest.raises(ValueError, match="Unknown domain"):
            DomainCorrelationMatrix(
                domains=["biological", "fantasy_domain"],
                correlation_matrix=mat,
            )

    def test_rejects_perturbation_strength_zero(self):
        with pytest.raises(ValueError, match="perturbation_strength"):
            DomainCorrelationMatrix(
                domains=list(DOMAIN_ORDER),
                correlation_matrix=_valid_4x4(),
                perturbation_strength=0.0,
            )


# ─────────────────────────────────────────────────────────────────────────────
# TestEquicorrelation  (6 tests)
# ─────────────────────────────────────────────────────────────────────────────

class TestEquicorrelation:
    def test_shape_with_default_domains(self):
        dcm = DomainCorrelationMatrix.equicorrelation(0.3)
        assert dcm.correlation_matrix.shape == (4, 4)

    def test_all_off_diagonals_equal_rho(self):
        rho = 0.35
        dcm = DomainCorrelationMatrix.equicorrelation(rho)
        mat = dcm.correlation_matrix
        np.fill_diagonal(mat.copy(), 0.0)
        off = mat - np.diag(np.diag(mat))
        assert np.allclose(off[off != 0.0], rho)

    def test_rho_zero_gives_identity(self):
        dcm = DomainCorrelationMatrix.equicorrelation(0.0)
        assert np.allclose(dcm.correlation_matrix, np.eye(4))

    def test_rho_ge_1_raises(self):
        with pytest.raises(ValueError, match="rho"):
            DomainCorrelationMatrix.equicorrelation(1.0)

    def test_custom_domain_subset(self):
        domains = ["structural", "environmental", "operational"]
        dcm = DomainCorrelationMatrix.equicorrelation(0.25, domains=domains)
        assert dcm.correlation_matrix.shape == (3, 3)
        assert dcm.domains == domains

    def test_perturbation_strength_forwarded(self):
        dcm = DomainCorrelationMatrix.equicorrelation(0.1, perturbation_strength=0.15)
        assert dcm.perturbation_strength == 0.15


# ─────────────────────────────────────────────────────────────────────────────
# TestExpertDefault  (6 tests)
# ─────────────────────────────────────────────────────────────────────────────

class TestExpertDefault:
    def setup_method(self):
        self.dcm = DomainCorrelationMatrix.expert_default()

    def test_domains_equal_domain_order(self):
        assert self.dcm.domains == DOMAIN_ORDER

    def test_env_struct_entry(self):
        env_idx = DOMAIN_ORDER.index("environmental")
        struct_idx = DOMAIN_ORDER.index("structural")
        val = self.dcm.correlation_matrix[env_idx, struct_idx]
        assert abs(val - 0.60) < 1e-9

    def test_env_bio_entry(self):
        env_idx = DOMAIN_ORDER.index("environmental")
        bio_idx = DOMAIN_ORDER.index("biological")
        val = self.dcm.correlation_matrix[env_idx, bio_idx]
        assert abs(val - 0.40) < 1e-9

    def test_ops_struct_entry(self):
        ops_idx = DOMAIN_ORDER.index("operational")
        struct_idx = DOMAIN_ORDER.index("structural")
        val = self.dcm.correlation_matrix[ops_idx, struct_idx]
        assert abs(val - 0.35) < 1e-9

    def test_is_positive_definite(self):
        assert self.dcm.is_positive_definite()

    def test_cholesky_reconstructs_matrix(self):
        L = self.dcm.cholesky()
        assert np.allclose(L @ L.T, self.dcm.correlation_matrix, atol=1e-10)


# ─────────────────────────────────────────────────────────────────────────────
# TestFromDict  (4 tests)
# ─────────────────────────────────────────────────────────────────────────────

class TestFromDict:
    def test_named_pairs_build_symmetric_matrix(self):
        dcm = DomainCorrelationMatrix.from_dict({
            "env_struct": 0.60,
            "env_biological": 0.40,
        })
        env_i = DOMAIN_ORDER.index("environmental")
        struct_i = DOMAIN_ORDER.index("structural")
        bio_i = DOMAIN_ORDER.index("biological")
        assert abs(dcm.correlation_matrix[env_i, struct_i] - 0.60) < 1e-9
        assert abs(dcm.correlation_matrix[struct_i, env_i] - 0.60) < 1e-9
        assert abs(dcm.correlation_matrix[env_i, bio_i] - 0.40) < 1e-9

    def test_unspecified_pairs_default_to_zero(self):
        dcm = DomainCorrelationMatrix.from_dict({"env_struct": 0.5})
        ops_i = DOMAIN_ORDER.index("operational")
        bio_i = DOMAIN_ORDER.index("biological")
        assert dcm.correlation_matrix[ops_i, bio_i] == 0.0

    def test_unknown_domain_name_raises(self):
        with pytest.raises(ValueError):
            DomainCorrelationMatrix.from_dict({"biological_fantasy": 0.3})

    def test_diagonal_is_one(self):
        dcm = DomainCorrelationMatrix.from_dict({"env_struct": 0.4})
        assert np.allclose(np.diag(dcm.correlation_matrix), 1.0)


# ─────────────────────────────────────────────────────────────────────────────
# TestSubMatrix  (3 tests)
# ─────────────────────────────────────────────────────────────────────────────

class TestSubMatrix:
    def setup_method(self):
        self.dcm = DomainCorrelationMatrix.expert_default()

    def test_sub_matrix_shape(self):
        sub = self.dcm.sub_matrix(["structural", "environmental", "operational"])
        assert sub.correlation_matrix.shape == (3, 3)
        assert sub.domains == ["structural", "environmental", "operational"]

    def test_extracted_values_match_parent(self):
        sub = self.dcm.sub_matrix(["structural", "environmental"])
        struct_i = DOMAIN_ORDER.index("structural")
        env_i = DOMAIN_ORDER.index("environmental")
        expected = self.dcm.correlation_matrix[struct_i, env_i]
        assert abs(sub.correlation_matrix[0, 1] - expected) < 1e-10

    def test_sub_matrix_is_positive_definite(self):
        sub = self.dcm.sub_matrix(["structural", "environmental", "operational"])
        assert sub.is_positive_definite()


# ─────────────────────────────────────────────────────────────────────────────
# TestIsPositiveDefinite / TestCholesky  (4 tests)
# ─────────────────────────────────────────────────────────────────────────────

class TestPDAndCholesky:
    def test_expert_default_is_pd(self):
        assert DomainCorrelationMatrix.expert_default().is_positive_definite()

    def test_non_pd_matrix_returns_false(self):
        # Equicorrelation with rho = -0.5: eigenvalues are
        #   1 + (D-1)*rho = 1 + 3*(-0.5) = -0.5 < 0  → NOT PD
        mat = np.full((4, 4), -0.5)
        np.fill_diagonal(mat, 1.0)
        dcm = DomainCorrelationMatrix(
            domains=list(DOMAIN_ORDER),
            correlation_matrix=mat,
        )
        assert dcm.is_positive_definite() is False

    def test_cholesky_shape_and_lower_triangular(self):
        L = DomainCorrelationMatrix.expert_default().cholesky()
        assert L.shape == (4, 4)
        # Lower triangular: upper triangle (excluding diagonal) should be zero
        assert np.allclose(np.triu(L, k=1), 0.0)

    def test_cholesky_fallback_for_borderline_matrix(self):
        mat = np.full((4, 4), 0.999)
        np.fill_diagonal(mat, 1.0)
        dcm = DomainCorrelationMatrix(domains=list(DOMAIN_ORDER), correlation_matrix=mat)
        # Should not raise; _nearest_psd fallback handles it
        L = dcm.cholesky()
        assert L.shape == (4, 4)
        # L @ L.T should be close to a PD matrix
        reconstructed = L @ L.T
        assert np.all(np.linalg.eigvalsh(reconstructed) > 0)


# ─────────────────────────────────────────────────────────────────────────────
# TestPerturbDomainWeights  (6 tests)
# ─────────────────────────────────────────────────────────────────────────────

class TestPerturbDomainWeights:
    def _base_fracs(self):
        return np.array([0.60, 0.20, 0.10, 0.10])

    def test_output_shape(self):
        dcm = DomainCorrelationMatrix.equicorrelation(0.3)
        w = _perturb_domain_weights(self._base_fracs(), 100, 5, dcm, _rng())
        assert w.shape == (100, 5, 4)

    def test_each_row_sums_to_one(self):
        dcm = DomainCorrelationMatrix.equicorrelation(0.3)
        w = _perturb_domain_weights(self._base_fracs(), 50, 5, dcm, _rng())
        row_sums = w.sum(axis=-1)
        assert np.allclose(row_sums, 1.0, atol=1e-12)

    def test_perturbation_strength_zero_gives_base_fracs(self):
        # Use near-zero perturbation_strength — need to temporarily bypass validation
        # We test this via a very small perturbation_strength instead
        dcm = DomainCorrelationMatrix(
            domains=list(DOMAIN_ORDER),
            correlation_matrix=np.eye(4),
            perturbation_strength=1e-12,
        )
        w = _perturb_domain_weights(self._base_fracs(), 20, 5, dcm, _rng())
        assert np.allclose(w, self._base_fracs()[np.newaxis, np.newaxis, :], atol=1e-6)

    def test_rho_zero_independent_domains(self):
        # With rho=0 (independent inputs), simplex constraint induces negative
        # cross-domain correlation.  Key check: sum-to-1 holds and each domain
        # fraction varies (std > 0) — NOT that correlation is near zero.
        dcm = DomainCorrelationMatrix.equicorrelation(0.0)
        w = _perturb_domain_weights(self._base_fracs(), 2000, 5, dcm, _rng())
        flat = w.reshape(-1, 4)
        # Each domain fraction has non-trivial variation
        assert flat[:, 0].std() > 0.01
        # Rows sum to 1
        assert np.allclose(flat.sum(axis=1), 1.0, atol=1e-12)

    def test_high_rho_affects_cross_domain_correlation(self):
        # High positive input rho induces more negative cross-domain correlation
        # in the normalized fracs (Aitchison simplex geometry: common shocks are
        # absorbed by normalization, strengthening the negative sum-to-1 constraint).
        # Observable: corr(bio_frac, struct_frac | rho=0.9) < corr(... | rho=0.0).
        dcm_high = DomainCorrelationMatrix.equicorrelation(0.90)
        dcm_zero = DomainCorrelationMatrix.equicorrelation(0.0)
        w_high = _perturb_domain_weights(self._base_fracs(), 3000, 5, dcm_high, _rng(1))
        w_zero = _perturb_domain_weights(self._base_fracs(), 3000, 5, dcm_zero, _rng(2))
        flat_high = w_high.reshape(-1, 4)
        flat_zero = w_zero.reshape(-1, 4)
        corr_high = np.corrcoef(flat_high[:, 0], flat_high[:, 1])[0, 1]
        corr_zero = np.corrcoef(flat_zero[:, 0], flat_zero[:, 1])[0, 1]
        # Different rho → different cross-domain correlation structure
        assert corr_high != pytest.approx(corr_zero, abs=0.05)

    def test_non_negative_constraint(self):
        # Even with large perturbation_strength, weights should be >= 0
        dcm = DomainCorrelationMatrix(
            domains=list(DOMAIN_ORDER),
            correlation_matrix=np.eye(4),
            perturbation_strength=5.0,   # extreme
        )
        w = _perturb_domain_weights(self._base_fracs(), 500, 5, dcm, _rng())
        assert np.all(w >= 0.0)


# ─────────────────────────────────────────────────────────────────────────────
# TestPredefined  (sanity)
# ─────────────────────────────────────────────────────────────────────────────

class TestPredefined:
    def test_keys(self):
        assert set(PREDEFINED_DOMAIN_CORRELATIONS.keys()) == {
            "independent", "expert_default", "low", "moderate"
        }

    def test_independent_is_identity(self):
        dcm = PREDEFINED_DOMAIN_CORRELATIONS["independent"]
        assert np.allclose(dcm.correlation_matrix, np.eye(4))

    def test_all_are_positive_definite(self):
        for name, dcm in PREDEFINED_DOMAIN_CORRELATIONS.items():
            assert dcm.is_positive_definite(), f"{name} is not PD"
