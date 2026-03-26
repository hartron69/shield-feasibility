"""
c5ai_plus/Barentswatch/bw_config.py

Central configuration for the BarentsWatch → C5AI+ integration.

  BW_DATA_DIR       — where fetched files are stored (auto-created)
  FETCHER_PATH      — path to the fetcher script
  OPERATOR_LOCALITIES — mapping: localityNo → site_id / biomass / exposure
"""

from __future__ import annotations

from pathlib import Path

# Output directory for all fetched BarentsWatch files
BW_DATA_DIR = Path(__file__).parent / "data"
BW_DATA_DIR.mkdir(exist_ok=True)

# Absolute path to the fetcher script
FETCHER_PATH = Path(__file__).parent / "barentswatch_c5ai_fetcher_2.0.py"

# ── Operator registry ──────────────────────────────────────────────────────────
# Each operator has:
#   operator_id, operator_name, localities
# Each locality maps Barentswatch localityNo to C5AI+ site metadata.
# biomass_value_nok is estimated from biomass_tonnes × ~65 000 NOK/t applied value.

OPERATOR_LOCALITIES: list[dict] = [
    {
        "operator_id":   "KORNSTAD_HAVBRUK",
        "operator_name": "Kornstad Havbruk AS",
        "localities": [
            {
                "localityNo":       12855,
                "site_id":          "KH_S01",
                "site_name":        "Kornstad",
                "lat":              62.960383,
                "lon":              7.45015,
                "biomass_tonnes":   3000,
                "biomass_value_nok": 195_000_000,
                "fjord_exposure":   "semi_exposed",
            },
            {
                "localityNo":       12870,
                "site_id":          "KH_S02",
                "site_name":        "Leite",
                "lat":              63.03515,
                "lon":              7.676817,
                "biomass_tonnes":   2500,
                "biomass_value_nok": 162_500_000,
                "fjord_exposure":   "semi_exposed",
            },
            {
                "localityNo":       12871,
                "site_id":          "KH_S03",
                "site_name":        "Hogsnes",
                "lat":              63.093033,
                "lon":              7.675883,
                "biomass_tonnes":   2800,
                "biomass_value_nok": 182_000_000,
                "fjord_exposure":   "sheltered",
            },
        ],
    },
]

# Default operator used when no specific operator is selected
DEFAULT_OPERATOR_CFG: dict = OPERATOR_LOCALITIES[0]
