"""
Portfolio correlation model for multi-site risk analysis.

Provides a site-to-site risk correlation matrix with factory constructors,
positive-definiteness checks, and Cholesky decomposition for use in the
Monte Carlo site-loss distribution engine.

Simplifying assumptions
-----------------------
* _nearest_psd clips eigenvalues to 1e-8 (rather than a machine-epsilon
  floor) which is robust for correlation matrices with values in [-1, 1].
* from_distance_decay produces symmetric off-diagonals; no geographical
  projection is applied (Euclidean distances in km assumed pre-computed).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np


# ─────────────────────────────────────────────────────────────────────────────
# Nearest PSD helper
# ─────────────────────────────────────────────────────────────────────────────

def _nearest_psd(A: np.ndarray) -> np.ndarray:
    """
    Return the nearest positive semi-definite matrix to A.

    Algorithm
    ---------
    1. Symmetrise A.
    2. Eigendecompose and clip negative eigenvalues to 1e-8.
    3. Reconstruct and renormalise diagonal to 1 (correlation constraint).

    Parameters
    ----------
    A : np.ndarray
        Square symmetric matrix.

    Returns
    -------
    np.ndarray
        Nearest PSD matrix with unit diagonal.
    """
    A = (A + A.T) / 2.0
    eigvals, eigvecs = np.linalg.eigh(A)
    eigvals = np.maximum(eigvals, 1e-8)
    A_psd = eigvecs @ np.diag(eigvals) @ eigvecs.T
    # Renormalise diagonal to 1 (correlation matrix constraint)
    d = np.sqrt(np.diag(A_psd))
    d = np.where(d == 0.0, 1.0, d)
    return A_psd / np.outer(d, d)


# ─────────────────────────────────────────────────────────────────────────────
# Correlation matrix dataclass
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RiskCorrelationMatrix:
    """
    Site-to-site risk correlation matrix.

    Attributes
    ----------
    risk_type : str
        Scope of the correlation estimate: "biological" | "structural" | "all".
    site_ids : List[str]
        Ordered site identifiers corresponding to matrix rows/columns.
    correlation_matrix : np.ndarray
        Shape (S, S). Must be symmetric with unit diagonal.

    Notes
    -----
    The ordering of site_ids must match the ordering of sites passed to
    MonteCarloEngine._distribute_to_sites().
    """

    risk_type: str
    site_ids: List[str]
    correlation_matrix: np.ndarray

    def __post_init__(self) -> None:
        S = len(self.site_ids)
        if self.correlation_matrix.shape != (S, S):
            raise ValueError(
                f"correlation_matrix shape {self.correlation_matrix.shape} "
                f"does not match {S} site_ids"
            )
        if not np.allclose(self.correlation_matrix, self.correlation_matrix.T, atol=1e-6):
            raise ValueError("correlation_matrix must be symmetric")
        if not np.allclose(np.diag(self.correlation_matrix), 1.0, atol=1e-6):
            raise ValueError("correlation_matrix diagonal must be 1")

    # ── Factory constructors ──────────────────────────────────────────────────

    @classmethod
    def equicorrelation(
        cls,
        site_ids: List[str],
        rho: float,
        risk_type: str = "all",
    ) -> "RiskCorrelationMatrix":
        """
        Uniform pairwise correlation rho between all sites.

        Parameters
        ----------
        site_ids : List[str]
        rho : float
            Off-diagonal correlation in [0, 1).
        risk_type : str

        Returns
        -------
        RiskCorrelationMatrix
        """
        if not 0.0 <= rho < 1.0:
            raise ValueError(f"rho must be in [0, 1), got {rho}")
        S = len(site_ids)
        mat = np.full((S, S), rho, dtype=float)
        np.fill_diagonal(mat, 1.0)
        return cls(risk_type=risk_type, site_ids=site_ids, correlation_matrix=mat)

    @classmethod
    def from_distance_decay(
        cls,
        site_ids: List[str],
        distances_km: np.ndarray,
        max_rho: float = 0.6,
        decay: float = 0.05,
        risk_type: str = "biological",
    ) -> "RiskCorrelationMatrix":
        """
        Build a correlation matrix from pairwise distances via exponential decay.

        Formula: rho_ij = max_rho * exp(-decay * distance_km_ij)  for i ≠ j
        Diagonal is set to 1.

        Parameters
        ----------
        site_ids : List[str]
        distances_km : np.ndarray
            Shape (S, S). Symmetric pairwise distance matrix in km.
        max_rho : float
            Maximum correlation at zero distance.
        decay : float
            Exponential decay rate per km (larger → faster decay).
        risk_type : str

        Returns
        -------
        RiskCorrelationMatrix
        """
        S = len(site_ids)
        if distances_km.shape != (S, S):
            raise ValueError(
                f"distances_km shape {distances_km.shape} does not match "
                f"{S} site_ids"
            )
        mat = max_rho * np.exp(-decay * distances_km)
        np.fill_diagonal(mat, 1.0)
        return cls(risk_type=risk_type, site_ids=site_ids, correlation_matrix=mat)

    # ── Properties and methods ────────────────────────────────────────────────

    def is_positive_definite(self) -> bool:
        """Return True if all eigenvalues of the correlation matrix are > 0."""
        eigvals = np.linalg.eigvalsh(self.correlation_matrix)
        return bool(np.all(eigvals > 0))

    def cholesky(self) -> np.ndarray:
        """
        Return lower-triangular Cholesky factor L such that L @ L.T == C.

        If the matrix is not positive definite, the nearest PSD matrix is
        used (with a small eigenvalue floor of 1e-8).

        Returns
        -------
        np.ndarray
            Shape (S, S) lower-triangular matrix.
        """
        mat = self.correlation_matrix
        if not self.is_positive_definite():
            mat = _nearest_psd(mat)
        return np.linalg.cholesky(mat)
