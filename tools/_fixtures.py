import json
from pathlib import Path

import config

# tools/ -> project root -> tests/fixtures
DEFAULT_FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures"


def get_fixtures_dir() -> Path:
    if config.FIXTURES_DIR:
        return Path(config.FIXTURES_DIR)
    return DEFAULT_FIXTURES_DIR


def load_fixture(filename: str):
    """Read a JSON fixture. Returns the parsed data, or {"error": ...} on failure."""
    path = get_fixtures_dir() / filename
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return {"error": f"File not found: {filename}"}
    except json.JSONDecodeError:
        return {"error": f"Invalid JSON in {filename}"}
