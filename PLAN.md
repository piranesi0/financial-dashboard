# Financials App Plan

This document is our working notepad for turning the current finance spreadsheets into a consolidated scenario tool.

## Project goal

Build a master financial planning app/database that consolidates the current spreadsheets and supports configurable scenarios.

The app should help answer questions such as:

- What is our current household financial position?
- What changes when Charly returns to work at different hours or rates?
- What happens if Charly does not return to work?
- What would we receive from selling the flat at a given price after fees?
- What house price and mortgage payment can we afford?
- How do household, personal, fixed, variable, savings, and debt figures change under a scenario?

The output does not need to be an Excel spreadsheet. It should provide clear summaries and allow drill-down into areas such as mortgage details, personal expenses, income, nursery, and transaction categories.

## Current source files

### `sheets/Alex Pay and Stock.xlsx`

Contains Alex salary, deductions, benefits/select points, pension, student loan, and RSU/stock calculations.

Sheets:

- **`Pay`**
  - Salary scenarios by year/version.
  - Monthly base pay.
  - Pension.
  - Benefits/select points.
  - Gross pay.
  - PAYE.
  - NI.
  - Student loan.
  - Net pay.
  - Tax percentage.
  - Tax/NI/student-loan thresholds.
  - Pension projection assumptions.

- **`2024 Stock`**
  - Detailed RSU vest/distribution/sale tracking.
  - Vesting date, distribution date, available date, quantity, tax shares, sell price, sell date, and related calculations.

- **`2025`**
  - Summary RSU model for two vests plus excess.
  - Includes vest quantities, cost basis, tax, received quantity, sell price, estimated cash out, actual GBP, and USDGBP assumption.

- **`2026`**
  - Same structure as `2025`, likely for future RSU planning.

### `sheets/Charly Pay and Nursery.xlsx`

Contains Charly return-to-work and nursery calculations.

Key sections:

- Current/request/offer hourly pay and weekly hours.
- Nursery funding assumptions.
- Nursery days, excess hours, hourly cost, per-diem cost, and weekly costs.
- Work schedule by day.
- Take-home examples for different weekly-hour scenarios.
- Gross income, pension deductions, taxable income, tax, NI, student loan, and net/take-home figures.

### `sheets/Monzo Transactions.xlsx`

Contains Alex's Monzo personal account export.

Important notes:

- Covers only Alex's Monzo card/account activity.
- It is not a complete household ledger.
- It should be treated as a starting point for spending categorisation.

Main transaction sheet:

- **`Personal Account Transactions`**
  - Around 2,223 transaction rows.
  - Date range inspected: 2024-08-06 to 2026-05-03.
  - Columns include transaction ID, date, time, type, name, category, amount, local amount, notes, address, receipt, description, and category split.

Common transaction types:

- Card payment.
- Pot transfer.
- Faster payment.
- Direct Debit.
- Monzo Paid.
- Flex.
- Bacs Direct Credit.

Common categories:

- Savings.
- Groceries.
- Shopping.
- Entertainment.
- Eating out.
- Transfers.
- Transport.
- Subscriptions.
- Projects.
- Bills.
- Income.

## Key interpretation notes

- Current spreadsheets contain useful logic, but they are too manual and partly outdated.
- We should not copy the spreadsheet structure directly into the app.
- We should extract the underlying domain concepts and calculations.
- Monzo categories need cleaning before they can be used as household spending figures.
- Pot transfers, savings movements, round-ups, faster payments, and internal transfers need explicit classification.
- Household vs personal classification is central.
- Scenario assumptions should be editable and traceable.

## Proposed domain model

### Core entities

- **Person**
  - Alex.
  - Charly.
  - Theodore if child-specific costs need separate tracking.

- **Account**
  - Monzo personal account.
  - Joint/household account if available.
  - Credit cards if available.
  - Savings accounts/pots.
  - Mortgage account.

- **Transaction**
  - Raw source fields.
  - Normalised date/time.
  - Account/source.
  - Amount/currency.
  - Merchant/name/description.
  - Raw category/type.
  - Normalised category.
  - Income/expense/transfer/saving classification.
  - Household/personal classification.

