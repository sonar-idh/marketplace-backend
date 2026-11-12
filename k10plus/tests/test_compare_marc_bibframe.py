"""
Compare MARC and BIBFRAME statistics to validate no data loss in the transformation.

Usage: uv run pytest tests/test_compare_marc_bibframe.py
Input: data/schumann.xml (MARCXML) and data/schumann_bib.ttl (its BIBFRAME conversion)
Output: none (assertions only)
"""

import json
import re
from collections import Counter
from pathlib import Path

import pytest

from bibframe_statistics import generate_bibframe_statistics
from fast_marc_analysis import fast_marc_analyser

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MARC_TAGS = ["100", "110", "111", "700", "710", "711", "040"]


@pytest.fixture(scope="module")
def generated_stats(tmp_path_factory):
    """Generate MARC and BIBFRAME statistics once for the module."""
    out_dir = tmp_path_factory.mktemp("stats")
    marc_stats = out_dir / "statistics_marc.json"
    bibframe_stats = out_dir / "statistics_bibframe.json"

    fast_marc_analyser(DATA_DIR / "schumann.xml", MARC_TAGS, output_path=marc_stats)
    generate_bibframe_statistics(DATA_DIR / "schumann_bib.ttl", bibframe_stats)

    return marc_stats, bibframe_stats


def _load(generated_stats):
    return (json.loads(p.read_text(encoding="utf-8")) for p in generated_stats)


def _year_counts(date_counts: dict) -> Counter:
    """Reduce date strings ('[ca. 1832]', '07.12.1884', '(c) 1860') to 4-digit year counts."""
    years = Counter()
    for date, count in date_counts.items():
        if date.startswith("\u00a9"):  # copyright date: mapped to bf:copyrightDate, not a provision date
            continue
        for year in re.findall(r"\d{4}", date):
            years[year] += count
    return years

def test_total_records_match(generated_stats):
    """Total record counts in MARC must equal those in BIBFRAME."""
    marc, bibframe = _load(generated_stats)
    assert marc["total_records"] == bibframe["total_records"]

def test_total_records_rda_ger_encoding_match(generated_stats):
    """Total record counts with data quality filter in MARC must equal those in BIBFRAME."""
    marc, bibframe = _load(generated_stats)
    assert marc["total_records_rda_ger_encoding"] == bibframe["total_records_rda_ger_encoding"]

def test_cataloging_source_match(generated_stats):
    """Total record counts with cataloging source in MARC must equal those in BIBFRAME."""
    marc, bibframe = _load(generated_stats)
    assert marc["cataloging_source"]["rda_ger"] == bibframe["cataloging_source"]

def test_encoding_level_match(generated_stats):
    """MARC records with full encoding level (leader/17 = blank) must equal the BIBFRAME count.

    The BIBFRAME query counts a single level (bflc:encodingLevel = menclvl/f), a plain int,
    while MARC reports a dict per leader/17 value.
    """
    marc, bibframe = _load(generated_stats)
    assert marc["encoding_level_counts"][" "] == bibframe["encoding_level_counts"]

def test_place_of_publication_match(generated_stats):
    """008/15-18 in MARC must equal bf:place in BIBFRAME Instance/Provision activity."""
    marc, bibframe = _load(generated_stats)
    assert marc["place_of_publication_count"] == bibframe["place_of_publication_count"]

def test_language_match(generated_stats):
    """008/35-37 + 041$a in MARC must equal bf:language in BIBFRAME."""
    marc, bibframe = _load(generated_stats)
    assert marc["language_counts"] == bibframe["language_counts"]


# MARC 264 ind2 -> BIBFRAME ProvisionActivity subclass / property name
FUNCTION_NAMES = {
    "0": "Production",
    "1": "Publication",
    "2": "Distribution",
    "3": "Manufacture",
    "4": "copyrightDate",
}


def test_function_of_entity_counts_match(generated_stats):
    """264 ind2 (once per record) in MARC must equal the activity types in BIBFRAME."""
    marc, bibframe = _load(generated_stats)
    marc_functions = {
        FUNCTION_NAMES.get(code, code): count
        for code, count in marc["function_of_entity_counts"].items()
    }
    assert marc_functions == bibframe["function_of_entity_counts"]


def test_specific_date_years_match(generated_stats):
    """Years in 264 $c (MARC) must equal years in bflc:simpleDate (BIBFRAME).

    Only the years are compared: the converter normalises brackets and moves
    copyright dates, so the raw strings are not expected to be identical.
    """
    marc, bibframe = _load(generated_stats)
    marc_years = _year_counts(marc["specific_date_counts"])
    bf_years = _year_counts(bibframe["specific_date_counts"])
    diff = {
        year: {"marc": marc_years[year], "bibframe": bf_years[year]}
        for year in sorted(marc_years.keys() | bf_years.keys())
        if marc_years[year] != bf_years[year]
    }
    assert not diff, f"Year counts differ (MARC vs BIBFRAME): {diff}"


def _marc_role_codes(role_counts: dict) -> Counter:
    """Turn MARC keys like '700_Author' / '100_Unknown (xyz)' into relator-code counts."""
    relators = json.loads((DATA_DIR / "relators.json").read_text(encoding="utf-8"))
    name_to_code = {name: code for code, name in relators.items()}
    codes = Counter()
    for key, count in role_counts.items():
        name = key.split("_", 1)[1]  # drop the "<tag>_" prefix
        if name.startswith("Unknown (") and name.endswith(")"):
            code = name[len("Unknown (") : -1]
        else:
            code = name_to_code[name]
        codes[code] += count
    return codes


def test_role_counts_match(generated_stats):
    """Every $4 in 100/110/111/700/710/711 (MARC) must equal one bf:role on a contribution."""
    marc, bibframe = _load(generated_stats)
    marc_roles = _marc_role_codes(marc["role_counts"])
    bf_roles = Counter(bibframe["role_counts"])
    diff = {
        code: {"marc": marc_roles[code], "bibframe": bf_roles[code]}
        for code in sorted(marc_roles.keys() | bf_roles.keys())
        if marc_roles[code] != bf_roles[code]
    }
    assert not diff, f"Role counts differ (MARC vs BIBFRAME): {diff}"
