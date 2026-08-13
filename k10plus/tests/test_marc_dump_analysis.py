"""
Testing the marc dump analysis script for regression.

Run this test file with:
    uv run pytest tests/test_marc_dump_analysis.py
"""

from pathlib import Path

import pytest

from k10plus.marc_dump_analysis import marc_analyser

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@pytest.fixture(scope="module")
def generated_marc_stats():
    """
    Run the MARC analyser exactly once for the entire module.
    """
    output_file = DATA_DIR / "statistics.txt"
    marc_analyser(
        str(DATA_DIR / "schumann.xml"),
        ["100", "700"],
        ["4"],
        output_path=str(output_file),
    )
    return {
        "marc_output": output_file,
        "date_counts": DATA_DIR / "date_counts_marc.json",
        "record_dates": DATA_DIR / "dates_with_recordID_marc.json",
    }


def test_marc_analyser_regression(file_regression, generated_marc_stats):
    """
    Test for regression on the generated statistics.txt file.
    """
    with open(generated_marc_stats["marc_output"], "r", encoding="utf-8") as f:
        actual_output = f.read()

    file_regression.check(actual_output, extension=".txt")


def test_date_counts_marc_regression(file_regression, generated_marc_stats):
    """
    Test for regression on the generated date_counts_marc.json file.
    """
    with open(generated_marc_stats["date_counts"], "r", encoding="utf-8") as f:
        actual_output = f.read()

    file_regression.check(actual_output, extension=".json")


def test_dates_with_recordID_marc_regression(file_regression, generated_marc_stats):
    """
    Test for regression on the generated dates_with_recordID_marc.json file.
    """
    with open(generated_marc_stats["record_dates"], "r", encoding="utf-8") as f:
        actual_output = f.read()

    file_regression.check(actual_output, extension=".json")


@pytest.mark.slow
def test_marc_analyser_regression2(file_regression):
    """
    Test for regression using pytest-regressions on kxp.mrcxml.
    """
    output_file = DATA_DIR / "statistics_kxpmrcxml.txt"
    marc_analyser(
        str(DATA_DIR / "kxp.mrcxml"),
        ["100", "700"],
        ["4"],
        output_path=str(output_file),
    )

    with open(output_file, "r", encoding="utf-8") as f:
        actual_output = f.read()

    file_regression.check(actual_output, extension=".txt")
