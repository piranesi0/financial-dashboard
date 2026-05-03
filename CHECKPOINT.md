# Financials — Checkpoint (2026-05-03)

## What this is

Local-first Python/SQLite household financial planning tool for Alex + Charly + Theodore.
No auth, no external deps at runtime, all data stays local.

Run: `uv run financials web <db> --port 8765`
Dev DB: `/tmp/financials-dev.sqlite`
Tests: `uv run pytest` → 41 passing

---

## Current state

### Schema (`src/financials/schema.py`)

| Table | Purpose |
|---|---|
| `scenario` | Named bundles of assumptions (e.g. "baseline") |
| `assumption` | Key/value constants per scenario, editable via web |
| `manual_summary` | Income/expense/saving rows, editable via web |
| `calculator_output` | Persisted results from calculators |
| `source_file` | Provenance for imported xlsx files |
| `workbook_sheet` | Sheet-level profile metadata |
| `transaction_raw` | Raw Monzo transaction rows (schema only, no importer yet) |

### Calculators (`src/financials/calculators/`)

| Module | Inputs → Outputs |
|---|---|
| `income.py` | Alex: base salary + select points → PAYE, NI, pension → net monthly |
| `charly.py` | Hourly rate × weekly hours → gross → pension, PAYE, NI, student loan → net monthly |
| `nursery.py` | Days/week × daily cost → gross; minus term-time funded hours saving → monthly net |
| `housing.py` | Flat sale proceeds; repayment mortgage payment; 4×/4.5× affordability |

### Baseline seed (`src/financials/seeds.py`)

Seeded on every `uv run financials seed-db` or web server start:
- **Housing**: flat balance £259k, sale range £290k–£320k, agent fee 1.25%, solicitor £3,500, house range £300k–£450k, deposit 10%, rate 4.5%, term 25yr, affordability multiples 4×/4.5×
- **Alex income**: base salary £50,495.24, select points £8,622.35, pension 9.2%, tax code 1257L, all PAYE/NI thresholds, stock gross/net
- **Charly income**: hourly £21.90, tax code 1257L, pension 5%, PAYE/NI/student loan (Plan 2) thresholds; four scenario hour counts (0/20/37.5/25), `charly_weekly_hours` = 0 (mat leave default)
- **Nursery**: £70/day, 3 days/week, 15 funded hrs/week, £8.50/hr cost, 9 hrs/day
- **Categorisation**: projects=personal, subscriptions=personal, faster payments=internal, pots=budgeting
- **Fixed bills** (from Finances 2024 structure, values are 2024 baseline — update to current):
  - Income: Flat rental income £1,144/mo
  - Expenses: Flat mortgage £1,124.10, buildings insurance £28.55, car insurance £51.14, car tax £15.75, pet insurance £31.41, Petplan £21, life insurance £13.82, mobile £39.67, gym £36, Spotify £10.99, cloud storage £8.57, Runna £15.99, Ring doorbell £4.99, Lloyds Platinum £16
- **Variable spending** (from one month of Monzo transactions — rough baseline, update or delete):
  Groceries £671.58, personal care £451.06, treats £380, eating out £249.58, etc. Total ~£3,381.81/mo

### Web UI (`src/financials/web.py`)

8 pages at `http://127.0.0.1:8765`:

| Path | Page | Key content |
|---|---|---|
| `/` | Dashboard | Household net/income/expenses/savings; Alex, Charly, Flat summary cards |
| `/alex` | Alex Income | Employment breakdown, pension %, RSU section, include-stock toggle |
| `/charly` | Charly Income | **4-scenario comparison table** (None/Part-time/Full-time/Flexible): gross, pension, tax, NI, student loan, net/mo, nursery cost, net gain; Set active button |
| `/flat` | Flat | Rent vs mortgage vs buildings insurance; fixed rate end date |
| `/sale` | Flat Sale | Sale price form, full proceeds breakdown, quick range table |
| `/purchase` | House Purchase | Price/deposit/rate form; affordability using Alex + Charly active gross; rate comparison; 7% stress test |
| `/expenses` | Expenses & Income | All manual summaries sectioned by type with monthly totals; add + delete |
| `/variables` | Variables | Every assumption editable, grouped by namespace |

---

## Key context / decisions

| Topic | Decision |
|---|---|
| Household scope | Alex + Charly. All household costs come out of Alex for simplicity |
| Charly personal spend | Out of scope for now |
| Transaction imports | Monzo data (2,223 rows Aug 2024–May 2026) not yet imported |
| Savings | Simplify to one pot per person — not yet modelled |
| Housing | Flat sale target Jun 2026. Fixed rate ends Jul 2027. No early repayment charge known |
| Nursery funding | 15 hrs/week (2-year-old entitlement), term time only (38 weeks/year) |
| Charly student loan | Plan 2, threshold £27,295, 9% |
| Auth | None, local only |

---

## Gaps / next steps (prioritised)

### 1. Charly net → household income (broken link — high priority)
`charly_weekly_hours` drives the `/charly` calculators but the Dashboard and Expenses household totals only read `manual_summary` rows. Charly's calculated net take-home never appears in the household income figure. Fix: wire `calculate_charly_income_for_scenario` into `calculate_mvp_summary` and add her net to household income.

### 2. Savings model
One pot each (Alex, Charly). Current balances → 12-month savings trajectory under each Charly scenario. Key question: "if Charly works full-time from September, how much do we have saved by end of 2026?"

### 3. Alex student loan
Likely Plan 1 (pre-2012, threshold ~£24,990, 9%). Not in income calculator yet. Possibly already repaid — needs confirming.

### 4. Debt tracker
MBNA/Barclaycard/Lloyds Credit outstanding balances (trending down in 2024 data). Current monthly repayments can be entered via Expenses but there's no balance/payoff-date model.

### 5. RSU calculator (dynamic)
Currently uses static `alex_stock_gross_annual`/`alex_stock_net_annual` from workbook. Need: vest quantity × $ORCL price × USD/GBP → gross GBP → net after tax withholding. September vest, updates with live or manually entered price.

### 6. Edit manual summaries
Currently add + delete only. Need inline edit so 2024 bill values can be corrected without delete + re-add.

### 7. Scenario cloning
Fork baseline into named scenarios (e.g. "charly-full-time-300k-sale") to compare them side by side.

### 8. Monzo transaction importer
Import `sheets/Monzo Transactions.xlsx` (2,223 rows) into `transaction_raw`. Classify by category; produce rolling 3-month spending averages. Most useful once back in own home and tracking live spending.

---

## File map

```
src/financials/
  cli.py              — CLI entry point (init-db, seed-db, web, ...)
  defaults.py         — All default constants (dataclasses)
  seeds.py            — Baseline scenario seeding
  schema.py           — DB init and table definitions
  scenario.py         — Assumption read/write helpers
  summaries.py        — Manual summary CRUD + household summary calc
  outputs.py          — Calculator output persistence
  mvp.py              — Orchestration: wires calculators + assumptions
  web.py              — 8-page stdlib web UI
  profile_store.py    — xlsx profile persistence
  xlsx.py             — stdlib xlsx profiler
  calculators/
    income.py         — Alex income calculator
    charly.py         — Charly income calculator
    housing.py        — Flat sale, mortgage, affordability
    nursery.py        — Nursery cost calculator

sheets/               — Source xlsx files (local only, not in git)
tests/                — 41 tests
PLAN.md               — Original domain model and decisions
PROJECT.md            — Problem definition
CHECKPOINT.md         — This file
```
