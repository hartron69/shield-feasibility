"""
C5AI+ v5.0 – Site Risk Network (networkx-based).

Represents geographic and biological risk propagation between aquaculture
sites. Sites within a configurable distance share elevated risk when one
site experiences a HAB or disease outbreak.

Architecture
------------
  – Nodes: sites (keyed by site_id)
  – Edges: risk sharing connections (within max_distance_km)
  – Edge weights: inverse-distance decay of risk transfer

Dependency: networkx (optional). If not installed, network risk
adjustment is skipped with a warning.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional

from c5ai_plus.config.c5ai_settings import C5AI_SETTINGS
from c5ai_plus.data_models.biological_input import SiteMetadata

try:
    import networkx as nx
    _NX_AVAILABLE = True
except ImportError:
    _NX_AVAILABLE = False


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points in kilometres."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


class SiteRiskNetwork:
    """
    Build and query a geographic risk-sharing network between sites.

    Parameters
    ----------
    sites : List[SiteMetadata]
    max_distance_km : float
        Maximum distance within which two sites share risk.
    distance_decay : float
        Exponential decay constant controlling how fast risk sharing
        diminishes with distance.
    """

    def __init__(
        self,
        sites: List[SiteMetadata],
        max_distance_km: float = C5AI_SETTINGS.network_max_distance_km,
        distance_decay: float = C5AI_SETTINGS.network_distance_decay,
    ):
        self.sites = {s.site_id: s for s in sites}
        self.max_distance_km = max_distance_km
        self.distance_decay = distance_decay
        self._graph = self._build_graph() if _NX_AVAILABLE else None
        self.available = _NX_AVAILABLE

    def _build_graph(self):
        """Construct weighted networkx graph of site connections."""
        G = nx.Graph()
        site_list = list(self.sites.values())
        G.add_nodes_from(s.site_id for s in site_list)

        for i, s1 in enumerate(site_list):
            for s2 in site_list[i + 1:]:
                dist = _haversine_km(
                    s1.latitude, s1.longitude,
                    s2.latitude, s2.longitude,
                )
                if dist <= self.max_distance_km:
                    # Edge weight = risk transfer coefficient (0–1)
                    weight = math.exp(-self.distance_decay * dist)
                    G.add_edge(s1.site_id, s2.site_id, distance_km=dist, weight=weight)

        return G

    def get_risk_multiplier(self, site_id: str) -> float:
        """
        Return a risk multiplier for the given site based on its network
        neighbourhood.

        A site surrounded by many connected neighbours has elevated risk
        due to potential cross-contamination (e.g. lice from adjacent pens,
        shared HAB water mass).

        Returns
        -------
        float
            Multiplier ≥ 1.0. A site with no neighbours returns 1.0.
            Each connected neighbour contributes weight × 0.15 to the multiplier
            (capped at 1.5).
        """
        if not _NX_AVAILABLE or self._graph is None:
            return 1.0
        if site_id not in self._graph:
            return 1.0

        neighbours = self._graph[site_id]
        total_exposure = sum(
            data.get("weight", 0) for data in neighbours.values()
        )
        multiplier = 1.0 + min(0.50, total_exposure * 0.15)
        return round(multiplier, 4)

    def connected_sites(self, site_id: str) -> List[str]:
        """Return list of site_ids connected to the given site."""
        if not _NX_AVAILABLE or self._graph is None:
            return []
        if site_id not in self._graph:
            return []
        return list(self._graph.neighbors(site_id))

    def network_summary(self) -> Dict[str, object]:
        """Return a summary dict describing network topology."""
        if not _NX_AVAILABLE or self._graph is None:
            return {"available": False, "reason": "networkx not installed"}

        G = self._graph
        return {
            "available": True,
            "n_sites": G.number_of_nodes(),
            "n_connections": G.number_of_edges(),
            "connected_components": nx.number_connected_components(G),
            "site_risk_multipliers": {
                sid: self.get_risk_multiplier(sid)
                for sid in self.sites
            },
        }
