#!/usr/bin/env python3
"""
Add publications and conference presentations missing from the CCV XML to it,
producing a new XML file that can be uploaded directly to the CIHR CCV system.

Usage:
    python3 inject_into_ccv.py

Reads:   CCV-10129937.xml  (original export)
Writes:  CCV-10129937-update.xml
"""

import re
import uuid
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
REPO       = Path(__file__).parent.parent.parent
XML_IN     = Path(__file__).parent / "CCV-10129937.xml"
XML_OUT    = Path(__file__).parent / "CCV-10129937-update.xml"
PAPERS_BIB = REPO / "references" / "papers.bib"
POSTERS_BIB= REPO / "references" / "posters.bib"
TALKS_BIB  = REPO / "references" / "talks.bib"

# ── CCV fixed IDs (same across all instances of each record type) ──────────────
SECTION_ID_JOURNAL = "9a34d6b273914f18b2273e8de7c48fd6"
SECTION_ID_CONF    = "4b9f909503cd4c8aa8d826c87d6d874d"
PARENT_PUB_ID      = "46e8f57e67db48b29d84dda77cf0ef51"  # Publications

# Field IDs for Journal Articles (from existing entries)
JA_FIELDS = {
    "Article Title":                 "f3fd4878d47c4e83aef6959620ba4870",
    "Journal":                       "5c04ea4dae464499807d0b40b4cad049",
    "Volume":                        "0a826c656ff34e579dfcbfb373771260",
    "Issue":                         "cc1d9e14945b4e8496641dbe22b3448a",
    "Page Range":                    "00ba1799ece344dc8d0779a3f05a4df8",
    "Publishing Status":             "3b56e4362d6a495aa5d22a1de5914741",
    "Year":                          "6fafe258e19e49a7884428cb49d75424",
    "Publisher":                     "4ad593960aba4a21bf154fa8daf37f9f",
    "Publication Location":          "4c3bc805ceaa42259f014514fc4905f8",
    "Description / Contribution Value": "1167905d079c4400ae7a4a76a203a445",
    "URL":                           "478545acac5340c0a73b7e0d2a4bee06",
    "Refereed?":                     "2089ff1a86844b6c9a10fc63469f9a9d",
    "Open Access?":                  "51b7eaff05444990af823b9d80924f5b",
    "Synthesis?":                    "b779cc6478bd4b09b516c6d55e938583",
    "Contribution Role":             "289c8814fff141d89b12569d49aa2cb3",
    "Number of Contributors":        "dc7922dfa04348a3a83c9afb5bbaa24a",
    "Authors":                       "bc3b428d99384b04bb749311bb804e1d",
    "Editors":                       "707a6e0ca58341a5a82fb923b2842530",
    "DOI":                           "375a0e2ea0914291b05b0529c4755aa7",
    "Contribution Percentage":       "9afd9e28df47464faf3f9ee2c4809e25",
    "Description of Contribution Role": "9f2e163dfcbf4abdb73e9d5c4daf03c4",
}

