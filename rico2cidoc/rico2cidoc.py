"""
Script that converts RiC-O to CIDOC-CRM/CER using SPARQL construct.

Usage:
python3 rico2cidoc.py -i <input_file> -o <output_file>

Input:
- RDF file in RiC-O format (ttl)

Output:
- RDF file in CIDOC-CRM/CER format (ttl)

Check the documentation at: MVP_KALLIOPE.md
"""

import argparse
import logging
from pathlib import Path

from rdflib import Graph

SCRIPT_DIR = Path(__file__).resolve().parent
LOG_DIR = SCRIPT_DIR / "data"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "rico_to_cidoc.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

# For queries in the input graph
PREFIX_BLOCK = """
PREFIX crm:   <http://www.cidoc-crm.org/cidoc-crm/>
PREFIX rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rico:  <https://www.ica.org/standards/RiC/ontology#>
PREFIX cer:   <https://lod.academy/cer/vocab/ontology#>
PREFIX kpe:   <https://kalliope-verbund.info/ead?ead.id=>
PREFIX rel:   <http://id.loc.gov/vocabulary/relators/>
"""

queries = {
    "Q1_titleInfo": PREFIX_BLOCK
    + """
        CONSTRUCT {
        ?letterURI
            a crm:E73_Information_Object ;
            a cer:1_Letter;
            crm:P1_is_identified_by [
                a crm:E42_Identifier ;
                crm:P190_has_symbolic_content ?letterId
            ];
            crm:P102_has_title [
                a crm:E35_Title ;
                crm:P190_has_symbolic_content ?titleName
            ].
        }
    WHERE {
        ?letterURI a rico:Record ;
            rico:title ?titleName .

        BIND(STRAFTER(STR(?letterURI), STR(kpe:)) AS ?letterId)
    }

    """,
    "Q2_Creation": PREFIX_BLOCK
    + """
            CONSTRUCT {
                ?agentAssignmentURI a crm:PC14_Carried_Out_By ;
                    crm:P01_has_domain ?creationEventURI ;
                    crm:P02_has_range ?agentURI ;
                    crm:P14.1_in_the_role_of rel:aut .
                ?agentURI a crm:E21_Person .
                ?roleURI a crm:E55_Type .
                ?creationEventURI a crm:E65_Creation ;
                    crm:P94_has_created ?letterURI .
            }
            WHERE {
                ?letterURI a rico:Record .
                ?letterURI rico:hasAuthor ?agentURI .
                BIND(rel:aut AS ?roleURI)
                BIND(STRAFTER(STR(?letterURI), STR(kpe:)) AS ?letterId)
                BIND(URI(CONCAT(STR(kpe:), ?letterId, "#CreationEvent")) AS ?creationEventURI)
                BIND(URI(CONCAT(STR(kpe:), ?letterId, "#RoleAssignment_", SHA1(CONCAT(STR(?agentURI), STR(?roleURI))))) AS ?agentAssignmentURI)
            }
        """,
    "Q3_Sending": PREFIX_BLOCK
    + """
            CONSTRUCT {
                ?SendingURI a cer:13_Sending ;
                    cer:P9_was_intended_use_of ?letterURI ;
                    cer:P8_carried_out_by ?agentURI .
            }
            WHERE {
                ?letterURI a rico:Record .
                ?letterURI rico:hasAuthor ?agentURI .
                BIND(STRAFTER(STR(?letterURI), STR(kpe:)) AS ?letterId)
                BIND(URI(CONCAT(STR(kpe:Sending_), ?letterId)) AS ?SendingURI)  
            }
        """,
    "Q4_Receiving": PREFIX_BLOCK
    + """
            CONSTRUCT {
                ?ReceivingURI a cer:14_Receiving ;
                    cer:P9_was_intended_use_of ?letterURI ;
                    cer:P8_carried_out_by ?agentURI .
            }
            WHERE {
                ?letterURI a rico:Record .
                ?letterURI rico:hasAddressee ?agentURI .
                BIND(STRAFTER(STR(?letterURI), STR(kpe:)) AS ?letterId)
                BIND(URI(CONCAT(STR(kpe:Receiving_), ?letterId)) AS ?ReceivingURI)
            }
        """,
    "Q5_Timestamp": PREFIX_BLOCK
    + """
            CONSTRUCT {
                ?creationEventURI crm:P4_has_time-span ?timeSpanURI .
                ?timeSpanURI a crm:E52_Time_Span ;
                    crm:P170i_time_is_defined_by ?correctDatePrimitive .
            }
            WHERE {
                ?letterURI a rico:Record .
                ?letterURI rico:endDate ?date .
                BIND(STRAFTER(STR(?letterURI), STR(kpe:)) AS ?letterId)
                BIND(URI(CONCAT(STR(kpe:), ?letterId, "#CreationEvent")) AS ?creationEventURI)
                BIND(URI(CONCAT(STR(kpe:), ?letterId, "#TimeSpan")) AS ?timeSpanURI)
                BIND(STRDT(SUBSTR(STR(?date), 1, 4), crm:E61_Time_Primitive) AS ?correctDatePrimitive)
            }
    """,
}


def rico_to_cidoc(input_path: Path, output_path: Path) -> None:
    logger.info(f"Loading Input RiC-O graph from: {input_path}")
    source = Graph()
    try:
        if str(input_path) == "-":
            import sys

            source.parse(
                source=sys.stdin.buffer,
                format="turtle",
                publicID="https://kalliope-verbund.info/ead?ead.id=",  # not sure about this
            )
        else:
            source.parse(str(input_path), format="turtle")
        logger.info(f"{len(source)} triples loaded.")
    except Exception as e:  # noqa: BLE001
        logger.error(f"Error loading RiC-O graph: {e}")
        return

    # Target graph for storing CIDOC CRM triples
    target = Graph()
    # Namespaces for the output graph
    target.bind("crm", "http://www.cidoc-crm.org/cidoc-crm/")
    target.bind("gnd", "https://d-nb.info/gnd/")
    target.bind("rel", "http://id.loc.gov/vocabulary/relators/")
    target.bind("kpe", "https://kalliope-verbund.info/ead?ead.id=")
    target.bind("cer", "https://lod.academy/cer/vocab/ontology#")

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
    argp = argparse.ArgumentParser(description="Convert RiC-O to CIDOC CRM")
    argp.add_argument(
        "-i",
        "--input",
        default=str(SCRIPT_DIR / "data/rico_testdata.ttl"),
        help="RiC-O Turtle input",
    )
    argp.add_argument(
        "-o",
        "--output",
        default=str(LOG_DIR / "cidoc_result.ttl"),
        help="CIDOC CRM Turtle output",
    )
    args = argp.parse_args()
    rico_to_cidoc(args.input, args.output)


if __name__ == "__main__":
    main()
