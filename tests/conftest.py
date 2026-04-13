from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"

if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


@pytest.fixture
def fixture_path() -> Path:
    return REPO_ROOT / "tests" / "fixtures"


@pytest.fixture
def load_fixture_json(fixture_path: Path):
    def _load(relative_path: str):
        return json.loads((fixture_path / relative_path).read_text(encoding="utf-8"))

    return _load