# Field IDs for Conference Publications (from existing entries)
CP_FIELDS = {
    "Conference Publication Type":   "81ef87c09ded47ae8880b8d79e83406f",
    "Publication Title":             "8e6ee535c95e42ec866b777c7472bafb",
    "Conference Name":               "b3c8a60c053a405597b92899d95765a3",
    "Conference Location":           "5813833859a64bb58ee55e4f55aff29b",
    "City":                          "c2efd9725588489b8df73467c5597c32",
    "Conference Date":               "99b57db653a841ccbd5f8e52079745c0",
    "Published In":                  "1a1b39e861054ee59d270e66271a4ead",
    "Page Range":                    "684ccb1fcdd7421f89b304ff5c40579d",
    "Publishing Status":             "080301b1f1c0464bba7fcfa1fa8fe182",
    "Year":                          "0318d139f3e0479083188ff8319a97b2",
    "Publisher":                     "0c357193a93f4137a87394401ac81958",
    "Publication Location":          "2fc69f4076f149bda1f0bb3e0ef9d79f",
    "Description / Contribution Value": "a6e901e5f0cf48a3a7d674bf1e6fcd7f",
    "URL":                           "61690b466fb748d99ed29b340c0ee60b",
    "Refereed?":                     "560a2ce08e14497ba575af760eb12ba9",
    "Invited?":                      "06295e65f66b4c6aa286d08bd9fac59b",
    "Contribution Role":             "b101f8f057db434ba4fdee3a86c387cc",
    "Number of Contributors":        "1a66ad40654a45c9a0119b19d7cf20a6",
    "Authors":                       "3cc54d9bb92d421da46548979048396f",
    "Editors":                       "018e656a0f824b1f91a6a2cb33ac61dd",
    "DOI":                           "49e5507889954743b104959e62d9e496",
    "Contribution Percentage":       "575eaa1383ac49ed9d78b5a970a76eb8",
    "Description of Contribution Role": "890336779db441d8a38e7709f6866d15",
}

# LOV IDs
LOV_STATUS_PUBLISHED  = "00000000000000000000000100001704"
LOV_STATUS_IN_PRESS   = "00000000000000000000000100001703"
LOV_STATUS_SUBMITTED  = "00000000000000000000000100001700"

LOV_TYPE_ABSTRACT = "00000000000000000000000100007001"
LOV_TYPE_POSTER   = "00000000000000000000000100007002"

LOV_COUNTRY = {
    "usa":           "00000000000000000000000000002840",
    "united states": "00000000000000000000000000002840",
    "canada":        "00000000000000000000000000002124",
    "switzerland":   "00000000000000000000000000002756",
    "ch":            "00000000000000000000000000002756",
}
LOV_COUNTRY_NAME = {
    "00000000000000000000000000002840": "United States of America",
    "00000000000000000000000000002124": "Canada",
    "00000000000000000000000000002756": "Switzerland",
}


# ── BibTeX parser (same as compare_ccv.py) ────────────────────────────────────
def clean_bib_value(val: str) -> str:
    val = val.strip()
    if val.startswith('"') and val.endswith('"'):
        val = val[1:-1]
    while val.startswith('{') and val.endswith('}'):
        val = val[1:-1]
    prev = None
    while prev != val:
        prev = val
        val = re.sub(r'\{([^{}]*)\}', r'\1', val)
    val = val.replace('{', '').replace('}', '')
    val = val.replace('~', ' ')    # LaTeX non-breaking space
    val = val.replace('--', '–')  # LaTeX en-dash
    val = re.sub(r'\s+', ' ', val).strip()
    return val


