"""
Regression Test for the k10 plus data pipeline.

Run this test file with:
    uv run pytest tests/test_bibframe_to_cidoc.py

For the full (slow) dataset tests:
    uv run pytest tests/test_bibframe_to_cidoc.py -m slow
"""

from pathlib import Path

import pytest
from pyshacl import validate

from k10plus.bibframe_to_cidoc import bibframe_to_cidoc

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def test_schema_validation():
    """test for schema validation against schumann_example_cidoc.ttl (fast)."""
    input_path = DATA_DIR / "schumann_example_cidoc.ttl"
    shape_graph = DATA_DIR / "shacl.ttl"
    result = validate(data_graph=str(input_path), shape_graph=str(shape_graph))
    conforms, _, messages = result
    assert conforms, f"SHACL validation failed:\n{messages}"


def test_bibframe_to_cidoc(file_regression):
    """Fast regression test using the small example dataset (~18KB vs 14MB)."""
    input_path = DATA_DIR / "schumann_example_bib.ttl"
    output_path = DATA_DIR / "schumann_example_cidoc.ttl"
    bibframe_to_cidoc(input_path=input_path, output_path=output_path)
    with open(output_path, "r", encoding="utf-8") as f:
        actual_output = f.read()

    file_regression.check(actual_output, extension=".ttl")


@pytest.mark.slow
def test_bibframe_to_cidoc_full(file_regression):
    """Slow regression test using the full Schumann dataset (14MB, ~25s).

    Run explicitly with:
        uv run pytest -m slow
    """
    input_path = DATA_DIR / "schumann_bib.ttl"
    output_path = DATA_DIR / "schumann_cidoc.ttl"
    bibframe_to_cidoc(input_path=input_path, output_path=output_path)
    with open(output_path, "r", encoding="utf-8") as f:
        actual_output = f.read()

    file_regression.check(actual_output, extension=".ttl")


@pytest.mark.slow
def test_schema_validation_full():
    """SHACL validation against the full schumann_cidoc.ttl output."""
    input_path = DATA_DIR / "schumann_cidoc.ttl"
    shape_graph = DATA_DIR / "shacl.ttl"
    result = validate(data_graph=str(input_path), shape_graph=str(shape_graph))
    conforms, _, messages = result
    assert conforms, f"SHACL validation failed:\n{messages}"


def test_input_data(file_regression):
    input_paths = [
        DATA_DIR / "schumann.xml",
        DATA_DIR / "schumann_bib.xml",
        DATA_DIR / "schumann_bib.ttl",
    ]
    for input_path in input_paths:
        input_path = Path(input_path)
        with open(input_path, "r", encoding="utf-8") as f:
            actual_output = f.read()

        file_regression.check(
            actual_output,
            basename=f"test_input_{input_path.stem}",
            extension=input_path.suffix,
        )


def test_exclude_works_without_contributions(tmp_path):
    """Test that works with zero contributions are excluded from the output graph."""
    input_ttl = """
    @prefix bf: <http://id.loc.gov/ontologies/bibframe/> .
    @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
    @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

    # Work 1: Has a contribution (should be mapped)
    <http://example.org/work1> a bf:Work ;
        bf:adminMetadata [
            bf:identifiedBy [
                a bf:Identifier ;
                rdf:value "111"
            ]
        ] ;
        bf:title [
            a bf:Title ;
            bf:mainTitle "Title 1"
        ] ;
        bf:contribution [
            a bf:Contribution ;
            bf:agent <https://d-nb.info/gnd/12345> ;
            bf:role <http://id.loc.gov/vocabulary/relators/aut>
        ] .

    # Work 2: Has NO contributions (should be ignored)
    <http://example.org/work2> a bf:Work ;
        bf:adminMetadata [
            bf:identifiedBy [
                a bf:Identifier ;
                rdf:value "222"
            ]
        ] ;
        bf:title [
            a bf:Title ;
            bf:mainTitle "Title 2"
        ] .
    """
    input_file = tmp_path / "input.ttl"
    output_file = tmp_path / "output.ttl"
    input_file.write_text(input_ttl, encoding="utf-8")

    bibframe_to_cidoc(input_file, output_file)

    from rdflib import Graph, URIRef

    g = Graph()
    g.parse(output_file, format="turtle")

    # We expect work1 to be mapped to a E73_Information_Object
    assert (URIRef("https://opac.k10plus.de/PPNSET?PPN=111"), None, None) in g
    # We expect work2 to be completely ignored
    assert (URIRef("https://opac.k10plus.de/PPNSET?PPN=222"), None, None) not in g


# TODO: Suggested future test additions to validate graphs:
# 1. Negative Validation: Test that SHACL flags violations on intentionally broken/invalid CIDOC-CRM graphs.
# 2. Conversion Coverage: Assert that the number of converted works matches the expected output ratios.
#        - sum of creation events == sum of information objects
# 3. Parametrized Edge Cases: Dynamically test tiny mock graphs (e.g. single work + missing GND, single work + missing role) to assert specific output logic behaviors.
# 4. Layered Testing & Validation:
#    - Syntax Validation: Enforce syntax checking on intermediate and final Turtle files.
#    - SHACL Validation: Enhance shapes coverage for more strict property shapes.
#    - Unit/Regression Testing: Ensure precise field-by-field verification on dummy inputs.
#    - Ontology Reasoner: Add ontology consistency checking (e.g., using owlready2) to detect domain/range and class contradictions.
