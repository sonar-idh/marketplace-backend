"""
Testing the fast marc analysis script for regression.

Run this test file with:
    uv run pytest tests/test_fast_marc_analysis.py
"""

import json
from pathlib import Path

import pytest

from k10plus.fast_marc_analysis import fast_marc_analyser

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TAGS = ["100", "110", "111", "700", "710", "711", "040"]

# case id -> input file
CASES = {
    # 040 is rda/ger and leader/17 is blank: counted in rda_ger_encoding
    "included_blank_encoding": "mvp_test_record_pass.xml",
    # 040 is rda/ger but leader/17 is '2': must NOT count in rda_ger_encoding
    "excluded_encoding_level": "mvp_test_record_fail.xml",
    # small set of records for broad regression coverage
    "mvp_set": "mvp_data.xml",
}


@pytest.fixture(scope="module", params=CASES, ids=list(CASES))
def case_stats(request, tmp_path_factory):
    """
    Run the MARC analyser once per input file for the entire module.
    Returns (case id, parsed output file path).
    """
    output_file = tmp_path_factory.mktemp("stats") / f"statistics_{request.param}.json"
    fast_marc_analyser(
        str(DATA_DIR / CASES[request.param]),
        TAGS,
        output_path=str(output_file),
    )
    return request.param, output_file


def test_marc_analyser_regression(file_regression, case_stats):
    """
    Regression on the generated statistics file for each case.
    """
    _, output_file = case_stats
    file_regression.check(output_file.read_text(encoding="utf-8"), extension=".json")


def test_rda_ger_encoding_filter(case_stats):
    """
    Records with 040 rda/ger only count towards rda_ger_encoding when the
    encoding level is blank.
    """
    case, output_file = case_stats
    if case == "mvp_set":
        pytest.skip("explicit expectations only defined for single-record cases")
    stats = json.loads(output_file.read_text(encoding="utf-8"))

    included = case == "included_blank_encoding"

    assert stats["cataloging_source"] == {"rda_ger": 1}
    assert stats["encoding_level_counts"] == {" " if included else "2": 1}
    assert stats["total_records_rda_ger_encoding"] == (1 if included else 0)
