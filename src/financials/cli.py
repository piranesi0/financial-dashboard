from __future__ import annotations

import argparse
import json
from dataclasses import asdict, is_dataclass
from decimal import Decimal
from pathlib import Path

from financials.calculators.housing import (
    FlatSaleInput,
    MortgageInput,
    calculate_affordability,
    calculate_flat_sale,
    calculate_repayment_mortgage,
)
from financials.defaults import DEFAULTS
from financials.mvp import calculate_housing_for_scenario, calculate_mvp_summary
from financials.profile_store import profile_and_persist_workbook
from financials.scenario import (
    create_scenario,
    get_assumptions,
    list_scenarios,
    set_assumption,
)
from financials.schema import connect_database, initialise_database
from financials.seeds import upsert_baseline_scenario
from financials.summaries import add_manual_summary, calculate_household_summary, list_manual_summaries
from financials.web import run_web_app
from financials.xlsx import profile_workbook, workbook_profile_to_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="financials")
    subparsers = parser.add_subparsers(dest="command", required=True)

    profile_parser = subparsers.add_parser("profile-xlsx")
    profile_parser.add_argument("paths", nargs="+", type=Path)

    init_parser = subparsers.add_parser("init-db")
    init_parser.add_argument("path", type=Path)

    seed_parser = subparsers.add_parser("seed-db")
    seed_parser.add_argument("path", type=Path)

    persist_profile_parser = subparsers.add_parser("persist-xlsx-profile")
    persist_profile_parser.add_argument("database", type=Path)
    persist_profile_parser.add_argument("paths", nargs="+", type=Path)

    create_scenario_parser = subparsers.add_parser("create-scenario")
    create_scenario_parser.add_argument("database", type=Path)
    create_scenario_parser.add_argument("name")
    create_scenario_parser.add_argument("--description", default="")

    subparsers.add_parser("list-scenarios").add_argument("database", type=Path)

    list_assumptions_parser = subparsers.add_parser("list-assumptions")
    list_assumptions_parser.add_argument("database", type=Path)
    list_assumptions_parser.add_argument("--scenario", default="baseline")

    set_assumption_parser = subparsers.add_parser("set-assumption")
    set_assumption_parser.add_argument("database", type=Path)
    set_assumption_parser.add_argument("namespace")
    set_assumption_parser.add_argument("key")
    set_assumption_parser.add_argument("value")
    set_assumption_parser.add_argument("--scenario", default="baseline")
    set_assumption_parser.add_argument("--value-type", default="text")
    set_assumption_parser.add_argument("--unit", default="")
    set_assumption_parser.add_argument("--source", default="manual")

    add_summary_parser = subparsers.add_parser("add-manual-summary")
    add_summary_parser.add_argument("database", type=Path)
    add_summary_parser.add_argument("scope", choices=["income", "expense", "saving"])
    add_summary_parser.add_argument("category")
    add_summary_parser.add_argument("amount", type=Decimal)
    add_summary_parser.add_argument("frequency", choices=["weekly", "monthly", "yearly", "one_off"])
    add_summary_parser.add_argument("--scenario", default="baseline")
    add_summary_parser.add_argument("--notes", default="")

    household_summary_parser = subparsers.add_parser("household-summary")
    household_summary_parser.add_argument("database", type=Path)
    household_summary_parser.add_argument("--scenario", default="baseline")

    housing_parser = subparsers.add_parser("housing-summary")
    housing_parser.add_argument("--database", type=Path)
    housing_parser.add_argument("--scenario", default="baseline")
    housing_parser.add_argument("--sale-price", type=Decimal)
    housing_parser.add_argument("--house-price", type=Decimal)
    housing_parser.add_argument("--deposit-rate", type=Decimal)
    housing_parser.add_argument("--mortgage-rate", type=Decimal)
    housing_parser.add_argument("--combined-gross-income", type=Decimal)
    housing_parser.add_argument("--persist", action="store_true")

    mvp_summary_parser = subparsers.add_parser("mvp-summary")
    mvp_summary_parser.add_argument("database", type=Path)
    mvp_summary_parser.add_argument("--scenario", default="baseline")
    mvp_summary_parser.add_argument("--sale-price", type=Decimal)
    mvp_summary_parser.add_argument("--house-price", type=Decimal)
    mvp_summary_parser.add_argument("--deposit-rate", type=Decimal)
    mvp_summary_parser.add_argument("--mortgage-rate", type=Decimal)
    mvp_summary_parser.add_argument("--combined-gross-income", type=Decimal)
    mvp_summary_parser.add_argument("--persist", action="store_true")

    web_parser = subparsers.add_parser("web")
    web_parser.add_argument("database", type=Path)
    web_parser.add_argument("--host", default="0.0.0.0")
    web_parser.add_argument("--port", type=int, default=8000)

    return parser


