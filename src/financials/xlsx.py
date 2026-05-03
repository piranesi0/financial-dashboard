from __future__ import annotations

import json
import re
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
OFFICE_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"a": MAIN_NS, "rel": REL_NS}


@dataclass(frozen=True)
class CellValue:
    row: int
    column: int
    reference: str
    value: str | None
    formula: str | None


@dataclass(frozen=True)
class SheetProfile:
    name: str
    used_rows: int
    used_columns: int
    non_empty_cells: int
    formula_count: int
    headers: tuple[str | None, ...]
    sample_rows: tuple[tuple[str | None, ...], ...]


@dataclass(frozen=True)
class WorkbookProfile:
    path: Path
    sheets: tuple[SheetProfile, ...]


def column_to_number(column: str) -> int:
    result = 0
    for character in column:
        result = result * 26 + ord(character.upper()) - 64
    return result


def excel_serial_date_to_iso(value: str) -> str:
    date = datetime(1899, 12, 30) + timedelta(days=float(value))
    return date.date().isoformat()


def load_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    try:
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []

    strings: list[str] = []
    for item in root.findall("a:si", NS):
        strings.append("".join(text.text or "" for text in item.findall(".//a:t", NS)))
    return strings


def workbook_sheets(archive: zipfile.ZipFile) -> list[tuple[str, str]]:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    relationship_targets = {
        relationship.attrib["Id"]: relationship.attrib["Target"]
        for relationship in relationships.findall("rel:Relationship", NS)
    }

    sheets: list[tuple[str, str]] = []
    for sheet in workbook.findall("a:sheets/a:sheet", NS):
        relationship_id = sheet.attrib[f"{{{OFFICE_REL_NS}}}id"]
        target = relationship_targets[relationship_id]
        path = target if target.startswith("xl/") else f"xl/{target}"
        sheets.append((sheet.attrib["name"], path))
    return sheets


def parse_cell(cell: ET.Element, shared_strings: list[str]) -> CellValue:
    reference = cell.attrib.get("r", "")
    match = re.match(r"([A-Z]+)([0-9]+)", reference)
    column = column_to_number(match.group(1)) if match else 0
    row = int(match.group(2)) if match else 0
    cell_type = cell.attrib.get("t")
    value_node = cell.find("a:v", NS)
    formula_node = cell.find("a:f", NS)
    inline_node = cell.find("a:is", NS)

    value: str | None
    if cell_type == "s" and value_node is not None and value_node.text is not None:
        value = shared_strings[int(value_node.text)]
    elif cell_type == "inlineStr" and inline_node is not None:
        value = "".join(text.text or "" for text in inline_node.findall(".//a:t", NS))
    elif value_node is not None:
        value = value_node.text
    else:
        value = None

    return CellValue(
        row=row,
        column=column,
        reference=reference,
        value=value,
        formula=formula_node.text if formula_node is not None else None,
    )


def iter_sheet_cells(archive: zipfile.ZipFile, sheet_path: str, shared_strings: list[str]) -> Iterable[CellValue]:
    root = ET.fromstring(archive.read(sheet_path))
    for row in root.findall("a:sheetData/a:row", NS):
        for cell in row.findall("a:c", NS):
            yield parse_cell(cell, shared_strings)


def profile_workbook(path: str | Path, sample_limit: int = 8) -> WorkbookProfile:
    workbook_path = Path(path)
    sheet_profiles: list[SheetProfile] = []

    with zipfile.ZipFile(workbook_path) as archive:
        shared_strings = load_shared_strings(archive)
        for sheet_name, sheet_path in workbook_sheets(archive):
            rows: dict[int, dict[int, CellValue]] = {}
            non_empty_cells = 0
            formula_count = 0
            used_rows = 0
            used_columns = 0

            for cell in iter_sheet_cells(archive, sheet_path, shared_strings):
                rows.setdefault(cell.row, {})[cell.column] = cell
                has_value = cell.value not in (None, "")
                has_formula = cell.formula not in (None, "")
                if has_value or has_formula:
                    non_empty_cells += 1
                    used_rows = max(used_rows, cell.row)
                    used_columns = max(used_columns, cell.column)
                if has_formula:
                    formula_count += 1

            populated_rows = [row_number for row_number in sorted(rows) if any(cell.value not in (None, "") or cell.formula for cell in rows[row_number].values())]
            header_row_number = populated_rows[0] if populated_rows else 0
            headers = tuple(
                rows.get(header_row_number, {}).get(column, CellValue(header_row_number, column, "", None, None)).value
                for column in range(1, min(used_columns, 30) + 1)
            )
            sample_rows: list[tuple[str | None, ...]] = []
            for row_number in populated_rows[:sample_limit]:
                sample_rows.append(
                    tuple(
                        rows.get(row_number, {}).get(column, CellValue(row_number, column, "", None, None)).value
                        for column in range(1, min(used_columns, 30) + 1)
                    )
                )

            sheet_profiles.append(
                SheetProfile(
                    name=sheet_name,
                    used_rows=used_rows,
                    used_columns=used_columns,
                    non_empty_cells=non_empty_cells,
                    formula_count=formula_count,
                    headers=headers,
                    sample_rows=tuple(sample_rows),
                )
            )

    return WorkbookProfile(path=workbook_path, sheets=tuple(sheet_profiles))


def workbook_profile_to_json(profile: WorkbookProfile) -> str:
    payload = {
        "path": str(profile.path),
        "sheets": [
            {
                "name": sheet.name,
                "used_rows": sheet.used_rows,
                "used_columns": sheet.used_columns,
                "non_empty_cells": sheet.non_empty_cells,
                "formula_count": sheet.formula_count,
                "headers": sheet.headers,
                "sample_rows": sheet.sample_rows,
            }
            for sheet in profile.sheets
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)
