from __future__ import annotations

import json
from pathlib import Path

from app.providers.base import BaseProvider


class SofaScoreProvider(BaseProvider):
    name = "sofascore"

    # Fluxo: primeiro rode scripts.download_sofascore_rounds para gerar os JSONs,
    # depois rode scripts.sync_round para persistir no banco.

    def _load_json(self, path: Path) -> dict:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def fetch_round(self, competition_id: int, round_number: int) -> dict:
        backend_dir = Path(__file__).resolve().parents[2]
        data_path = backend_dir / "data" / f"sofascore_round_{round_number:03d}.json"

        if not data_path.exists():
            raise FileNotFoundError(
                f"Missing data file: {data_path}. "
                "Run: python -m scripts.download_sofascore_rounds --season-id 86993 --round 1"
            )

        return self._load_json(data_path)
