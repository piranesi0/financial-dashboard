# Financials — Checkpoint (2026-05-03, updated)

## What this is

Local-first Python/SQLite household financial planning tool for Alex + Charly + Theodore.
No auth, no external deps at runtime, all data stays local.

Run: `make run` (foreground, Ctrl+C to stop) or `make start` / `make stop` (background)
Default DB: `financials.sqlite` (project root). Binds `0.0.0.0:8000` — accessible on LAN.
Install: `make install` (once, installs package into `.venv`).
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

6 routes (some with alias paths) at `http://0.0.0.0:8000`:

| Path | Page | Key content |
|---|---|---|
| `/` | Dashboard | Household net (employment + other income − expenses − savings); Alex, Charly, Housing summary cards |
| `/alex` | Alex Income | Employment breakdown, pension %, RSU section, include-stock toggle |
| `/charly` | Charly Income | 4-scenario comparison table (None/Part-time/Full-time/Flexible); nursery toggle; active scenario card |
| `/housing` | Housing | 3-tab: Current (living with family), Flat (live-in), House purchase; sale proceeds, mortgage calc, affordability, rate comparison, 7% stress test |
| `/tracker` | Monthly Tracker | Grouped expense/income/saving rows, inline edit, stacked bar + group charts |
| `/variables` | Variables | Every assumption editable, grouped by namespace |

Dark mode toggle in header, preference persisted via `localStorage`.

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

## Recently fixed

- **Dashboard net bug**: manual income (rental etc.) was excluded from "Monthly net" — now `total = employment + other_income − expenses − savings`
- **Variables form bug**: `value_type` and `unit` inputs were outside `<form>` tag (split across `<td>`s), silently resetting type to "text" on every save — fixed using `form=` attribute
- **Charly active scenario**: `next()` with no default raised `StopIteration` if `charly_weekly_hours` didn't match a scenario — fixed with fallback to `charly_active.net_monthly`
- **Dark mode**: added toggle (header, localStorage), full CSS variable coverage including tracker group headers
- **LAN access**: server now binds `0.0.0.0:8000` by default
- **Dev UX**: `Makefile` with `make run` / `make start` / `make stop` / `make logs`; `make install` for one-time package install

## Gaps / next steps — see TASKS.md

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
