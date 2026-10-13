import json
from pathlib import Path

# tools/ -> project root -> tests/fixtures
FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures"


def load_fixture(filename: str):
    """Read a JSON fixture. Returns the parsed data, or {"error": ...} on failure."""
    path = FIXTURES_DIR / filename
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return {"error": f"File not found: {filename}"}
    except json.JSONDecodeError:
        return {"error": f"Invalid JSON in {filename}"}