"""Refund-abuse pattern detectors.

Each detector takes the full set of loaded records and returns a list of
FlaggedCase objects. A single refund can be flagged by more than one
detector; main.py de-dupes/merges by (refund_id, pattern).
"""

from collections import defaultdict
from datetime import timedelta
from typing import List

from .models import FlaggedCase, RefundEvent, Transaction, UsageEvent

DEFAULT_SERIAL_WINDOW_DAYS = 30
DEFAULT_SERIAL_MIN_REFUNDS = 3
DEFAULT_LOOP_MAX_GAP_HOURS = 24
DEFAULT_LOOP_MIN_OCCURRENCES = 2


def serial_refunder(
    refunds: List[RefundEvent],
    window_days: int = DEFAULT_SERIAL_WINDOW_DAYS,
    min_refunds: int = DEFAULT_SERIAL_MIN_REFUNDS,
) -> List[FlaggedCase]:
    """Flag users who filed >= min_refunds refunds within any window_days
    rolling window, across any of their apps."""
    by_user = defaultdict(list)
    for r in refunds:
        by_user[r.user_id].append(r)

    cases = []
    window = timedelta(days=window_days)
    for user_id, user_refunds in by_user.items():
        ordered = sorted(user_refunds, key=lambda r: r.refund_date)
        for i, anchor in enumerate(ordered):
            cluster = [
                r for r in ordered[i:]
                if r.refund_date - anchor.refund_date <= window
            ]
            if len(cluster) >= min_refunds:
                apps = sorted({r.app_id for r in cluster})
                dates = ", ".join(r.refund_date.date().isoformat() for r in cluster)
                for r in cluster:
                    cases.append(
                        FlaggedCase(
                            case_id=f"serial_refunder-{r.refund_id}",
                            pattern="serial_refunder",
                            user_id=user_id,
                            app_id=r.app_id,
                            refund_id=r.refund_id,
                            transaction_id=r.transaction_id,
                            summary=(
                                f"User {user_id} filed {len(cluster)} refunds within "
                                f"{window_days} days across app(s) {', '.join(apps)}."
                            ),
                            evidence=[
                                f"Refund dates in cluster: {dates}",
                                f"Apps affected: {', '.join(apps)}",
                            ],
                        )
                    )
                break  # this user is flagged; don't re-flag overlapping windows
    return cases


def consume_then_refund_loop(
    transactions: List[Transaction],
    refunds: List[RefundEvent],
    usage_events: List[UsageEvent],
    max_gap_hours: int = DEFAULT_LOOP_MAX_GAP_HOURS,
    min_occurrences: int = DEFAULT_LOOP_MIN_OCCURRENCES,
) -> List[FlaggedCase]:
    """Flag users who repeatedly consume purchased content shortly before
    requesting a refund on that same transaction ("consume then refund")."""
    tx_by_id = {t.transaction_id: t for t in transactions}
    usage_by_tx = defaultdict(list)
    for u in usage_events:
        usage_by_tx[u.transaction_id].append(u)

    gap = timedelta(hours=max_gap_hours)
    occurrences_by_user = defaultdict(list)  # user_id -> list of (refund, usage_events_used)

    for r in refunds:
        tx = tx_by_id.get(r.transaction_id)
        if tx is None:
            continue
        usages = usage_by_tx.get(r.transaction_id, [])
        consumed_before_refund = [
            u for u in usages
            if u.timestamp <= r.refund_date and (r.refund_date - u.timestamp) <= gap
        ]
        if consumed_before_refund:
            occurrences_by_user[r.user_id].append((r, consumed_before_refund))

    cases = []
    for user_id, occurrences in occurrences_by_user.items():
        if len(occurrences) < min_occurrences:
            continue
        for r, consumed in occurrences:
            details = "; ".join(u.detail or u.event_type for u in consumed)
            cases.append(
                FlaggedCase(
                    case_id=f"consume_then_refund_loop-{r.refund_id}",
                    pattern="consume_then_refund_loop",
                    user_id=user_id,
                    app_id=r.app_id,
                    refund_id=r.refund_id,
                    transaction_id=r.transaction_id,
                    summary=(
                        f"User {user_id} consumed purchased content then refunded "
                        f"within {max_gap_hours}h, repeated across "
                        f"{len(occurrences)} separate transactions."
                    ),
                    evidence=[
                        f"Consumption recorded before refund: {details}",
                        f"Gap between consumption and refund request: <= {max_gap_hours}h",
                        f"Pattern repeated {len(occurrences)} times for this user",
                    ],
                )
            )
    return cases


def family_sharing_exploit(
    transactions: List[Transaction],
    refunds: List[RefundEvent],
) -> List[FlaggedCase]:
    """Flag refunds on family-shared purchases requested by a family member
    who did not make the original purchase, especially when the same
    original_transaction_id has multiple refund claimants."""
    tx_by_id = {t.transaction_id: t for t in transactions}

    claimants_by_original_tx = defaultdict(set)
    for r in refunds:
        tx = tx_by_id.get(r.transaction_id)
        if tx is None or not tx.is_family_shared:
            continue
        claimant = r.requested_by_user_id or r.user_id
        claimants_by_original_tx[tx.original_transaction_id].add(claimant)

    cases = []
    for r in refunds:
        tx = tx_by_id.get(r.transaction_id)
        if tx is None or not tx.is_family_shared:
            continue
        claimant = r.requested_by_user_id or r.user_id
        claimants = claimants_by_original_tx[tx.original_transaction_id]
        purchaser_mismatch = claimant != tx.user_id
        multiple_claimants = len(claimants) > 1
        if purchaser_mismatch or multiple_claimants:
            cases.append(
                FlaggedCase(
                    case_id=f"family_sharing_exploit-{r.refund_id}",
                    pattern="family_sharing_exploit",
                    user_id=claimant,
                    app_id=r.app_id,
                    refund_id=r.refund_id,
                    transaction_id=r.transaction_id,
                    summary=(
                        f"Family-shared purchase by {tx.user_id} refunded by "
                        f"{claimant}"
                        + (
                            f"; {len(claimants)} distinct family members have "
                            f"claimed refunds on this purchase"
                            if multiple_claimants
                            else ""
                        )
                        + "."
                    ),
                    evidence=[
                        f"Original purchaser: {tx.user_id}",
                        f"Refund requested by: {claimant}",
                        f"Distinct refund claimants on original_transaction_id "
                        f"{tx.original_transaction_id}: {sorted(claimants)}",
                    ],
                )
            )
    return cases
