from __future__ import annotations

from abc import ABC, abstractmethod


class BaseProvider(ABC):
    name: str

    @abstractmethod
    def fetch_round(self, competition_id: int, round_number: int) -> dict:
        raise NotImplementedError
