#!/usr/bin/env python3
"""
Compare Canadian Common CV (CCV) XML export against bibliography files
to find publications and conference presentations missing from the CCV.

Outputs two CSV files:
  - missing_papers.csv        : journal articles not in CCV (PMID, title, year, journal)
  - missing_conferences.csv   : conference presentations not in CCV
"""

import re
import csv
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
REPO = Path(__file__).parent.parent.parent   # /Users/lhilton/repos/cv
XML_PATH    = Path(__file__).parent / "CCV-10129937.xml"
PAPERS_BIB  = REPO / "references" / "papers.bib"
POSTERS_BIB = REPO / "references" / "posters.bib"
TALKS_BIB   = REPO / "references" / "talks.bib"
OUT_PAPERS  = Path(__file__).parent / "missing_papers.csv"
OUT_CONF    = Path(__file__).parent / "missing_conferences.csv"


# ── BibTeX parser ──────────────────────────────────────────────────────────────
def clean_bib_value(val: str) -> str:
    """Strip outer braces/quotes, remove LaTeX brace markup, collapse whitespace."""
    val = val.strip()
    if val.startswith('"') and val.endswith('"'):
        val = val[1:-1]
    # Remove outermost braces repeatedly
    while val.startswith('{') and val.endswith('}'):
        val = val[1:-1]
    # Iteratively remove all brace pairs (handles nested title-case braces)
    prev = None
    while prev != val:
        prev = val
        val = re.sub(r'\{([^{}]*)\}', r'\1', val)
    # Remove any stray remaining braces
    val = val.replace('{', '').replace('}', '')
    # Collapse whitespace
    val = re.sub(r'\s+', ' ', val).strip()
    return val


def parse_bib(path: Path) -> list[dict]:
    """Parse a .bib file and return a list of entry dicts."""
    text = path.read_text(encoding="utf-8")
    entries = []

    # Split on entry beginnings
    raw_entries = re.split(r'(?=@\w+\{)', text)
    for raw in raw_entries:
        raw = raw.strip()
        if not raw:
            continue
        # Entry type and key
        m = re.match(r'@(\w+)\{([^,]+),', raw)
        if not m:
            continue
        entry_type = m.group(1).lower()
        key = m.group(2).strip()

        entry = {"_type": entry_type, "_key": key}

        # Extract fields: handle nested braces properly
        # We iterate char by char to find top-level field = value pairs
        body = raw[m.end():]
        field_re = re.compile(r'(\w+)\s*=\s*', re.S)
        pos = 0
        while pos < len(body):
            fm = field_re.search(body, pos)
            if not fm:
                break
            field_name = fm.group(1).lower()
            val_start = fm.end()
            # Find start delimiter
            if val_start >= len(body):
                break
            delim = body[val_start]
            if delim == '{':
                # Find matching closing brace
                depth = 0
                i = val_start
                while i < len(body):
                    if body[i] == '{':
                        depth += 1
                    elif body[i] == '}':
                        depth -= 1
                        if depth == 0:
                            break
                    i += 1
                val = body[val_start+1:i]
                pos = i + 1
            elif delim == '"':
                # Find closing quote (not preceded by \)
                i = val_start + 1
                while i < len(body):
                    if body[i] == '"' and body[i-1] != '\\':
                        break
                    i += 1
                val = body[val_start+1:i]
                pos = i + 1
            else:
                # Bare value (number)
                m2 = re.match(r'[\w\-]+', body[val_start:])
                if not m2:
                    pos = val_start + 1
                    continue
                val = m2.group(0)
                pos = val_start + len(val)

            entry[field_name] = clean_bib_value(val)

        entries.append(entry)

    return entries


