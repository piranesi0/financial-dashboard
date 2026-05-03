# Finances


## Context
- I have multiple xlsx sheets for tracking various financial metrics
- I want to consolidate them into a single database

- We are a two person household: Alex (me) and wife Charly, with baby Theodore
- Charly started maternity leave in August 2025, and is due to return to work in September 2026


**Housing**
- We are renting our flat but are terminating the contract June 2026
- We are living with Charly's parents
- The rent covers the mortgage completely
- We are planning to sell the flat straight away
- We want to buy a house, we are unsure what we can afford
- We have a fixed rate mortgage that will renew at a higher interest rate in July 2027

**Outgoings**
- We have multiple bills, some fixed, some variable
- We have multiple income sources, some fixed, some variable

**Income**
- Alex has a static income
- Alex receives vested RSUs every year in September, linked to $ORCL stock price
- Charly has a current Statutory Maternity Pay income, and then will have a salaried job
- We have some savings
- Charly is negotiating hours for her return to work

## Problem definition

- I want a master solution for all things financial

- I want variables that can be tweaked

- I want to explore options for different scenarios, e.g.
    - Charly works x hours, or gets a new job with £x/hr wage
    - Charly does not go back to work
    - We sell the flat for £x, here's what we get after fees
    - We want to buy a house for X, here's what mortgage we can achieve given X,Y,Z

- I want a dynamic summary sheet that shows the current state of our finances given a scenario

- I want to see expenses for the household (fixed without housing) then see what they look like given a certain mortgage
- I want to see categories of expenses broken down by type (e.g. food, transport, entertainment, etc.)
- I want to see how our expenses change as Charly returns to work 
- I want to see how our income changes as Charly returns to work 
- I want to see how our savings change as Charly returns to work 
- I want some a Personal section where I can track my own expenses and income and debts
- There should be a split between household and personal finances

## Existing files

`sheets/` directory contains the existing xlsx files that we want to consolidate into a single database, with some modifications:
    - they are currently too verbose and have too much information
    - they are currently too manual and have too much manual input
    - they are outdated in some areas
    - Monzo transactions only account for Alex's purchases with Monzo card, we should only use this as a starting point

## Output
- It **does not** need to be an Excel spreadsheet
- It should just give clear summaries of the data given a scenario
- We should be able to dig deeper into certain aspects, e.g. Mortgage details, Personal expenses, etc.
- It should be easily configured with different variables, e.g. mortgage rate, charly hourly pay, etc.
- There should be clear outputs, such as monthly mortgage payment, net flat sale profit/loss, etc.