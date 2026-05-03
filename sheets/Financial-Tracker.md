---
type: project
category: personal
status: active
progress: 50
priority: high
created: 2026-03-25
updated: 2026-03-26
phase: v1-complete
tags:
  - topic/finances
  - personal
  - tracker
---
# Financial Tracker

A personal monthly finance tracker for monitoring income, expenditure by category, surplus/deficit, and savings over time.

## Goals

- Track monthly income and all outgoing expenditure
- Categorise spending clearly, aligned to Monzo categories
- Identify surplus or deficit each month
- Monitor savings over time
- Expandable structure — easy to add new line items without breaking formulas

## Current Status

**Phase:** v1 Complete
**Progress:** 50%
**Last Updated:** 2026-03-26

### Completed

- Project scoped and structure defined
- Text-based layout drafted (see [Layout](Layout.md))
- Spreadsheet built at `04-Personal/Finances/finances.xlsx`
- Horizontal layout — 4 category column groups side by side (Bills | Household | Personal | Savings)
- Frozen summary header (rows 1–5) spanning full width:
  - Row 2: Salary | Bills total | Household total | Personal total
  - Row 3: Other income | Total Outgoing | Total Saved | Surplus/Deficit
  - Row 4: Total Income (muted reference)
- Categories aligned to Monzo:
  - Bills → Recurring (Phone, Internet, Subscriptions, Car, Transport) / Debt Repayment / Misc
  - Household → Groceries / Shopping (inc. Holidays) / Dog / Baby / Misc
  - Personal → Needs (Health, Personal care) / Wants (Eating out, Entertainment, Treats) / Misc
  - Savings → Regular / Keep (Monzo) / Ad hoc
- All sub-group formulas use contiguous SUM ranges (`SUM(B8:B14)`) — easy to expand by inserting rows
- Section totals use `SUM()` of sub-group subtotals
- Surplus/Deficit cell has conditional green/red formatting
- Year Summary sheet pulls all key metrics from each month sheet
- Debt Repayment sub-group under Bills (Car finance, Credit card)

### Next Up

- Populate March 2026 with real data and validate formulas end-to-end
- Add April 2026 sheet — test the process of duplicating a month
- Review category granularity once real data is entered (e.g. is Misc catching too much?)
- Consider: should Personal care move from Personal/Needs to its own sub-group?
- Consider: Transport — currently under Bills/Recurring, may suit Personal/Needs better depending on usage
- Transfers / General from Monzo not yet mapped — decide if needed
- Build out process for adding a new month (manual copy vs. script)

## Architecture

### Structure

The tracker lives as a spreadsheet with one sheet per month plus a summary sheet.

**File location:** `04-Personal/Finances/finances.xlsx`

**Sheet structure:**

- `Summary` - year-to-date overview, savings rate, trends
- `YYYY-MM` (e.g. `2026-03`) - one sheet per month

### Category Hierarchy

```text
Income
  Salary
  Other

Outgoing
  Bills
    Car
    Phone
    Other bills
  Household
    Groceries
      Sainsbury's
      Other
    Baby
    Subscriptions
    Eating out
    Other household
  Online
    Amazon
      Recurring items
      One-off purchases
    Other online
  Personal
    Eating out
    Entertainment
    Clothing
    Health
    Other personal

Savings
  Regular savings
  Ad hoc savings
```

## Related

### Project Files

- [Layout](Layout.md) - Text-based table mockup and column definitions
- Spreadsheet: `04-Personal/Finances/finances.xlsx`

### Links

- [[04-Personal/Finances/Finances]]
- [[04-Personal/Finances/Debt status]]

## Recent Changes

**2026-03-26 - v1 complete:**

- Built spreadsheet (`finances.xlsx`) with horizontal 4-column-group layout
- Frozen summary header with income inputs and category totals
- Monzo-aligned categories with sub-groups and contiguous SUM ranges
- Debt Repayment section, conditional surplus/deficit formatting
- Year Summary sheet

**2026-03-25 - Project initiated:**

- Created project directory and page
- Defined MVP scope and category hierarchy
- Drafted table layout

## Notes & Learnings

**Design Decisions:**
- Monthly sheets rather than a single flat table to keep months self-contained and easy to review
- Categories start simple but are built to be expandable with sub-rows
- Surplus/deficit is income minus total outgoing; savings tracked separately from unspent surplus

---

**Status:** Active | **Updated:** 2026-03-25 | **Progress:** 5% | **Priority:** High
