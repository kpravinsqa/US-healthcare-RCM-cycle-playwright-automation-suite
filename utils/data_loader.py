import json
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "test_data"


@lru_cache(maxsize=None)
def load(name: str):
    """Load a JSON file from ``test_data`` (cached)."""
    with open(DATA_DIR / f"{name}.json", encoding="utf-8") as fh:
        return json.load(fh)


def cases(name: str, key: str):
    """Return ``pytest.param`` friendly list of (id, case) from a JSON data set."""
    import pytest

    return [pytest.param(case, id=case.get("id", str(i))) for i, case in enumerate(load(name)[key])]
