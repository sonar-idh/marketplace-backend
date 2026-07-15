"""
Testing the marc dump analysis script for regression.

Run this test file with the following command in experiments/k10plus dir:
uv run pytest test_marc_dump_analysis.py
"""
from marc_dump_analysis import marc_analyser

def test_marc_analyser_regression(file_regression):
    """
    Test for regression using pytest-regressions.
    """
    marc_analyser("./data/schumann.xml", ["100", "700"], ["4"])

    with open("./data/statistics.txt", "r", encoding="utf-8") as f:
        actual_output = f.read()
    
    file_regression.check(actual_output, extension=".txt")
    