def json_default(value: object) -> object:
    if isinstance(value, Decimal):
        return format(value, "f")
    if is_dataclass(value):
        return asdict(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serialisable")


def main() -> None:
    args = build_parser().parse_args()

    if args.command == "profile-xlsx":
        for path in args.paths:
            print(workbook_profile_to_json(profile_workbook(path)))
        return

    if args.command == "init-db":
        connection = initialise_database(args.path)
        connection.close()
        print(args.path)
        return

    if args.command == "seed-db":
        connection = initialise_database(args.path)
        scenario_id = upsert_baseline_scenario(connection)
        connection.close()
        print(json.dumps({"database": str(args.path), "scenario_id": scenario_id, "scenario": "baseline"}))
        return

    if args.command == "persist-xlsx-profile":
        connection = initialise_database(args.database)
        source_file_ids = []
        for path in args.paths:
            source_file_ids.append(profile_and_persist_workbook(connection, path))
        connection.close()
        print(json.dumps({"database": str(args.database), "source_file_ids": source_file_ids}))
        return

    if args.command == "create-scenario":
        connection = initialise_database(args.database)
        scenario_id = create_scenario(connection, args.name, args.description)
        connection.close()
        print(json.dumps({"database": str(args.database), "scenario_id": scenario_id, "scenario": args.name}))
        return

    if args.command == "list-scenarios":
        connection = connect_database(args.database)
        rows = list_scenarios(connection)
        connection.close()
        print(json.dumps([dict(row) for row in rows], indent=2))
        return

    if args.command == "list-assumptions":
        connection = connect_database(args.database)
        assumptions = get_assumptions(connection, args.scenario)
        connection.close()
        print(
            json.dumps(
                [
                    {
                        "namespace": value.namespace,
                        "key": value.key,
                        "value": value.value,
                        "value_type": value.value_type,
                        "unit": value.unit,
                        "source": value.source,
                    }
                    for value in assumptions.values()
                ],
                indent=2,
            )
        )
        return

    if args.command == "set-assumption":
        connection = connect_database(args.database)
        set_assumption(
            connection,
            scenario_name=args.scenario,
            namespace=args.namespace,
            key=args.key,
            value=args.value,
            value_type=args.value_type,
            unit=args.unit,
            source=args.source,
        )
        connection.close()
        print(json.dumps({"database": str(args.database), "scenario": args.scenario, "updated": f"{args.namespace}.{args.key}"}))
        return

    if args.command == "add-manual-summary":
        connection = connect_database(args.database)
        summary_id = add_manual_summary(
            connection,
            scenario_name=args.scenario,
            scope=args.scope,
            category=args.category,
            amount=args.amount,
            frequency=args.frequency,
            notes=args.notes,
        )
        connection.close()
        print(json.dumps({"database": str(args.database), "scenario": args.scenario, "manual_summary_id": summary_id}))
        return

    if args.command == "household-summary":
        connection = connect_database(args.database)
        household = calculate_household_summary(list_manual_summaries(connection, args.scenario))
        connection.close()
        print(json.dumps(household, default=json_default, indent=2))
        return

    if args.command == "housing-summary":
        if args.database:
            connection = connect_database(args.database)
            housing = calculate_housing_for_scenario(
                connection=connection,
                scenario_name=args.scenario,
                sale_price=args.sale_price,
                house_price=args.house_price,
                deposit_rate=args.deposit_rate,
                mortgage_rate=args.mortgage_rate,
                combined_gross_income=args.combined_gross_income,
                persist=args.persist,
            )
            connection.close()
            flat_sale = housing.flat_sale
            mortgage = housing.mortgage
            affordability = housing.affordability
        else:
            flat_sale = calculate_flat_sale(
                FlatSaleInput(
                    sale_price=args.sale_price or DEFAULTS.housing.flat_sale_price_low,
                    outstanding_mortgage=DEFAULTS.housing.flat_mortgage_balance,
                    estate_agent_fee_rate=DEFAULTS.housing.estate_agent_fee_rate,
                    solicitor_fee=DEFAULTS.housing.solicitor_fee,
                )
            )
            mortgage = calculate_repayment_mortgage(
                MortgageInput(
                    purchase_price=args.house_price or DEFAULTS.housing.house_price_low,
                    deposit_rate=args.deposit_rate or DEFAULTS.housing.default_deposit_rate,
                    annual_interest_rate=args.mortgage_rate or DEFAULTS.housing.default_mortgage_rate,
                    term_years=DEFAULTS.housing.mortgage_term_years,
                )
            )
            affordability = calculate_affordability(
                combined_gross_income=args.combined_gross_income or DEFAULTS.housing.default_combined_gross_income,
                deposit=mortgage.deposit,
                low_multiple=DEFAULTS.housing.affordability_income_multiple_low,
                high_multiple=DEFAULTS.housing.affordability_income_multiple_high,
            )
        print(
            json.dumps(
                {
                    "flat_sale": flat_sale,
                    "mortgage": mortgage,
                    "affordability": affordability,
                },
                default=json_default,
                indent=2,
            )
        )
        return

    if args.command == "mvp-summary":
        connection = connect_database(args.database)
        summary = calculate_mvp_summary(
            connection=connection,
            scenario_name=args.scenario,
            sale_price=args.sale_price,
            house_price=args.house_price,
            deposit_rate=args.deposit_rate,
            mortgage_rate=args.mortgage_rate,
            combined_gross_income=args.combined_gross_income,
            persist=args.persist,
        )
        connection.close()
        print(json.dumps(summary, default=json_default, indent=2))
        return

    if args.command == "web":
        run_web_app(args.database, host=args.host, port=args.port)
        return

    raise ValueError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
