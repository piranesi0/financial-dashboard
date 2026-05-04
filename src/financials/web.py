from __future__ import annotations

import traceback as _traceback
from dataclasses import asdict, is_dataclass
from decimal import Decimal, InvalidOperation
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

from financials.mvp import (
    calculate_alex_static_income_for_scenario,
    calculate_charly_all_scenarios,
    calculate_charly_income_for_scenario,
    calculate_housing_for_scenario,
    calculate_mvp_summary,
    calculate_nursery_for_scenario,
)
from financials.scenario import get_assumptions, list_scenarios, set_assumption
from financials.schema import connect_database, initialise_database
from financials.seeds import upsert_baseline_scenario
from financials.summaries import ManualSummaryItem, add_manual_summary, delete_manual_summary, list_manual_summaries, monthly_amount, update_manual_summary


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def fmt_money(value: Decimal) -> str:
    return f"£{value:,.2f}"


def fmt_pct(value: Decimal) -> str:
    return f"{value * 100:.2f}%"


def serialise_value(value: object) -> object:
    if isinstance(value, Decimal):
        return format(value, "f")
    if is_dataclass(value):
        return {key: serialise_value(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {key: serialise_value(item) for key, item in value.items()}
    return value


def type_options(selected: str) -> str:
    values = ("text", "money", "decimal", "integer", "percent", "boolean", "list")
    return "".join(
        f'<option value="{escape(value)}" {"selected" if value == selected else ""}>{escape(value)}</option>'
        for value in values
    )


def variable_value_input(item) -> str:
    if item.value_type == "boolean":
        return (
            f'<select name="value">'
            f'<option value="true" {"selected" if item.value == "true" else ""}>true</option>'
            f'<option value="false" {"selected" if item.value == "false" else ""}>false</option>'
            f"</select>"
        )
    return f'<input name="value" value="{escape(item.value)}">'


def selected_scenario(query: dict[str, list[str]]) -> str:
    return query.get("scenario", ["baseline"])[0] or "baseline"


def form_value(form: dict[str, list[str]], key: str, default: str = "") -> str:
    return form.get(key, [default])[0]


def parse_decimal_form(form: dict[str, list[str]], key: str, default: Decimal | None = None) -> Decimal:
    value = form_value(form, key)
    if not value and default is not None:
        return default
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid decimal for {key}: {value}") from exc


# ---------------------------------------------------------------------------
# Page layout
# ---------------------------------------------------------------------------

_NAV_LINKS = [
    ("/", "Dashboard"),
    ("/alex", "Alex"),
    ("/charly", "Charly"),
    ("/housing", "Housing"),
    ("/plan", "Plan"),
    ("/tracker", "Tracker"),
    ("/variables", "Variables"),
]


def html_page(title: str, body: str, scenario: str, current_path: str = "/", message: str = "") -> str:
    escaped_title = escape(title)
    escaped_scenario = escape(scenario)
    banner = f'<div class="message">{escape(message)}</div>' if message else ""
    nav_links = "".join(
        f'<a href="{path}?scenario={escaped_scenario}" class="{"active" if path == current_path else ""}">'
        f'{escape(label)}</a>'
        for path, label in _NAV_LINKS
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escaped_title} — Financials</title>
  <style>
    :root {{
      --bg: #f1f5f9; --surface: #ffffff; --border: #e2e8f0;
      --text: #0f172a; --muted: #64748b; --accent: #2563eb;
      --accent-dark: #1d4ed8; --green: #16a34a; --red: #dc2626;
      --amber: #d97706; --radius: 14px;
      --surface-alt: #f8fafc; --highlight: #eff6ff;
      --tag-income-bg: #dcfce7; --tag-income-fg: #166534;
      --tag-expense-bg: #fee2e2; --tag-expense-fg: #991b1b;
      --tag-saving-bg: #dbeafe; --tag-saving-fg: #1e40af;
      --message-bg: #dcfce7; --message-fg: #166534; --message-border: #86efac;
      color-scheme: light;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, sans-serif;
    }}
    [data-theme="dark"] {{
      --bg: #0f172a; --surface: #1e293b; --border: #334155;
      --text: #f1f5f9; --muted: #94a3b8; --accent: #60a5fa;
      --accent-dark: #3b82f6; --green: #4ade80; --red: #f87171;
      --amber: #fbbf24;
      --surface-alt: #1e293b; --highlight: #1e3a5f;
      --tag-income-bg: #14532d; --tag-income-fg: #86efac;
      --tag-expense-bg: #450a0a; --tag-expense-fg: #fca5a5;
      --tag-saving-bg: #1e3a5f; --tag-saving-fg: #93c5fd;
      --message-bg: #14532d; --message-fg: #86efac; --message-border: #166534;
      color-scheme: dark;
    }}
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: var(--bg); color: var(--text); min-height: 100vh; }}
    header {{ background: linear-gradient(135deg, #172554, #2563eb); color: white;
              display: flex; align-items: center; gap: 24px; padding: 0 32px; height: 56px; }}
    header .brand {{ font-weight: 800; font-size: 18px; color: white; text-decoration: none; white-space: nowrap; }}
    nav {{ display: flex; gap: 4px; flex: 1; }}
    nav a {{ color: #bfdbfe; padding: 6px 12px; border-radius: 8px; text-decoration: none;
             font-size: 14px; font-weight: 600; white-space: nowrap; }}
    nav a:hover {{ background: rgba(255,255,255,0.12); color: white; }}
    nav a.active {{ background: rgba(255,255,255,0.2); color: white; }}
    .scenario-badge {{ font-size: 12px; color: #93c5fd; white-space: nowrap; }}
    main {{ max-width: 1280px; margin: 0 auto; padding: 28px 24px; }}
    h1 {{ font-size: 24px; font-weight: 800; margin-bottom: 20px; }}
    h2 {{ font-size: 18px; font-weight: 700; margin-bottom: 14px; }}
    h3 {{ font-size: 15px; font-weight: 700; margin-bottom: 8px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 20px; }}
    .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }}
    .grid-3 {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 20px; }}
    .card {{ background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius);
             padding: 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }}
    .metric {{ font-size: 28px; font-weight: 800; color: var(--accent); line-height: 1.1; }}
    .metric.green {{ color: var(--green); }}
    .metric.red {{ color: var(--red); }}
    .metric.amber {{ color: var(--amber); }}
    .label {{ font-size: 13px; color: var(--muted); margin-top: 4px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border-bottom: 1px solid var(--border); padding: 10px 12px; text-align: left; font-size: 14px; }}
    th {{ background: var(--surface-alt); color: var(--muted); font-size: 12px; font-weight: 700;
          text-transform: uppercase; letter-spacing: 0.04em; }}
    td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    th.num {{ text-align: right; }}
    tr:last-child td {{ border-bottom: none; }}
    tr.total td {{ font-weight: 700; background: var(--surface-alt); }}
    tr.highlight td {{ background: var(--highlight); font-weight: 700; }}
    input, select, textarea {{
      width: 100%; padding: 9px 12px; border: 1px solid var(--border); border-radius: 10px;
      font: inherit; font-size: 14px; color: var(--text); background: var(--surface);
    }}
    input:focus, select:focus {{ outline: 2px solid var(--accent); border-color: transparent; }}
    label {{ display: block; font-size: 13px; font-weight: 600; color: var(--muted); margin-bottom: 5px; }}
    .form-row {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; align-items: end; }}
    button, .btn {{
      background: var(--accent); color: white; border: 0; padding: 9px 16px;
      border-radius: 10px; font: inherit; font-size: 14px; font-weight: 700;
      cursor: pointer; text-decoration: none; display: inline-block; white-space: nowrap;
    }}
    button:hover, .btn:hover {{ background: var(--accent-dark); }}
    .btn-sm {{ padding: 5px 10px; font-size: 12px; border-radius: 7px; }}
    .btn-danger {{ background: var(--red); }}
    .btn-danger:hover {{ background: #b91c1c; }}
    .btn-success {{ background: var(--green); }}
    .btn-success:hover {{ background: #15803d; }}
    .btn-ghost {{ background: transparent; color: var(--accent); border: 1.5px solid var(--accent); }}
    .btn-ghost:hover {{ background: var(--highlight); }}
    .muted {{ color: var(--muted); font-size: 13px; }}
    .message {{ background: var(--message-bg); color: var(--message-fg); border: 1px solid var(--message-border);
                padding: 12px 16px; border-radius: 10px; margin-bottom: 18px; font-size: 14px; }}
    .danger {{ color: var(--red); }}
    .divider {{ border: none; border-top: 1px solid var(--border); margin: 24px 0; }}
    .scenario-table {{ overflow-x: auto; }}
    .scenario-table table {{ min-width: 600px; }}
    .scenario-table th:not(:first-child), .scenario-table td:not(:first-child) {{ text-align: right; }}
    .active-col td {{ background: var(--highlight) !important; }}
    .breakdown-row {{ display: flex; justify-content: space-between; padding: 8px 0;
                      border-bottom: 1px solid var(--border); font-size: 14px; }}
    .breakdown-row:last-child {{ border-bottom: none; font-weight: 700; }}
    .breakdown-row .amount {{ font-variant-numeric: tabular-nums; }}
    .tag {{ display: inline-block; padding: 2px 8px; border-radius: 20px; font-size: 11px; font-weight: 700; }}
    .tag-income {{ background: var(--tag-income-bg); color: var(--tag-income-fg); }}
    .tag-expense {{ background: var(--tag-expense-bg); color: var(--tag-expense-fg); }}
    .tag-saving {{ background: var(--tag-saving-bg); color: var(--tag-saving-fg); }}
    .bar-chart {{ margin: 0; padding: 0; list-style: none; }}
    .bar-chart li {{ margin-bottom: 10px; }}
    .bar-chart .bar-label {{ display: flex; justify-content: space-between; font-size: 13px; font-weight: 600; margin-bottom: 3px; }}
    .bar-chart .bar-label .bar-amount {{ color: var(--muted); font-variant-numeric: tabular-nums; }}
    .bar-track {{ background: var(--border); border-radius: 6px; height: 22px; overflow: hidden; position: relative; }}
    .bar-fill {{ height: 100%; border-radius: 6px; min-width: 2px; transition: width 0.3s; display: flex; align-items: center; padding-left: 8px; }}
    .bar-fill span {{ font-size: 11px; font-weight: 700; color: white; white-space: nowrap; }}
    .bar-pct {{ position: absolute; right: 8px; top: 50%; transform: translateY(-50%); font-size: 11px; font-weight: 600; color: var(--muted); }}
    .stacked-bar {{ display: flex; height: 32px; border-radius: 8px; overflow: hidden; margin-bottom: 8px; }}
    .stacked-bar div {{ height: 100%; display: flex; align-items: center; justify-content: center;
                        font-size: 11px; font-weight: 700; color: white; min-width: 0; }}
    .legend {{ display: flex; flex-wrap: wrap; gap: 12px; margin-top: 8px; }}
    .legend-item {{ display: flex; align-items: center; gap: 5px; font-size: 12px; font-weight: 600; }}
    .legend-dot {{ width: 10px; height: 10px; border-radius: 50%; }}
    @media (max-width: 768px) {{
      .grid-2, .grid-3 {{ grid-template-columns: 1fr; }}
      header {{ flex-wrap: wrap; height: auto; padding: 12px 16px; gap: 8px; }}
    }}
    #theme-toggle {{
      background: rgba(255,255,255,0.15); color: white; border: 1px solid rgba(255,255,255,0.3);
      padding: 5px 12px; border-radius: 8px; font-size: 13px; font-weight: 600;
      cursor: pointer; white-space: nowrap; flex-shrink: 0;
    }}
    #theme-toggle:hover {{ background: rgba(255,255,255,0.25); }}
  </style>
  <script>
    (function() {{
      var t = localStorage.getItem('theme') || 'light';
      document.documentElement.setAttribute('data-theme', t);
    }})();
  </script>
</head>
<body>
  <header>
    <a class="brand" href="/?scenario={escaped_scenario}">💷 Financials</a>
    <nav>{nav_links}</nav>
    <span class="scenario-badge">Scenario: <strong>{escaped_scenario}</strong></span>
    <button id="theme-toggle" onclick="
      var next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('theme', next);
      this.textContent = next === 'dark' ? '☀ Light' : '☾ Dark';
    "></button>
  </header>
  <main>{banner}{body}</main>
  <script>
    document.getElementById('theme-toggle').textContent =
      document.documentElement.getAttribute('data-theme') === 'dark' ? '☀ Light' : '☾ Dark';
  </script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

class FinancialsWebApp:
    def __init__(self, database_path: Path):
        self.database_path = database_path

    def connection(self):
        return connect_database(self.database_path)

    # -----------------------------------------------------------------------
    # Dashboard
    # -----------------------------------------------------------------------

    def render_summary(self, scenario: str, message: str = "") -> str:
        conn = self.connection()
        try:
            summary = calculate_mvp_summary(conn, scenario, persist=True)
            charly_active = calculate_charly_income_for_scenario(conn, scenario)
            scenarios = list_scenarios(conn)
        finally:
            conn.close()

        alex_net = summary.alex_income.net_income_monthly
        charly_net = charly_active.net_monthly
        employment_income = alex_net + charly_net
        other_income = summary.household.monthly_income
        household_income = employment_income + other_income
        monthly_expenses = summary.household.monthly_expenses
        monthly_savings = summary.household.monthly_savings
        monthly_net = household_income - monthly_expenses - monthly_savings
        net_class = "green" if monthly_net >= 0 else "red"
        scenario_options = "".join(
            f'<option value="{escape(r["name"])}" {"selected" if r["name"] == scenario else ""}>{escape(r["name"])}</option>'
            for r in scenarios
        )
        body = f"""
<div style="display:flex;align-items:center;gap:12px;margin-bottom:20px">
  <h1 style="margin:0">Dashboard</h1>
  <form method="get" action="/" style="margin-left:auto;display:flex;gap:8px;align-items:center">
    <select name="scenario" style="width:auto">{scenario_options}</select>
    <button type="submit" class="btn-sm btn">Switch</button>
  </form>
</div>
<div class="grid">
  <div class="card">
    <div class="metric {net_class}">{fmt_money(monthly_net)}</div>
    <div class="label">Monthly net (household)</div>
  </div>
  <div class="card">
    <div class="metric green">{fmt_money(household_income)}</div>
    <div class="label">Total income (employment + other)</div>
  </div>
  <div class="card">
    <div class="metric red">{fmt_money(monthly_expenses)}</div>
    <div class="label">Monthly expenses</div>
  </div>
  <div class="card">
    <div class="metric">{fmt_money(monthly_savings)}</div>
    <div class="label">Monthly savings</div>
  </div>
</div>
<div class="grid">
  <div class="card">
    <h3>Alex</h3>
    <div class="metric">{fmt_money(alex_net)}</div>
    <div class="label">Net / month (primary income)</div>
    <hr class="divider" style="margin:12px 0">
    <div class="muted">Gross employment: {fmt_money(summary.alex_income.gross_employment_income_annual)}/yr</div>
    <div class="muted">Pension: {fmt_money(summary.alex_income.pension_contribution_annual)}/yr</div>
    <div class="muted">Tax + NI: {fmt_money(summary.alex_income.income_tax_annual + summary.alex_income.national_insurance_annual)}/yr</div>
    <a href="/alex?scenario={escape(scenario)}" class="btn btn-ghost btn-sm" style="margin-top:12px">Details →</a>
  </div>
  <div class="card">
    <h3>Charly</h3>
    <div class="metric {"green" if charly_net > 0 else "muted"}">{fmt_money(charly_net)}</div>
    <div class="label">Net / month ({charly_active.weekly_hours} hrs/week)</div>
    <hr class="divider" style="margin:12px 0">
    <div class="muted">Gross: {fmt_money(charly_active.gross_monthly)}/mo</div>
    <div class="muted">Tax + NI: {fmt_money((charly_active.income_tax_annual + charly_active.national_insurance_annual) / 12)}/mo</div>
    <div class="muted">Student loan: {fmt_money(charly_active.student_loan_annual / 12)}/mo</div>
    <a href="/charly?scenario={escape(scenario)}" class="btn btn-ghost btn-sm" style="margin-top:12px">Scenarios →</a>
  </div>
  <div class="card">
    <h3>Housing</h3>
    <div class="metric">{fmt_money(summary.housing.flat_sale.net_proceeds)}</div>
    <div class="label">Flat sale net proceeds</div>
    <hr class="divider" style="margin:12px 0">
    <div class="muted">New house mortgage: {fmt_money(summary.housing.mortgage.monthly_payment)}/mo</div>
    <div class="muted">Afford 4x: {fmt_money(summary.housing.affordability.low_max_purchase_price)}</div>
    <div class="muted">Afford 4.5x: {fmt_money(summary.housing.affordability.high_max_purchase_price)}</div>
    <a href="/housing?scenario={escape(scenario)}" class="btn btn-ghost btn-sm" style="margin-top:12px">Housing details →</a>
  </div>
</div>"""
        return html_page("Dashboard", body, scenario, "/", message)

    # -----------------------------------------------------------------------
    # Alex Income
    # -----------------------------------------------------------------------

    def render_alex(self, scenario: str, message: str = "") -> str:
        conn = self.connection()
        try:
            result = calculate_alex_static_income_for_scenario(conn, scenario, persist=True)
            assumptions = get_assumptions(conn, scenario)
        finally:
            conn.close()

        include_stock = assumptions.get(("income", "alex_include_stock_in_static_income"))
        include_stock_val = include_stock.value if include_stock else "false"
        stock_gross = assumptions.get(("income", "alex_stock_gross_annual"))
        stock_net = assumptions.get(("income", "alex_stock_net_annual"))
        stock_gross_val = Decimal(stock_gross.value) if stock_gross else Decimal("0")
        stock_net_val = Decimal(stock_net.value) if stock_net else Decimal("0")

        body = f"""
<h1>Alex Income</h1>
<div class="grid">
  <div class="card">
    <div class="metric">{fmt_money(result.net_income_monthly)}</div>
    <div class="label">Net / month (employment)</div>
  </div>
  <div class="card">
    <div class="metric">{fmt_money(result.gross_employment_income_annual)}</div>
    <div class="label">Gross employment / year</div>
  </div>
  <div class="card">
    <div class="metric amber">{fmt_money(result.income_tax_annual + result.national_insurance_annual)}</div>
    <div class="label">Tax + NI / year</div>
  </div>
  <div class="card">
    <div class="metric">{fmt_money(result.pension_contribution_annual)}</div>
    <div class="label">Pension / year</div>
  </div>
</div>
<div class="grid-2">
  <div class="card">
    <h2>Employment breakdown</h2>
    <table>
      <tbody>
        <tr><td>Base salary</td><td class="num">{fmt_money(result.base_salary_annual)}/yr</td></tr>
        <tr><td>Select points income</td><td class="num">{fmt_money(result.select_income_annual)}/yr</td></tr>
        <tr class="total"><td>Gross employment</td><td class="num">{fmt_money(result.gross_employment_income_annual)}/yr</td></tr>
        <tr><td>Pension ({fmt_pct(Decimal(assumptions[("income","alex_pension_contribution_rate")].value) if ("income","alex_pension_contribution_rate") in assumptions else Decimal("0"))})</td><td class="num">−{fmt_money(result.pension_contribution_annual)}/yr</td></tr>
        <tr><td>Taxable income</td><td class="num">{fmt_money(result.taxable_income_annual)}/yr</td></tr>
        <tr><td>Income tax</td><td class="num">−{fmt_money(result.income_tax_annual)}/yr</td></tr>
        <tr><td>National Insurance</td><td class="num">−{fmt_money(result.national_insurance_annual)}/yr</td></tr>
        <tr><td>Student loan (Plan 2)</td><td class="num">−{fmt_money(result.student_loan_annual)}/yr</td></tr>
        <tr class="total"><td>Net annual</td><td class="num">{fmt_money(result.net_income_annual)}/yr</td></tr>
        <tr class="highlight"><td>Net monthly</td><td class="num">{fmt_money(result.net_income_monthly)}/mo</td></tr>
      </tbody>
    </table>
  </div>
  <div class="card">
    <h2>RSU / Stock</h2>
    <p class="muted" style="margin-bottom:14px">Oracle RSUs vest in September. Values based on seeded workbook data — update via Variables.</p>
    <table>
      <tbody>
        <tr><td>Gross RSU / year</td><td class="num">{fmt_money(stock_gross_val)}</td></tr>
        <tr><td>Net RSU / year (after withholding)</td><td class="num">{fmt_money(stock_net_val)}</td></tr>
        <tr><td>Net RSU / month</td><td class="num">{fmt_money(stock_net_val / 12)}</td></tr>
        <tr><td>Effective RSU tax rate</td><td class="num">{fmt_pct((stock_gross_val - stock_net_val) / stock_gross_val) if stock_gross_val else "—"}</td></tr>
      </tbody>
    </table>
    <hr class="divider" style="margin:14px 0">
    <form method="post" action="/variables?scenario={escape(scenario)}">
      <input type="hidden" name="namespace" value="income">
      <input type="hidden" name="key" value="alex_include_stock_in_static_income">
      <input type="hidden" name="unit" value="">
      <input type="hidden" name="value_type" value="boolean">
      <div class="form-row" style="align-items:center">
        <div>
          <label>Include RSU in monthly net</label>
          <select name="value">
            <option value="true" {"selected" if include_stock_val == "true" else ""}>Yes — include £{stock_net_val/12:,.2f}/mo</option>
            <option value="false" {"selected" if include_stock_val != "true" else ""}>No — exclude stock</option>
          </select>
        </div>
        <div><button type="submit">Update</button></div>
      </div>
    </form>
    {"<div style='margin-top:12px;padding:12px;background:var(--highlight);border-radius:10px'><strong>With RSU:</strong> " + fmt_money(result.net_income_monthly + stock_net_val / 12) + "/mo</div>" if include_stock_val != "true" else ""}
  </div>
</div>"""
        return html_page("Alex Income", body, scenario, "/alex", message)

    # -----------------------------------------------------------------------
    # Charly Income
    # -----------------------------------------------------------------------

    def render_charly(self, scenario: str, message: str = "") -> str:
        conn = self.connection()
        try:
            scenarios = calculate_charly_all_scenarios(conn, scenario)
            charly_active = calculate_charly_income_for_scenario(conn, scenario)
            nursery = calculate_nursery_for_scenario(conn, scenario)
            assumptions = get_assumptions(conn, scenario)
        finally:
            conn.close()

        active_hours = charly_active.weekly_hours
        nursery_enabled = assumptions.get(("nursery", "enabled"))
        nursery_on = nursery_enabled is None or nursery_enabled.value.lower() == "true"

        cols = [
            ("none", "None", "0 hrs/wk"),
            ("part_time", "Part-time", f"{scenarios['part_time'].weekly_hours} hrs/wk"),
            ("full_time", "Full-time", f"{scenarios['full_time'].weekly_hours} hrs/wk"),
            ("flexible", "Flexible", f"{scenarios['flexible'].weekly_hours} hrs/wk"),
        ]

        def is_active(label: str) -> bool:
            return scenarios[label].weekly_hours == active_hours

        def col_class(label: str) -> str:
            return "active-col" if is_active(label) else ""

        def charly_row(row_label: str, fn) -> str:
            cells = "".join(
                f'<td class="num {col_class(label)}">{fn(scenarios[label])}</td>'
                for label, _, _ in cols
            )
            return f"<tr><td>{row_label}</td>{cells}</tr>"

        nursery_cost_for_col = nursery.monthly_net_cost if nursery_on else Decimal("0")
        nursery_row_html = "".join(
            f'<td class="num {col_class(label)}">'
            f'{"—" if scenarios[label].weekly_hours == 0 else (fmt_money(nursery_cost_for_col) if nursery_on else "<span class=muted>disabled</span>")}'
            f'</td>'
            for label, _, _ in cols
        )
        net_gain_row = "".join(
            f'<td class="num {col_class(label)}" style="font-weight:700">'
            f'{"—" if scenarios[label].weekly_hours == 0 else fmt_money(scenarios[label].net_monthly - nursery_cost_for_col)}'
            f'</td>'
            for label, _, _ in cols
        )
        set_btn_row = "".join(
            f"""<td class="num {col_class(label)}">
              <form method="post" action="/charly?scenario={escape(scenario)}">
                <input type="hidden" name="_action" value="set_hours">
                <input type="hidden" name="hours" value="{scenarios[label].weekly_hours}">
                <button type="submit" class="btn btn-sm {"btn-success" if not is_active(label) else "btn-ghost"}">
                  {"Active ✓" if is_active(label) else "Set active"}
                </button>
              </form>
            </td>"""
            for label, _, _ in cols
        )
        header_row = "".join(
            f'<th class="num {col_class(label)}">{name}<br><span class="muted">{hrs}</span></th>'
            for label, name, hrs in cols
        )

        nursery_toggle_label = "Disable" if nursery_on else "Enable"
        nursery_toggle_value = "false" if nursery_on else "true"
        nursery_toggle_class = "btn-danger" if nursery_on else "btn-success"
        nursery_status = f'<span class="tag tag-income">Enabled</span>' if nursery_on else '<span class="tag tag-expense">Disabled</span>'

        nursery_toggle_btn = f"""
<form method="post" action="/charly?scenario={escape(scenario)}" style="display:inline">
  <input type="hidden" name="_action" value="toggle_nursery">
  <input type="hidden" name="enabled" value="{nursery_toggle_value}">
  <button type="submit" class="btn btn-sm {nursery_toggle_class}">{nursery_toggle_label} nursery costs</button>
</form>"""

        nursery_calculator_html = ""
        if nursery_on:
            nursery_calculator_html = f"""
  <div class="card">
    <h2>Nursery calculator</h2>
    <table>
      <tbody>
        <tr><td>Days / week</td><td class="num">{nursery.days_per_week}</td></tr>
        <tr><td>Daily cost</td><td class="num">{fmt_money(Decimal(assumptions[("nursery","daily_cost")].value))}</td></tr>
        <tr><td>Gross monthly</td><td class="num">{fmt_money(nursery.monthly_gross_cost)}</td></tr>
        <tr><td>Funded hours / week</td><td class="num">{nursery.weekly_funded_hours_applied} hrs</td></tr>
        <tr><td>Funded saving / month</td><td class="num">−{fmt_money(nursery.monthly_funded_saving)}</td></tr>
        <tr class="total"><td>Net nursery / month</td><td class="num">{fmt_money(nursery.monthly_net_cost)}</td></tr>
        <tr><td>Net nursery / year</td><td class="num">{fmt_money(nursery.annual_net_cost)}</td></tr>
      </tbody>
    </table>
    <p class="muted" style="margin-top:12px">Funded hours apply during term time only (~38 weeks/year). Update assumptions via <a href="/variables?scenario={escape(scenario)}">Variables</a>.</p>
  </div>"""
        else:
            nursery_calculator_html = f"""
  <div class="card">
    <h2>Nursery costs {nursery_status}</h2>
    <p class="muted">Nursery costs are currently excluded from calculations. Click the button below to include them.</p>
    <div style="margin-top:12px">{nursery_toggle_btn}</div>
  </div>"""

        body = f"""
<h1>Charly Income</h1>
<div class="card" style="margin-bottom:16px;display:flex;align-items:center;gap:12px;padding:14px 20px">
  <span style="font-weight:700">Nursery costs</span> {nursery_status}
  <span style="margin-left:auto">{nursery_toggle_btn}</span>
</div>
<div class="scenario-table card" style="margin-bottom:20px">
  <h2>Work scenarios — £{float(assumptions[("income","charly_hourly_rate")].value):.2f}/hr</h2>
  <table>
    <thead>
      <tr>
        <th></th>
        {header_row}
      </tr>
    </thead>
    <tbody>
      {charly_row("Gross / year", lambda r: fmt_money(r.gross_annual))}
      {charly_row("Gross / month", lambda r: fmt_money(r.gross_monthly))}
      {charly_row("Pension / year", lambda r: f"−{fmt_money(r.pension_annual)}")}
      {charly_row("Income tax / year", lambda r: f"−{fmt_money(r.income_tax_annual)}")}
      {charly_row("National Insurance / yr", lambda r: f"−{fmt_money(r.national_insurance_annual)}")}
      {charly_row("Student loan / year", lambda r: f"−{fmt_money(r.student_loan_annual)}")}
      <tr class="highlight"><td>Net / month</td>{"".join(f'<td class="num {col_class(label)}">{fmt_money(scenarios[label].net_monthly)}</td>' for label,_,_ in cols)}</tr>
      <tr><td colspan="5"><hr class="divider" style="margin:4px 0"></td></tr>
      <tr><td>Nursery cost / month</td>{nursery_row_html}</tr>
      <tr class="total"><td>Net gain / month</td>{net_gain_row}</tr>
      <tr><td></td>{set_btn_row}</tr>
    </tbody>
  </table>
</div>
<div class="grid-2">
  {nursery_calculator_html}
  <div class="card">
    <h2>Active scenario</h2>
    <div class="metric {"green" if active_hours > 0 else "muted"}">{fmt_money(scenarios["none"].net_monthly if active_hours == 0 else next((r.net_monthly for r in scenarios.values() if r.weekly_hours == active_hours), charly_active.net_monthly))}</div>
    <div class="label">Charly net / month at {active_hours} hrs/wk</div>
    <p class="muted" style="margin-top:12px">This feeds into the Dashboard and Purchase affordability. Click <strong>Set active</strong> in the table to switch scenario.</p>
  </div>
</div>"""
        return html_page("Charly Income", body, scenario, "/charly", message)

    # -----------------------------------------------------------------------
    # Housing (unified: Current / Flat / House tabs)
    # -----------------------------------------------------------------------

    def render_housing(self, scenario: str, tab: str = "current",
                       sale_price: Decimal | None = None,
                       house_price: Decimal | None = None,
                       deposit_rate: Decimal | None = None,
                       mortgage_rate: Decimal | None = None,
                       message: str = "") -> str:
        from financials.calculators.housing import MortgageInput, calculate_repayment_mortgage
        conn = self.connection()
        try:
            assumptions = get_assumptions(conn, scenario)
            summaries = list_manual_summaries(conn, scenario)
            alex_income = calculate_alex_static_income_for_scenario(conn, scenario)
            charly_active = calculate_charly_income_for_scenario(conn, scenario)
            combined_gross = alex_income.gross_employment_income_annual + charly_active.gross_annual
            housing = calculate_housing_for_scenario(
                conn, scenario,
                sale_price=sale_price,
                house_price=house_price,
                deposit_rate=deposit_rate,
                mortgage_rate=mortgage_rate,
                combined_gross_income=combined_gross,
            )
        finally:
            conn.close()

        rent = Decimal(assumptions[("housing", "current_rent_income")].value) if ("housing", "current_rent_income") in assumptions else Decimal("0")
        flat_mortgage_pmt = Decimal(assumptions[("housing", "current_mortgage_payment")].value) if ("housing", "current_mortgage_payment") in assumptions else Decimal("0")
        balance = Decimal(assumptions[("housing", "flat_mortgage_balance")].value) if ("housing", "flat_mortgage_balance") in assumptions else Decimal("0")
        buildings_ins = next((Decimal(i.amount) for i in summaries if "buildings insurance" in i.category.lower()), Decimal("28.55"))

        # Household bills that apply when living independently (flat or house)
        HOUSEHOLD_BILL_CATEGORIES = {"council tax", "water", "gas & electric", "broadband", "tv licence", "home insurance"}
        household_bills: list[tuple[str, Decimal]] = []
        for i in summaries:
            if i.scope == "expense" and i.category.lower() in HOUSEHOLD_BILL_CATEGORIES:
                household_bills.append((i.category, monthly_amount(Decimal(str(i.amount)), i.frequency)))
        household_bills.sort(key=lambda x: x[1], reverse=True)
        household_bills_total = sum(amt for _, amt in household_bills)

        keep_in_place = Decimal("250")
        current_housing_cost = keep_in_place
        flat_housing_cost = flat_mortgage_pmt + buildings_ins
        flat_net = rent - flat_housing_cost

        sale_price_low = Decimal(assumptions[("housing", "flat_sale_price_low")].value)
        sale_price_high = Decimal(assumptions[("housing", "flat_sale_price_high")].value)
        agent_rate = Decimal(assumptions[("housing", "estate_agent_fee_rate")].value)
        sol_fee = Decimal(assumptions[("housing", "solicitor_fee")].value)

        price_low = Decimal(assumptions[("housing", "house_price_low")].value)
        price_high = Decimal(assumptions[("housing", "house_price_high")].value)
        resolved_house_price = house_price or price_low
        resolved_rate = mortgage_rate or Decimal(assumptions[("housing", "default_mortgage_rate")].value)
        resolved_deposit = deposit_rate or Decimal(assumptions[("housing", "default_deposit_rate")].value)
        resolved_sale_price = sale_price or sale_price_low

        rate_options = [Decimal("0.035"), Decimal("0.04"), Decimal("0.045"), Decimal("0.05"), Decimal("0.055"), Decimal("0.06")]
        alex_gross = alex_income.gross_employment_income_annual
        charly_gross = charly_active.gross_annual
        a = housing.affordability
        m = housing.mortgage
        r = housing.flat_sale

        # Reusable bills breakdown for flat / house tabs
        bills_rows_html = "".join(
            f'<tr><td>{escape(cat)}</td><td class="num" style="color:var(--red)">−{fmt_money(amt)}/mo</td></tr>'
            for cat, amt in household_bills
        )
        bills_section_html = f"""
<div class="card" style="margin-bottom:20px">
  <h2>Household bills</h2>
  <table>
    <tbody>
      {bills_rows_html}
      <tr class="highlight"><td>Total bills</td><td class="num" style="color:var(--red)">−{fmt_money(household_bills_total)}/mo</td></tr>
    </tbody>
  </table>
  <p class="muted" style="margin-top:8px">Edit amounts on the <a href="/tracker?scenario={escape(scenario)}">Tracker</a> page.</p>
</div>"""

        def tab_class(t: str) -> str:
            return "active" if t == tab else ""

        tab_bar = f"""
<div style="display:flex;gap:4px;margin-bottom:20px">
  <a href="/housing?scenario={escape(scenario)}&tab=current" class="btn btn-sm {"btn" if tab == "current" else "btn-ghost"}">Current</a>
  <a href="/housing?scenario={escape(scenario)}&tab=flat" class="btn btn-sm {"btn" if tab == "flat" else "btn-ghost"}">Flat</a>
  <a href="/housing?scenario={escape(scenario)}&tab=house" class="btn btn-sm {"btn" if tab == "house" else "btn-ghost"}">House</a>
</div>"""

        if tab == "current":
            body = f"""
<h1>Housing — Current</h1>
{tab_bar}
<p class="muted" style="margin-bottom:20px">Living with family. No mortgage — £{keep_in_place:,.0f}/mo keep-in-place contribution. Flat is let to tenants generating rental income.</p>
<div class="grid">
  <div class="card">
    <div class="metric amber">{fmt_money(current_housing_cost)}</div>
    <div class="label">Monthly housing cost (keep-in-place)</div>
  </div>
  <div class="card">
    <div class="metric green">{fmt_money(rent)}</div>
    <div class="label">Flat rental income / month</div>
  </div>
  <div class="card">
    <div class="metric amber">{fmt_money(flat_housing_cost)}</div>
    <div class="label">Flat costs (mortgage + insurance)</div>
  </div>
  <div class="card">
    <div class="metric {"green" if flat_net >= 0 else "red"}">{fmt_money(flat_net)}</div>
    <div class="label">Net from flat / month</div>
  </div>
</div>
<div class="card">
  <h2>Summary</h2>
  <table>
    <tbody>
      <tr><td>Keep-in-place contribution</td><td class="num" style="color:var(--red)">−{fmt_money(keep_in_place)}/mo</td></tr>
      <tr><td>Flat rental income</td><td class="num" style="color:var(--green)">+{fmt_money(rent)}/mo</td></tr>
      <tr><td>Flat mortgage</td><td class="num" style="color:var(--red)">−{fmt_money(flat_mortgage_pmt)}/mo</td></tr>
      <tr><td>Flat buildings insurance</td><td class="num" style="color:var(--red)">−{fmt_money(buildings_ins)}/mo</td></tr>
      <tr class="highlight"><td>Net housing position</td><td class="num">{fmt_money(rent - flat_housing_cost - keep_in_place)}/mo</td></tr>
    </tbody>
  </table>
</div>"""

        elif tab == "flat":
            flat_living_cost = flat_mortgage_pmt + buildings_ins + household_bills_total
            body = f"""
<h1>Housing — Flat</h1>
{tab_bar}
<p class="muted" style="margin-bottom:20px">Living in the flat with existing mortgage. Outstanding balance: {fmt_money(balance)}. No rental income in this scenario.</p>
<div class="grid">
  <div class="card">
    <div class="metric amber">{fmt_money(flat_mortgage_pmt)}</div>
    <div class="label">Mortgage / month</div>
  </div>
  <div class="card">
    <div class="metric">{fmt_money(buildings_ins)}</div>
    <div class="label">Buildings insurance / month</div>
  </div>
  <div class="card">
    <div class="metric amber">{fmt_money(household_bills_total)}</div>
    <div class="label">Household bills / month</div>
  </div>
  <div class="card">
    <div class="metric red">{fmt_money(flat_living_cost)}</div>
    <div class="label">Total living cost / month</div>
  </div>
</div>
<div class="card" style="margin-bottom:20px">
  <h2>Monthly costs</h2>
  <table>
    <tbody>
      <tr><td>Mortgage</td><td class="num" style="color:var(--red)">−{fmt_money(flat_mortgage_pmt)}/mo</td></tr>
      <tr><td>Buildings insurance</td><td class="num" style="color:var(--red)">−{fmt_money(buildings_ins)}/mo</td></tr>
      {bills_rows_html}
      <tr class="highlight"><td>Total living cost</td><td class="num" style="color:var(--red)">−{fmt_money(flat_living_cost)}/mo</td></tr>
    </tbody>
  </table>
</div>
<div class="grid-2">
  <div class="card">
    <h2>Sale proceeds</h2>
    <form method="get" action="/housing" style="margin-bottom:14px">
      <input type="hidden" name="scenario" value="{escape(scenario)}">
      <input type="hidden" name="tab" value="flat">
      <div class="form-row">
        <div>
          <label>Sale price ({fmt_money(sale_price_low)} – {fmt_money(sale_price_high)})</label>
          <input name="sale_price" type="number" step="1000" value="{resolved_sale_price}">
        </div>
        <div><label>&nbsp;</label><button type="submit">Calculate</button></div>
      </div>
    </form>
    <div class="breakdown-row"><span>Sale price</span><span class="amount">{fmt_money(r.sale_price)}</span></div>
    <div class="breakdown-row"><span>Agent fee ({fmt_pct(agent_rate)})</span><span class="amount" style="color:var(--red)">−{fmt_money(r.estate_agent_fee)}</span></div>
    <div class="breakdown-row"><span>Solicitor</span><span class="amount" style="color:var(--red)">−{fmt_money(r.solicitor_fee)}</span></div>
    <div class="breakdown-row"><span>Outstanding mortgage</span><span class="amount" style="color:var(--red)">−{fmt_money(r.outstanding_mortgage)}</span></div>
    <div class="breakdown-row"><span style="font-weight:700">Net proceeds</span><span class="amount" style="font-weight:700;color:{"var(--green)" if r.net_proceeds >= 0 else "var(--red)"}">{fmt_money(r.net_proceeds)}</span></div>
  </div>
  <div class="card">
    <h2>Quick range</h2>
    <table>
      <thead><tr><th>Sale price</th><th class="num">Net proceeds</th></tr></thead>
      <tbody>
        {"".join(f'<tr{"" if p != int(resolved_sale_price) else " class=highlight"}><td>{fmt_money(Decimal(p))}</td><td class="num">{fmt_money(Decimal(p) - Decimal(p)*agent_rate - sol_fee - balance)}</td></tr>' for p in range(int(sale_price_low), int(sale_price_high)+1, 5000))}
      </tbody>
    </table>
  </div>
</div>"""

        else:  # house
            rate_opts_html = "".join(
                f'<option value="{rt}" {"selected" if rt == resolved_rate else ""}>{fmt_pct(rt)}</option>'
                for rt in rate_options
            )
            dep_options = [Decimal("0.05"), Decimal("0.10"), Decimal("0.15"), Decimal("0.20")]
            dep_opts_html = "".join(
                f'<option value="{d}" {"selected" if d == resolved_deposit else ""}>{fmt_pct(d)}</option>'
                for d in dep_options
            )
            stress = calculate_repayment_mortgage(MortgageInput(
                purchase_price=m.purchase_price,
                deposit_rate=resolved_deposit,
                annual_interest_rate=Decimal("0.07"),
                term_years=m.term_years,
            ))
            body = f"""
<h1>Housing — House Purchase</h1>
{tab_bar}
<div class="card" style="margin-bottom:20px">
  <form method="get" action="/housing">
    <input type="hidden" name="scenario" value="{escape(scenario)}">
    <input type="hidden" name="tab" value="house">
    <div class="form-row">
      <div>
        <label>House price ({fmt_money(price_low)}–{fmt_money(price_high)})</label>
        <input name="house_price" type="number" step="5000" value="{resolved_house_price}">
      </div>
      <div><label>Deposit</label><select name="deposit_rate">{dep_opts_html}</select></div>
      <div><label>Rate</label><select name="mortgage_rate">{rate_opts_html}</select></div>
      <div><label>&nbsp;</label><button type="submit">Calculate</button></div>
    </div>
  </form>
</div>
<div class="grid" style="grid-template-columns:repeat(5,1fr)">
  <div class="card">
    <div class="metric">{fmt_money(m.deposit)}</div>
    <div class="label">Deposit ({fmt_pct(resolved_deposit)})</div>
  </div>
  <div class="card">
    <div class="metric">{fmt_money(m.principal)}</div>
    <div class="label">Mortgage principal</div>
  </div>
  <div class="card">
    <div class="metric amber">{fmt_money(m.monthly_payment)}</div>
    <div class="label">Monthly payment at {fmt_pct(resolved_rate)}</div>
  </div>
  <div class="card">
    <div class="metric amber">{fmt_money(household_bills_total)}</div>
    <div class="label">Household bills / month</div>
  </div>
  <div class="card">
    <div class="metric red">{fmt_money(m.monthly_payment + household_bills_total)}</div>
    <div class="label">Total living cost / month</div>
  </div>
</div>
{bills_section_html}
<div class="grid-2">
  <div class="card">
    <h2>Affordability</h2>
    <table>
      <tbody>
        <tr><td>Alex gross</td><td class="num">{fmt_money(alex_gross)}/yr</td></tr>
        <tr><td>Charly gross ({charly_active.weekly_hours} hrs/wk)</td><td class="num">{fmt_money(charly_gross)}/yr</td></tr>
        <tr class="total"><td>Combined gross</td><td class="num">{fmt_money(combined_gross)}/yr</td></tr>
        <tr><td>4× max purchase</td><td class="num">{fmt_money(a.low_max_purchase_price)}</td></tr>
        <tr class="highlight"><td>4.5× max purchase</td><td class="num">{fmt_money(a.high_max_purchase_price)}</td></tr>
      </tbody>
    </table>
  </div>
  <div class="card">
    <h2>Rate comparison — {fmt_money(resolved_house_price)}</h2>
    <table>
      <thead><tr><th>Rate</th><th class="num">Monthly</th><th class="num">Annual</th></tr></thead>
      <tbody>
        {"".join(f'<tr{"" if rt != resolved_rate else " class=highlight"}><td>{fmt_pct(rt)}</td><td class="num">{fmt_money(calculate_repayment_mortgage(MortgageInput(resolved_house_price, resolved_deposit, rt, m.term_years)).monthly_payment)}</td><td class="num">{fmt_money(calculate_repayment_mortgage(MortgageInput(resolved_house_price, resolved_deposit, rt, m.term_years)).annual_payment)}</td></tr>' for rt in rate_options)}
      </tbody>
    </table>
  </div>
</div>
<div class="card" style="margin-top:20px">
  <h2>Stress test — 7%</h2>
  <div class="grid-3" style="margin-bottom:0">
    <div><div class="metric red">{fmt_money(stress.monthly_payment)}</div><div class="label">Mortgage only</div></div>
    <div><div class="metric red">{fmt_money(stress.monthly_payment + household_bills_total)}</div><div class="label">+ household bills</div></div>
  </div>
</div>"""

        return html_page("Housing", body, scenario, "/housing", message)

    # -----------------------------------------------------------------------
    # Plan (structured budget planning with living-situation tabs)
    # -----------------------------------------------------------------------

    def render_plan(self, scenario: str, tab: str = "flat", message: str = "") -> str:
        conn = self.connection()
        try:
            summaries = list_manual_summaries(conn, scenario)
            # Pull the housing mortgage calculator output for House tab Mortgage hint
            scenario_id_row = conn.execute(
                "SELECT id FROM scenario WHERE name = ?", (scenario,)
            ).fetchone()
            housing_calc_mortgage: Decimal | None = None
            if scenario_id_row:
                row = conn.execute(
                    "SELECT value FROM calculator_output WHERE scenario_id = ? AND calculator = 'housing' AND key = 'mortgage_monthly_payment'",
                    (scenario_id_row["id"],),
                ).fetchone()
                if row:
                    housing_calc_mortgage = Decimal(row["value"])
        finally:
            conn.close()

        # Plan group names used on this page
        PLAN_GROUPS = {"Housing-Flat", "Housing-House", "Obligations", "Living", "Lifestyle", "Sinking Funds"}
        plan_items = [i for i in summaries if (i.group_name or "") in PLAN_GROUPS]

        # Index items by (group_name, category) → item for quick lookup
        item_index: dict[tuple[str, str], ManualSummaryItem] = {}
        for i in plan_items:
            item_index[(i.group_name, i.category)] = i

        # Determine active housing group based on tab
        housing_group = "Housing-Flat" if tab == "flat" else ("Housing-House" if tab == "house" else None)

        # Section definitions: (display_title, group_name, scope)
        # Housing section is tab-dependent (None means not shown on current tab)
        SECTIONS = [
            ("🏠 Housing", housing_group, "expense"),
            ("📋 Obligations", "Obligations", "expense"),
            ("🛒 Living", "Living", "expense"),
            ("🎉 Lifestyle", "Lifestyle", "expense"),
            ("💰 Sinking Funds", "Sinking Funds", "saving"),
        ]

        # Expected category order per group (from docs/budget-plan.md)
        CATEGORY_ORDER: dict[str, list[str]] = {
            "Housing-Flat": ["Mortgage", "Electricity", "Gas", "Water", "Broadband",
                             "Council Tax", "TV Licence", "Home Insurance", "Maintenance"],
            "Housing-House": ["Mortgage", "Electricity", "Gas", "Water", "Broadband",
                              "Council Tax", "TV Licence", "Home Insurance", "Maintenance"],
            "Obligations": ["Car Finance", "Phone (Alex)", "Phone (Charly)",
                            "Life Insurance", "Car Insurance", "Pet Insurance"],
            "Living": ["Groceries", "Pet", "Fuel/Transit", "Household",
                       "Personal Care", "Health", "Clothing", "Baby"],
            "Lifestyle": ["Subscriptions", "Dining Out", "Hobbies", "Fitness", "Travel", "Gifts"],
            "Sinking Funds": ["Emergency Fund", "Car Maintenance", "Renewals", "Holiday Fund", "Christmas"],
        }

        # Calculate totals for summary bar
        expense_total = Decimal("0")
        saving_total = Decimal("0")
        for i in plan_items:
            m = monthly_amount(i.amount, i.frequency)
            if i.group_name == housing_group or i.group_name not in {"Housing-Flat", "Housing-House"}:
                if i.scope == "expense":
                    expense_total += m
                elif i.scope == "saving":
                    saving_total += m

        # Tab bar
        tab_links = ""
        for tab_key, tab_label, tab_desc in [
            ("current", "Current", "Living at family's"),
            ("flat", "Flat", "Living in the flat"),
            ("house", "House", "New house purchase"),
        ]:
            active = "style=\"background:var(--accent);color:white\"" if tab_key == tab else ""
            tab_links += (
                f'<a href="/plan?scenario={escape(scenario)}&tab={tab_key}" '
                f'class="btn btn-ghost btn-sm" {active}>{escape(tab_label)}</a> '
            )

        # Render each section
        sections_html = ""
        for section_title, group_name, scope in SECTIONS:
            if group_name is None:
                # Current tab — no housing costs
                sections_html += f"""
<div class="card" style="margin-bottom:16px">
  <h2>{escape(section_title)}</h2>
  <p class="muted">No housing costs in this scenario — living at family's place.</p>
</div>"""
                continue

            categories = CATEGORY_ORDER.get(group_name, [])
            # Also include any DB items for this group not in the expected list
            db_categories = sorted({i.category for i in plan_items if i.group_name == group_name})
            all_cats = list(dict.fromkeys(categories + [c for c in db_categories if c not in categories]))

            rows_html = ""
            section_total = Decimal("0")
            for cat in all_cats:
                item = item_index.get((group_name, cat))
                item_id = item.id if item else ""
                amount_val = item.amount if item else Decimal("0")
                # For Housing-House Mortgage, fall back to the calculator output if not set
                is_house_mortgage = group_name == "Housing-House" and cat == "Mortgage"
                if is_house_mortgage and housing_calc_mortgage is not None and amount_val == Decimal("0"):
                    amount_val = housing_calc_mortgage
                monthly_val = monthly_amount(amount_val, item.frequency if item else "monthly") if item else monthly_amount(amount_val, "monthly")
                section_total += monthly_val
                # Extra hint for House Mortgage sourced from the Housing calculator
                hint_html = ""
                if is_house_mortgage and housing_calc_mortgage is not None:
                    hint_html = f' <span class="muted" style="font-size:11px">(from <a href="/housing?scenario={escape(scenario)}&tab=house">Housing</a>)</span>'
                rows_html += f"""
<tr>
  <form method="post" action="/plan?scenario={escape(scenario)}&tab={escape(tab)}">
    <input type="hidden" name="_action" value="update_item">
    <input type="hidden" name="_tab" value="{escape(tab)}">
    <input type="hidden" name="id" value="{escape(str(item_id))}">
    <input type="hidden" name="group_name" value="{escape(group_name)}">
    <input type="hidden" name="scope" value="{escape(scope)}">
    <input type="hidden" name="category" value="{escape(cat)}">
    <td style="font-weight:600">{escape(cat)}{hint_html}</td>
    <td style="width:140px">
      <div style="display:flex;align-items:center;gap:4px">
        <span class="muted" style="font-size:13px">£</span>
        <input name="amount" type="number" step="0.01" min="0"
               value="{amount_val}"
               style="width:110px;text-align:right">
      </div>
    </td>
    <td class="num muted" style="width:100px">{fmt_money(monthly_val)}/mo</td>
    <td style="width:40px"><button type="submit" class="btn btn-sm" title="Save">✓</button></td>
  </form>
</tr>"""

            sections_html += f"""
<div class="card" style="margin-bottom:16px">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
    <h2 style="margin:0">{escape(section_title)}</h2>
    <span style="font-size:15px;font-weight:700;color:var(--{"red" if scope == "expense" else "accent"})">{fmt_money(section_total)}/mo</span>
  </div>
  <table>
    <thead><tr><th>Category</th><th class="num">Amount (£/mo)</th><th class="num">Monthly</th><th></th></tr></thead>
    <tbody>{rows_html}
      <tr class="total"><td>Total</td><td></td><td class="num">{fmt_money(section_total)}/mo</td><td></td></tr>
    </tbody>
  </table>
</div>"""

        body = f"""
<div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;flex-wrap:wrap">
  <h1 style="margin:0">Budget Plan</h1>
  <div style="display:flex;gap:6px;flex-wrap:wrap">{tab_links}</div>
</div>

<div class="grid" style="margin-bottom:20px">
  <div class="card">
    <div class="metric red">{fmt_money(expense_total)}</div>
    <div class="label">Total expenses / month</div>
  </div>
  <div class="card">
    <div class="metric" style="color:var(--accent)">{fmt_money(saving_total)}</div>
    <div class="label">Total savings / month</div>
  </div>
  <div class="card">
    <div class="metric amber">{fmt_money(expense_total + saving_total)}</div>
    <div class="label">Total outgoings / month</div>
  </div>
</div>

<p class="muted" style="margin-bottom:20px">
  Edit each amount and click ✓ to save. Switch tabs to compare housing costs for each living situation.
  Amounts are stored in the same database as the <a href="/tracker?scenario={escape(scenario)}">Tracker</a>.
</p>

{sections_html}"""
        return html_page("Budget Plan", body, scenario, "/plan", message)

    # -----------------------------------------------------------------------
    # Tracker (grouped expenses, inline edit)
    # -----------------------------------------------------------------------

    def render_tracker(self, scenario: str, message: str = "") -> str:
        conn = self.connection()
        try:
            summaries = list_manual_summaries(conn, scenario)
        finally:
            conn.close()

        expense_items = [i for i in summaries if i.scope == "expense"]
        income_items = [i for i in summaries if i.scope == "income"]
        saving_items = [i for i in summaries if i.scope == "saving"]

        all_groups = sorted({i.group_name or "Other" for i in expense_items})
        if not all_groups:
            all_groups = ["Bills", "Household", "Personal"]

        GROUP_COLOURS = {
            "Bills": "#2563eb",
            "Household": "#16a34a",
            "Personal": "#d97706",
            "Flat": "#6366f1",
            "Savings": "#0891b2",
            "Other": "#64748b",
        }

        def group_colour(name: str) -> str:
            return GROUP_COLOURS.get(name, "#64748b")

        def group_select(current: str) -> str:
            known = ["Bills", "Household", "Personal", "Flat", "Savings", "Other"]
            opts = sorted(set(known + all_groups))
            return "".join(
                f'<option value="{escape(g)}" {"selected" if g == current else ""}>{escape(g)}</option>'
                for g in opts
            )

        # ---- Compute totals ----
        monthly_expenses_total = sum(monthly_amount(i.amount, i.frequency) for i in expense_items)
        monthly_income_total = sum(monthly_amount(i.amount, i.frequency) for i in income_items)
        monthly_savings_total = sum(monthly_amount(i.amount, i.frequency) for i in saving_items)

        # ---- Group totals for charts ----
        group_totals: dict[str, Decimal] = {}
        for i in expense_items:
            g = i.group_name or "Other"
            group_totals[g] = group_totals.get(g, Decimal("0")) + monthly_amount(i.amount, i.frequency)

        # ---- Category totals (top 10) ----
        cat_totals: dict[str, Decimal] = {}
        for i in expense_items:
            cat_totals[i.category] = cat_totals.get(i.category, Decimal("0")) + monthly_amount(i.amount, i.frequency)
        top_categories = sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)[:10]

        # ---- Stacked bar (groups) ----
        stacked_parts = ""
        legend_parts = ""
        for gname in sorted(group_totals.keys()):
            gtotal = group_totals[gname]
            pct = (gtotal / monthly_expenses_total * 100) if monthly_expenses_total else Decimal("0")
            colour = group_colour(gname)
            stacked_parts += f'<div style="width:{pct:.1f}%;background:{colour}" title="{escape(gname)}: {fmt_money(gtotal)} ({pct:.0f}%)">{escape(gname) if pct > 8 else ""}</div>'
            legend_parts += f'<div class="legend-item"><div class="legend-dot" style="background:{colour}"></div>{escape(gname)} {fmt_money(gtotal)} ({pct:.0f}%)</div>'

        # ---- Group bar chart ----
        max_group = max(group_totals.values()) if group_totals else Decimal("1")
        group_bars = ""
        for gname in sorted(group_totals.keys()):
            gtotal = group_totals[gname]
            pct_of_max = (gtotal / max_group * 100) if max_group else Decimal("0")
            pct_of_total = (gtotal / monthly_expenses_total * 100) if monthly_expenses_total else Decimal("0")
            colour = group_colour(gname)
            group_bars += f"""<li>
  <div class="bar-label"><span>{escape(gname)}</span><span class="bar-amount">{fmt_money(gtotal)}</span></div>
  <div class="bar-track"><div class="bar-fill" style="width:{pct_of_max:.1f}%;background:{colour}"></div><span class="bar-pct">{pct_of_total:.0f}%</span></div>
</li>"""

        # ---- Top categories bar chart ----
        max_cat = top_categories[0][1] if top_categories else Decimal("1")
        cat_bars = ""
        for cat_name, cat_total in top_categories:
            pct_of_max = (cat_total / max_cat * 100) if max_cat else Decimal("0")
            pct_of_total = (cat_total / monthly_expenses_total * 100) if monthly_expenses_total else Decimal("0")
            # Find group colour for this category
            cat_group = next((i.group_name or "Other" for i in expense_items if i.category == cat_name), "Other")
            colour = group_colour(cat_group)
            cat_bars += f"""<li>
  <div class="bar-label"><span>{escape(cat_name)}</span><span class="bar-amount">{fmt_money(cat_total)}</span></div>
  <div class="bar-track"><div class="bar-fill" style="width:{pct_of_max:.1f}%;background:{colour}"></div><span class="bar-pct">{pct_of_total:.0f}%</span></div>
</li>"""

        # ---- Editable table helpers ----
        def render_group_table(items: list, scope: str) -> str:
            grouped: dict[str, list] = {}
            for i in items:
                g = i.group_name or "Other"
                grouped.setdefault(g, []).append(i)

            html_parts: list[str] = []
            grand_total = Decimal("0")

            for gname in sorted(grouped.keys()):
                gitems = grouped[gname]
                group_total = sum(monthly_amount(i.amount, i.frequency) for i in gitems)
                grand_total += group_total
                colour = group_colour(gname)

                html_parts.append(f'<tr class="total" style="background:var(--highlight)"><td colspan="2" style="font-size:13px;text-transform:uppercase;letter-spacing:0.04em;color:{colour}"><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{colour};margin-right:6px"></span>{escape(gname)}</td><td class="num" style="color:{colour}">{fmt_money(group_total)}</td><td colspan="3"></td></tr>')

                for i in gitems:
                    html_parts.append(f"""<tr>
  <form method="post" action="/tracker?scenario={escape(scenario)}">
    <input type="hidden" name="_action" value="update">
    <input type="hidden" name="id" value="{i.id}">
    <td><input name="category" value="{escape(i.category)}" style="border:none;background:transparent;padding:4px 0;width:100%"></td>
    <td><input name="amount" value="{i.amount}" type="number" step="0.01" style="width:90px;text-align:right"></td>
    <td class="num muted">{fmt_money(monthly_amount(i.amount, i.frequency))}</td>
    <td><select name="frequency" style="width:auto;font-size:12px"><option {"selected" if i.frequency=="monthly" else ""}>monthly</option><option {"selected" if i.frequency=="weekly" else ""}>weekly</option><option {"selected" if i.frequency=="yearly" else ""}>yearly</option></select></td>
    <td><select name="group_name" style="width:auto;font-size:12px">{group_select(i.group_name or "Other")}</select></td>
    <td style="white-space:nowrap">
      <button type="submit" class="btn btn-sm" title="Save">✓</button>
  </form>
  <form method="post" action="/tracker?scenario={escape(scenario)}" style="display:inline">
      <input type="hidden" name="_action" value="delete">
      <input type="hidden" name="id" value="{i.id}">
      <button type="submit" class="btn btn-sm btn-danger" title="Delete">✕</button>
  </form>
    </td>
</tr>""")

            if items:
                html_parts.append(f'<tr class="total"><td>Total {scope}</td><td></td><td class="num">{fmt_money(grand_total)}</td><td colspan="3"></td></tr>')
            return "".join(html_parts)

        def render_editable_rows(items: list, scope_label: str) -> str:
            rows = ""
            total = Decimal("0")
            for i in items:
                m = monthly_amount(i.amount, i.frequency)
                total += m
                rows += f"""<tr>
  <form method="post" action="/tracker?scenario={escape(scenario)}">
    <input type="hidden" name="_action" value="update">
    <input type="hidden" name="id" value="{i.id}">
    <td><input name="category" value="{escape(i.category)}" style="border:none;background:transparent;padding:4px 0;width:100%"></td>
    <td><input name="amount" value="{i.amount}" type="number" step="0.01" style="width:90px;text-align:right"></td>
    <td class="num muted">{fmt_money(m)}</td>
    <td><select name="frequency" style="width:auto;font-size:12px"><option {"selected" if i.frequency=="monthly" else ""}>monthly</option><option {"selected" if i.frequency=="weekly" else ""}>weekly</option><option {"selected" if i.frequency=="yearly" else ""}>yearly</option></select></td>
    <td><select name="group_name" style="width:auto;font-size:12px">{group_select(i.group_name or "Other")}</select></td>
    <td style="white-space:nowrap">
      <button type="submit" class="btn btn-sm" title="Save">✓</button>
  </form>
  <form method="post" action="/tracker?scenario={escape(scenario)}" style="display:inline">
      <input type="hidden" name="_action" value="delete">
      <input type="hidden" name="id" value="{i.id}">
      <button type="submit" class="btn btn-sm btn-danger" title="Delete">✕</button>
  </form>
    </td>
</tr>"""
            if items:
                rows += f'<tr class="total"><td>Total {scope_label}</td><td></td><td class="num">{fmt_money(total)}</td><td colspan="3"></td></tr>'
            return rows

        # ---- Bills detail breakdown ----
        bills_items = [i for i in expense_items if (i.group_name or "Other") == "Bills"]
        bills_total = sum(monthly_amount(i.amount, i.frequency) for i in bills_items)

        bills_breakdown = ""
        for i in sorted(bills_items, key=lambda x: monthly_amount(x.amount, x.frequency), reverse=True):
            m = monthly_amount(i.amount, i.frequency)
            pct = (m / bills_total * 100) if bills_total else Decimal("0")
            bills_breakdown += f'<div class="breakdown-row"><span>{escape(i.category)}</span><span class="amount">{fmt_money(m)} <span class="muted">({pct:.0f}%)</span></span></div>'

        body = f"""
<h1>Monthly Tracker</h1>

<div class="grid" style="margin-bottom:20px">
  <div class="card">
    <div class="metric red">{fmt_money(monthly_expenses_total)}</div>
    <div class="label">Total monthly spend</div>
  </div>
  <div class="card">
    <div class="metric" style="color:#2563eb">{fmt_money(group_totals.get("Bills", Decimal("0")))}</div>
    <div class="label">Bills</div>
  </div>
  <div class="card">
    <div class="metric" style="color:#16a34a">{fmt_money(group_totals.get("Household", Decimal("0")))}</div>
    <div class="label">Household</div>
  </div>
  <div class="card">
    <div class="metric" style="color:#d97706">{fmt_money(group_totals.get("Personal", Decimal("0")))}</div>
    <div class="label">Personal</div>
  </div>
  <div class="card">
    <div class="metric" style="color:#6366f1">{fmt_money(group_totals.get("Flat", Decimal("0")))}</div>
    <div class="label">Flat</div>
  </div>
</div>

<div class="card" style="margin-bottom:20px">
  <h2>Spending breakdown</h2>
  <div class="stacked-bar">{stacked_parts}</div>
  <div class="legend">{legend_parts}</div>
</div>

<div class="grid-2" style="margin-bottom:20px">
  <div class="card">
    <h2>By group</h2>
    <ul class="bar-chart">{group_bars}</ul>
  </div>
  <div class="card">
    <h2>Top 10 categories</h2>
    <ul class="bar-chart">{cat_bars}</ul>
  </div>
</div>

<div class="grid-2" style="margin-bottom:20px">
  <div class="card">
    <h2>Bills breakdown ({fmt_money(bills_total)}/mo)</h2>
    {bills_breakdown}
  </div>
  <div class="card">
    <h2>Summary</h2>
    <div class="breakdown-row"><span>Monthly expenses</span><span class="amount" style="color:var(--red)">{fmt_money(monthly_expenses_total)}</span></div>
    <div class="breakdown-row"><span>Other income (manual)</span><span class="amount" style="color:var(--green)">{fmt_money(monthly_income_total)}</span></div>
    <div class="breakdown-row"><span>Monthly savings</span><span class="amount">{fmt_money(monthly_savings_total)}</span></div>
    <hr class="divider" style="margin:12px 0">
    <div class="muted" style="margin-bottom:8px">Group count: {len(group_totals)} groups, {len(expense_items)} expense items</div>
    <div class="muted">Largest group: {max(group_totals.items(), key=lambda x: x[1])[0] if group_totals else "—"} ({fmt_money(max(group_totals.values()) if group_totals else Decimal("0"))})</div>
    <div class="muted">Largest category: {top_categories[0][0] if top_categories else "—"} ({fmt_money(top_categories[0][1]) if top_categories else "—"})</div>
  </div>
</div>

<div class="card" style="margin-bottom:16px">
  <h2>Add entry</h2>
  <form method="post" action="/tracker?scenario={escape(scenario)}">
    <input type="hidden" name="_action" value="add">
    <div class="form-row">
      <div><label>Scope</label><select name="scope"><option>income</option><option selected>expense</option><option>saving</option></select></div>
      <div><label>Group</label><select name="group_name">{group_select("Household")}</select></div>
      <div><label>Category</label><input name="category" required placeholder="e.g. Groceries"></div>
      <div><label>Amount (£)</label><input name="amount" type="number" step="0.01" required placeholder="0.00"></div>
      <div><label>Frequency</label><select name="frequency"><option selected>monthly</option><option>weekly</option><option>yearly</option></select></div>
      <div><label>&nbsp;</label><button type="submit">Add</button></div>
    </div>
  </form>
</div>

{"<div class='card' style='margin-bottom:16px'><h2><span class='tag tag-income'>Income</span> Other income</h2><div style='overflow-x:auto'><table><thead><tr><th>Category</th><th class='num'>Amount</th><th class='num'>Monthly</th><th>Freq</th><th>Group</th><th></th></tr></thead><tbody>" + render_editable_rows(income_items, "income") + "</tbody></table></div></div>" if income_items else ""}

<div class="card" style="margin-bottom:16px">
  <h2><span class="tag tag-expense">Outgoing</span> Expenses</h2>
  <div style="overflow-x:auto">
  <table>
    <thead><tr><th>Category</th><th class="num">Amount</th><th class="num">Monthly</th><th>Freq</th><th>Group</th><th></th></tr></thead>
    <tbody>
      {render_group_table(expense_items, "expenses")}
    </tbody>
  </table>
  </div>
</div>

{"<div class='card' style='margin-bottom:16px'><h2><span class='tag tag-saving'>Savings</span></h2><div style='overflow-x:auto'><table><thead><tr><th>Category</th><th class='num'>Amount</th><th class='num'>Monthly</th><th>Freq</th><th>Group</th><th></th></tr></thead><tbody>" + render_editable_rows(saving_items, "savings") + "</tbody></table></div></div>" if saving_items else ""}
"""
        return html_page("Tracker", body, scenario, "/tracker", message)

    # -----------------------------------------------------------------------
    # Variables
    # -----------------------------------------------------------------------

    def render_variables(self, scenario: str, message: str = "") -> str:
        conn = self.connection()
        try:
            assumptions = list(get_assumptions(conn, scenario).values())
        finally:
            conn.close()

        grouped: dict[str, list] = {}
        for item in assumptions:
            grouped.setdefault(item.namespace, []).append(item)

        sections = ""
        for ns, items in sorted(grouped.items()):
            rows = "".join(f"""
<tr>
  <td class="muted" style="font-size:12px">{escape(item.key)}</td>
  <td>
    <form id="vf-{item.namespace}-{item.key}" method="post" action="/variables?scenario={escape(scenario)}">
      <input type="hidden" name="namespace" value="{escape(item.namespace)}">
      <input type="hidden" name="key" value="{escape(item.key)}">
      {variable_value_input(item)}
    </form>
  </td>
  <td><select name="value_type" form="vf-{item.namespace}-{item.key}">{type_options(item.value_type)}</select></td>
  <td><input name="unit" value="{escape(item.unit)}" form="vf-{item.namespace}-{item.key}" style="width:80px"></td>
  <td class="muted" style="font-size:11px">{escape(item.source)}</td>
  <td><button type="submit" class="btn btn-sm" form="vf-{item.namespace}-{item.key}">Save</button></td>
</tr>""" for item in items)
            sections += f"""
<div class="card" style="margin-bottom:16px">
  <h2 style="text-transform:capitalize">{escape(ns)}</h2>
  <div style="overflow-x:auto">
  <table>
    <thead><tr><th>Key</th><th>Value</th><th>Type</th><th>Unit</th><th>Source</th><th></th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  </div>
</div>"""

        body = f"<h1>Variables</h1>{sections}"
        return html_page("Variables", body, scenario, "/variables", message)

    # -----------------------------------------------------------------------
    # POST handler
    # -----------------------------------------------------------------------

    def handle_post(self, path: str, scenario: str, form: dict[str, list[str]]) -> tuple[str, str]:
        action = form_value(form, "_action")

        if path == "/variables":
            conn = self.connection()
            try:
                set_assumption(
                    conn,
                    scenario_name=scenario,
                    namespace=form_value(form, "namespace"),
                    key=form_value(form, "key"),
                    value=form_value(form, "value"),
                    value_type=form_value(form, "value_type", "text"),
                    unit=form_value(form, "unit"),
                    source="web_ui",
                )
            finally:
                conn.close()
            return "/variables", "Variable updated."

        if path in ("/tracker", "/expenses", "/manual-summaries"):
            if action == "delete":
                conn = self.connection()
                try:
                    delete_manual_summary(conn, int(form_value(form, "id")))
                finally:
                    conn.close()
                return "/tracker", "Entry deleted."
            if action == "update":
                conn = self.connection()
                try:
                    summary_id = int(form_value(form, "id"))
                    update_manual_summary(
                        conn,
                        summary_id,
                        category=form_value(form, "category") or None,
                        amount=parse_decimal_form(form, "amount", default=None),
                        frequency=form_value(form, "frequency") or None,
                        group_name=form_value(form, "group_name") or None,
                    )
                finally:
                    conn.close()
                return "/tracker", "Entry updated."
            conn = self.connection()
            try:
                add_manual_summary(
                    conn,
                    scenario_name=scenario,
                    scope=form_value(form, "scope"),
                    category=form_value(form, "category"),
                    amount=parse_decimal_form(form, "amount"),
                    frequency=form_value(form, "frequency", "monthly"),
                    notes=form_value(form, "notes"),
                    group_name=form_value(form, "group_name"),
                )
            finally:
                conn.close()
            return "/tracker", "Entry added."

        if path == "/charly":
            if action == "set_hours":
                hours_str = form_value(form, "hours")
                conn = self.connection()
                try:
                    set_assumption(
                        conn,
                        scenario_name=scenario,
                        namespace="income",
                        key="charly_weekly_hours",
                        value=hours_str,
                        value_type="decimal",
                        unit="hours/week",
                        source="web_ui",
                    )
                finally:
                    conn.close()
                return "/charly", f"Charly active hours set to {hours_str}/week."
            if action == "toggle_nursery":
                enabled_str = form_value(form, "enabled", "true")
                conn = self.connection()
                try:
                    set_assumption(
                        conn,
                        scenario_name=scenario,
                        namespace="nursery",
                        key="enabled",
                        value=enabled_str,
                        value_type="boolean",
                        unit="",
                        source="web_ui",
                    )
                finally:
                    conn.close()
                label = "enabled" if enabled_str == "true" else "disabled"
                return "/charly", f"Nursery costs {label}."

        if path == "/plan":
            if action == "update_item":
                item_id_str = form_value(form, "id")
                amount = parse_decimal_form(form, "amount", default=Decimal("0"))
                if item_id_str:
                    # Update existing item
                    conn = self.connection()
                    try:
                        update_manual_summary(conn, int(item_id_str), amount=amount)
                    finally:
                        conn.close()
                else:
                    # Create new item (plan entry doesn't exist yet for this scenario)
                    conn = self.connection()
                    try:
                        from financials.seeds import SEEDED_PLAN_NOTE_PREFIX
                        add_manual_summary(
                            conn,
                            scenario_name=scenario,
                            scope=form_value(form, "scope", "expense"),
                            category=form_value(form, "category"),
                            amount=amount,
                            frequency="monthly",
                            notes=f"{SEEDED_PLAN_NOTE_PREFIX}; added via Plan page",
                            group_name=form_value(form, "group_name"),
                        )
                    finally:
                        conn.close()
                tab = form_value(form, "_tab", "flat")
                return f"/plan?tab={tab}", f"Saved {form_value(form, 'category')}."

        return "/", "Unknown action."


# ---------------------------------------------------------------------------
# WSGI-lite: HTTP handler and server
# ---------------------------------------------------------------------------

def make_handler(app: FinancialsWebApp):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            scenario = selected_scenario(query)
            message = query.get("message", [""])[0]
            p = parsed.path

            try:
                if p == "/alex":
                    html = app.render_alex(scenario, message)
                elif p == "/charly":
                    html = app.render_charly(scenario, message)
                elif p == "/housing":
                    tab = query.get("tab", ["current"])[0]
                    sale_price = Decimal(query["sale_price"][0]) if "sale_price" in query else None
                    house_price = Decimal(query["house_price"][0]) if "house_price" in query else None
                    deposit_rate = Decimal(query["deposit_rate"][0]) if "deposit_rate" in query else None
                    mortgage_rate = Decimal(query["mortgage_rate"][0]) if "mortgage_rate" in query else None
                    html = app.render_housing(scenario, tab, sale_price, house_price, deposit_rate, mortgage_rate, message)
                elif p in ("/flat", "/sale", "/purchase"):
                    tab = {"/flat": "flat", "/sale": "flat", "/purchase": "house"}.get(p, "current")
                    html = app.render_housing(scenario, tab=tab, message=message)
                elif p in ("/tracker", "/expenses", "/manual-summaries"):
                    html = app.render_tracker(scenario, message)
                elif p == "/plan":
                    tab = query.get("tab", ["flat"])[0]
                    html = app.render_plan(scenario, tab, message)
                elif p == "/variables":
                    html = app.render_variables(scenario, message)
                elif p == "/":
                    html = app.render_summary(scenario, message)
                else:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                self.send_html(html)
            except Exception:
                from html import escape as esc
                self.send_html(
                    html_page("Error", f'<div class="card danger"><pre>{esc(_traceback.format_exc())}</pre></div>', scenario),
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                )

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            scenario = selected_scenario(query)
            length = int(self.headers.get("Content-Length", "0"))
            form = parse_qs(self.rfile.read(length).decode("utf-8"))
            try:
                target, message = app.handle_post(parsed.path, scenario, form)
                # target may already contain query params (e.g. /plan?tab=flat)
                target_parsed = urlparse(target)
                target_params = parse_qs(target_parsed.query)
                target_params["scenario"] = [scenario]
                target_params["message"] = [message]
                location = target_parsed.path + "?" + urlencode({k: v[0] for k, v in target_params.items() if v})
                self.send_response(HTTPStatus.SEE_OTHER)
                self.send_header("Location", location)
                self.end_headers()
            except Exception:
                from html import escape as esc
                self.send_html(
                    html_page("Error", f'<div class="card danger"><pre>{esc(_traceback.format_exc())}</pre></div>', scenario),
                    HTTPStatus.BAD_REQUEST,
                )

        def send_html(self, html: str, status: HTTPStatus = HTTPStatus.OK) -> None:
            payload = html.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            return

    return Handler


def run_web_app(database: str | Path, host: str = "0.0.0.0", port: int = 8000) -> None:
    database_path = Path(database)
    connection = initialise_database(database_path)
    upsert_baseline_scenario(connection)
    connection.close()
    server = ThreadingHTTPServer((host, port), make_handler(FinancialsWebApp(database_path)))
    print(f"Financials web UI running at http://{host}:{port}")
    print(f"Database: {database_path}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()
