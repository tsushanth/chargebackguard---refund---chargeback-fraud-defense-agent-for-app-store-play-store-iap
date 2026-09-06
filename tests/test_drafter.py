from datetime import datetime

from chargebackguard.drafter import draft_response
from chargebackguard.models import App, FlaggedCase, RefundEvent, Transaction, UsageEvent


def test_draft_includes_required_evidence_fields():
    app = App(app_id="app_1", name="TestApp", platform="ios", bundle_id="com.example.testapp")
    transaction = Transaction(
        transaction_id="tx_1",
        app_id="app_1",
        user_id="user_1",
        product_id="pro_unlock",
        purchase_date=datetime(2026, 8, 1, 10, 0, 0),
        price_usd=9.99,
        platform="ios",
        original_transaction_id="tx_1",
        is_family_shared=False,
    )
    refund = RefundEvent(
        refund_id="rf_1",
        transaction_id="tx_1",
        app_id="app_1",
        user_id="user_1",
        refund_date=datetime(2026, 8, 2, 10, 0, 0),
        reason="consumption_request",
        platform="ios",
    )
    usage = [
        UsageEvent(
            event_id="ue_1",
            transaction_id="tx_1",
            app_id="app_1",
            user_id="user_1",
            timestamp=datetime(2026, 8, 1, 20, 0, 0),
            event_type="content_consumed",
            detail="Unlocked all pro features and used them for 3 hours",
        )
    ]
    case = FlaggedCase(
        case_id="consume_then_refund_loop-rf_1",
        pattern="consume_then_refund_loop",
        user_id="user_1",
        app_id="app_1",
        refund_id="rf_1",
        transaction_id="tx_1",
        summary="User user_1 consumed purchased content then refunded within 24h.",
        evidence=["Consumption recorded before refund: Unlocked all pro features"],
    )

    text = draft_response(case, app, transaction, refund, usage)

    # Purchase date
    assert "2026-08-01T10:00:00" in text
    # Consumption amount/duration evidence
    assert "Unlocked all pro features and used them for 3 hours" in text
    # Account identifier available in the data
    assert "user_1" in text
    # Transaction identifiers
    assert "tx_1" in text
    # Pattern-specific recommendation
    assert "recommend denying" in text.lower()


def test_draft_handles_case_with_no_usage_events():
    app = App(app_id="app_1", name="TestApp", platform="ios", bundle_id="com.example.testapp")
    transaction = Transaction(
        transaction_id="tx_2",
        app_id="app_1",
        user_id="user_2",
        product_id="pro_unlock",
        purchase_date=datetime(2026, 8, 1, 10, 0, 0),
        price_usd=9.99,
        platform="ios",
        original_transaction_id="tx_2",
        is_family_shared=False,
    )
    refund = RefundEvent(
        refund_id="rf_2",
        transaction_id="tx_2",
        app_id="app_1",
        user_id="user_2",
        refund_date=datetime(2026, 8, 5, 10, 0, 0),
        reason="cancellation_reason.UNWANTED",
        platform="ios",
    )
    case = FlaggedCase(
        case_id="serial_refunder-rf_2",
        pattern="serial_refunder",
        user_id="user_2",
        app_id="app_1",
        refund_id="rf_2",
        transaction_id="tx_2",
        summary="User user_2 filed 3 refunds within 30 days.",
        evidence=["Refund dates in cluster: 2026-08-05"],
    )

    text = draft_response(case, app, transaction, refund, [])

    assert "No usage events recorded" in text
    assert "user_2" in text
    assert "2026-08-01T10:00:00" in text
