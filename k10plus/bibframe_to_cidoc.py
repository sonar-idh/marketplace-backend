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
# TODO: including name title entries of 700

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

# Queries to create HNA Graph from BIBFRAME
"""
Modelling Decisions:
- The data from a work object in bibframe is an Information object, as we are interested in specific data about the work
- like ID, name, persons involved.
- strict class defintiions or inference based definitions
- selecting the works with all agents with GND IDs and role definition
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

            BIND(URI(CONCAT("https://opac.k10plus.de/PPNSET?PPN=", ?titleId)) AS ?objectURI)
            BIND(URI(CONCAT("https://opac.k10plus.de/PPNSET?PPN=", ?titleId, "#CreationEvent")) AS ?creationEventURI)
            BIND(URI(CONCAT("https://opac.k10plus.de/PPNSET?PPN=", ?titleId, "#RoleAssignment_", SHA1(STR(?agentURI)))) AS ?agentAssignmentURI)
        }
    """,
}


def bibframe_to_cidoc(input_path: Path, output_path: Path) -> None:
    logger.info(f"Loading Input BIBFRAME graph from: {input_path}")
    source = Graph()
    try:
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
    target.serialize(destination=str(output_path), format="turtle")

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
