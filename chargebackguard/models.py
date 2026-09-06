"""Dataclasses for the raw records ChargebackGuard reasons over.

Field names loosely mirror the shapes of Apple's App Store Server
Notifications (refund / consumption_request) and Google Play's real-time
developer notifications (voidedPurchases), simplified for local fixtures.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class App:
    app_id: str
    name: str
    platform: str  # "ios" | "android"
    bundle_id: str


@dataclass
class Transaction:
    transaction_id: str
    app_id: str
    user_id: str
    product_id: str
    purchase_date: datetime
    price_usd: float
    platform: str  # "ios" | "android"
    original_transaction_id: str
    is_family_shared: bool = False


@dataclass
class RefundEvent:
    refund_id: str
    transaction_id: str
    app_id: str
    user_id: str
    refund_date: datetime
    reason: str  # e.g. "consumption_request", "cancellation_reason.UNWANTED"
    platform: str
    requested_by_user_id: Optional[str] = None  # differs from purchaser in family-sharing claims


@dataclass
class UsageEvent:
    event_id: str
    transaction_id: str
    app_id: str
    user_id: str
    timestamp: datetime
    event_type: str  # e.g. "content_consumed", "feature_unlocked"
    detail: str = ""  # human-readable consumption detail, quoted in drafts


@dataclass
class FlaggedCase:
    """A single refund event flagged by one or more detectors."""

    case_id: str
    pattern: str  # "serial_refunder" | "consume_then_refund_loop" | "family_sharing_exploit"
    user_id: str
    app_id: str
    refund_id: str
    transaction_id: str
    summary: str
    evidence: List[str] = field(default_factory=list)

