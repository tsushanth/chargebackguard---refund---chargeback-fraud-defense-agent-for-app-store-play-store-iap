"""Aggregates flagged cases into a console summary and a JSON report file."""

import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import List

from .models import FlaggedCase


def print_summary(cases: List[FlaggedCase]) -> None:
    if not cases:
        print("No refund-abuse patterns detected in this data set.")
        return

    by_pattern = Counter(c.pattern for c in cases)
    print(f"Flagged {len(cases)} case(s) across {len(by_pattern)} pattern(s):\n")
    for pattern, count in by_pattern.most_common():
        print(f"  {pattern}: {count}")
    print()

    for case in cases:
        print(f"[{case.pattern}] {case.case_id}")
        print(f"  user={case.user_id} app={case.app_id} refund={case.refund_id}")
        print(f"  {case.summary}")
        print()


def write_flagged_cases(cases: List[FlaggedCase], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "flagged_cases.json"
    with path.open("w") as f:
        json.dump([asdict(c) for c in cases], f, indent=2)
    return path
