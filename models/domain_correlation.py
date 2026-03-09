"""
Shield Captive Risk Platform – Domain-level Risk Correlation (Sprint 7).

Provides a 4×4 correlation matrix governing how domain loss weight fractions
co-vary across simulation years.  Correlated Gaussian perturbations shift
the fixed prior fractions (bio=60%, struct=20%, env=10%, ops=10%) year-by-year
while preserving the portfolio total exactly.

This class is **conceptually orthogonal** to ``RiskCorrelationMatrix``
(Sprint 1, site-to-site) and shares no inheritance hierarchy.  The only
shared utility is ``_nearest_psd`` from ``models.correlation``.

Perturbation model (feasibility-grade)
--------------------------------------
For each (N, T) simulation year cell::

    Z_raw  ~ N(0, I_D)                         shape (N·T, D)
    Z_corr = Z_raw @ L.T                        Cholesky-correlated
    w_raw  = base_fracs + α × Z_corr            additive shift
    w_raw  = clip(w_raw, 0)                     non-negative fractions
    w_norm = w_raw / sum(w_raw)                 renormalise → sums to 1

Properties:

* Totals preserved exactly (renormalisation ensures this).
* ``perturbation_strength = 0`` → fixed fractions every year.
* ``rho = 0`` equicorrelation → independent domain fraction shifts.
* Fully vectorised (one Cholesky per run, no Python loops).

Expert correlation defaults (``expert_default``)
-------------------------------------------------
============  ====  ======  =====  =====
pair          bio   struct  env    ops
============  ====  ======  =====  =====
bio           1.00  0.20    0.40   0.15
struct        0.20  1.00    0.60   0.35
env           0.40  0.60    1.00   0.15
ops           0.15  0.35    0.15   1.00
============  ====  ======  =====  =====

Rationale:

* env↔struct 0.60 – storms damage both environmental quality and physical structures.
* env↔bio   0.40 – warm/hypoxic years increase biological event probability.
* ops↔struct 0.35 – operational incidents raise structural failure risk.
* bio↔struct 0.20 – large biomass events stress cage and mooring systems.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np

from models.correlation import _nearest_psd


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

#: Canonical ordering of the four risk domains.
DOMAIN_ORDER: List[str] = [
    "biological",
    "structural",
    "environmental",
    "operational",
]


# ─────────────────────────────────────────────────────────────────────────────
# DomainCorrelationMatrix
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class DomainCorrelationMatrix:
    """
    Correlation matrix governing co-movement of domain loss weight fractions.

    Attributes
    ----------
    domains : List[str]
        Ordered domain names.  Must be a non-empty subset of ``DOMAIN_ORDER``.
    correlation_matrix : np.ndarray
        Shape ``(D, D)`` symmetric matrix with unit diagonal where
        ``D = len(domains)``.
    perturbation_strength : float
        Standard deviation of the additive Gaussian fraction shift per
        simulation year.  Default 0.20 (feasibility-grade).  Must be > 0.
    """

    domains: List[str]
    correlation_matrix: np.ndarray
    perturbation_strength: float = 0.20

    def __post_init__(self) -> None:
        D = len(self.domains)
        if D == 0:
            raise ValueError("domains must be non-empty.")
        for name in self.domains:
            if name not in DOMAIN_ORDER:
                raise ValueError(
                    f"Unknown domain '{name}'. Must be one of {DOMAIN_ORDER}."
                )
        if self.correlation_matrix.shape != (D, D):
            raise ValueError(
                f"correlation_matrix shape {self.correlation_matrix.shape} "
                f"does not match {D} domains."
            )
        if not np.allclose(
            self.correlation_matrix, self.correlation_matrix.T, atol=1e-6
        ):
            raise ValueError("correlation_matrix must be symmetric.")
        if not np.allclose(np.diag(self.correlation_matrix), 1.0, atol=1e-6):
            raise ValueError("correlation_matrix diagonal must be 1.0.")
        if self.perturbation_strength <= 0:
            raise ValueError(
                f"perturbation_strength must be > 0, got {self.perturbation_strength}."
            )

    # ── Factory constructors ──────────────────────────────────────────────────

    @classmethod
    def equicorrelation(
        cls,
        rho: float,
        domains: List[str] = DOMAIN_ORDER,
        perturbation_strength: float = 0.20,
    ) -> "DomainCorrelationMatrix":
        """
        Build a matrix where all off-diagonals equal ``rho``.

        Parameters
        ----------
        rho : float
            Off-diagonal correlation in ``[0, 1)``.
        domains : List[str]
            Ordered domain names (default: all four domains).
        perturbation_strength : float

        Returns
        -------
        DomainCorrelationMatrix
        """
        if not 0.0 <= rho < 1.0:
            raise ValueError(f"rho must be in [0, 1), got {rho}.")
        D = len(domains)
        mat = np.full((D, D), rho, dtype=float)
        np.fill_diagonal(mat, 1.0)
        return cls(
            domains=list(domains),
            correlation_matrix=mat,
            perturbation_strength=perturbation_strength,
        )

    @classmethod
    def expert_default(cls) -> "DomainCorrelationMatrix":
        """
        Documented 4×4 expert-elicited domain correlation matrix.

        Order: biological, structural, environmental, operational.

        Returns
        -------
        DomainCorrelationMatrix
        """
        mat = np.array([
            #  bio   struct  env    ops
            [1.00,  0.20,  0.40,  0.15],   # biological
            [0.20,  1.00,  0.60,  0.35],   # structural
            [0.40,  0.60,  1.00,  0.15],   # environmental
            [0.15,  0.35,  0.15,  1.00],   # operational
        ], dtype=float)
        return cls(
            domains=list(DOMAIN_ORDER),
            correlation_matrix=mat,
        )

    @classmethod
    def from_dict(
        cls,
        d: Dict[str, float],
        perturbation_strength: float = 0.20,
    ) -> "DomainCorrelationMatrix":
        """
        Build a 4×4 matrix from a dict of named pairwise correlations.

        Keys are ``"<domain_a>_<domain_b>"`` in any order (e.g.
        ``"env_struct"`` or ``"struct_env"`` — both are accepted).
        Unspecified pairs default to 0.  Domain names must be in
        ``DOMAIN_ORDER``.

        Parameters
        ----------
        d : Dict[str, float]
            Pairwise correlation values.
        perturbation_strength : float

        Returns
        -------
        DomainCorrelationMatrix

        Raises
        ------
        ValueError
            If a key cannot be resolved to two valid domain names.
        """
        # Accept both full names ("environmental") and common abbreviations
        _ALIAS: Dict[str, str] = {
            "bio":    "biological",
            "struct": "structural",
            "env":    "environmental",
            "ops":    "operational",
        }

        D = len(DOMAIN_ORDER)
        mat = np.eye(D, dtype=float)
        idx = {name: i for i, name in enumerate(DOMAIN_ORDER)}

        def _resolve(token: str, key: str) -> str:
            if token in idx:
                return token
            if token in _ALIAS:
                return _ALIAS[token]
            raise ValueError(f"Unknown domain '{token}' in key '{key}'.")

        for key, rho in d.items():
            # Try splitting at each underscore position to find two valid names
            parts = key.split("_")
            resolved = None
            for split_at in range(1, len(parts)):
                a_tok = "_".join(parts[:split_at])
                b_tok = "_".join(parts[split_at:])
                try:
                    a = _resolve(a_tok, key)
                    b = _resolve(b_tok, key)
                    resolved = (a, b)
                    break
                except ValueError:
                    continue
            if resolved is None:
                raise ValueError(
                    f"Key '{key}' cannot be resolved to two valid domain names."
                )
            a, b = resolved
            i, j = idx[a], idx[b]
            mat[i, j] = rho
            mat[j, i] = rho

        return cls(
            domains=list(DOMAIN_ORDER),
            correlation_matrix=mat,
            perturbation_strength=perturbation_strength,
        )

    # ── Sub-matrix extraction ─────────────────────────────────────────────────

    def sub_matrix(self, domain_names: List[str]) -> "DomainCorrelationMatrix":
        """
        Extract a sub-matrix for the named domain subset.

        Parameters
        ----------
        domain_names : List[str]
            Ordered subset of ``self.domains``.

        Returns
        -------
        DomainCorrelationMatrix
            With ``domains = domain_names`` and the corresponding sub-matrix.
        """
        indices = []
        for name in domain_names:
            if name not in self.domains:
                raise ValueError(
                    f"Domain '{name}' not in this matrix's domains {self.domains}."
                )
            indices.append(self.domains.index(name))
        sub = self.correlation_matrix[np.ix_(indices, indices)]
        return DomainCorrelationMatrix(
            domains=list(domain_names),
            correlation_matrix=sub.copy(),
            perturbation_strength=self.perturbation_strength,
        )

    # ── PD / Cholesky ─────────────────────────────────────────────────────────

    def is_positive_definite(self) -> bool:
        """Return True if all eigenvalues are strictly positive."""
        eigvals = np.linalg.eigvalsh(self.correlation_matrix)
        return bool(np.all(eigvals > 0))

    def cholesky(self) -> np.ndarray:
        """
        Return the lower-triangular Cholesky factor ``L`` such that
        ``L @ L.T ≈ correlation_matrix``.

        Falls back to ``_nearest_psd`` if the matrix is not positive definite.

        Returns
        -------
        np.ndarray
            Shape ``(D, D)`` lower-triangular.
        """
        mat = self.correlation_matrix
        if not self.is_positive_definite():
            mat = _nearest_psd(mat)
        return np.linalg.cholesky(mat)


# ─────────────────────────────────────────────────────────────────────────────
# Predefined instances
# ─────────────────────────────────────────────────────────────────────────────

PREDEFINED_DOMAIN_CORRELATIONS: Dict[str, DomainCorrelationMatrix] = {
    "independent":    DomainCorrelationMatrix.equicorrelation(0.0),
    "expert_default": DomainCorrelationMatrix.expert_default(),
    "low":            DomainCorrelationMatrix.equicorrelation(0.20),
    "moderate":       DomainCorrelationMatrix.equicorrelation(0.40),
}
