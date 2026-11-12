from pathlib import Path

import pytest

from k10plus.bibframe_statistics import generate_bibframe_statistics

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@pytest.fixture(scope="module", params=["schumann_bib.ttl"], ids=["BIBFRAME"])
def case_bibframe_stats(request,tmp_path_factory):
    """
    Run parsing and file generation exactly once for the entire module.
    """

    bibframe_output_stats = tmp_path_factory.mktemp("stats") / f"statistics_{request.param}.json"
    
    generate_bibframe_statistics(DATA_DIR / request.param, bibframe_output_stats)
    return bibframe_output_stats


def test_bibframe_statistics_regression(file_regression, case_bibframe_stats):
    """
    Test for regression on the generated statistics_bibframe.txt file.
    """
    bibframe_output_stats = case_bibframe_stats
    file_regression.check(bibframe_output_stats.read_text(encoding="utf-8"), extension=".json")
