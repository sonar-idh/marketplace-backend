import json
from collections import Counter
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from pydoc import plain

import rdflib


SCRIPT_DIR = Path(__file__).resolve().parent
(SCRIPT_DIR / "data").mkdir(exist_ok=True)

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(
            SCRIPT_DIR / "data/verify_bibframe_dates.log", encoding="utf-8"
        ),
        logging.StreamHandler(),
    ],
)

@dataclass
class BibframeStatistics:
    total_records: int
    total_records_rda_ger_encoding: int
    cataloging_source: int
    encoding_level_counts: int
    place_of_publication_count: dict
    language_counts: dict
    function_of_entity_counts: dict
    specific_date_counts: dict
    role_counts: dict

PREFIX_BLOCK = """    
PREFIX bf: <http://id.loc.gov/ontologies/bibframe/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bflc: <http://id.loc.gov/ontologies/bflc/>
"""

QUERIES = {
    "total_records" : """
SELECT DISTINCT ?sub WHERE {
  ?sub a bf:Work .
  FILTER(REGEX(STR(?sub), "/PPN/[^#]+#Work$"))
}
""", 
"total_records_rda_ger_encoding" : """
SELECT DISTINCT ?sub WHERE {
  ?sub a bf:Work ;
       bf:adminMetadata ?am .
  ?am bf:descriptionConventions <http://id.loc.gov/vocabulary/descriptionConventions/rda> ;
      bf:descriptionLanguage <http://id.loc.gov/vocabulary/languages/ger> ;
      bflc:encodingLevel <http://id.loc.gov/vocabulary/menclvl/f> .
  FILTER(REGEX(STR(?sub), "/PPN/[^#]+#Work$"))
}
""",
"cataloging_source" : """
SELECT DISTINCT ?sub WHERE {
  ?sub a bf:Work ;
       bf:adminMetadata ?am .
  ?am bf:descriptionConventions <http://id.loc.gov/vocabulary/descriptionConventions/rda> ;
      bf:descriptionLanguage <http://id.loc.gov/vocabulary/languages/ger> ;
  FILTER(REGEX(STR(?sub), "/PPN/[^#]+#Work$"))
}
""", 
"encoding_level_counts" : """
SELECT DISTINCT ?sub WHERE {
  ?sub a bf:Work ;
       bf:adminMetadata ?am .
  ?am bflc:encodingLevel <http://id.loc.gov/vocabulary/menclvl/f> .
  FILTER(REGEX(STR(?sub), "/PPN/[^#]+#Work$"))
}
""", 
"place_of_publication_count" : """
SELECT DISTINCT ?sub ?place WHERE {
  ?sub a bf:Instance ;
       bf:provisionActivity ?pa .
  ?pa bf:place ?place .
  FILTER(REGEX(STR(?sub), "/PPN/[^#]+#Instance$"))
}
""", 
"language_counts" : """
SELECT DISTINCT ?sub ?lang WHERE {
  ?sub a bf:Work ;
       bf:language ?lang .
  FILTER(REGEX(STR(?sub), "/PPN/[^#]+#Work$"))
}
""",
"function_of_entity_counts" : """
SELECT DISTINCT ?sub ?func_entity WHERE {
  ?sub a bf:Instance .
  FILTER(REGEX(STR(?sub), "/PPN/[^#]+#Instance$"))
  {
    # 264 ind2 0/1/2/3 -> Production/Publication/Distribution/Manufacture
    ?sub bf:provisionActivity ?pa .
    ?pa a ?func_entity ;
        bflc:simpleDate|bflc:simplePlace|bflc:simpleAgent ?simple .
    FILTER(?func_entity != bf:ProvisionActivity)
  } UNION {
    # 264 ind2 4 -> copyright date
    ?sub bf:copyrightDate ?cd .
    BIND(bf:copyrightDate AS ?func_entity)
  }
}
""",
"specific_date_counts" : """
SELECT DISTINCT ?sub ?date WHERE {
  ?sub a bf:Instance ;
       bf:provisionActivity ?pa .
  ?pa bflc:simpleDate ?date .
  FILTER(REGEX(STR(?sub), "/PPN/[^#]+#Instance$"))
}
""", 
"role_counts" : """
SELECT ?sub ?role ?bn WHERE {
  ?sub a bf:Work ;
       bf:contribution ?bn .
  ?bn bf:role ?role .
  FILTER(REGEX(STR(?sub), "/PPN/[^#]+#Work$"))
}
""", 
}

def generate_bibframe_statistics(rdf_path, output_path):
    logger.info(f"Parsing BIBFRAME RDF: {rdf_path}...")
    g = rdflib.Graph()
    g.parse(rdf_path, format="turtle")

    # running queries
    total_records = 0
    total_records_rda_ger_encoding = 0
    cataloging_source = 0
    encoding_level_counts = 0
    place_of_publication_count = {}
    language_counts = {}
    function_of_entity_counts = {}
    specific_date_counts = {}
    role_counts = {}
    for query_name, query in QUERIES.items():
        logger.info(f"Running query: {query_name}")
        results = g.query(PREFIX_BLOCK + query)
        logger.info(f"Query {query_name} returned {len(results)} results")

        if query_name == "total_records":
            total_records = len(results)
            logger.info(f"Total records: {total_records}")
        if query_name == "total_records_rda_ger_encoding":
            total_records_rda_ger_encoding = len(results)
            logger.info(f"Total records with RDA German encoding: {total_records_rda_ger_encoding}")
        if query_name == "cataloging_source":
            cataloging_source = len(results)
            logger.info(f"Total records with cataloging source: {cataloging_source}")
        if query_name == "encoding_level_counts":
            encoding_level_counts = len(results)
            logger.info(f"Total records with encoding level counts: {encoding_level_counts}")
        if query_name == "place_of_publication_count":
            counter = Counter(str(row[1]).rsplit("/", 1)[-1] for row in results)
            place_of_publication_count = dict(sorted(counter.items()))
        if query_name == "language_counts":
            counter = Counter(str(row[1]).rsplit("/", 1)[-1] for row in results)
            language_counts = dict(sorted(counter.items()))
        if query_name == "function_of_entity_counts":
            counter = Counter(str(row[1]).rsplit("/", 1)[-1] for row in results)
            function_of_entity_counts = dict(sorted(counter.items()))
        if query_name == "specific_date_counts":
            counter = Counter(str(row[1]).rsplit("/", 1)[-1] for row in results)
            specific_date_counts = dict(sorted(counter.items()))
        if query_name == "role_counts":
            counter = Counter(str(row[1]).rsplit("/", 1)[-1] for row in results)
            role_counts = dict(sorted(counter.items()))

            

    # Save results to output file (once, after all queries)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(asdict(BibframeStatistics(total_records=total_records, 
                                            total_records_rda_ger_encoding=total_records_rda_ger_encoding, 
                                            cataloging_source=cataloging_source, 
                                            encoding_level_counts=encoding_level_counts, 
                                            place_of_publication_count=place_of_publication_count, 
                                            language_counts=language_counts,
                                            function_of_entity_counts=function_of_entity_counts,
                                            role_counts=role_counts,
                                            specific_date_counts=specific_date_counts)), f, indent=4)

if __name__ == "__main__":
    rdf_file = SCRIPT_DIR / "data/schumann_bib.ttl"
    bf_output = SCRIPT_DIR / "data/statistics_bibframe.json"

    generate_bibframe_statistics(rdf_file, bf_output)