- **Income source**
  - Alex salary.
  - Alex RSUs.
  - Charly maternity pay.
  - Charly salary/hourly pay.
  - Rental income.
  - Other income.

- **Recurring expense**
  - Bills.
  - Subscriptions.
  - Nursery.
  - Food/groceries baseline.
  - Transport.
  - Car.
  - Dog.
  - Child-related costs.
  - Personal debt payments.

- **Asset**
  - Flat.
  - Savings.
  - RSUs/shares.
  - Other investments if needed.

- **Liability**
  - Existing mortgage.
  - Future mortgage.
  - Student loans if modeled.
  - Personal debts.

- **Scenario**
  - Named bundle of assumptions.
  - Charly hours/rate/job option.
  - Nursery days/cost/funding.
  - Mortgage rate/term/deposit/purchase price.
  - Flat sale price and fees.
  - RSU price and FX assumptions.
  - Savings assumptions.

## Calculation modules

### Salary calculator

Inputs:

- Gross income.
- Pension contribution.
- Tax code / personal allowance.
- PAYE thresholds.
- NI thresholds.
- Student loan plan and threshold.
- Benefits/select deductions or additions.

Outputs:

- Gross monthly/yearly.
- Pension deductions.
- PAYE.
- NI.
- Student loan.
- Net monthly/yearly.

### RSU calculator

Inputs:

- Vest date.
- Quantity.
- Stock price.
- Shares withheld/sold for tax.
- Sale price.
- USDGBP.
- Fees if applicable.

Outputs:

- Gross vested value.
- Tax/withheld value.
- Net shares/value.
- Estimated GBP cash out.
- Actual GBP proceeds if known.

### Nursery calculator

Inputs:

- Nursery days.
- Nursery hours.
- Funded hours.
- Excess hours.
- Hourly nursery rate.
- Per-diem cost.
- Work schedule.

Outputs:

- Weekly nursery cost.
- Monthly nursery cost.
- Annual nursery cost.
- Difference between options.

### Mortgage calculator

Inputs:

- Purchase price.
- Deposit.
- Mortgage principal.
- Interest rate.
- Term.
- Repayment type.

Outputs:

- Monthly payment.
- Annual payment.
- Interest sensitivity/stress-tested payment.

### Flat-sale calculator

Inputs:

- Sale price.
- Outstanding mortgage.
- Estate agent fees.
- Solicitor fees.
- Early repayment charge.
- Other sale costs.

Outputs:

- Net sale proceeds.
- Profit/loss.
- Cash available for deposit.

### Scenario summary calculator

Inputs:

- Scenario assumptions.
- Income sources.
- Recurring expenses.
- Transaction-derived spending baseline.
- Housing assumptions.

Outputs:

- Monthly household income.
- Monthly household fixed costs.
- Monthly variable spending estimate.
- Nursery cost.
- Housing/mortgage cost.
- Net monthly surplus/deficit.
- Savings trajectory.

## Implementation plan

### Milestone 1: Data audit and canonical schema

- Define the first database schema.
- Create raw import tables for each workbook/sheet.
- Create normalised tables for transactions, people, accounts, income sources, recurring expenses, assets, liabilities, and scenarios.
- Preserve source workbook provenance for traceability.
- Create an importer/profiler script for `.xlsx` files.
- Import the three current workbooks as raw source data.

### Milestone 2: Rebuild spreadsheet calculations as tested code

- Port Alex salary/net-pay logic.
- Port Alex RSU logic.
- Port Charly pay/take-home logic.
- Port nursery calculation logic.
- Add tests against known spreadsheet outputs.
- Decide which spreadsheet assumptions are current vs historical.

### Milestone 3: Transaction cleaning and monthly baseline

- Import Monzo transactions.
- Normalise column names and date/time fields.
- Build classification rules for transaction type/category/name/description.
- Separate real spending from transfers, pot movements, round-ups, and internal savings movements.
- Create household vs personal mappings.
- Produce monthly baseline outputs:
  - Spending by category.
  - Spending by merchant.
  - Income vs outgoings.
  - Fixed vs variable estimates.

