#!/usr/bin/env python3
"""
Scrape Ahlsell EMV-EL catalog (iPaper flipbook) to extract all product data.

Source: https://se.ahlsell.se/katalog/emv-el/
Output: ahlsell_emv_el.csv and ahlsell_emv_el.xlsx

The catalog HTML embeds page text as a JSON array (window.staticSettings.pageTexts).
Each page's text contains product sections: product name, description, "Artikel Nr",
column headers, then rows of 7-digit article numbers with spec values.

Output columns:
    artikelnummer  — 7-digit article number
    benamning      — product name / heading
    kolumnrubriker — column headers for this product's table
    specifikationer — the spec values for this article row

Usage:
    python3 scrape_ahlsell.py
"""

import requests
import re
import json
import csv
import os

CATALOG_URL = "https://se.ahlsell.se/katalog/emv-el/?page=1"
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# Words that appear as residual table data (packaging, colors, materials)
RESIDUAL_WORDS = [
    "trumma", "bobin", "box", "kartong", "kapad",
    "svart", "grön", "gul", "vit", "röd", "antracit", "grå",
    "platt", "plan", "nej", "ja", "stål", "plast", "metall",
    "rörelsesensor",
]


def fetch_page_texts(url):
    """Fetch catalog HTML and extract the pageTexts JSON array."""
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    m = re.search(r'"pageTexts"\s*:\s*(\[.*?\])\s*[,}]', resp.text, re.DOTALL)
    if not m:
        raise ValueError("Could not find pageTexts in HTML")
    return json.loads(m.group(1))


def clean_product_name(raw_text):
    """Extract product name from raw text that may have residual table data at the start."""
    text = raw_text.strip()
    if not text:
        return ""

    # Remove filler text
    text = re.sub(r"Läs mer om produkterna på ahlsell\.se\s*", "", text)

    # Iteratively strip leading residual patterns
    changed = True
    iterations = 0
    while changed and iterations < 50:
        changed = False
        iterations += 1
        text = text.strip()
        if not text:
            break

        # Strip leading unit abbreviations left over from previous dimension
        m = re.match(r"^(?:mm²|mm|cm|lm|kg|kN|kW|mAh?)\s+", text)
        if m:
            text = text[m.end():]
            changed = True
            continue

        # Strip leading dimension/spec patterns
        m = re.match(
            r"^[\d\s,./xGX×:+-]+"
            r"(?:mm²|mm|cm|m\b|kW|kN|W\b|V\b|A\b|°C|lm|kg|mAh|mA|K\b)"
            r"[\d\s,.²/]*",
            text,
        )
        if m:
            text = text[m.end():]
            changed = True
            continue

        # Strip leading spec patterns: "IP44 ", "DC ", "AC "
        m = re.match(r"^(?:IP\d{2}|DC|AC)\s+", text)
        if m:
            text = text[m.end():]
            changed = True
            continue

        # Strip lamp base + power + color temp: "E27 4,5 W 3000 K "
        m = re.match(r"^E\d{1,2}\s+[\d,.]+\s*W\s+\d+\s*K\s+", text)
        if m:
            text = text[m.end():]
            changed = True
            continue

        # Strip standalone short numbers (page numbers)
        m = re.match(r"^(\d{1,4})\s+", text)
        if m:
            text = text[m.end():]
            changed = True
            continue

        # Strip standalone punctuation at start
        if text and text[0] in ".!,;:":
            text = text[1:].lstrip()
            changed = True
            continue

        # Strip single uppercase letter at start
        m = re.match(r"^[A-Z]\s+", text)
        if m:
            text = text[m.end():]
            changed = True
            continue

        # Strip residual packaging/color words (case-insensitive)
        for word in RESIDUAL_WORDS:
            if text.lower().startswith(word + " ") or text.lower().startswith(word + "/"):
                text = text[len(word):].lstrip(" /")
                changed = True
                break

        # Strip leading model/type codes — only if followed by a long capitalized word
        if not changed:
            m = re.match(
                r"^[A-Za-z0-9][A-Za-z0-9/_.-]{0,20}"
                r"(?:\s*\([^)]*\))?"
                r"(?:\s+[\d,.]+\s*(?:V|A|W|mm²?|m)\b)*"
                r"\s+",
                text,
            )
            if m:
                rest = text[m.end():].strip()
                first_word_m = re.match(r"([A-ZÅÄÖ][a-zåäö]{3,})", rest)
                if first_word_m and first_word_m.group(1).lower() not in set(RESIDUAL_WORDS):
                    text = rest
                    changed = True

    # Take text up to first period
    period_idx = text.find(".")
    if period_idx > 5:
        text = text[:period_idx].strip()

    # Truncate overly long names
    if len(text) > 150:
        words = text.split()
        result = []
        length = 0
        for word in words:
            if length + len(word) + 1 > 150:
                break
            result.append(word)
            length += len(word) + 1
        text = " ".join(result)

    return text.strip()


