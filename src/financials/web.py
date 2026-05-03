from __future__ import annotations

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
from financials.summaries import add_manual_summary, delete_manual_summary, list_manual_summaries


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
    ("/flat", "Flat"),
    ("/sale", "Sale"),
    ("/purchase", "Purchase"),
    ("/expenses", "Expenses"),
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
      color-scheme: light;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, sans-serif;
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
    th {{ background: #f8fafc; color: var(--muted); font-size: 12px; font-weight: 700;
          text-transform: uppercase; letter-spacing: 0.04em; }}
    td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    th.num {{ text-align: right; }}
    tr:last-child td {{ border-bottom: none; }}
    tr.total td {{ font-weight: 700; background: #f8fafc; }}
    tr.highlight td {{ background: #eff6ff; font-weight: 700; }}
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
    .btn-ghost:hover {{ background: #eff6ff; }}
    .muted {{ color: var(--muted); font-size: 13px; }}
    .message {{ background: #dcfce7; color: #166534; border: 1px solid #86efac;
                padding: 12px 16px; border-radius: 10px; margin-bottom: 18px; font-size: 14px; }}
    .danger {{ color: var(--red); }}
    .divider {{ border: none; border-top: 1px solid var(--border); margin: 24px 0; }}
    .scenario-table {{ overflow-x: auto; }}
    .scenario-table table {{ min-width: 600px; }}
    .scenario-table th:not(:first-child), .scenario-table td:not(:first-child) {{ text-align: right; }}
    .active-col td {{ background: #eff6ff !important; }}
    .breakdown-row {{ display: flex; justify-content: space-between; padding: 8px 0;
                      border-bottom: 1px solid var(--border); font-size: 14px; }}
    .breakdown-row:last-child {{ border-bottom: none; font-weight: 700; }}
    .breakdown-row .amount {{ font-variant-numeric: tabular-nums; }}
    .tag {{ display: inline-block; padding: 2px 8px; border-radius: 20px; font-size: 11px; font-weight: 700; }}
    .tag-income {{ background: #dcfce7; color: #166534; }}
    .tag-expense {{ background: #fee2e2; color: #991b1b; }}
    .tag-saving {{ background: #dbeafe; color: #1e40af; }}
    @media (max-width: 768px) {{
      .grid-2, .grid-3 {{ grid-template-columns: 1fr; }}
      header {{ flex-wrap: wrap; height: auto; padding: 12px 16px; gap: 8px; }}
    }}
  </style>
</head>
<body>
  <header>
    <a class="brand" href="/?scenario={escaped_scenario}">💷 Financials</a>
    <nav>{nav_links}</nav>
    <span class="scenario-badge">Scenario: <strong>{escaped_scenario}</strong></span>
  </header>
  <main>{banner}{body}</main>
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

        net = summary.household.monthly_net
        net_class = "green" if net >= 0 else "red"
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
    <div class="metric {net_class}">{fmt_money(net)}</div>
    <div class="label">Monthly net (household)</div>
  </div>
  <div class="card">
    <div class="metric">{fmt_money(summary.household.monthly_income)}</div>
    <div class="label">Monthly income</div>
  </div>
  <div class="card">
    <div class="metric">{fmt_money(summary.household.monthly_expenses)}</div>
    <div class="label">Monthly expenses</div>
  </div>
  <div class="card">
    <div class="metric">{fmt_money(summary.household.monthly_savings)}</div>
    <div class="label">Monthly savings</div>
  </div>
</div>
<div class="grid">
  <div class="card">
    <h3>Alex</h3>
    <div class="metric">{fmt_money(summary.alex_income.net_income_monthly)}</div>
    <div class="label">Net / month</div>
    <hr class="divider" style="margin:12px 0">
    <div class="muted">Gross employment: {fmt_money(summary.alex_income.gross_employment_income_annual)}/yr</div>
    <div class="muted">Pension: {fmt_money(summary.alex_income.pension_contribution_annual)}/yr</div>
    <div class="muted">Tax + NI: {fmt_money(summary.alex_income.income_tax_annual + summary.alex_income.national_insurance_annual)}/yr</div>
    <a href="/alex?scenario={escape(scenario)}" class="btn btn-ghost btn-sm" style="margin-top:12px">Details →</a>
  </div>
  <div class="card">
    <h3>Charly</h3>
    <div class="metric {"green" if charly_active.net_monthly > 0 else "muted"}">{fmt_money(charly_active.net_monthly)}</div>
    <div class="label">Net / month ({charly_active.weekly_hours} hrs/week)</div>
    <hr class="divider" style="margin:12px 0">
    <div class="muted">Gross: {fmt_money(charly_active.gross_monthly)}/mo</div>
    <div class="muted">Tax + NI: {fmt_money((charly_active.income_tax_annual + charly_active.national_insurance_annual) / 12)}/mo</div>
    <div class="muted">Student loan: {fmt_money(charly_active.student_loan_annual / 12)}/mo</div>
    <a href="/charly?scenario={escape(scenario)}" class="btn btn-ghost btn-sm" style="margin-top:12px">Scenarios →</a>
  </div>
  <div class="card">
    <h3>Flat</h3>
    <div class="metric">{fmt_money(summary.housing.flat_sale.net_proceeds)}</div>
    <div class="label">Net sale proceeds</div>
    <hr class="divider" style="margin:12px 0">
    <div class="muted">Mortgage: {fmt_money(summary.housing.mortgage.monthly_payment)}/mo (new house)</div>
    <div class="muted">Afford 4x: {fmt_money(summary.housing.affordability.low_max_purchase_price)}</div>
    <div class="muted">Afford 4.5x: {fmt_money(summary.housing.affordability.high_max_purchase_price)}</div>
    <a href="/flat?scenario={escape(scenario)}" class="btn btn-ghost btn-sm" style="margin-top:12px">Flat details →</a>
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
    {"<div style='margin-top:12px;padding:12px;background:#eff6ff;border-radius:10px'><strong>With RSU:</strong> " + fmt_money(result.net_income_monthly + stock_net_val / 12) + "/mo</div>" if include_stock_val != "true" else ""}
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
            nursery = calculate_nursery_for_scenario(conn, scenario)
            assumptions = get_assumptions(conn, scenario)
        finally:
            conn.close()

        active_hours = Decimal(assumptions[("income", "charly_weekly_hours")].value) if ("income", "charly_weekly_hours") in assumptions else Decimal("0")

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

        nursery_row_html = "".join(
            f'<td class="num {col_class(label)}">'
            f'{"—" if scenarios[label].weekly_hours == 0 else fmt_money(nursery.monthly_net_cost)}'
            f'</td>'
            for label, _, _ in cols
        )
        net_gain_row = "".join(
            f'<td class="num {col_class(label)}" style="font-weight:700">'
            f'{"—" if scenarios[label].weekly_hours == 0 else fmt_money(scenarios[label].net_monthly - nursery.monthly_net_cost)}'
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

        body = f"""
<h1>Charly Income</h1>
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
  </div>
  <div class="card">
    <h2>Active scenario</h2>
    <div class="metric {"green" if active_hours > 0 else "muted"}">{fmt_money(scenarios["none"].net_monthly if active_hours == 0 else next(r.net_monthly for r in scenarios.values() if r.weekly_hours == active_hours))}</div>
    <div class="label">Charly net / month at {active_hours} hrs/wk</div>
    <p class="muted" style="margin-top:12px">This feeds into the Dashboard and Purchase affordability. Click <strong>Set active</strong> in the table to switch scenario.</p>
  </div>
</div>"""
        return html_page("Charly Income", body, scenario, "/charly", message)

    # -----------------------------------------------------------------------
    # Flat
    # -----------------------------------------------------------------------

    def render_flat(self, scenario: str, message: str = "") -> str:
        conn = self.connection()
        try:
            assumptions = get_assumptions(conn, scenario)
            summaries = list_manual_summaries(conn, scenario)
        finally:
            conn.close()

        rent = Decimal(assumptions[("housing", "current_rent_income")].value) if ("housing", "current_rent_income") in assumptions else Decimal("0")
        mortgage_pmt = Decimal(assumptions[("housing", "current_mortgage_payment")].value) if ("housing", "current_mortgage_payment") in assumptions else Decimal("0")
        balance = Decimal(assumptions[("housing", "flat_mortgage_balance")].value) if ("housing", "flat_mortgage_balance") in assumptions else Decimal("0")
        buildings_ins = next((Decimal(i.amount) for i in summaries if "buildings insurance" in i.category.lower()), Decimal("28.55"))
        flat_net = rent - mortgage_pmt - buildings_ins

        body = f"""
<h1>Flat</h1>
<p class="muted" style="margin-bottom:20px">Current situation: flat let to tenants at £{rent:,.2f}/mo. Tenants pay utilities. Flat sale planned — <a href="/sale?scenario={escape(scenario)}">see Sale page</a>.</p>
<div class="grid">
  <div class="card">
    <div class="metric green">{fmt_money(rent)}</div>
    <div class="label">Rent income / month</div>
  </div>
  <div class="card">
    <div class="metric amber">{fmt_money(mortgage_pmt)}</div>
    <div class="label">Mortgage payment / month</div>
  </div>
  <div class="card">
    <div class="metric">{fmt_money(buildings_ins)}</div>
    <div class="label">Buildings insurance / month</div>
  </div>
  <div class="card">
    <div class="metric {"green" if flat_net >= 0 else "red"}">{fmt_money(flat_net)}</div>
    <div class="label">Net from flat / month</div>
  </div>
</div>
<div class="grid-2">
  <div class="card">
    <h2>Monthly breakdown</h2>
    <div class="breakdown-row"><span>Rent income</span><span class="amount" style="color:var(--green)">+{fmt_money(rent)}</span></div>
    <div class="breakdown-row"><span>Mortgage payment</span><span class="amount" style="color:var(--red)">−{fmt_money(mortgage_pmt)}</span></div>
    <div class="breakdown-row"><span>Buildings insurance</span><span class="amount" style="color:var(--red)">−{fmt_money(buildings_ins)}</span></div>
    <div class="breakdown-row"><span>Net</span><span class="amount" style="color:{"var(--green)" if flat_net >= 0 else "var(--red)"}">{fmt_money(flat_net)}</span></div>
  </div>
  <div class="card">
    <h2>Mortgage info</h2>
    <table>
      <tbody>
        <tr><td>Outstanding balance</td><td class="num">{fmt_money(balance)}</td></tr>
        <tr><td>Monthly payment</td><td class="num">{fmt_money(mortgage_pmt)}</td></tr>
        <tr><td>Fixed rate ends</td><td class="num">July 2027</td></tr>
        <tr><td>Planned sale</td><td class="num">June 2026</td></tr>
      </tbody>
    </table>
    <p class="muted" style="margin-top:12px">Fixed rate mortgage renews at higher rate in July 2027 — sale target is June 2026 ahead of this.</p>
    <a href="/sale?scenario={escape(scenario)}" class="btn btn-sm" style="margin-top:12px">Calculate sale proceeds →</a>
  </div>
</div>"""
        return html_page("Flat", body, scenario, "/flat", message)

    # -----------------------------------------------------------------------
    # Sale
    # -----------------------------------------------------------------------

    def render_sale(self, scenario: str, sale_price_override: Decimal | None = None, message: str = "") -> str:
        conn = self.connection()
        try:
            assumptions = get_assumptions(conn, scenario)
            housing = calculate_housing_for_scenario(conn, scenario, sale_price=sale_price_override)
        finally:
            conn.close()

        sale_price_low = Decimal(assumptions[("housing", "flat_sale_price_low")].value)
        sale_price_high = Decimal(assumptions[("housing", "flat_sale_price_high")].value)
        agent_rate = Decimal(assumptions[("housing", "flat_sale_price_low")].value) if False else Decimal(assumptions[("housing", "estate_agent_fee_rate")].value)
        sol_fee = Decimal(assumptions[("housing", "solicitor_fee")].value)
        balance = Decimal(assumptions[("housing", "flat_mortgage_balance")].value)
        r = housing.flat_sale
        sale_price_input = sale_price_override or sale_price_low

        body = f"""
<h1>Flat Sale</h1>
<div class="card" style="margin-bottom:20px">
  <form method="get" action="/sale">
    <input type="hidden" name="scenario" value="{escape(scenario)}">
    <div class="form-row">
      <div>
        <label>Sale price (range: {fmt_money(sale_price_low)} – {fmt_money(sale_price_high)})</label>
        <input name="sale_price" type="number" step="1000" value="{sale_price_input}" placeholder="{sale_price_low}">
      </div>
      <div><label>&nbsp;</label><button type="submit">Calculate</button></div>
    </div>
  </form>
</div>
<div class="grid-2">
  <div class="card">
    <h2>Proceeds breakdown</h2>
    <div class="breakdown-row"><span>Sale price</span><span class="amount">{fmt_money(r.sale_price)}</span></div>
    <div class="breakdown-row"><span>Estate agent fee ({fmt_pct(agent_rate)})</span><span class="amount" style="color:var(--red)">−{fmt_money(r.estate_agent_fee)}</span></div>
    <div class="breakdown-row"><span>Solicitor / legal fees</span><span class="amount" style="color:var(--red)">−{fmt_money(r.solicitor_fee)}</span></div>
    <div class="breakdown-row"><span>Outstanding mortgage</span><span class="amount" style="color:var(--red)">−{fmt_money(r.outstanding_mortgage)}</span></div>
    <div class="breakdown-row"><span>Early repayment charge</span><span class="amount" style="color:var(--red)">−{fmt_money(r.early_repayment_charge)}</span></div>
    <div class="breakdown-row"><span>Other costs</span><span class="amount" style="color:var(--red)">−{fmt_money(r.other_costs)}</span></div>
    <div class="breakdown-row"><span style="font-weight:700">Net proceeds</span><span class="amount" style="font-weight:700;color:{"var(--green)" if r.net_proceeds >= 0 else "var(--red)"}">{fmt_money(r.net_proceeds)}</span></div>
  </div>
  <div class="card">
    <h2>Deposit availability</h2>
    <div class="metric {"green" if r.net_proceeds >= 0 else "red"}">{fmt_money(r.net_proceeds)}</div>
    <div class="label">Available as deposit for new house</div>
    <hr class="divider" style="margin:14px 0">
    <p class="muted">Tip: use this as the deposit on the <a href="/purchase?scenario={escape(scenario)}&deposit={r.net_proceeds}">Purchase page</a> to see what mortgage you can get.</p>
    <hr class="divider" style="margin:14px 0">
    <h3>Quick range</h3>
    <table>
      <thead><tr><th>Sale price</th><th class="num">Net proceeds</th></tr></thead>
      <tbody>
        {"".join(f'<tr{"" if p != int(sale_price_input) else " class=highlight"}><td>{fmt_money(Decimal(p))}</td><td class="num">{fmt_money(Decimal(p) - Decimal(p)*agent_rate - sol_fee - balance)}</td></tr>' for p in range(int(sale_price_low), int(sale_price_high)+1, 5000))}
      </tbody>
    </table>
  </div>
</div>"""
        return html_page("Flat Sale", body, scenario, "/sale", message)

    # -----------------------------------------------------------------------
    # Purchase
    # -----------------------------------------------------------------------

    def render_purchase(
        self,
        scenario: str,
        house_price: Decimal | None = None,
        deposit_rate: Decimal | None = None,
        mortgage_rate: Decimal | None = None,
        message: str = "",
    ) -> str:
        conn = self.connection()
        try:
            assumptions = get_assumptions(conn, scenario)
            alex_income = calculate_alex_static_income_for_scenario(conn, scenario)
            charly_active = calculate_charly_income_for_scenario(conn, scenario)
            housing = calculate_housing_for_scenario(
                conn, scenario,
                house_price=house_price,
                deposit_rate=deposit_rate,
                mortgage_rate=mortgage_rate,
            )
        finally:
            conn.close()

        rate_options = [Decimal("0.035"), Decimal("0.04"), Decimal("0.045"), Decimal("0.05"), Decimal("0.055"), Decimal("0.06")]
        deposit_options = [Decimal("0.05"), Decimal("0.10"), Decimal("0.15"), Decimal("0.20")]
        price_low = Decimal(assumptions[("housing", "house_price_low")].value)
        price_high = Decimal(assumptions[("housing", "house_price_high")].value)

        resolved_house_price = house_price or price_low
        resolved_rate = mortgage_rate or Decimal(assumptions[("housing", "default_mortgage_rate")].value)
        resolved_deposit = deposit_rate or Decimal(assumptions[("housing", "default_deposit_rate")].value)

        alex_gross = alex_income.gross_employment_income_annual
        charly_gross = charly_active.gross_annual
        combined_gross = alex_gross + charly_gross

        rate_opts_html = "".join(
            f'<option value="{r}" {"selected" if r == resolved_rate else ""}>{fmt_pct(r)}</option>'
            for r in rate_options
        )
        dep_opts_html = "".join(
            f'<option value="{d}" {"selected" if d == resolved_deposit else ""}>{fmt_pct(d)}</option>'
            for d in deposit_options
        )

        # Stress test at 7%
        from financials.calculators.housing import MortgageInput, calculate_repayment_mortgage
        stress = calculate_repayment_mortgage(MortgageInput(
            purchase_price=housing.mortgage.purchase_price,
            deposit_rate=resolved_deposit,
            annual_interest_rate=Decimal("0.07"),
            term_years=housing.mortgage.term_years,
        ))

        m = housing.mortgage
        a = housing.affordability

        body = f"""
<h1>House Purchase</h1>
<div class="card" style="margin-bottom:20px">
  <form method="get" action="/purchase">
    <input type="hidden" name="scenario" value="{escape(scenario)}">
    <div class="form-row">
      <div>
        <label>House price (range: {fmt_money(price_low)}–{fmt_money(price_high)})</label>
        <input name="house_price" type="number" step="5000" value="{resolved_house_price}">
      </div>
      <div>
        <label>Deposit</label>
        <select name="deposit_rate">{dep_opts_html}</select>
      </div>
      <div>
        <label>Mortgage rate</label>
        <select name="mortgage_rate">{rate_opts_html}</select>
      </div>
      <div><label>&nbsp;</label><button type="submit">Calculate</button></div>
    </div>
  </form>
</div>
<div class="grid">
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
    <div class="metric red">{fmt_money(stress.monthly_payment)}</div>
    <div class="label">Stress test at 7%</div>
  </div>
</div>
<div class="grid-2">
  <div class="card">
    <h2>Affordability check</h2>
    <table>
      <tbody>
        <tr><td>Alex gross employment</td><td class="num">{fmt_money(alex_gross)}/yr</td></tr>
        <tr><td>Charly gross ({charly_active.weekly_hours} hrs/wk)</td><td class="num">{fmt_money(charly_gross)}/yr</td></tr>
        <tr class="total"><td>Combined gross</td><td class="num">{fmt_money(combined_gross)}/yr</td></tr>
        <tr><td>4× max borrowing</td><td class="num">{fmt_money(a.low_max_borrowing)}</td></tr>
        <tr><td>4.5× max borrowing</td><td class="num">{fmt_money(a.high_max_borrowing)}</td></tr>
        <tr><td>4× max purchase (+ deposit)</td><td class="num">{fmt_money(a.low_max_purchase_price)}</td></tr>
        <tr class="highlight"><td>4.5× max purchase (+ deposit)</td><td class="num">{fmt_money(a.high_max_purchase_price)}</td></tr>
      </tbody>
    </table>
    <p class="muted" style="margin-top:12px">Combined gross updates automatically when you change Charly's active scenario on the <a href="/charly?scenario={escape(scenario)}">Charly page</a>.</p>
  </div>
  <div class="card">
    <h2>Rate comparison — {fmt_money(resolved_house_price)}</h2>
    <table>
      <thead><tr><th>Rate</th><th class="num">Monthly</th><th class="num">Annual</th></tr></thead>
      <tbody>
        {"".join(f"""<tr{"" if r != resolved_rate else " class=highlight"}>
          <td>{fmt_pct(r)}</td>
          <td class="num">{fmt_money(calculate_repayment_mortgage(MortgageInput(resolved_house_price, resolved_deposit, r, housing.mortgage.term_years)).monthly_payment)}</td>
          <td class="num">{fmt_money(calculate_repayment_mortgage(MortgageInput(resolved_house_price, resolved_deposit, r, housing.mortgage.term_years)).annual_payment)}</td>
        </tr>""" for r in rate_options)}
      </tbody>
    </table>
  </div>
</div>"""
        return html_page("House Purchase", body, scenario, "/purchase", message)

    # -----------------------------------------------------------------------
    # Expenses
    # -----------------------------------------------------------------------

    def render_expenses(self, scenario: str, message: str = "") -> str:
        conn = self.connection()
        try:
            summaries = list_manual_summaries(conn, scenario)
        finally:
            conn.close()

        from financials.summaries import monthly_amount
        income_items = [i for i in summaries if i.scope == "income"]
        expense_items = [i for i in summaries if i.scope == "expense"]
        saving_items = [i for i in summaries if i.scope == "saving"]

        def render_section(items, scope: str, tag_class: str) -> str:
            if not items:
                return f'<tr><td colspan="5" class="muted" style="text-align:center">No {scope} entries</td></tr>'
            total = sum(monthly_amount(i.amount, i.frequency) for i in items)
            rows = "".join(f"""
<tr>
  <td><span class="tag {tag_class}">{escape(i.scope)}</span></td>
  <td>{escape(i.category)}</td>
  <td class="num">{fmt_money(i.amount)}</td>
  <td>{escape(i.frequency)}</td>
  <td class="num">{fmt_money(monthly_amount(i.amount, i.frequency))}</td>
  <td class="muted" style="font-size:11px;max-width:180px;overflow:hidden;text-overflow:ellipsis">{escape(i.notes)}</td>
  <td>
    <form method="post" action="/expenses?scenario={escape(scenario)}" style="display:inline">
      <input type="hidden" name="_action" value="delete">
      <input type="hidden" name="id" value="{i.id}">
      <button type="submit" class="btn btn-sm btn-danger">✕</button>
    </form>
  </td>
</tr>""" for i in items)
            return rows + f'<tr class="total"><td colspan="4">Total {scope}</td><td class="num">{fmt_money(total)}</td><td colspan="2"></td></tr>'

        monthly_income = sum(monthly_amount(i.amount, i.frequency) for i in income_items)
        monthly_expenses = sum(monthly_amount(i.amount, i.frequency) for i in expense_items)
        monthly_savings = sum(monthly_amount(i.amount, i.frequency) for i in saving_items)
        monthly_net = monthly_income - monthly_expenses - monthly_savings

        body = f"""
<h1>Expenses &amp; Income</h1>
<div class="grid" style="margin-bottom:20px">
  <div class="card">
    <div class="metric green">{fmt_money(monthly_income)}</div>
    <div class="label">Monthly income</div>
  </div>
  <div class="card">
    <div class="metric red">{fmt_money(monthly_expenses)}</div>
    <div class="label">Monthly expenses</div>
  </div>
  <div class="card">
    <div class="metric">{fmt_money(monthly_savings)}</div>
    <div class="label">Monthly savings</div>
  </div>
  <div class="card">
    <div class="metric {"green" if monthly_net >= 0 else "red"}">{fmt_money(monthly_net)}</div>
    <div class="label">Monthly net</div>
  </div>
</div>
<div class="card" style="margin-bottom:20px">
  <h2>Add entry</h2>
  <form method="post" action="/expenses?scenario={escape(scenario)}">
    <div class="form-row">
      <div><label>Scope</label><select name="scope"><option>income</option><option selected>expense</option><option>saving</option></select></div>
      <div><label>Category</label><input name="category" required placeholder="e.g. Groceries"></div>
      <div><label>Amount (£)</label><input name="amount" type="number" step="0.01" required placeholder="0.00"></div>
      <div><label>Frequency</label><select name="frequency"><option selected>monthly</option><option>weekly</option><option>yearly</option><option>one_off</option></select></div>
      <div><label>Notes</label><input name="notes" placeholder="optional"></div>
      <div><label>&nbsp;</label><button type="submit">Add</button></div>
    </div>
  </form>
</div>
<div class="card">
  <h2>All entries</h2>
  <div style="overflow-x:auto">
  <table>
    <thead><tr><th>Scope</th><th>Category</th><th class="num">Amount</th><th>Frequency</th><th class="num">Monthly equiv.</th><th>Notes</th><th></th></tr></thead>
    <tbody>
      {render_section(income_items, "income", "tag-income")}
      {render_section(expense_items, "expense", "tag-expense")}
      {render_section(saving_items, "saving", "tag-saving")}
    </tbody>
  </table>
  </div>
</div>"""
        return html_page("Expenses & Income", body, scenario, "/expenses", message)

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
    <form method="post" action="/variables?scenario={escape(scenario)}">
      <input type="hidden" name="namespace" value="{escape(item.namespace)}">
      <input type="hidden" name="key" value="{escape(item.key)}">
      {variable_value_input(item)}
  </td>
  <td><select name="value_type">{type_options(item.value_type)}</select></td>
  <td><input name="unit" value="{escape(item.unit)}" style="width:80px"></td>
  <td class="muted" style="font-size:11px">{escape(item.source)}</td>
  <td><button type="submit" class="btn btn-sm">Save</button></form></td>
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

        if path in ("/expenses", "/manual-summaries"):
            if action == "delete":
                conn = self.connection()
                try:
                    delete_manual_summary(conn, int(form_value(form, "id")))
                finally:
                    conn.close()
                return "/expenses", "Entry deleted."
            conn = self.connection()
            try:
                add_manual_summary(
                    conn,
                    scenario_name=scenario,
                    scope=form_value(form, "scope"),
                    category=form_value(form, "category"),
                    amount=parse_decimal_form(form, "amount"),
                    frequency=form_value(form, "frequency"),
                    notes=form_value(form, "notes"),
                )
            finally:
                conn.close()
            return "/expenses", "Entry added."

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
                elif p == "/flat":
                    html = app.render_flat(scenario, message)
                elif p == "/sale":
                    sale_price = Decimal(query["sale_price"][0]) if "sale_price" in query else None
                    html = app.render_sale(scenario, sale_price, message)
                elif p == "/purchase":
                    house_price = Decimal(query["house_price"][0]) if "house_price" in query else None
                    deposit_rate = Decimal(query["deposit_rate"][0]) if "deposit_rate" in query else None
                    mortgage_rate = Decimal(query["mortgage_rate"][0]) if "mortgage_rate" in query else None
                    html = app.render_purchase(scenario, house_price, deposit_rate, mortgage_rate, message)
                elif p in ("/expenses", "/manual-summaries"):
                    html = app.render_expenses(scenario, message)
                elif p == "/variables":
                    html = app.render_variables(scenario, message)
                elif p == "/":
                    html = app.render_summary(scenario, message)
                else:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                self.send_html(html)
            except Exception as exc:
                from html import escape as esc
                self.send_html(
                    html_page("Error", f'<div class="card danger"><pre>{esc(str(exc))}</pre></div>', scenario),
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
                location = f"{target}?{urlencode({'scenario': scenario, 'message': message})}"
                self.send_response(HTTPStatus.SEE_OTHER)
                self.send_header("Location", location)
                self.end_headers()
            except Exception as exc:
                from html import escape as esc
                self.send_html(
                    html_page("Error", f'<div class="card danger"><pre>{esc(str(exc))}</pre></div>', scenario),
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


def run_web_app(database: str | Path, host: str = "127.0.0.1", port: int = 8000) -> None:
    database_path = Path(database)
    connection = initialise_database(database_path)
    upsert_baseline_scenario(connection)
    connection.close()
    server = ThreadingHTTPServer((host, port), make_handler(FinancialsWebApp(database_path)))
    print(f"Financials web UI running at http://{host}:{port}")
    print(f"Database: {database_path}")
    server.serve_forever()
