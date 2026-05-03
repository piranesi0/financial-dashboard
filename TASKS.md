# TASKS

Next steps, roughly prioritised. Top items are actionable now; lower items need more info or are longer-term.

---

## High priority

> human added feedback

### 0. general feedback and improvements
- certain bills like utilities need to be categorized to only be included in Flat/House, NOT current (bills included in current situation )


### 1. Update seeded bill values to current figures
All fixed bills in `seeds.py` are from 2024 Finances workbook. Flat mortgage, insurance premiums, subscriptions etc. should be updated to current values before relying on the dashboard numbers.
- Edit `src/financials/seeds.py` or use the Tracker page inline edit
- Cross-reference against current bank statements / Monzo
> input from a spreadsheet or notebooks manual creation

### 2. Alex student loan — confirm Plan 1 status
Likely Plan 1 (pre-2012 entry, threshold ~£24,990, 9%). If not yet repaid, add to `income.py` calculator alongside pension/NI/tax deductions. If repaid, note it.
- Check payslip or HMRC account for student loan deduction line
- If active: add `student_loan_threshold` + `student_loan_rate` assumptions and deduction to `StaticIncomeInput` / `calculate_static_income`

> plan 2

### 3. Savings trajectory model
Key question: "If Charly goes full-time from September 2026, how much do we have saved by end of 2026?"
- Add current balance assumptions: `savings.alex_balance`, `savings.charly_balance`
- New page `/savings` — month-by-month table under each Charly scenario
- Show crossover point where deposit target is hit

---

## Medium priority

### 4. RSU calculator — dynamic price input
Currently uses static `alex_stock_gross_annual` / `alex_stock_net_annual` seeded from workbook.
- Add inputs: vest quantity (shares), $ORCL price (USD, manually entered), USD/GBP rate
- Calculate: gross GBP → UK PAYE/NI on the vest → net GBP
- September vest date — show days to vest on Alex page
> include Wise transfer and conversion fees
> can go much deeper, e.g. now 3 vests this year of different values.
> full timeline of vesting for next 3 years

### 5. Debt tracker
MBNA / Barclaycard / Lloyds Credit balances visible in 2024 Monzo data, trending down.
- Add `debt` scope to `manual_summary` (or new table) with outstanding balance + monthly payment
- Show payoff date at current repayment rate
- Show impact on monthly cashflow
> keep segregated - should distinguish between Alex and Household financial - could be separate app/window
> reason being itll be a much deeper dive into spending habits, doesnt need to be 'public' / included in high level.
> this is where the deeper analyses of spends and categories and merchants comes in
> from that we could pull estimates

### 6. Scenario cloning
Fork baseline into named scenarios (e.g. "charly-full-time-300k-sale") to compare side by side.
- Add "Clone scenario" form on Variables or Dashboard
- `create_scenario` already exists in `scenario.py` — just needs a copy of all assumptions

### 7. Error page — show full traceback
The error handler in `make_handler` calls `str(exc)` which hides the stack trace.
- Change to `traceback.format_exc()` so errors are debuggable without checking the terminal
- Only show on `127.0.0.1` / non-LAN requests if desired

---

## Lower priority / longer term

### 8. Monzo transaction importer
`sheets/Monzo Transactions.xlsx` has 2,223 rows (Aug 2024–May 2026). Schema table `transaction_raw` already exists.
- Import + classify by Monzo category / merchant
- Rolling 3-month average by category to auto-populate Tracker
- Most useful once back in own home and tracking live spending again

### 9. Flat sale — solicitor fee split
Current model deducts the seeded solicitor fee (£3,500) from sale proceeds only. In practice there are two solicitors (sale + purchase). Add a separate `purchase_solicitor_fee` assumption to the house purchase tab.
> need much deeper variables like shown in example sheet, adjustments for all sorts of fees

> related: purchase fees, stamp duty, survey etc.

### 10. Tracker — frequency display
The Tracker table shows the raw `amount` (e.g. £2,000 yearly) rather than the monthly-normalised figure in the amount column. The monthly column is correct, but editing the amount field and saving re-interprets it as a monthly amount. Consider showing and editing the monthly-equivalent directly, or making the frequency column more prominent.

### 11. Mobile layout
The scenario comparison table on `/charly` overflows on small screens (5 columns). Either collapse to a scrollable card or add a responsive breakpoint to show only the active scenario column on mobile.
