#!/usr/bin/env python3
"""Print a comparison table across eval result files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_summary(path: Path) -> dict:
    data = json.loads(path.read_text())
    if "summary" in data:
        return {"label": data.get("label", path.stem), **data["summary"]}
    return {"label": path.stem}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args()

    rows = [load_summary(p) for p in args.files]
    cols = [
        "label",
        "retrieval_hit",
        "citation_correct",
        "not_found_accuracy",
        "wrong_refusals",
        "injection",
        "avg_latency_s",
        "avg_ttft_s",
    ]
    widths = {c: max(len(c), *(len(str(r.get(c, ""))) for r in rows)) for c in cols}
    header = " | ".join(c.ljust(widths[c]) for c in cols)
    print(header)
    print("-+-".join("-" * widths[c] for c in cols))
    for r in rows:
        print(" | ".join(str(r.get(c, "")).ljust(widths[c]) for c in cols))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())