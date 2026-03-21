"""CodeCouncil API server entry point."""
import os
from pathlib import Path

# Load .env from project root (manual, no python-dotenv dependency required)
_env_path = Path(__file__).parents[3] / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _key, _val = _line.split("=", 1)
            os.environ.setdefault(_key.strip(), _val.strip())

from codecouncil.api.app import create_app

app = create_app()
