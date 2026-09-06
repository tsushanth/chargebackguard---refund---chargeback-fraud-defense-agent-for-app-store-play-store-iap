from datetime import datetime

from chargebackguard import detectors
from chargebackguard.models import RefundEvent, Transaction, UsageEvent


def _tx(transaction_id, user_id="user_1", app_id="app_1", original=None, family=False, product="p1"):
    return Transaction(
        transaction_id=transaction_id,
        app_id=app_id,
        user_id=user_id,
        product_id=product,
        purchase_date=datetime(2026, 8, 1, 10, 0, 0),
        price_usd=9.99,
        platform="ios",
        original_transaction_id=original or transaction_id,
        is_family_shared=family,
    )


def _refund(refund_id, transaction_id, refund_date, user_id="user_1", app_id="app_1", requested_by=None):
    return RefundEvent(
        refund_id=refund_id,
        transaction_id=transaction_id,
        app_id=app_id,
        user_id=user_id,
        refund_date=refund_date,
        reason="consumption_request",
        platform="ios",
        requested_by_user_id=requested_by,
    )


def _usage(event_id, transaction_id, timestamp, user_id="user_1", app_id="app_1", detail="used it"):
    return UsageEvent(
        event_id=event_id,
        transaction_id=transaction_id,
        app_id=app_id,
        user_id=user_id,
        timestamp=timestamp,
        event_type="content_consumed",
        detail=detail,
    )


class TestSerialRefunder:
    def test_flags_user_with_many_refunds_in_window(self):
        refunds = [
            _refund("r1", "t1", datetime(2026, 8, 1)),
            _refund("r2", "t2", datetime(2026, 8, 10)),
            _refund("r3", "t3", datetime(2026, 8, 20)),
        ]
        cases = detectors.serial_refunder(refunds, window_days=30, min_refunds=3)
        assert len(cases) == 3
        assert all(c.pattern == "serial_refunder" for c in cases)
        assert all(c.user_id == "user_1" for c in cases)

    def test_does_not_flag_single_legitimate_refund(self):
        refunds = [_refund("r1", "t1", datetime(2026, 8, 1))]
        cases = detectors.serial_refunder(refunds, window_days=30, min_refunds=3)
        assert cases == []

    def test_does_not_flag_refunds_outside_window(self):
        refunds = [
            _refund("r1", "t1", datetime(2026, 1, 1)),
            _refund("r2", "t2", datetime(2026, 4, 1)),
            _refund("r3", "t3", datetime(2026, 8, 1)),
        ]
        cases = detectors.serial_refunder(refunds, window_days=30, min_refunds=3)
        assert cases == []


class TestConsumeThenRefundLoop:
    def test_flags_repeated_consume_then_refund(self):
        transactions = [_tx("t1"), _tx("t2")]
        refunds = [
            _refund("r1", "t1", datetime(2026, 8, 1, 20, 0, 0)),
            _refund("r2", "t2", datetime(2026, 8, 2, 20, 0, 0)),
        ]
        usage = [
            _usage("u1", "t1", datetime(2026, 8, 1, 10, 0, 0)),
            _usage("u2", "t2", datetime(2026, 8, 2, 10, 0, 0)),
        ]
        cases = detectors.consume_then_refund_loop(
            transactions, refunds, usage, max_gap_hours=24, min_occurrences=2
        )
        assert len(cases) == 2
        assert all(c.pattern == "consume_then_refund_loop" for c in cases)

    def test_does_not_flag_single_occurrence(self):
        transactions = [_tx("t1")]
        refunds = [_refund("r1", "t1", datetime(2026, 8, 1, 20, 0, 0))]
        usage = [_usage("u1", "t1", datetime(2026, 8, 1, 10, 0, 0))]
        cases = detectors.consume_then_refund_loop(
            transactions, refunds, usage, max_gap_hours=24, min_occurrences=2
        )
        assert cases == []

    def test_does_not_flag_when_gap_too_large(self):
        transactions = [_tx("t1"), _tx("t2")]
        refunds = [
            _refund("r1", "t1", datetime(2026, 8, 5, 20, 0, 0)),
            _refund("r2", "t2", datetime(2026, 8, 6, 20, 0, 0)),
        ]
        usage = [
            _usage("u1", "t1", datetime(2026, 8, 1, 10, 0, 0)),
            _usage("u2", "t2", datetime(2026, 8, 2, 10, 0, 0)),
        ]
        cases = detectors.consume_then_refund_loop(
            transactions, refunds, usage, max_gap_hours=24, min_occurrences=2
        )
        assert cases == []


class TestFamilySharingExploit:
    def test_flags_refund_by_non_purchasing_family_member(self):
        transactions = [_tx("t1", user_id="purchaser", original="ot1", family=True)]
        refunds = [_refund("r1", "t1", datetime(2026, 8, 1), user_id="purchaser", requested_by="claimant")]
        cases = detectors.family_sharing_exploit(transactions, refunds)
        assert len(cases) == 1
        assert cases[0].pattern == "family_sharing_exploit"
        assert cases[0].user_id == "claimant"

    def test_flags_multiple_claimants_on_same_original_transaction(self):
        transactions = [
            _tx("t1", user_id="purchaser", original="ot1", family=True),
            _tx("t2", user_id="purchaser", original="ot1", family=True),
        ]
        refunds = [
            _refund("r1", "t1", datetime(2026, 7, 1), user_id="purchaser", requested_by="member_a"),
            _refund("r2", "t2", datetime(2026, 8, 1), user_id="purchaser", requested_by="member_b"),
        ]
        cases = detectors.family_sharing_exploit(transactions, refunds)
        assert len(cases) == 2

    def test_does_not_flag_non_family_shared_purchase(self):
        transactions = [_tx("t1", user_id="purchaser", family=False)]
        refunds = [_refund("r1", "t1", datetime(2026, 8, 1), user_id="purchaser", requested_by=None)]
        cases = detectors.family_sharing_exploit(transactions, refunds)
        assert cases == []

    def test_does_not_flag_purchaser_refunding_their_own_shared_purchase(self):
        transactions = [_tx("t1", user_id="purchaser", original="ot1", family=True)]
        refunds = [_refund("r1", "t1", datetime(2026, 8, 1), user_id="purchaser", requested_by=None)]
        cases = detectors.family_sharing_exploit(transactions, refunds)
        assert cases == []
