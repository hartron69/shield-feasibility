"""
C5AI+ v5.0 – Forecast Exporter.

Serialises a RiskForecast object to a JSON file on disk.
The output file is the canonical exchange format consumed by the
PCC Feasibility Tool's MonteCarloEngine.
"""

from __future__ import annotations

import json
from pathlib import Path

from c5ai_plus.data_models.forecast_schema import RiskForecast


class ForecastExporter:
    """
    Export a RiskForecast to a JSON file.

    Parameters
    ----------
    output_path : str
        File path for the output JSON. Parent directories are created
        automatically if they do not exist.
    indent : int
        JSON indentation level (default 2).
    """

    def __init__(self, output_path: str = "risk_forecast.json", indent: int = 2):
        self.output_path = Path(output_path)
        self.indent = indent

    def export(self, forecast: RiskForecast) -> Path:
        """
        Write the forecast to disk.

        Parameters
        ----------
        forecast : RiskForecast

        Returns
        -------
        Path
            Absolute path to the written file.
        """
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.output_path, "w", encoding="utf-8") as fh:
            json.dump(forecast.to_dict(), fh, indent=self.indent, ensure_ascii=False)

        return self.output_path.resolve()

    @staticmethod
    def load(path: str) -> RiskForecast:
        """
        Load a RiskForecast from a JSON file.

        Parameters
        ----------
        path : str
            Path to the risk_forecast.json file.

        Returns
        -------
        RiskForecast

        Raises
        ------
        FileNotFoundError
            If the file does not exist.
        ValueError
            If the JSON is malformed or missing required fields.
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(
                f"C5AI+ forecast file not found: {path}\n"
                f"Run 'python -m c5ai_plus.pipeline' to generate it, "
                f"or remove 'c5ai_forecast_path' from input to use static model."
            )

        with open(p, "r", encoding="utf-8") as fh:
            data = json.load(fh)

        try:
            return RiskForecast.from_dict(data)
        except (KeyError, TypeError) as exc:
            raise ValueError(
                f"Could not parse C5AI+ forecast file '{path}': {exc}"
            ) from exc
