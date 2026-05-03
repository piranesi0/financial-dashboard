# TASKS

Next steps, prioritised. ✅ = done. Items marked with human feedback noted inline.

---

## Completed

- ✅ **Error page shows full traceback** — Both GET and POST error handlers now use `traceback.format_exc()`.
- ✅ **Tracker edit form — frequency field** — Frequency selector added to edit rows; frequency now saved on update.
- ✅ **Seeds persistence across restarts** — Assumptions use `ON CONFLICT DO NOTHING`; bill/expense seeds skipped if already present. User edits in Variables and Tracker survive `make run`.
- ✅ **Alex student loan Plan 2** — `student_loan_threshold` (£27,295) and `student_loan_rate` (9%) added to `StaticIncomeInput` / `calculate_static_income` / `defaults.py` / `seeds.py` / `mvp.py`. Deduction shown on Alex Income page. (human: confirmed Plan 2)

---

## High priority

### 1. RSU — yearly only, remove monthly toggle
RSU should never appear in net monthly — only in gross/net yearly figures. (human: "rsu, never needs to be included in net monthly. it would only ever be included in gross/net yearly")
- Remove the "Include RSU in monthly net" toggle from the Alex Income page and `seeds.py`
- Remove `include_stock_in_static_income` assumption and the `stock_net` contribution from `calculate_static_income` net income
- Show RSU as a standalone yearly card only (gross, net after withholding, effective tax rate)
- Confirm Dashboard does not spread RSU across months

### 2. Update seeded bill values to current figures
All fixed bills in `seeds.py` are 2024 Finances workbook values. Update before relying on dashboard numbers. (human: prefer manual entry via UI or import from spreadsheet/notebook)
- Edit via Tracker inline or update `seeds.py` directly
- Cross-reference against current bank statements / Monzo
- Consider a simple CSV/text import for bulk entry

### 3. Bill category scoping — Flat/House vs Current
Utilities (gas, electric, water, council tax, broadband, TV licence, home insurance) are currently in a flat "Bills" group applied to all scenarios. They should only appear where they apply. (human: "certain bills like utilities need to be categorized to only be included in Flat/House, NOT current")
- Delineate three tiers: **Essential/committed** (car insurance, mobile, car finance), **Household utilities** (gas, electric, water, broadband), **Discretionary** (gym, subscriptions, dining out)
- Tag each bill with a `housing_scope` and filter by active housing tab
- Utilities may differ between flat and house — allow per-scenario override or estimate from historical usage/standing charge

### 4. Savings trajectory model
Key question: "If Charly goes full-time from September 2026, how much do we have saved by end of 2026?"
- Add assumptions: `savings.alex_balance`, `savings.charly_balance`
- New page `/savings` — month-by-month table under each Charly scenario
- Show crossover point where deposit target is hit

### 5. Yearly expenses area
One-off annual costs like car insurance, pet insurance, and MOT are awkward in a monthly tracker. (human: "area for yearly expenses like car insurance pet insurance")
- Add a dedicated "Yearly one-offs" section on the Tracker page (frequency=yearly already supported)
- Normalise to monthly in all summaries (already works via `monthly_amount`)
- Optional: calendar-style reminder view for when each annual expense is due

### 6. House purchase price persists across windows
House price on the Housing tab resets to the default on every page load because it is a GET param. (human: "saving house purchase price should persist across windows")
- On GET, save `house_price` / `deposit_rate` / `mortgage_rate` to assumptions when a value is provided
- Read them back as the page default so the last entry is preserved

---

## Medium priority

### 7. RSU calculator — dynamic price input
Currently uses static `alex_stock_gross_annual` / `alex_stock_net_annual` seeded from workbook.
- Add inputs: vest quantity (shares), $ORCL price (USD), USD/GBP rate
- Calculate gross GBP → UK PAYE/NI on vest → net GBP
- Show days to September vest date on Alex page
- Include Wise transfer and conversion fees (human)
- Support multiple vests this year with different values — now 3 vests (human)
- Full timeline of vesting for next 3 years (human)

### 8. Admin panel — reseed with current state
Currently the only way to reset seed values is to delete the DB. (human: "admin panel, maybe action to update seed values with current state?")
- Add an `/admin` page with a "Reset to defaults" button that re-seeds assumptions (overwriting, unlike normal startup)
- Optional: "Export current tracker to seed file" to create a new baseline from current values

### 9. Scenario cloning
Fork baseline into named scenarios (e.g. "charly-full-time-300k-sale") to compare side by side.
- Add "Clone scenario" form on Variables or Dashboard
- `create_scenario` already exists in `scenario.py` — copy all assumptions + summaries

### 10. Flat sale — deeper purchase fee variables
Current model deducts a single solicitor fee from sale proceeds. In practice there are separate fees for sale and purchase, plus stamp duty, survey, and other conveyancing costs. (human: "need much deeper variables like shown in example sheet, adjustments for all sorts of fees")
- Add `purchase_solicitor_fee` assumption to the House tab
- Add stamp duty calculation (based on purchase price and first-time-buyer status)
- Add survey / valuation fee assumption
- Add other moving / conveyancing costs

### 11. Debt tracker — segregated from household
MBNA / Barclaycard / Lloyds balances in Monzo data, trending down. (human: "keep segregated — should distinguish between Alex and Household financial — could be separate app/window")
- Keep separate from household summary — personal / Alex-only view
- Outstanding balance, monthly payment, payoff date at current rate
- Deeper merchant-level spending analysis lives here (human: "this is where the deeper analyses of spends and categories and merchants comes in — from that we could pull estimates")
- Consider a separate app/window for privacy from the high-level household view

---

## Lower priority / longer term

### 12. Monzo transaction importer
`sheets/Monzo Transactions.xlsx` has 2,223 rows (Aug 2024–May 2026). Schema table `transaction_raw` already exists.
- Import + classify by Monzo category / merchant
- Rolling 3-month average by category to auto-populate Tracker
- Most useful once back in own home and tracking live spending

### 13. Mobile layout
The scenario comparison table on `/charly` overflows on small screens (5 columns).
- Collapse to scrollable card or add responsive breakpoint to show only the active scenario column on mobile

### 14. Dashboard — pre-existing test failure
`test_render_summary_uses_database_values` asserts "Household income" is in the Dashboard HTML. The string is not present; either the label changed or the test expectation is stale. Fix test or render.

---

## Ambitious / longer term (human feedback)

### 15. Spending review tool
Ability to look at each statement line item or tracker entry and mark as unnecessary / not essential. Show where costs can be cut.

### 16. Deep tax breakdown — select points and benefit costs
- Select points tool: benefit points awarded at year start, can be used for dental plan or taken as cash (£0.88/point)
- Sliders/toggles for point selection, effect on gross monthly, tax %, monthly pension contributions
- Tax efficiency of pension contributions
- Detail from Alex's Pay and Stock sheet

### 17. Pension contribution and growth simulator/forecast

### 18. Alex job scenarios — pay rise or job switch
- Prospective pay rise: effect on monthly/yearly income
- Job switch: effect where new employer doesn't use select points system
