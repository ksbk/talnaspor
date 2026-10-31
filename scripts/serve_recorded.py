"""Serve Talnaspor from recorded PX-Web responses, without the network: a demo backup.

A question whose PX-Web requests are in evaluation/recordings is answered exactly as when
they were recorded. Any other question is answered without the tables that were not
recorded (often with suggestions only), so keep to the recorded questions. Record them
beforehand by asking them with --record (live, and saved).
Say so when presenting from recordings: the data is as of the recording, and response
times are not those of a live request.

    uv run python scripts/serve_recorded.py [--record] [--port 8001]
"""

import sys

import requests
import uvicorn
from evaluate_understanding import RECORDINGS, recorded


def main() -> None:
    record = "--record" in sys.argv
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8001
    RECORDINGS.mkdir(parents=True, exist_ok=True)
    requests.get = recorded(requests.get, "GET", offline=not record)  # type: ignore[assignment]
    requests.post = recorded(requests.post, "POST", offline=not record)  # type: ignore[assignment]

    from talnaspor.app import app

    print(f"Answering from {'live, recorded' if record else 'recorded'} PX-Web responses.")
    uvicorn.run(app, host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
