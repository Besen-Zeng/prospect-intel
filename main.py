"""
main.py — orchestrate the prospect intelligence pipeline.

Reads:   prospects.csv
Writes:  output/report.xlsx

Pipeline per row:
  1. fetcher.py scrapes the company website
  2. analyzer.py sends data to Claude for 5P analysis
  3. Results merged and written to Excel with colour-coded opportunity levels
"""

import csv
import os

from dotenv import load_dotenv
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

import fetcher
import analyzer

load_dotenv(override=True)

INPUT_FILE  = "prospects.csv"
OUTPUT_DIR  = "output"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "report.xlsx")

# Colour fills for opportunity_level column
FILL_HIGH = PatternFill("solid", fgColor="C6EFCE")   # green
FILL_MID  = PatternFill("solid", fgColor="FFEB9C")   # yellow
FILL_LOW  = PatternFill("solid", fgColor="FFC7CE")   # red
FILL_MAP  = {"High": FILL_HIGH, "Mid": FILL_MID, "Low": FILL_LOW}

ANALYSIS_COLS = [
    "people", "product", "place", "price",
    "promotion", "opportunity_level", "next_action",
]


def main():
    rows = _read_csv(INPUT_FILE)
    results = []

    print(f"\nprospect-intel: processing {len(rows)} prospects\n{'─' * 45}")

    for i, row in enumerate(rows, 1):
        company = row.get("company", f"Row {i}")
        print(f"[{i}/{len(rows)}] Researching {company}...")

        site_data = fetcher.fetch(row.get("website", ""), company=company)
        analysis  = analyzer.analyze(row, site_data["text"])

        results.append({**row, **analysis, "_fetch_error": site_data["error"] or ""})

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    _write_excel(results)

    print(f"\n{'─' * 45}")
    print(f"Done! Report saved to {OUTPUT_FILE}\n")


def _read_csv(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write_excel(results: list[dict]) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Prospect Intelligence"

    # Build header list: original CSV cols + analysis cols (skip internal _keys)
    csv_cols = [k for k in results[0].keys() if not k.startswith("_") and k not in ANALYSIS_COLS]
    headers  = csv_cols + ANALYSIS_COLS

    # Header row — bold, grey background
    header_fill = PatternFill("solid", fgColor="D9D9D9")
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=header.replace("_", " ").title())
        cell.font      = Font(bold=True)
        cell.fill      = header_fill
        cell.alignment = Alignment(wrap_text=True, vertical="top")

    # Data rows
    opp_col_idx = headers.index("opportunity_level") + 1

    for row_idx, row in enumerate(results, 2):
        for col_idx, key in enumerate(headers, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=row.get(key, ""))
            cell.alignment = Alignment(wrap_text=True, vertical="top")

            # Colour the opportunity_level cell
            if col_idx == opp_col_idx:
                level = row.get("opportunity_level", "")
                if level in FILL_MAP:
                    cell.fill = FILL_MAP[level]

    # Auto-fit column widths (capped at 50 chars)
    for col_idx, header in enumerate(headers, 1):
        col_letter = get_column_letter(col_idx)
        max_len = len(header)
        for row_idx in range(2, len(results) + 2):
            val = ws.cell(row=row_idx, column=col_idx).value or ""
            max_len = max(max_len, min(len(str(val)), 50))
        ws.column_dimensions[col_letter].width = max_len + 2

    # Freeze header row
    ws.freeze_panes = "A2"

    wb.save(OUTPUT_FILE)


if __name__ == "__main__":
    main()
