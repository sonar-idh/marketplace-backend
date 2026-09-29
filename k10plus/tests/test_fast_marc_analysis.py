"""
Testing the fast marc analysis script for regression.

Run this test file with:
    uv run pytest tests/test_fast_marc_analysis.py
"""

from pathlib import Path

import pytest

from k10plus.fast_marc_analysis import fast_marc_analyser

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@pytest.fixture(scope="module")
def generated_marc_stats():
    """
    Run the MARC analyser exactly once for the entire module.
    """
    output_file = DATA_DIR / "statistics.json"
    fast_marc_analyser(
        str(DATA_DIR / "schumann.xml"),
        ["100", "700"],
        output_path=str(output_file),
    )
    return {
        "marc_output": output_file,
    }


def test_marc_analyser_regression(file_regression, generated_marc_stats):
    """
    Test for regression on the generated statistics.json file.
    """
    with open(generated_marc_stats["marc_output"], "r", encoding="utf-8") as f:
        actual_output = f.read()

    file_regression.check(actual_output, extension=".json")


@pytest.mark.slow
def test_marc_analyser_regression2(file_regression):
    """
    Test for regression using pytest-regressions on kxp.mrcxml.
    """
    output_file = DATA_DIR / "statistics_kxpmrcxml.json"
    fast_marc_analyser(
        str(DATA_DIR / "kxp.mrcxml"),
        ["100", "700"],
        output_path=str(output_file),
    )

    with open(output_file, "r", encoding="utf-8") as f:
        actual_output = f.read()

    file_regression.check(actual_output, extension=".json")