### Milestone 4: Scenario engine

- Add editable scenario assumptions.
- Support Charly work scenarios.
- Support nursery scenarios.
- Support flat-sale scenarios.
- Support house purchase/mortgage scenarios.
- Support Alex RSU price/FX assumptions.
- Produce scenario-level monthly summary and savings trajectory.

### Milestone 5: App/dashboard

- Build a simple local-first UI.
- Provide scenario selection/editing.
- Show current baseline vs selected scenario.
- Show household monthly summary.
- Show income breakdown.
- Show expense breakdown.
- Show mortgage and flat-sale outputs.
- Add drill-down views for transactions, categories, mortgage, nursery, and personal finances.

## Suggested initial technical shape

Start simple and local-first.

Potential stack:

- SQLite for the database.
- Python for importers and financial calculations.
- A lightweight web UI once the model stabilises.

The first useful version can be command-line/notebook driven if that gets the model correct faster. The UI should come after we trust the calculations and classifications.

## Decisions from open questions

- **Data strategy**
  - We are not trying to exhaustively import every card/account statement.
  - Credit card data can be used to understand patterns, but the app should support manually entered outgoings and summary figures.
  - Charly does not have bank/card exports for this project; use payslip, monthly figures, and approximate outgoings.
  - Current savings should be simplified to one Alex pot and one Charly pot.
  - Monzo pots are budgeting pots, not real savings.

- **Scope**
  - Focus on household and Alex personal finances first.
  - Ignore Charly personal spending for now.
  - Household expenses can be treated as coming out of Alex for simplicity.
  - Household-vs-personal category mapping should be configurable input.

- **Categorisation defaults**
  - `Projects` is personal.
  - Subscriptions are personal for now.
  - Faster payments can be assumed internal for now.
  - True savings contributions should not count as monthly outgoings.

- **Income assumptions**
  - Alex's `2026` sheet is the current baseline.
  - Benefits/select points should be simplified.
  - RSU scenarios should support both live `$ORCL` price and manual price input.
  - RSU tax withholding and sale timing should be modeled exactly.
  - Charly return-to-work options are full-time, part-time, flexible, and none/stay-at-home.
  - Charly's current assumed hourly rate is £21.90.
  - Charly's tax code should be configurable; current assumption is `1257L` / £12,570 personal allowance.

- **Housing assumptions**
  - Current flat mortgage balance default is £259,000, but should be variable.
  - Flat sale range should start at £290k-£320k.
  - Estate agent fee default is 1.25%.
  - Solicitor/legal fee default is £3,500.
  - Early repayment charge and tax considerations are unknown and should remain variables.
  - Current rent is £1,144 and mortgage cost is £1,124.10.
  - New house price range should start at £300k-£450k.
  - Deposit default is 10%, with 5% and 15% options.
  - Mortgage term default is 25 years.
  - Mortgage rate options should include 3.5%, 4%, 4.5%, 5%, plus manual/live expected rate input.
  - Affordability should include both monthly payment affordability and lender-style gross income multiple checks, initially 4x-4.5x combined gross income.

- **App shape**
  - Local-only for now.
  - Raw transaction data stays local-only.
  - No authentication for now.
  - SQLite is acceptable for the first version.
  - Start with importers, calculators, and tests before a web app.
  - Verify the source data is current before building too much around it.

## Open questions

### Data coverage

- Do we have Charly's bank/card transaction exports?
  - No, we just have payslip and monthly, as well as approximate outgoings.
- Is there a joint account or shared bills account?
  - Yes for just mortgage payment nothing else
- Are there credit card statements to ingest?
  - Yes, IMPORTANT: but I don't think our goal should be to import all of them, just to get a sense of the data. We can manually input the outgoings data as well as data summaries.
  - See `/home/alex/dev/awt-lab/jupyter/financials/notebook.ipynb` that is an ongoing project for categorization
- Where are current savings balances held?
  - Various, we'll just have 1 pot for alex and one for charly
