# Financials



Local-first household financial planning tool. Python + SQLite, no external services, no auth.

Built for Alex & Charly's household: income modelling, expense tracking, flat sale / house purchase scenarios, and Charly's return-to-work options.


## Live Preview
https://piranesi0.github.io/financial-dashboard/

## Quick start

```bash
# Create venv and install (editable)
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# Initialise database and seed baseline scenario
financials init-db financials.sqlite
financials seed-db financials.sqlite

# Start web UI
financials web financials.sqlite --port 8765
# → http://127.0.0.1:8765
```

Or without installing:

```bash
PYTHONPATH=src python -c "from financials.web import run_web_app; run_web_app('financials.sqlite', port=8765)"
```

## Web UI pages

| Page | Path | Description |
|------|------|-------------|
| Dashboard | `/` | Household net, Alex + Charly income, housing summary |
| Alex | `/alex` | Static income breakdown (gross → tax → NI → net) |
| Charly | `/charly` | Return-to-work scenarios (part-time / full-time / flexible) + nursery costs |
| Housing | `/housing` | Three tabs: **Current** (£250 keep-in-place), **Flat** (mortgage + sale proceeds), **House** (purchase mortgage + affordability) |
| Tracker | `/tracker` | Grouped expenses (Bills / Household / Personal / Flat) with inline editing, add, delete |
| Variables | `/variables` | All scenario assumptions — editable with type support |

## CLI commands

```
financials init-db <db>                  Create/migrate the database
financials seed-db <db>                  Seed baseline scenario with defaults
financials web <db> [--port 8000]        Start the web UI

financials profile-xlsx <file>...        Profile an Excel workbook (JSON)
financials persist-xlsx-profile <db> <file>...

financials create-scenario <db> <name>
financials list-scenarios <db>
financials list-assumptions <db> [--scenario baseline]
financials set-assumption <db> <ns> <key> <val> [--value-type text]

financials add-manual-summary <db> <scope> <category> <amount> <frequency>
financials household-summary <db>
financials housing-summary [--database <db>] [--sale-price ...] [--house-price ...]
financials mvp-summary <db> [--persist]
```

## Tests

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Project structure

```
src/financials/
  cli.py          CLI entry point
  web.py          Stdlib HTTP web UI (no frameworks)
  schema.py       SQLite schema + migrations
  seeds.py        Baseline scenario seeder (bills, income, expenses)
  defaults.py     Default constants (housing, income, nursery)
  summaries.py    Manual summary CRUD + household totals
  mvp.py          Orchestration layer (calculators + summaries)
  scenario.py     Scenario & assumption read/write
  outputs.py      Calculator output persistence
  calculators/
    housing.py    Mortgage, flat sale, affordability
    income.py     Alex static income (tax, NI, pension)
    charly.py     Charly income scenarios
    nursery.py    Nursery cost calculator

sheets/           Source data & planning docs
tests/            Unit tests (42 passing)
```

## Key design decisions

- **No dependencies** — stdlib only (http.server, sqlite3, xml.etree for xlsx)
- **Scenario-driven** — all assumptions namespaced per scenario, swappable via UI
- **Manual summaries over imports** — expenses entered/edited directly, not bulk-imported from bank
- **Local SQLite** — single file, no server, portable
- **Seeds are one-time** — baseline seeds run on first `seed-db`; after that, edit everything via the web UI
