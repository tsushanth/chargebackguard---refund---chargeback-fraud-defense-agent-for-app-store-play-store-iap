"""Builds the consumption-evidence dispute text for a flagged case.

The output is Markdown meant to be copy/pasted into App Store Connect's
consumption-request response field or Google Play's refund-dispute form,
both of which accept free-text evidence within a limited response window.
"""

from .models import App, FlaggedCase, RefundEvent, Transaction, UsageEvent

_PATTERN_LABELS = {
    "serial_refunder": "Serial Refunder",
    "consume_then_refund_loop": "Consume-Then-Refund Loop",
    "family_sharing_exploit": "Family-Sharing Refund Exploit",
}

_PATTERN_RECOMMENDATIONS = {
    "serial_refunder": (
        "This account has an established pattern of requesting refunds shortly "
        "after purchase across multiple transactions. We recommend denying this "
        "refund on the grounds of repeated abuse of the refund process."
    ),
    "consume_then_refund_loop": (
        "Usage logs show the purchased content/feature was fully consumed before "
        "the refund was requested, and this pattern has repeated across multiple "
        "transactions from this account. We recommend denying this refund because "
        "the customer received and used the value of the purchase."
    ),
    "family_sharing_exploit": (
        "This refund was requested by a family-sharing member other than the "
        "original purchaser, and/or multiple family members have separately "
        "claimed refunds on the same purchase. We recommend denying or limiting "
        "this refund to a single claim per purchase."
    ),
}


def draft_response(
    case: FlaggedCase,
    app: App,
    transaction: Transaction,
    refund: RefundEvent,
    usage_events: list,
) -> str:
    label = _PATTERN_LABELS.get(case.pattern, case.pattern)
    recommendation = _PATTERN_RECOMMENDATIONS.get(
        case.pattern, "We recommend reviewing this refund request for abuse."
    )

    lines = [
        f"# Consumption-Evidence Response — {case.case_id}",
        "",
        f"**Detected pattern:** {label}",
        f"**App:** {app.name} ({app.bundle_id}, {app.platform})",
        f"**Account identifier:** {case.user_id}",
        f"**Transaction ID:** {transaction.transaction_id} "
        f"(original: {transaction.original_transaction_id})",
        f"**Product:** {transaction.product_id}",
        f"**Purchase date:** {transaction.purchase_date.isoformat()}",
        f"**Purchase price:** ${transaction.price_usd:.2f}",
        f"**Refund requested:** {refund.refund_date.isoformat()} "
        f"(reason given: {refund.reason})",
        "",
        "## Consumption evidence",
        "",
    ]

    if usage_events:
        for u in usage_events:
            lines.append(
                f"- {u.timestamp.isoformat()} — {u.event_type}"
                + (f": {u.detail}" if u.detail else "")
            )
    else:
        lines.append("- No usage events recorded for this transaction.")

    lines += [
        "",
        "## Why this refund should be reviewed",
        "",
        case.summary,
        "",
    ]
    for e in case.evidence:
        lines.append(f"- {e}")

    lines += [
        "",
        "## Recommendation",
        "",
        recommendation,
    ]

    return "\n".join(lines) + "\n"