- Are Monzo pots real savings, budgeting pots, or both?
  - Budgeting

### Categorisation

- Which categories/merchants are household vs Alex personal?
  - Leave open for now, we'll add that as input
- Which categories/merchants are Charly personal?
  - None right now, let's focus on Household and Alex. Household all come out of Alex for simplicity
- Should `Projects` be personal, business, professional development, or household?
  - Personal
- Are subscriptions household or personal?
  - Call them personal for now
- Which faster payments are internal transfers vs real income/spend?
  - Assume all internal
- Should true savings contributions count as monthly outgoings?
  - No

### Income assumptions

- Is the latest `2026` scenario in Alex's sheet the current expected baseline?
  - Yes
- Should benefits/select points be modeled in detail or simplified?
  - Simplified
- Should RSU scenarios use live `$ORCL` price, manually entered price, or both?
  - Both
- Should RSU tax withholding and sale timing be modeled exactly?
  - Yes
- What are Charly's likely working-hour options?
  - Full time, part time, flexible, None (stay at home)
- What hourly rate should be used for Charly's expected return?
  - £21.90 is current assumed
- Are Charly's pension/tax/student-loan assumptions correct?
  - Yes, but they vary based on percentage, as well as UK 2026 PAYE tax brackets
  - We'll provide tax code (currnetly 1257L, £12,570 personal allowance)

### Housing assumptions

- What is the current outstanding mortgage balance on the flat?
  - £259,000, but should be a variable
- What sale price range should we model?
  - £290k - £320k
- What estate agent fee should we assume?
  - 1.25%
- What solicitor/legal fee should we assume?
  - £3500
- Is there an early repayment charge?
  - Unknown/leave open variable
- Are there any tax considerations on the flat sale?
  - Unknown/leave open variable
- What rental income exists, and when does it end?
  - £1144, mortgage cost is £1124.10
- What house purchase price range should we model?
  - £300k-£450k, we should be able to use a slider or type input
- What deposit amount should we assume?
  - 10%, option of 5% or 15%
- What mortgage term should we assume?
  - 25 years
- What interest rates should we model?
  - 3.5%, 4%, 4.5%, 5%, we'll get a live/expected rate to input
- Should we model lender affordability rules or only monthly payment affordability?
  - both, assume 4x - 4.5x combined gross income, to be verified

### App shape

- Should the app remain local-only?
  - Yes, for now
- Should raw transaction data stay local only?
  - Yes, for now
- Is authentication needed?
  - No, for now
- Is SQLite acceptable for the first version?
  - Yes
- Do we want a web app immediately, or start with importers/calculators/tests first?
  - Start with importers/calculators/tests first
  - We should verify data is current before anything else

## Blockers and risks

- **Incomplete household ledger**
  - Monzo only covers Alex's Monzo activity.
  - This is acceptable for the first version if household outgoings can be manually entered or summarised.

- **Manual and outdated spreadsheet assumptions**
  - We need to verify source data is current before porting calculations or building UI.

- **Transfer classification**
  - Monzo has many savings, transfer, pot, and round-up movements.
  - For now, faster payments can be treated as internal and Monzo pots as budgeting.
  - Raw category totals should still not be used blindly as household spending.

- **Housing data not yet modeled**
  - Existing sheets do not include enough flat-sale and new-mortgage detail.
  - We have starting assumptions, but early repayment charge and tax implications remain open variables.

- **Formula parity**
  - Some spreadsheet formulas need to be carefully ported and tested to avoid subtle tax/net-pay differences.

## Immediate next actions

1. Verify which spreadsheet values and assumptions are current.
2. Create a Python/SQLite project scaffold.
3. Build a read-only `.xlsx` importer/profiler for the current sheets.
4. Define the first database schema around assumptions, scenarios, manual summaries, transactions, and calculator outputs.
5. Add seed/default scenario values from the decisions above.
6. Port the first calculator, likely flat-sale/mortgage or Charly pay/nursery.
7. Add tests against known spreadsheet outputs before building UI.
