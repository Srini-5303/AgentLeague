"""Tiny SSE smoke client: drives one turn against a running GM and prints events.

Usage (server must be running):  python scripts/sse_smoke.py "I search the ruined chapel for runes."
"""
from __future__ import annotations

import sys

import httpx

URL = "http://localhost:8000/turn"


def main() -> None:
    player_input = sys.argv[1] if len(sys.argv) > 1 else "I search the ruined chapel for ancient runes."
    with httpx.stream("POST", URL, json={"input": player_input}, timeout=60) as r:
        print(f"HTTP {r.status_code}")
        for line in r.iter_lines():
            if line.startswith("data: "):
                print(line[6:])


if __name__ == "__main__":
    main()
