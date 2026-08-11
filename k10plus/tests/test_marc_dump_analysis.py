"""
Testing the marc dump analysis script for regression.

Run this test file with:
    uv run pytest tests/test_marc_dump_analysis.py
"""

from pathlib import Path

import pytest

from k10plus.marc_dump_analysis import marc_analyser

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def test_marc_analyser_regression(file_regression):
    """
    Test for regression using pytest-regressions.
    """
    output_file = DATA_DIR / "statistics.txt"
    marc_analyser(
        str(DATA_DIR / "schumann.xml"),
        ["100", "700"],
        ["4"],
        output_path=str(output_file),
    )

    with open(output_file, "r", encoding="utf-8") as f:
        actual_output = f.read()

    file_regression.check(actual_output, extension=".txt")


@pytest.mark.slow
def test_marc_analyser_regression2(file_regression):
    """
    Test for regression using pytest-regressions.
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
