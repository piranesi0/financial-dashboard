# Financial Tracker - Layout

Text-based mockup of the monthly sheet structure and column layout.

## Month Sheet Layout

Each month (e.g. `2026-03`) has a single sheet structured as below.

### Header Block

```
| Month: March 2026                          |
|---------------------------------------------|
| Income Total:    £X,XXX.XX                  |
| Outgoing Total:  £X,XXX.XX                  |
| Surplus/Deficit: £  XXX.XX  [+ surplus]     |
| Saved:           £  XXX.XX                  |
| Spent:           £X,XXX.XX                  |
```

### Income Section

```
| INCOME              | Amount     |
|---------------------|------------|
| Salary              | £X,XXX.XX  |
| Other               |            |
| TOTAL INCOME        | £X,XXX.XX  |
```

### Outgoing Section

```
| OUTGOING            | Budget     | Actual     | Diff       |
|---------------------|------------|------------|------------|
|                     |            |            |            |
| BILLS               |            |            |            |
|   Car               |            |            |            |
|   Phone             |            |            |            |
|   Internet          |            |            |            |
|   Other             |            |            |            |
| Bills Subtotal      | £XXX.XX    | £XXX.XX    | £XXX.XX    |
|                     |            |            |            |
| HOUSEHOLD           |            |            |            |
|   Groceries         |            |            |            |
|     Sainsbury's     |            |            |            |
|   Other             |            |            |            |
| Household Subtotal  | £XXX.XX    | £XXX.XX    | £XXX.XX    |
|                     |            |            |            |
| ONLINE              |            |            |            |
|   Amazon            |            |            |            |
|     Recurring       |            |            |            |
|     One-off         |            |            |            |
|   Other online      |            |            |            |
| Online Subtotal     | £XXX.XX    | £XXX.XX    | £XXX.XX    |
|                     |            |            |            |
| PERSONAL            |            |            |            |
|   Eating out        |            |            |            |
|   Entertainment     |            |            |            |
|   Health            |            |            |            |
|   Other             |            |            |            |
| Personal Subtotal   | £XXX.XX    | £XXX.XX    | £XXX.XX    |
|                     |            |            |            |
| TOTAL OUTGOING      | £X,XXX.XX  | £X,XXX.XX  | £XXX.XX    |
```

### Savings Section

```
| SAVINGS             | Amount     |
|---------------------|------------|
| Regular savings     |            |
| Ad hoc              |            |
| TOTAL SAVED         | £XXX.XX    |
```

### Summary Block

```
| SUMMARY             |            |
|---------------------|------------|
| Total Income        | £X,XXX.XX  |
| Total Outgoing      | £X,XXX.XX  |
| Total Saved         | £  XXX.XX  |
| Surplus / Deficit   | £  XXX.XX  |
| Savings Rate        |      XX%   |
```

## Column Definitions

| Column   | Description                                              |
|----------|----------------------------------------------------------|
| Budget   | Planned/expected spend for the month                     |
| Actual   | Real spend entered manually or imported                  |
| Diff     | Budget minus Actual (positive = under budget)            |

## Key Formulas (concept)

- **Total Outgoing** = sum of all category actuals
- **Surplus/Deficit** = Total Income - Total Outgoing - Total Saved
- **Savings Rate** = Total Saved / Total Income * 100
- **Spent** = Total Outgoing (excludes savings)
- **Category Subtotals** = sum of rows within each section

## Notes

- Budget column is optional on first pass — can add once baseline spending is known
- Sub-rows (e.g. Sainsbury's under Groceries, Oat milk under Amazon) are additive; their parent row = sum of sub-rows + any unitemised amount
- Start with March 2026 as the first populated month