def normalize_title(title: str) -> str:
    """Lowercase, strip punctuation and extra spaces for fuzzy matching."""
    t = title.lower()
    t = re.sub(r'[^a-z0-9 ]', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def format_authors(raw: str) -> str:
    """
    Convert BibTeX author string 'Last, First and Last, First ...'
    into 'First Last, First Last, ...'
    """
    if not raw:
        return ""
    authors = re.split(r'\s+and\s+', raw, flags=re.IGNORECASE)
    formatted = []
    for a in authors:
        a = a.strip()
        if ',' in a:
            parts = [p.strip() for p in a.split(',', 1)]
            formatted.append(f"{parts[1]} {parts[0]}")
        else:
            formatted.append(a)
    return ", ".join(formatted)


def bib_year_month(entry: dict) -> str:
    """Return yyyy/MM string from bib entry."""
    year = entry.get("year", "")
    month_raw = entry.get("month", "")
    month_map = {
        "jan": "01", "feb": "02", "mar": "03", "apr": "04",
        "may": "05", "jun": "06", "jul": "07", "aug": "08",
        "sep": "09", "oct": "10", "nov": "11", "dec": "12",
        "january": "01", "february": "02", "march": "03", "april": "04",
        "june": "06", "july": "07", "august": "08",
        "september": "09", "october": "10", "november": "11", "december": "12",
    }
    month = month_map.get(month_raw.lower(), "")
    if year and month:
        return f"{year}/{month}"
    return year


# ── CCV XML parser ─────────────────────────────────────────────────────────────
def parse_ccv_xml(path: Path):
    """
    Extract titles already present in the CCV.
    Returns (set of normalised journal article titles,
             set of normalised conference publication titles).

    Note: the CCV XML uses the namespace only on the root element;
    child <section> and <field> elements are unqualified.
    """
    tree = ET.parse(path)
    root = tree.getroot()

    journal_titles: set[str] = set()
    journal_urls:   set[str] = set()
    conf_titles:    set[str] = set()

    def find_field_value(section_el, label: str) -> str:
        for field in section_el.iter("field"):
            if field.get("label") == label:
                value_el = field.find("value")
                if value_el is not None and value_el.text:
                    return value_el.text.strip()
        return ""

    for section in root.iter("section"):
        lbl = section.get("label", "")
        if lbl == "Journal Articles":
            title = find_field_value(section, "Article Title")
            url   = find_field_value(section, "URL")
            if title:
                journal_titles.add(normalize_title(title))
            if url:
                journal_urls.add(url.strip().rstrip("/"))
        elif lbl == "Conference Publications":
            title = find_field_value(section, "Publication Title")
            if title:
                conf_titles.add(normalize_title(title))

    return journal_titles, journal_urls, conf_titles


# ── Location helpers ───────────────────────────────────────────────────────────
def parse_address(address: str) -> tuple[str, str, str]:
    """
    Try to split 'City, State, Country' or 'City, Country' into components.
    Returns (city, state_province, country).
    """
    address = address.strip()
    parts = [p.strip() for p in address.split(",")]
    if len(parts) >= 3:
        return parts[0], parts[1], parts[-1]
    if len(parts) == 2:
        return parts[0], "", parts[1]
    return address, "", ""


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    print("Parsing CCV XML …")
    ccv_journal_titles, ccv_journal_urls, ccv_conf_titles = parse_ccv_xml(XML_PATH)
    print(f"  CCV contains {len(ccv_journal_titles)} journal articles, "
          f"{len(ccv_conf_titles)} conference publications")

    print("Parsing bibliography files …")
    papers  = parse_bib(PAPERS_BIB)
    posters = parse_bib(POSTERS_BIB)
    talks   = parse_bib(TALKS_BIB)
    print(f"  papers.bib: {len(papers)} entries")
    print(f"  posters.bib: {len(posters)} entries")
    print(f"  talks.bib: {len(talks)} entries")

    # ── Missing journal articles ───────────────────────────────────────────────
    missing_papers = []
    for entry in papers:
        title = entry.get("title", "")
        nt = normalize_title(title)
        doi = entry.get("doi", "")
        doi_url = f"https://doi.org/{doi}" if doi else ""

        # Check by normalised title
        in_ccv_by_title = nt in ccv_journal_titles
        # Check by DOI URL
        in_ccv_by_url = any(doi_url and u.endswith(doi.strip("/")) for u in ccv_journal_urls) if doi else False

        if not (in_ccv_by_title or in_ccv_by_url):
            pmid = entry.get("pmid", "")
            year = entry.get("year", "")
            journal = entry.get("journal", "")
            authors = format_authors(entry.get("author", ""))
            missing_papers.append({
                "PMID": pmid,
                "Title": title,
                "Journal": journal,
                "Year": year,
                "Authors": authors,
                "DOI": doi,
            })

    print(f"\n{len(missing_papers)} journal articles missing from CCV")

    # ── Missing conference publications ───────────────────────────────────────
    missing_conf = []

    def process_conf(entries: list[dict], pub_type: str):
        for entry in entries:
            title = entry.get("title", "")
            nt = normalize_title(title)
            if nt not in ccv_conf_titles:
                address = entry.get("address", "")
                city, state, country = parse_address(address)
                year_month = bib_year_month(entry)
                booktitle = entry.get("booktitle", "")
                authors = format_authors(entry.get("author", ""))
                missing_conf.append({
                    "Publication Type": pub_type,
                    "Title": title,
                    "Conference Name": booktitle,
                    "Conference Date (yyyy/MM)": year_month,
                    "City": city,
                    "State/Province": state,
                    "Country": country,
                    "Authors": authors,
                    "DOI": entry.get("doi", ""),
                })

    process_conf(posters, "Poster")
    process_conf(talks,   "Abstract")

    # Sort by date descending
    missing_conf.sort(key=lambda x: x["Conference Date (yyyy/MM)"], reverse=True)

    print(f"{len(missing_conf)} conference publications missing from CCV")
    print(f"  (from posters.bib + talks.bib combined = "
          f"{len(posters)+len(talks)} total)")

    # ── Write CSV files ────────────────────────────────────────────────────────
    with open(OUT_PAPERS, "w", newline="", encoding="utf-8") as f:
        if missing_papers:
            writer = csv.DictWriter(f, fieldnames=list(missing_papers[0].keys()))
            writer.writeheader()
            writer.writerows(missing_papers)
        else:
            f.write("No missing journal articles found.\n")
    print(f"\nWrote: {OUT_PAPERS}")

    with open(OUT_CONF, "w", newline="", encoding="utf-8") as f:
        if missing_conf:
            writer = csv.DictWriter(f, fieldnames=list(missing_conf[0].keys()))
            writer.writeheader()
            writer.writerows(missing_conf)
        else:
            f.write("No missing conference publications found.\n")
    print(f"Wrote: {OUT_CONF}")

    # ── Print summary to terminal ──────────────────────────────────────────────
    if missing_papers:
        print("\n── Missing journal articles ──────────────────────────────────")
        print(f"{'PMID':<12} {'Year':<6} {'Journal':<30} {'Title'}")
        for p in missing_papers:
            print(f"{p['PMID']:<12} {p['Year']:<6} {p['Journal'][:28]:<30} {p['Title'][:70]}")

    if missing_conf:
        print("\n── Missing conference publications ───────────────────────────")
        print(f"{'Type':<10} {'Date':<10} {'Location':<30} {'Title'}")
        for c in missing_conf:
            loc = f"{c['City']}, {c['Country']}".strip(", ")
            print(f"{c['Publication Type']:<10} {c['Conference Date (yyyy/MM)']:<10} "
                  f"{loc[:28]:<30} {c['Title'][:65]}")


if __name__ == "__main__":
    main()
