from pathlib import Path

import pytest

from k10plus.marc_dump_analysis import marc_analyser
from k10plus.verify_bibframe_dates import (
    compare_statistics,
    deep_compare_statistics,
    generate_bibframe_statistics,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@pytest.fixture(scope="module")
def generated_stats():
    """
    Run parsing and file generation exactly once for the entire module.
    """
    rdf_file = DATA_DIR / "schumann_bib.ttl"
    bf_output = DATA_DIR / "statistics_bibframe.txt"
    xml_file = DATA_DIR / "schumann.xml"

    # Generate statistics once
    generate_bibframe_statistics(rdf_file, bf_output)
    marc_analyser(str(xml_file), ["100", "700"], ["4"])

    return {
        "bf_output": bf_output,
        "date_counts": DATA_DIR / "date_counts_bibframe.json",
        "record_dates": DATA_DIR / "dates_with_recordID_bibframe.json",
    }


def test_compare_statistics(generated_stats):
    """
    Differential/Cross-Validation Testing
    Test that the numeric date counts derived from the BIBFRAME RDF
    match the date counts from the MARC XML statistics exactly.
    """
    marc_json_path = DATA_DIR / "date_counts_marc.json"
    bf_json_path = DATA_DIR / "date_counts_bibframe.json"
    assert compare_statistics(marc_json_path, bf_json_path)


def test_deep_compare_statistics(generated_stats):
    """
    Checking whether the bibframe SPARQL Query and MARC Analysis use the same date for a record.
    """
    marc_json_path = DATA_DIR / "dates_with_recordID_marc.json"
    bf_json_path = DATA_DIR / "dates_with_recordID_bibframe.json"
    assert deep_compare_statistics(marc_json_path, bf_json_path)


def test_bibframe_statistics_regression(file_regression, generated_stats):
    """
    Test for regression on the generated statistics_bibframe.txt file.
    """
    with open(generated_stats["bf_output"], "r", encoding="utf-8") as f:
        actual_output = f.read()

    file_regression.check(actual_output, extension=".txt")


def test_date_counts_bibframe_regression(file_regression, generated_stats):
    """
    Test for regression on the generated date_counts_bibframe.json file.
    """
    with open(generated_stats["date_counts"], "r", encoding="utf-8") as f:
        actual_output = f.read()

    file_regression.check(actual_output, extension=".json")


def test_dates_with_recordID_bibframe_regression(file_regression, generated_stats):
    """
    Test for regression on the generated dates_with_recordID_bibframe.json file.
    """
    with open(generated_stats["record_dates"], "r", encoding="utf-8") as f:
        actual_output = f.read()

    file_regression.check(actual_output, extension=".json")
