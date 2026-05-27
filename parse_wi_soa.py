#!/usr/bin/env python3
"""Parse Wisconsin Statement of Assessment (SOA) PDF forms into CSV.

Extracts Lines 1-9 from Page 1 of each SOA form. Adds municipality header
columns to each row. Accepts one or more PDF files as arguments.

Requires: pdfplumber
"""

import csv
import re
import sys
import os

import pdfplumber

HEADER = [
    "Town/Village/City", "Municipality Name", "County Name",
    "Line No.", "Real Estate",
    "Total Land (Col A)", "Improvements (Col B)", "No. of Acres (Col C)",
    "Value of Land (Col D)", "Value of Improvements (Col E)",
    "Total Value of Land and Improvements (Col F)",
]

COL_LETTERS = list("ABCDEF")


def extract_text(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        pages = []
        for page in pdf.pages:
            text = page.extract_text(layout=True)
            if text:
                pages.append(text)
        return "\f".join(pages)


def find_col_right_edges(lines):
    for line in lines:
        if "(Col. A)" in line and "(Col. F)" in line:
            edges = {}
            for letter in COL_LETTERS:
                label = f"(Col. {letter})"
                idx = line.index(label)
                edges[letter] = idx + len(label)
            return edges
    return None


def parse_municipality_header(lines):
    for line in lines:
        m = re.search(r"FOR\s+(TOWN|VILLAGE|CITY)\s+OF", line)
        if m:
            mun_type = m.group(1).title()
            rest = line[m.end():]
            m2 = re.match(r"\s+OF\s+", rest)
            if m2:
                rest = rest[m2.end():]
            parts = [p.strip() for p in re.split(r"\s{3,}", rest.strip()) if p.strip()]
            mun_name = parts[0] if parts else ""
            county = parts[1] if len(parts) > 1 else ""
            county = re.sub(r"\s+COUNTY$", "", county)
            return mun_type, mun_name, county
    return None, None, None


def assign_values_to_columns(line, col_edges, max_dist=15):
    values = {c: "" for c in COL_LETTERS}
    leftmost_edge = col_edges["A"]

    for m in re.finditer(r"\d[\d,]*", line):
        token = m.group()
        right_pos = m.end()
        if right_pos < leftmost_edge - max_dist:
            continue
        best_col = min(COL_LETTERS, key=lambda c: abs(right_pos - col_edges[c]))
        if abs(right_pos - col_edges[best_col]) <= max_dist:
            values[best_col] = token.replace(",", "")

    return [values[c] for c in COL_LETTERS]


class ParseError(Exception):
    pass


def parse_page(lines, source="(unknown)"):
    col_edges = find_col_right_edges(lines)
    if not col_edges:
        raise ParseError(
            f"{source}: could not find column headers "
            f"(Col. A through Col. F). Is this a Wisconsin SOA form?"
        )

    mun_type, mun_name, county = parse_municipality_header(lines)
    if not mun_type:
        raise ParseError(
            f"{source}: could not find municipality header "
            f"(FOR TOWN/VILLAGE/CITY OF ...)."
        )

    found_lines = set()
    rows = []
    for line in lines:
        m = re.match(r"\s+(\d)\s{2,}", line)
        if not m:
            continue
        line_no = int(m.group(1))
        if not (1 <= line_no <= 9):
            continue

        text_after = line[m.end():]
        cm = re.match(r"(.*?-\s*(?:Class\s+\d+\w*|ALL COLUMNS))", text_after)
        class_name = cm.group(1).strip() if cm else text_after.strip()

        values = assign_values_to_columns(line, col_edges)
        found_lines.add(line_no)
        rows.append([mun_type, mun_name, county, str(line_no), class_name] + values)

    if found_lines != set(range(1, 10)):
        missing = sorted(set(range(1, 10)) - found_lines)
        raise ParseError(
            f"{source}: missing data lines {missing}. Expected lines 1-9."
        )

    return rows


def is_soa_page(lines):
    return find_col_right_edges(lines) and parse_municipality_header(lines)[0]


def parse_forms(text, source="(unknown)"):
    pages = text.split("\f")
    all_rows = []
    for i, page in enumerate(pages):
        lines = page.split("\n")
        if not is_soa_page(lines):
            continue
        page_source = f"{source} (page {i+1})" if len(pages) > 1 else source
        all_rows.extend(parse_page(lines, source=page_source))
    if not all_rows:
        raise ParseError(
            f"{source}: no SOA forms found."
        )
    return all_rows


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <pdf_file> [pdf_file ...]", file=sys.stderr)
        sys.exit(1)

    all_rows = []
    for path in sys.argv[1:]:
        if not os.path.exists(path):
            print(f"Error: {path} not found", file=sys.stderr)
            sys.exit(1)
        try:
            text = extract_text(path)
        except Exception:
            print(f"Error: {path} is not a valid PDF file.", file=sys.stderr)
            sys.exit(1)
        try:
            all_rows.extend(parse_forms(text, source=path))
        except ParseError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    writer = csv.writer(sys.stdout)
    writer.writerow(HEADER)
    for row in all_rows:
        writer.writerow(row)


if __name__ == "__main__":
    main()
