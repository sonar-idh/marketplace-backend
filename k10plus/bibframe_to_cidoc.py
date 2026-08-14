"""
Script that converts bibframe to CIDOC CRM using SPARQL construct.

Usage:
python3 bibframe_to_cidoc_simple.py -i <input_file> -o <output_file>

Input:
- RDF file in bibframe format (ttl)

Output:
- RDF file in CIDOC CRM format (ttl)

Check the documentation at: MVP_K10PLUS.md
"""
# Modeling: TODO:
# 1. including name title entries of 700
# 2. including 773 to integrate parts with host, because titles might me missing in parts of the host.(EX:https://opac.k10plus.de/PPNSET?PPN=1003381596)

import argparse
import logging
from pathlib import Path

from rdflib import Graph

SCRIPT_DIR = Path(__file__).resolve().parent

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(
            SCRIPT_DIR / "data/bibframe_to_cidoc.log", encoding="utf-8"
        ),
        logging.StreamHandler(),
    ],
)

# For queries in the input graph
PREFIX_BLOCK = """
PREFIX crm:   <http://www.cidoc-crm.org/cidoc-crm/>
PREFIX rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX bf:    <http://id.loc.gov/ontologies/bibframe/>
"""

# Shared work validation filters (contribution completeness & date requirement)
WORK_FILTER_BLOCK = """
        # Enforce that the work has at least one contribution
        FILTER EXISTS { ?work bf:contribution [] }

        # Only select works that have all contributions with a GND ID
        FILTER NOT EXISTS {
            ?work bf:contribution/bf:agent ?anyAgentURI .
            FILTER(!STRSTARTS(STR(?anyAgentURI), "https://d-nb.info/gnd/"))
        }

        # Only select works that have all contributions with a role definition
        FILTER NOT EXISTS {
            ?work bf:contribution ?anyContrib .
            FILTER NOT EXISTS { ?anyContrib bf:role ?anyRole . }
        }

        # Enforce date requirement (original date or publication date)
        ?work bf:hasInstance ?instance .
        OPTIONAL {
            ?instance bf:note ?note .
            ?note a <http://id.loc.gov/vocabulary/mnotetype/orig> ;
                rdfs:label ?origDate .
        }
        OPTIONAL {
            ?instance bf:provisionActivity/bf:date ?pubDate .
        }
        BIND(COALESCE(?origDate, ?pubDate) AS ?correctDate)
        FILTER(BOUND(?correctDate))
"""

