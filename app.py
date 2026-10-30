"""Entry point for `uvicorn app:app`, as in the organizers' Track 2 setup.

The application lives in src/talnaspor; this file makes it importable from the
repository root after `pip install -r requirements.txt`.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from talnaspor.app import app

__all__ = ["app"]
