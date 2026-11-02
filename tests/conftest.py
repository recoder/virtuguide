import hashlib
from pathlib import Path

import pytest

from virtuguide.loader import load_persona, load_tour

ROOT = Path(__file__).parent.parent
TOUR = ROOT / "tours" / "newburyport.yaml"
PERSONA = ROOT / "personas" / "dry-historian.yaml"


class FakeLLM:
    def __init__(self, model_id: str = "fake"):
        self.model_id = model_id
        self.calls = 0

    def complete(self, system: str, user: str) -> str:
        self.calls += 1
        return "story " + hashlib.sha256((system + user).encode()).hexdigest()[:8]


@pytest.fixture
def tour():
    return load_tour(TOUR)


@pytest.fixture
def persona():
    return load_persona(PERSONA)
