#!/usr/bin/env python3
"""ChargebackGuard CLI: load fixtures -> detect refund abuse -> draft evidence.

Usage:
    python3 main.py --data data/ --out output/
"""

import argparse
from pathlib import Path

from chargebackguard import detectors, report
from chargebackguard.drafter import draft_response
from chargebackguard.loaders import (
    load_apps,
    load_refund_events,
    load_transactions,
    load_usage_events,
)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data", type=Path, default=Path("data"), help="directory with fixture JSON files"
    )
    parser.add_argument(
        "--out", type=Path, default=Path("output"), help="directory to write results to"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    apps = load_apps(args.data)
    transactions = load_transactions(args.data)
    refunds = load_refund_events(args.data)
    usage_events = load_usage_events(args.data)

    apps_by_id = {a.app_id: a for a in apps}
    tx_by_id = {t.transaction_id: t for t in transactions}
    refund_by_id = {r.refund_id: r for r in refunds}
    usage_by_tx = {}
    for u in usage_events:
        usage_by_tx.setdefault(u.transaction_id, []).append(u)

    cases = []
    cases += detectors.serial_refunder(refunds)
    cases += detectors.consume_then_refund_loop(transactions, refunds, usage_events)
    cases += detectors.family_sharing_exploit(transactions, refunds)

    report.print_summary(cases)
    flagged_path = report.write_flagged_cases(cases, args.out)
    print(f"Wrote {flagged_path}")

    drafts_dir = args.out / "drafts"
    drafts_dir.mkdir(parents=True, exist_ok=True)
    for case in cases:
        app = apps_by_id[case.app_id]
        transaction = tx_by_id[case.transaction_id]
        refund = refund_by_id[case.refund_id]
        draft = draft_response(
            case, app, transaction, refund, usage_by_tx.get(case.transaction_id, [])
        )
        draft_path = drafts_dir / f"{case.case_id}.md"
        draft_path.write_text(draft)

    print(f"Wrote {len(cases)} draft(s) to {drafts_dir}")


if __name__ == "__main__":
    main()