def parse_catalog(pages):
    """Parse pageTexts into rows with full product data.

    Returns list of dicts with keys:
        artikelnummer, benamning, kolumnrubriker, specifikationer
    """
    # Skip cover page (first) and back page (last)
    content_pages = pages[1:-1] if len(pages) > 2 else pages
    full_text = " ".join(content_pages)

    # Split by "Artikel Nr" markers
    sections = full_text.split("Artikel Nr")

    # Regex for 7-digit article numbers (optionally followed by 'E')
    art_re = re.compile(r"\b(\d{7})E?\b")

    results = []
    last_good_name = ""

    for i in range(len(sections) - 1):
        # --- Extract product name from sections[i] ---
        name_section = sections[i]
        last_num_end = 0
        for m in art_re.finditer(name_section):
            last_num_end = m.end()

        raw_name = name_section[last_num_end:]
        product_name = clean_product_name(raw_name)

        if len(product_name) < 3:
            product_name = last_good_name
        else:
            last_good_name = product_name

        # --- Extract column headers and article data from sections[i+1] ---
        data_section = sections[i + 1]

        # Find all article number positions in data_section
        art_matches = list(art_re.finditer(data_section))
        if not art_matches:
            continue

        # Column headers = text before the first article number
        col_headers = data_section[: art_matches[0].start()].strip()
        # Clean up whitespace in column headers
        col_headers = re.sub(r"\s+", " ", col_headers).strip()

        # Extract spec data for each article number:
        # spec = text between this article number and the next one
        for j, match in enumerate(art_matches):
            art_num = match.group(1)
            spec_start = match.end()

            if j + 1 < len(art_matches):
                spec_end = art_matches[j + 1].start()
            else:
                spec_end = len(data_section)

            spec_text = data_section[spec_start:spec_end].strip()
            # Clean up whitespace
            spec_text = re.sub(r"\s+", " ", spec_text).strip()

            # Clean "Läs mer" filler text and page numbers from specs
            spec_text = re.sub(
                r"\d*\s*Läs mer om produkterna på ahlsell\.se.*", "", spec_text
            ).strip()

            # For the last article in a section, the spec text may have
            # the next product's name+description appended. Trim it by
            # looking for where non-spec content begins: typically a
            # capitalized Swedish word (>=5 chars) that isn't a spec value.
            if j + 1 >= len(art_matches) and len(spec_text) > 30:
                # Find first long capitalized word that looks like a product name
                trim_m = re.search(
                    r"\b([A-ZÅÄÖ][a-zåäö]{4,})\b", spec_text
                )
                if trim_m:
                    # Check if there's reasonable spec data before it
                    candidate = spec_text[: trim_m.start()].strip()
                    if len(candidate) >= 2:
                        spec_text = candidate

            results.append({
                "artikelnummer": art_num,
                "benamning": product_name,
                "kolumnrubriker": col_headers,
                "specifikationer": spec_text,
            })

    return results


def export_csv(results, path):
    """Write results to CSV with headers."""
    fields = ["artikelnummer", "benamning", "kolumnrubriker", "specifikationer"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)


def export_xlsx(results, path):
    """Write results to Excel (.xlsx)."""
    try:
        import openpyxl
        from openpyxl.styles import Font
    except ImportError:
        print("  openpyxl not installed — skipping Excel export")
        print("  Install with: pip install openpyxl")
        return False

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "EMV-EL Katalog"

    headers = ["artikelnummer", "benämning", "kolumnrubriker", "specifikationer"]
    ws.append(headers)
    # Bold header row
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for row in results:
        ws.append([
            row["artikelnummer"],
            row["benamning"],
            row["kolumnrubriker"],
            row["specifikationer"],
        ])

    # Column widths
    ws.column_dimensions["A"].width = 16
    ws.column_dimensions["B"].width = 60
    ws.column_dimensions["C"].width = 40
    ws.column_dimensions["D"].width = 50

    wb.save(path)
    return True


def main():
    print(f"Fetching catalog from {CATALOG_URL} ...")
    pages = fetch_page_texts(CATALOG_URL)
    print(f"  Found {len(pages)} pages")

    results = parse_catalog(pages)
    print(f"  Extracted {len(results)} article entries")

    # Deduplicate by artikelnummer, keeping first occurrence
    seen = set()
    unique = []
    for row in results:
        if row["artikelnummer"] not in seen:
            seen.add(row["artikelnummer"])
            unique.append(row)
    print(f"  Unique articles: {len(unique)}")

    # Export
    csv_path = os.path.join(OUTPUT_DIR, "ahlsell_emv_el.csv")
    export_csv(unique, csv_path)
    print(f"  Saved CSV:   {csv_path}")

    xlsx_path = os.path.join(OUTPUT_DIR, "ahlsell_emv_el.xlsx")
    if export_xlsx(unique, xlsx_path):
        print(f"  Saved Excel: {xlsx_path}")

    # Show sample rows
    print("\nSample rows:")
    for row in unique[:5]:
        print(f"  {row['artikelnummer']}  |  {row['benamning'][:40]}  |  {row['kolumnrubriker'][:30]}  |  {row['specifikationer'][:30]}")
    print("  ...")
    for row in unique[-3:]:
        print(f"  {row['artikelnummer']}  |  {row['benamning'][:40]}  |  {row['kolumnrubriker'][:30]}  |  {row['specifikationer'][:30]}")


if __name__ == "__main__":
    main()
