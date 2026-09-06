# ChargebackGuard — Local MVP Scaffold Plan

## Goal of this MVP

Prove the core value with zero external accounts, zero deployed infra:
**given raw transaction/refund/usage data for a set of apps, detect refund-abuse
patterns and auto-draft the consumption-evidence dispute text a developer would
paste into App Store Connect / Play Console within the response window.**

Everything else (real S2S webhook ingestion, RevenueCat/StoreKit live
integration, actually filing a dispute, multi-tenant SaaS billing) is
downstream of proving this works on real-shaped data.

## 1. Stack

**Plain Python 3, stdlib only.** No framework, no database, no package
installs required beyond a `pytest` dev dependency for tests.

Why: the core logic is pattern-matching over structured records (transactions,
refunds, usage events) and templated text generation. Python's `dataclasses`,
`json`, and `datetime` cover this with no dependencies. A CLI script that
reads local JSON fixtures and writes local output files is the fastest path
to a runnable demo — no server, no compiled binary, no build step.

Rejected alternatives:
- Node/TS CLI — equally viable, but Python's stdlib CSV/JSON/date handling is
  slightly more ergonomic for this data-shape-heavy task, and avoids a
  `package.json`/`tsconfig`/build step entirely.
- Go single binary — better for a distributable tool later, but adds
  compile-step friction for an MVP whose only job is proving the detection +
  drafting logic works.

## 2. Explicitly out of scope for this MVP

- **No auth, no accounts, no multi-tenancy.** Single local user, single run.
- **No billing/Stripe.** Irrelevant to proving detection/drafting works.
- **No hosting or deployment.** Runs via `python3 main.py` on a laptop.
- **No real Apple/Google API calls.** No App Store Connect API auth, no
  Google Play Developer API auth, no RevenueCat API keys. Real S2S
  notification schemas are mimicked with local JSON fixtures shaped like
  Apple's `refund` / `consumption_request` notifications and Google's
  `voidedPurchases`/RTDN payloads, so the detection logic is built against
  realistic fields — but no live credentials or network calls are involved.
- **No automatic filing of disputes.** The tool drafts the response text to
  a local file for a human to copy/paste. Apple/Google don't offer a public
  API to submit consumption-request evidence programmatically today, so
  auto-filing is out of scope for the product, not just the MVP.
- **No web UI/dashboard.** CLI output (stdout + written files) only.
- **No persistent database.** Fixtures and outputs are flat JSON/Markdown
  files on disk.
- **No scheduling/polling daemon.** One-shot CLI run over a fixture snapshot.

Core value (does abuse-pattern detection + evidence drafting actually work
and produce something a developer would find credible?) is fully
demonstrable without any of the above.

## 3. File / directory layout

```
chargebackguard-refund-chargeback-fraud-defense-ag/
├── plan.md                        # this file
├── main.py                        # CLI entrypoint: load fixtures -> detect -> draft -> report
├── chargebackguard/
│   ├── __init__.py
│   ├── models.py                  # dataclasses: Transaction, RefundEvent, UsageEvent, App, User
│   ├── loaders.py                 # read fixture JSON into model objects
│   ├── detectors.py               # pattern functions:
│   │                               #   - serial_refunder (N refunds across time window)
│   │                               #   - consume_then_refund_loop (usage right before refund, repeated)
│   │                               #   - family_sharing_exploit (shared purchase, multiple refund claimants)
│   ├── drafter.py                 # builds consumption-evidence response text per flagged case
│   └── report.py                  # aggregates flagged cases into a summary (console + file)
├── data/
│   ├── apps.json                  # sample: a few of Sushanth's ~15 apps (fictional/anonymized shape)
│   ├── transactions.json          # sample IAP transactions
│   ├── refund_events.json         # sample refund notifications (Apple/Google-shaped fields)
│   └── usage_events.json          # sample consumption/usage logs tied to transactions
├── output/                        # generated at runtime, gitignored
│   ├── flagged_cases.json
│   └── drafts/
│       └── <case_id>.md           # one drafted dispute response per flagged case
├── tests/
│   ├── test_detectors.py          # unit tests per detection pattern, using small inline fixtures
│   └── test_drafter.py            # confirms draft text includes required evidence fields
└── .gitignore                     # ignore output/
```

## 4. Verification

- **Unit tests** (`pytest tests/`): each detector gets 2-3 hand-built cases —
  one that should trigger (e.g., 4 refunds in 30 days across different apps
  by the same user) and one that shouldn't (a single legitimate refund),
  confirming no false positive/negative on the obvious cases. `test_drafter`
  asserts the generated text contains the specific fields Apple/Google
  evidence responses require (purchase date, consumption amount/duration,
  device/account identifiers available in the data).
- **Manual run-through**: `python3 main.py --data data/ --out output/`
  against the checked-in sample fixtures, then inspect:
  1. Console summary listing flagged cases and which pattern matched.
  2. `output/flagged_cases.json` for structured detection output.
  3. `output/drafts/*.md` — read a couple of the generated dispute drafts
     and confirm they read as something a developer could plausibly paste
     into App Store Connect's consumption-request response field.
- No CI, no lint pipeline, no coverage threshold — this is a scaffold to
  prove the concept, not a shippable package yet.
