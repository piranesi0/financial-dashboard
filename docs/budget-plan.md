# Budget Plan — Design Document

## Overview

A structured budget planning page (`/plan`) that replaces the free-form Tracker entry with a
pre-defined category hierarchy. Users fill in monthly amounts for each subcategory; the UI
shows per-section totals and a grand total for the active living situation.

---

## Living-Situation Tabs

Housing costs vary depending on where the household lives. Three tabs switch the visible
Housing section:

| Tab | Description |
|-----|-------------|
| **Current** | Living at family's place — no rent or mortgage, no household utilities to budget |
| **Flat** | Living in the owned flat — mortgage + full utility set |
| **House** | Living in the purchased house — new mortgage + full utility set |

Obligations, Living, Lifestyle, and Sinking Funds are identical across all three tabs.

---

## Category Hierarchy

### 1. Housing *(tab-dependent)*

#### Flat tab
| Subcategory | Default (£/mo) |
|-------------|---------------|
| Mortgage | 1124.10 |
| Electricity | 80.00 |
| Gas | 60.00 |
| Water | 45.00 |
| Broadband | 35.00 |
| Council Tax | 165.00 |
| TV Licence | 14.00 |
| Home Insurance | 25.00 |
| Maintenance | 50.00 |

#### House tab
| Subcategory | Default (£/mo) |
|-------------|---------------|
| Mortgage | Pulled from Housing — House Purchase calculator |
| Electricity | 80.00 |
| Gas | 60.00 |
| Water | 45.00 |
| Broadband | 35.00 |
| Council Tax | 180.00 |
| TV Licence | 14.00 |
| Home Insurance | 30.00 |
| Maintenance | 100.00 |

#### Current tab
No housing costs shown (living with family, rent-free).

---

### 2. Obligations *(all tabs)*

| Subcategory | Default (£/mo) |
|-------------|---------------|
| Car Finance | 290.00 |
| Phone (Alex) | 40.00 |
| Phone (Charly) | 29.00 |
| Life Insurance | 14.00 |
| Car Insurance | 51.00 |
| Pet Insurance | 31.00 |

---

### 3. Living *(all tabs)*

| Subcategory | Default (£/mo) |
|-------------|---------------|
| Groceries | 800.00 |
| Pet | 50.00 |
| Fuel/Transit | 100.00 |
| Household | 50.00 |
| Personal Care | 50.00 |
| Health | 0.00 |
| Clothing | 50.00 |
| Baby | 200.00 |

---

### 4. Lifestyle *(all tabs)*

| Subcategory | Default (£/mo) |
|-------------|---------------|
| Subscriptions | 50.00 |
| Dining Out | 100.00 |
| Hobbies | 50.00 |
| Fitness | 36.00 |
| Travel | 50.00 |
| Gifts | 30.00 |

---

### 5. Sinking Funds *(all tabs, scope = saving)*

| Subcategory | Default (£/mo) |
|-------------|---------------|
| Emergency Fund | 200.00 |
| Car Maintenance | 50.00 |
| Renewals | 30.00 |
| Holiday Fund | 100.00 |
| Christmas | 50.00 |

---

## Data Storage

Plan entries are stored in the existing `manual_summary` table with group names from the
new taxonomy:

| Group name | Tab scope | Notes prefix |
|------------|-----------|--------------|
| `Housing-Flat` | Flat | `seed:plan` |
| `Housing-House` | House | `seed:plan` |
| `Obligations` | All | `seed:plan` |
| `Living` | All | `seed:plan` |
| `Lifestyle` | All | `seed:plan` |
| `Sinking Funds` | All (scope=saving) | `seed:plan` |

The **Tracker** page continues to show all entries (including plan entries), providing a
low-level view. The **Plan** page provides a higher-level structured view over the same data.

---

## UI Behaviour

- Tab selection is a `GET` param (`?tab=flat`). Defaults to `flat`.
- Each section is a separate `<form>` with a **Save** button per row. Submitting saves the
  amount for that individual item.
- Each form row shows: label, £ amount input, monthly equivalent (calculated from frequency).
- Section subtotals and grand total are shown at the bottom.
- A **monthly outgoings** card at the top shows `expenses + savings` for the active tab, with
  separate cards for total expenses and total savings.