queries = {
    "Q1_titleInfo": PREFIX_BLOCK
    + """
        CONSTRUCT {
        ?objectURI
            a crm:E73_Information_Object ;
            crm:P1_is_identified_by [
                a crm:E42_Identifier ;
                crm:P190_has_symbolic_content ?titleId
            ];
            crm:P102_has_title [
                a crm:E35_Title ;
                crm:P190_has_symbolic_content ?titleName
            ].

        }
    WHERE {
        ?work a bf:Work ;
            bf:adminMetadata/bf:identifiedBy/rdf:value ?titleId ;
            bf:title/bf:mainTitle ?titleName .

"""
    + WORK_FILTER_BLOCK
    + """
        BIND(URI(CONCAT("https://opac.k10plus.de/PPNSET?PPN=", ?titleId)) AS ?objectURI)
    }

    """,
    "Q2_Agents": PREFIX_BLOCK
    + """
        CONSTRUCT {
            ?agentAssignmentURI a crm:PC14_Carried_Out_By ;
                crm:P01_has_domain ?creationEventURI ;
                crm:P02_has_range ?agentURI ;
                <http://www.cidoc-crm.org/cidoc-crm/P14.1_in_the_role_of> ?roleURI .

            ?agentURI a crm:E21_Person .
            ?roleURI a crm:E55_Type .
            ?creationEventURI a crm:E65_Creation ;
                crm:P94_has_created ?objectURI .
        }
        WHERE {
            ?work a bf:Work ;
                bf:adminMetadata/bf:identifiedBy/rdf:value ?titleId ;
                bf:contribution ?contributionNode .

            ?contributionNode bf:agent ?agentURI ;
                bf:role ?roleURI .

            # Only process contributions with GND IDs
            FILTER(STRSTARTS(STR(?agentURI), "https://d-nb.info/gnd/"))

"""
    + WORK_FILTER_BLOCK
    + """
            BIND(URI(CONCAT("https://opac.k10plus.de/PPNSET?PPN=", ?titleId)) AS ?objectURI)
            BIND(URI(CONCAT("https://opac.k10plus.de/PPNSET?PPN=", ?titleId, "#CreationEvent")) AS ?creationEventURI)
            BIND(URI(CONCAT("https://opac.k10plus.de/PPNSET?PPN=", ?titleId, "#RoleAssignment_", SHA1(STR(?agentURI)))) AS ?agentAssignmentURI)
        }
    """,
    "Q3_Timestamp": PREFIX_BLOCK
    + """
        CONSTRUCT {
            ?creationEventURI crm:P4_has_time-span ?timeSpanURI .

            ?timeSpanURI a crm:E52_Time_Span ;
                crm:P170i_time_is_defined_by ?correctDatePrimitive .
        }
        WHERE {
            ?work a bf:Work ;
                    bf:adminMetadata/bf:identifiedBy/rdf:value ?titleId .

"""
    + WORK_FILTER_BLOCK
    + """
            BIND(URI(CONCAT("https://opac.k10plus.de/PPNSET?PPN=", ?titleId)) AS ?objectURI)
            BIND(URI(CONCAT("https://opac.k10plus.de/PPNSET?PPN=", ?titleId, "#CreationEvent")) AS ?creationEventURI)
            BIND(URI(CONCAT("https://opac.k10plus.de/PPNSET?PPN=", ?titleId, "#TimeSpan")) AS ?timeSpanURI)
            BIND(STRDT(SUBSTR(STR(?correctDate), 1, 4), crm:E61_Time_Primitive) AS ?correctDatePrimitive)
        }
    """,
}


def bibframe_to_cidoc(input_path: Path, output_path: Path) -> None:
    logger.info(f"Loading Input BIBFRAME graph from: {input_path}")
    source = Graph()
    try:
        if str(input_path) == "-":
            import sys

            source.parse(
                source=sys.stdin.buffer,
                format="turtle",
                publicID="https://opac.k10plus.de/PPNSET/PPN/",
            )
        else:
            source.parse(str(input_path), format="turtle")
        logger.info(f"{len(source)} triples loaded.")
    except Exception as e:  # noqa: BLE001
        logger.error(f"Error loading BIBFRAME graph: {e}")
        return

    # Target graph for storing CIDOC CRM triples
    target = Graph()
    # Namespaces for the output graph
    target.bind("crm", "http://www.cidoc-crm.org/cidoc-crm/")
    target.bind("gnd", "https://d-nb.info/gnd/")
    target.bind("rel", "http://id.loc.gov/vocabulary/relators/")
    target.bind("k10plus", "https://opac.k10plus.de/PPNSET?PPN=")

    # Iterating on queries
    logger.info("======Executing SPARQL CONSTRUCT queries======")
    for query_name, query in queries.items():
        logger.info(f"Executing SPARQL CONSTRUCT query: {query_name}")
        result = source.query(query)
        for triple in result:
            target.add(triple)

    logger.info(f"Serializing to Turtle: {output_path}")
    serialized_ttl = target.serialize(format="turtle")
    cleaned_ttl = serialized_ttl.rstrip() + "\n"

    if str(output_path) == "-":
        import sys

        sys.stdout.write(cleaned_ttl)
    else:
        Path(output_path).write_text(cleaned_ttl, encoding="utf-8")

    logger.info(f"Done. {len(target)} CRM triples → {output_path}")


def main():
    argp = argparse.ArgumentParser(description="Convert BIBFRAME to CIDOC CRM")
    argp.add_argument(
        "-i",
        "--input",
        default=str(SCRIPT_DIR / "data/schumann_bib.ttl"),
        help="BIBFRAME Turtle input",
    )
    argp.add_argument(
        "-o",
        "--output",
        default=str(SCRIPT_DIR / "data/schumann_cidoc.ttl"),
        help="CIDOC CRM Turtle output",
    )
    args = argp.parse_args()
    bibframe_to_cidoc(args.input, args.output)


if __name__ == "__main__":
    main()
