# ChargebackGuard (local MVP scaffold)

An AI agent concept for App Store / Play Store IAP refund-abuse defense.
This scaffold proves the **core value** locally, with no external services:

> Given raw transaction / refund / usage data for a set of apps, detect
> refund-abuse patterns and auto-draft the consumption-evidence dispute text
> a developer would paste into App Store Connect / Play Console within the
> response window.

See [`plan.md`](./plan.md) for the full scoping rationale, including what's
explicitly out of scope for this MVP (auth, billing, live Apple/Google API
calls, auto-filing, a web UI, a database).

## What it does

1. Loads sample fixture data (`data/*.json`) shaped like Apple App Store
   Server Notifications (`refund`, `consumption_request`) and Google Play
   RTDN / `voidedPurchases` payloads — apps, transactions, refund events,
   and usage/consumption events.
2. Runs three abuse-pattern detectors over that data:
   - **`serial_refunder`** — a user filing an unusually high number of
     refunds across a rolling time window, across any of their apps.
   - **`consume_then_refund_loop`** — a user who consumes purchased content
     (e.g. burns hints, unlocks levels) shortly before refunding, repeated
     across multiple transactions.
   - **`family_sharing_exploit`** — a family-shared purchase refunded by a
     family member other than the purchaser, or claimed for refund by more
     than one family member.
3. For every flagged case, drafts a Markdown consumption-evidence response
   (purchase date, price, consumption evidence, and a recommendation) ready
   to copy/paste into Apple's or Google's dispute response field.
4. Writes a structured summary (`output/flagged_cases.json`) and one draft
   per case (`output/drafts/<case_id>.md`), plus a console summary.

## Requirements

Python 3.9+, standard library only. `pytest` is only needed to run the tests.

```bash
pip install pytest   # only needed to run tests
```

## Running it

```bash
python3 main.py --data data/ --out output/
```

Then inspect:

- The console summary printed by the run.
- `output/flagged_cases.json` — structured detection output.
- `output/drafts/*.md` — the generated dispute drafts, e.g.
  `output/drafts/consume_then_refund_loop-rf_2001.md`.

`output/` is gitignored — it's regenerated on every run.

## Running the tests

```bash
python3 -m pytest tests/ -v
```

Each detector has hand-built cases that should and shouldn't trigger it, and
`test_drafter.py` confirms the generated draft text contains the evidence
fields Apple/Google's dispute forms expect (purchase date, consumption
detail, account/transaction identifiers).

## Layout

```
main.py                     CLI entrypoint: load -> detect -> draft -> report
chargebackguard/
  models.py                 Transaction, RefundEvent, UsageEvent, App, FlaggedCase
  loaders.py                fixture JSON -> model objects
  detectors.py               the three abuse-pattern detectors
  drafter.py                 builds the consumption-evidence Markdown per case
  report.py                  console summary + flagged_cases.json
data/                       sample fixtures (fictional/anonymized shape)
output/                     generated at runtime (gitignored)
tests/                      unit tests for detectors + drafter
```

## Why this is worth building

Apple withholds refund-identity data from developers, so indie/small teams
have zero visibility into who requests refunds or why — developer forum
threads describe individual devs manually spotting hundreds of suspected
abuse cases with no tooling. RevenueCat/Appfigures cover analytics, not
auto-contest workflows, so there's no dedicated refund-fraud-defense product
today. This MVP is the smallest slice that proves the detection + drafting
logic actually produces something a developer would find credible, before
any integration, billing, or sales work.