def parse_bib(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    entries = []
    raw_entries = re.split(r'(?=@\w+\{)', text)
    for raw in raw_entries:
        raw = raw.strip()
        if not raw:
            continue
        m = re.match(r'@(\w+)\{([^,]+),', raw)
        if not m:
            continue
        entry = {"_type": m.group(1).lower(), "_key": m.group(2).strip()}
        body = raw[m.end():]
        field_re = re.compile(r'(\w+)\s*=\s*', re.S)
        pos = 0
        while pos < len(body):
            fm = field_re.search(body, pos)
            if not fm:
                break
            field_name = fm.group(1).lower()
            val_start = fm.end()
            if val_start >= len(body):
                break
            delim = body[val_start]
            if delim == '{':
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
                i = val_start + 1
                while i < len(body):
                    if body[i] == '"' and body[i-1] != '\\':
                        break
                    i += 1
                val = body[val_start+1:i]
                pos = i + 1
            else:
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
    t = title.lower()
    t = t.replace('~', ' ')       # LaTeX non-breaking space → regular space
    t = re.sub(r'[^a-z0-9 ]', '', t)   # remove other non-alphanumeric
    return re.sub(r'\s+', ' ', t).strip()


# ── Author formatting ──────────────────────────────────────────────────────────
def _split_authors(raw: str) -> list[str]:
    """Split BibTeX author string into list of individual author strings."""
    return [a.strip() for a in re.split(r'\s+and\s+', raw, flags=re.IGNORECASE) if a.strip()]


def authors_abbreviated(raw: str) -> str:
    """
    Format for journal articles: 'Hilton LK , Collinge B , ...'
    BibTeX format: 'Hilton, Laura K. and Collinge, Brett and ...'
    """
    if not raw:
        return ""
    result = []
    for a in _split_authors(raw):
        if ',' in a:
            last, first = [p.strip() for p in a.split(',', 1)]
            # Build initials from first name parts
            initials = ''.join(p[0].upper() for p in first.split() if p)
            result.append(f"{last} {initials}")
        else:
            # Already in "First Last" order — just take the last word as surname
            parts = a.split()
            if len(parts) >= 2:
                last = parts[-1]
                initials = ''.join(p[0].upper() for p in parts[:-1] if p)
                result.append(f"{last} {initials}")
            else:
                result.append(a)
    return " , ".join(result)


def reformat_firstlast_to_abbreviated(stored: str) -> str:
    """
    Convert a stored CCV author string (First Last or F. Last or mixed) into
    the canonical abbreviated form: 'Last Initials , Last Initials , ...'

    Called as a fallback when a bib entry cannot be matched by title.
    Names are comma-separated; within each name the last whitespace token
    is treated as the surname and all preceding tokens supply initials.
    Examples:
      'Laura K. Hilton'         → 'Hilton LK'
      'D. A Russler-Germain'    → 'Russler-Germain DA'
      'Haya Shaalan'            → 'Shaalan H'
      'Ciare Louise Freeman'    → 'Freeman CL'
    """
    if not stored:
        return ""
    result = []
    for name in re.split(r',\s*', stored):
        name = name.strip()
        if not name:
            continue
        tokens = name.split()
        if len(tokens) == 1:
            # Single token — check if it already looks abbreviated (e.g. 'Hilton')
            result.append(tokens[0])
            continue
        # Last token = surname; strip any trailing period
        surname = tokens[-1].rstrip('.')
        # All preceding tokens → first character only, strip periods, uppercase
        initials = ''.join(t.lstrip('.')[0].upper()
                           for t in tokens[:-1]
                           if t.lstrip('.'))
        result.append(f"{surname} {initials}" if initials else surname)
    return " , ".join(result)


# ── Address parsing ────────────────────────────────────────────────────────────
def parse_address(address: str) -> tuple[str, str, str, str | None]:
    """
    Returns (city_with_state, country_lov_id, country_name, city_display).
    Examples:
      'San Diego, CA, USA'  → ('San Diego, CA', '...2840', 'United States of America', 'San Diego, CA')
      'Lugano, CH'          → ('Lugano', '...2756', 'Switzerland', 'Lugano')
      'Virtual'             → ('Virtual', None, '', 'Virtual')
    """
    address = address.strip()
    if not address or address.lower() == "virtual":
        return "Virtual", None, "", "Virtual"

    parts = [p.strip() for p in address.split(",")]
    # Last part is usually country code or name
    last = parts[-1].lower()
    country_lov = LOV_COUNTRY.get(last)
    country_name = LOV_COUNTRY_NAME.get(country_lov, "") if country_lov else ""

    # City display: everything before the country
    if len(parts) >= 3:
        city_display = ", ".join(parts[:-1])  # e.g. "San Diego, CA"
    elif len(parts) == 2:
        city_display = parts[0]
    else:
        city_display = address

    return city_display, country_lov, country_name, city_display


# ── Publishing status heuristic ────────────────────────────────────────────────
def publishing_status(entry: dict) -> tuple[str, str]:
    """Returns (lov_id, label)."""
    journal = entry.get("journal", "").lower()
    if "medrxiv" in journal or "biorxiv" in journal:
        return LOV_STATUS_SUBMITTED, "Submitted"
    pmid = entry.get("pmid", "")
    if pmid:
        return LOV_STATUS_PUBLISHED, "Published"
    pages = entry.get("pages", "")
    # Real page numbers look like "123-456" or "e705"
    if pages and re.search(r'\d{3,}', pages):
        return LOV_STATUS_PUBLISHED, "Published"
    return LOV_STATUS_IN_PRESS, "In Press"


# ── CCV XML parser ─────────────────────────────────────────────────────────────
def parse_ccv_existing(path: Path):
    """Return sets of normalised titles already in the CCV."""
    tree = ET.parse(path)
    root = tree.getroot()
    journal_titles: set[str] = set()
    conf_titles:    set[str] = set()

    def field_val(section_el, label):
        for f in section_el.iter("field"):
            if f.get("label") == label:
                v = f.find("value")
                if v is not None and v.text:
                    return v.text.strip()
        return ""

    for s in root.iter("section"):
        lbl = s.get("label", "")
        if lbl == "Journal Articles":
            t = field_val(s, "Article Title")
            if t:
                journal_titles.add(normalize_title(t))
        elif lbl == "Conference Publications":
            t = field_val(s, "Publication Title")
            if t:
                conf_titles.add(normalize_title(t))

    return journal_titles, conf_titles


# ── XML element builders ───────────────────────────────────────────────────────
def new_record_id() -> str:
    return uuid.uuid4().hex  # 32-char hex, matching CCV's format


def make_field(field_id: str, label: str, content_xml: str) -> ET.Element:
    """Build a <field> element with the given content XML string."""
    # Build via string to preserve exact format, then parse
    raw = f'<field id="{field_id}" label="{label}">{content_xml}</field>'
    return ET.fromstring(raw)


def string_val(text: str) -> str:
    """XML snippet for a plain string value."""
    safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    return f'<value type="String">{safe}</value>'


def empty_string() -> str:
    return '<value type="String"/>'


def year_val(year: str) -> str:
    if year:
        return f'<value format="yyyy" type="Year">{year}</value>'
    return '<value format="yyyy" type="Year"/>'


def yearmonth_val(ym: str) -> str:
    """ym like '2023/11'."""
    if ym:
        return f'<value format="yyyy/MM" type="YearMonth">{ym}</value>'
    return '<value format="yyyy/MM" type="YearMonth"/>'


def lov_val(lov_id: str, text: str) -> str:
    return f'<lov id="{lov_id}">{text}</lov>'


def bilingual_empty() -> str:
    return '<value type="Bilingual"/><bilingual><french/><english/></bilingual>'


def number_val() -> str:
    return '<value type="Number"/>'


def bib_year_month(entry: dict) -> str:
    year = entry.get("year", "")
    month_raw = entry.get("month", "").lower()
    month_map = {
        "jan": "01", "feb": "02", "mar": "03", "apr": "04",
        "may": "05", "jun": "06", "jul": "07", "aug": "08",
        "sep": "09", "oct": "10", "nov": "11", "dec": "12",
        "january": "01", "february": "02", "march": "03", "april": "04",
        "june": "06", "july": "07", "august": "08",
        "september": "09", "october": "10", "november": "11", "december": "12",
    }
    month = month_map.get(month_raw, "")
    if year and month:
        return f"{year}/{month}"
    return year


# ── Build new Journal Article section element ──────────────────────────────────
def make_journal_article(entry: dict) -> ET.Element:
    title   = entry.get("title", "")
    journal = entry.get("journal", "")
    volume  = entry.get("volume", "")
    number  = entry.get("number", "")
    pages   = entry.get("pages", "")
    year    = entry.get("year", "")
    doi     = entry.get("doi", "")
    url     = f"https://doi.org/{doi}" if doi else entry.get("url", "")
    authors = authors_abbreviated(entry.get("author", ""))
    status_lov, status_text = publishing_status(entry)

    # Normalise page range format: replace em-dash with hyphen
    pages = pages.replace("–", "-").replace("--", "-")

    sec = ET.Element("section", id=SECTION_ID_JOURNAL, label="Journal Articles",
                     recordId=new_record_id())

    fields = [
        (JA_FIELDS["Article Title"],    string_val(title)),
        (JA_FIELDS["Journal"],          string_val(journal)),
        (JA_FIELDS["Volume"],           string_val(volume) if volume else empty_string()),
        (JA_FIELDS["Issue"],            string_val(number) if number else empty_string()),
        (JA_FIELDS["Page Range"],       string_val(pages) if pages else empty_string()),
        (JA_FIELDS["Publishing Status"],lov_val(status_lov, status_text)),
        (JA_FIELDS["Year"],             year_val(year)),
        (JA_FIELDS["Publisher"],        empty_string()),
        (JA_FIELDS["Publication Location"], ""),      # empty field, no child
        (JA_FIELDS["Description / Contribution Value"], bilingual_empty()),
        (JA_FIELDS["URL"],              string_val(url) if url else empty_string()),
        (JA_FIELDS["Refereed?"],        ""),
        (JA_FIELDS["Open Access?"],     ""),
        (JA_FIELDS["Synthesis?"],       ""),
        (JA_FIELDS["Contribution Role"],""),
        (JA_FIELDS["Number of Contributors"], number_val()),
        (JA_FIELDS["Authors"],          string_val(authors) if authors else empty_string()),
        (JA_FIELDS["Editors"],          empty_string()),
        (JA_FIELDS["DOI"],              empty_string()),
        (JA_FIELDS["Contribution Percentage"], ""),
        (JA_FIELDS["Description of Contribution Role"], bilingual_empty()),
    ]

    label_map = {v: k for k, v in JA_FIELDS.items()}
    for fid, content in fields:
        lbl = label_map[fid]
        if content:
            raw = f'<field id="{fid}" label="{lbl}">{content}</field>'
        else:
            raw = f'<field id="{fid}" label="{lbl}"/>'
        sec.append(ET.fromstring(raw))

    return sec


# ── Build new Conference Publication section element ───────────────────────────
def make_conf_publication(entry: dict, pub_type: str) -> ET.Element:
    """pub_type: 'Poster' or 'Abstract'"""
    title     = entry.get("title", "")
    booktitle = entry.get("booktitle", "")
    address   = entry.get("address", "")
    year_month = bib_year_month(entry)
    year      = entry.get("year", "")
    pages     = entry.get("pages", "").replace("--", "-")
    doi       = entry.get("doi", "")
    authors   = authors_abbreviated(entry.get("author", ""))

    city_display, country_lov, country_name, _ = parse_address(address)

    type_lov = LOV_TYPE_POSTER if pub_type == "Poster" else LOV_TYPE_ABSTRACT

    sec = ET.Element("section", id=SECTION_ID_CONF, label="Conference Publications",
                     recordId=new_record_id())

    # Conference Location field: lov if we know country, else empty field
    if country_lov:
        loc_content = lov_val(country_lov, country_name)
    else:
        loc_content = ""  # empty field

    fields = [
        (CP_FIELDS["Conference Publication Type"], lov_val(type_lov, pub_type)),
        (CP_FIELDS["Publication Title"],           string_val(title)),
        (CP_FIELDS["Conference Name"],             string_val(booktitle) if booktitle else empty_string()),
        (CP_FIELDS["Conference Location"],         loc_content),
        (CP_FIELDS["City"],                        string_val(city_display) if city_display and city_display != "Virtual" else empty_string()),
        (CP_FIELDS["Conference Date"],             yearmonth_val(year_month)),
        (CP_FIELDS["Published In"],                empty_string()),
        (CP_FIELDS["Page Range"],                  string_val(pages) if pages else empty_string()),
        (CP_FIELDS["Publishing Status"],           ""),
        (CP_FIELDS["Year"],                        year_val(year) if not year_month else year_val("")),
        (CP_FIELDS["Publisher"],                   empty_string()),
        (CP_FIELDS["Publication Location"],        ""),
        (CP_FIELDS["Description / Contribution Value"], bilingual_empty()),
        (CP_FIELDS["URL"],                         empty_string()),
        (CP_FIELDS["Refereed?"],                   ""),
        (CP_FIELDS["Invited?"],                    ""),
        (CP_FIELDS["Contribution Role"],           ""),
        (CP_FIELDS["Number of Contributors"],      number_val()),
        (CP_FIELDS["Authors"],                     string_val(authors) if authors else empty_string()),
        (CP_FIELDS["Editors"],                     empty_string()),
        (CP_FIELDS["DOI"],                         string_val(doi) if doi else empty_string()),
        (CP_FIELDS["Contribution Percentage"],     ""),
        (CP_FIELDS["Description of Contribution Role"], bilingual_empty()),
    ]

    label_map = {v: k for k, v in CP_FIELDS.items()}
    for fid, content in fields:
        lbl = label_map[fid]
        if content:
            raw = f'<field id="{fid}" label="{lbl}">{content}</field>'
        else:
            raw = f'<field id="{fid}" label="{lbl}"/>'
        sec.append(ET.fromstring(raw))

    return sec


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    print("Parsing existing CCV …")
    ccv_journal_titles, ccv_conf_titles = parse_ccv_existing(XML_IN)
    print(f"  {len(ccv_journal_titles)} journal articles already in CCV")
    print(f"  {len(ccv_conf_titles)} conference publications already in CCV")

    print("Parsing bibliography files …")
    papers  = parse_bib(PAPERS_BIB)
    posters = parse_bib(POSTERS_BIB)
    talks   = parse_bib(TALKS_BIB)

    # ── Find missing entries ───────────────────────────────────────────────────
    missing_papers = [e for e in papers
                      if normalize_title(e.get("title","")) not in ccv_journal_titles]
    missing_posters= [e for e in posters
                      if normalize_title(e.get("title","")) not in ccv_conf_titles]

    # For talks, deduplicate by normalised title (bib has duplicate ICML entries)
    seen_conf = set(ccv_conf_titles)
    missing_talks = []
    for e in talks:
        nt = normalize_title(e.get("title",""))
        if nt not in seen_conf:
            missing_talks.append(e)
            seen_conf.add(nt)  # prevent duplicate bib entries adding twice

    print(f"  {len(missing_papers)} journal articles to add")
    print(f"  {len(missing_posters)} poster presentations to add")
    print(f"  {len(missing_talks)} oral presentations to add")

    # ── Build title → bib-entry lookup for all conference entries ─────────────
    conf_bib_by_title: dict[str, dict] = {}
    for e in posters + talks:
        nt = normalize_title(e.get("title", ""))
        if nt:
            conf_bib_by_title[nt] = e

    # ── Load and modify XML ────────────────────────────────────────────────────
    ET.register_namespace("generic-cv", "http://www.cihr-irsc.gc.ca/generic-cv/1.0.0")
    tree = ET.parse(XML_IN)
    root = tree.getroot()

    # Find Publications parent section
    pub_section = None
    for s in root.iter("section"):
        if s.get("id") == PARENT_PUB_ID:
            pub_section = s
            break
    if pub_section is None:
        raise RuntimeError("Could not find Publications section in XML")

    # ── Reformat author strings in existing conference publications ────────────
    reformat_count = 0
    for s in pub_section:
        if s.get("label") != "Conference Publications":
            continue
        # Get the publication title to look up the bib entry
        title_el = None
        author_field = None
        for f in s.iter("field"):
            if f.get("label") == "Publication Title":
                v = f.find("value")
                title_el = v.text.strip() if v is not None and v.text else ""
            if f.get("label") == "Authors":
                author_field = f
        if author_field is None:
            continue
        existing_authors_el = author_field.find("value")
        existing_authors = (existing_authors_el.text or "").strip() if existing_authors_el is not None else ""
        if not existing_authors:
            continue

        # Prefer the bib entry's author field (unambiguous Last, First format)
        nt = normalize_title(title_el or "")
        bib_entry = conf_bib_by_title.get(nt)
        if bib_entry and bib_entry.get("author"):
            new_authors = authors_abbreviated(bib_entry["author"])
        else:
            # Fall back to heuristic parsing of the stored full-name string
            new_authors = reformat_firstlast_to_abbreviated(existing_authors)

        if new_authors != existing_authors:
            if existing_authors_el is not None:
                existing_authors_el.text = new_authors
            reformat_count += 1

    print(f"  Reformatted authors in {reformat_count} existing conference publications")

    # Find insertion indices within pub_section children
    children = list(pub_section)
    last_ja_idx = -1
    last_cp_idx = -1
    for i, child in enumerate(children):
        if child.get("label") == "Journal Articles":
            last_ja_idx = i
        if child.get("label") == "Conference Publications":
            last_cp_idx = i

    # Insert journal articles after the last existing Journal Article
    # (insert in reverse order so indices stay valid)
    insert_at = last_ja_idx + 1
    for entry in reversed(missing_papers):
        el = make_journal_article(entry)
        pub_section.insert(insert_at, el)
        print(f"  + Journal: {entry.get('title','')[:70]}")

    # After insertion, recompute last_cp_idx
    children = list(pub_section)
    last_cp_idx = max(i for i, c in enumerate(children)
                      if c.get("label") == "Conference Publications")
    insert_at = last_cp_idx + 1

    all_conf = [(e, "Poster") for e in missing_posters] + [(e, "Abstract") for e in missing_talks]
    for entry, ptype in reversed(all_conf):
        el = make_conf_publication(entry, ptype)
        pub_section.insert(insert_at, el)
        print(f"  + {ptype}: {entry.get('title','')[:70]}")

    # ── Write output ───────────────────────────────────────────────────────────
    tree.write(XML_OUT, encoding="UTF-8", xml_declaration=True)
    print(f"\nWrote {XML_OUT}")
    print(f"Added {len(missing_papers)} journal articles and "
          f"{len(missing_posters)+len(missing_talks)} conference publications.")

    # ── Flag entries with missing volume/issue/pages ───────────────────────────
    # Check all papers (new + already-in-CCV), skipping preprints/in-press
    all_papers = papers  # full list; covers both new and existing bib entries

    def looks_like_real_pages(p: str) -> bool:
        """True if pages looks like a proper print page range, not an online ID."""
        if not p:
            return False
        # Reject online-only identifiers: bloodadvances.2025..., e705, S123, etc.
        if re.search(r'[a-zA-Z].*\d{4,}', p):   # letters then 4+ digits = ahead-of-print ID
            return False
        if re.match(r'^[eE]\d+$', p):             # e.g. e705
            return False
        return bool(re.search(r'\d', p))          # at least one digit

    incomplete = []
    for e in all_papers:
        _, status_text = publishing_status(e)
        # Only flag entries that are (or should be) Published
        if status_text not in ("Published", "In Press"):
            continue
        title  = e.get("title", "")
        year   = e.get("year", "")
        volume = e.get("volume", "")
        number = e.get("number", "")
        pages  = e.get("pages", "")
        doi    = e.get("doi", "")
        missing = []
        if not volume:
            missing.append("volume")
        if not number:
            missing.append("issue")
        if not looks_like_real_pages(pages):
            missing.append(f"pages (has: '{pages}')" if pages else "pages")
        if missing:
            incomplete.append((year, title, doi, missing))

    if incomplete:
        incomplete.sort(key=lambda x: x[0], reverse=True)
        print(f"\n⚠  {len(incomplete)} published/in-press papers with missing volume/issue/pages:")
        print(f"   (Update these in Zotero and re-run, or fix manually in the CCV)")
        print()
        for year, title, doi, missing in incomplete:
            print(f"  [{year}] {title[:72]}")
            print(f"         Missing: {', '.join(missing)}")
            if doi:
                print(f"         DOI: https://doi.org/{doi}")
            print()
    else:
        print("\nAll published papers have complete volume/issue/pages. ✓")


if __name__ == "__main__":
    main()
