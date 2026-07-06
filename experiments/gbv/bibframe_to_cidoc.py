"""
bibframe_to_cidoc.py
--------------------
Converts a BIBFRAME Turtle file (output of marc2bibframe2 XSLT) to
CIDOC CRM / LRMoo Turtle using a chain of SPARQL CONSTRUCT queries.

Each query handles one slice of the mapping documented in GBV.md:
   Q1  bf:Work          → lrmoo:F1_Work + crm:E35_Title
   Q2  bf:Person/Agent  → lrmoo:F10_Person (GND URI preserved)
   Q3  bf:Contribution  → lrmoo:F28_Expression_Creation + crm:PC14_carried_out_by
                          Uses the official CIDOC CRM .1 property pattern:
                          a single F28 event per work, with reified PC14 participation
                          nodes carrying P14.1_in_the_role_of for role assignment.
  Q4  bf:Instance      → lrmoo:F2_Expression + lrmoo:F3_Manifestation
  Q5  bf:language      → crm:E56_Language on Expression
  Q6  bf:Publication   → crm:E12_Production (place, publisher, date)
  Q7  bf:genreForm     → crm:E55_Type on Work
  Q8  bf:subject (689) → skos:Concept on Work
  Q9  bf:Series/Hub    → lrmoo:F15_Nomen (series nomen)

Usage:
    python bibframe_to_cidoc.py [input.ttl] [output.ttl]

    # Default:
    python bibframe_to_cidoc.py gbv_single_record.ttl gbv_cidoc_crm.ttl

Dependencies:
    pip install rdflib
"""

import sys
import argparse
from pathlib import Path

try:
    from rdflib import Graph, Namespace, URIRef
    from rdflib.namespace import RDF, RDFS, SKOS, XSD
except ImportError:
    sys.exit("❌ Missing dependency: pip install rdflib")

# ---------------------------------------------------------------------------
# Namespaces
# ---------------------------------------------------------------------------

BF    = Namespace("http://id.loc.gov/ontologies/bibframe/")
BFLC  = Namespace("http://id.loc.gov/ontologies/bflc/")
LRMOO = Namespace("http://iflastandards.info/ns/lrm/lrmoo/")
CRM   = Namespace("http://www.cidoc-crm.org/cidoc-crm/")

# ---------------------------------------------------------------------------
# SPARQL CONSTRUCT queries
# One query per logical mapping unit — easy to extend or disable individually
# ---------------------------------------------------------------------------

PREFIX_BLOCK = """
PREFIX bf:    <http://id.loc.gov/ontologies/bibframe/>
PREFIX bflc:  <http://id.loc.gov/ontologies/bflc/>
PREFIX lrmoo: <http://iflastandards.info/ns/lrm/lrmoo/>
PREFIX crm:   <http://www.cidoc-crm.org/cidoc-crm/>
PREFIX rdfs:  <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos:  <http://www.w3.org/2004/02/skos/core#>
PREFIX xsd:   <http://www.w3.org/2001/XMLSchema#>
PREFIX rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
"""

# Full URI for P14.1_in_the_role_of — SPARQL local names cannot contain dots,
# so the prefixed form crm:P14.1_in_the_role_of is invalid in SPARQL syntax.
P14_1_URI = "<http://www.cidoc-crm.org/cidoc-crm/P14.1_in_the_role_of>"

QUERIES = {

    # ------------------------------------------------------------------
    # Q1: Work → F1_Work with title
    # MARC 245 $a/$b  →  bf:Work / bf:title / bf:mainTitle
    # ------------------------------------------------------------------
    "Q1_work_and_title": PREFIX_BLOCK + """
CONSTRUCT {
  ?work  a lrmoo:F1_Work ;
         lrmoo:R13_has_title ?titleNode .

  ?titleNode a crm:E35_Title ;
             rdfs:label ?mainTitle .
}
WHERE {
  ?work a bf:Work ;
        bf:title ?titleBf .
  ?titleBf bf:mainTitle ?mainTitle .
  BIND(URI(CONCAT(STR(?work), "_CRM_Title")) AS ?titleNode)
}
""",

    # ------------------------------------------------------------------
    # Q2: Persons (bf:Agent / bf:Person) → F10_Person
    # GND URI from $0 (DE-588) is already the subject URI in BIBFRAME TTL
    # MARC 100/700 $a $d
    # ------------------------------------------------------------------
    "Q2_persons": PREFIX_BLOCK + """
CONSTRUCT {
  ?agent a lrmoo:F10_Person ;
         rdfs:label ?label .
}
WHERE {
  ?agent a bf:Agent, bf:Person ;
         rdfs:label ?label .
}
""",

    # ------------------------------------------------------------------
    # Q3: Contribution events → F28_Expression_Creation (one per work)
    #     + PC14_carried_out_by participation nodes (one per agent)
    # MARC 700 $4/$e  →  bf:contribution / bf:agent / bf:role
    #
    # Official CIDOC CRM .1 property pattern (PC classes):
    #   The F28 event is shared for the whole work.
    #   Each agent gets a reified crm:PC14_carried_out_by node that
    #   carries P14.1_in_the_role_of for their specific role URI.
    #
    #   _:participation a crm:PC14_carried_out_by ;
    #       crm:P14_carried_out_by <agent> ;
    #       crm:P14.1_in_the_role_of <role> .
    #   <event> crm:P14_carried_out_by _:participation .
    #
    # NOTE: SPARQL local names cannot contain dots, so P14.1_in_the_role_of
    # cannot be written as crm:P14.1_in_the_role_of — use the full URI instead.
    # ------------------------------------------------------------------
    "Q3_contribution_events": PREFIX_BLOCK + f"""
CONSTRUCT {{
  # One F28 creation event per Work
  ?creationEvent a lrmoo:F28_Expression_Creation .

  # Link Expression back to its creation event
  ?exprNode crm:P94i_was_created_by ?creationEvent .

  # Reified participation node (PC14) — one per (work, agent) pair
  ?participation a crm:PC14_carried_out_by ;
                 crm:P14_carried_out_by ?agent ;
                 {P14_1_URI} ?role .

  # The event points to the participation node via P14_carried_out_by
  ?creationEvent crm:P14_carried_out_by ?participation .
}}
WHERE {{
  ?work a bf:Work ;
        bf:contribution ?contrib .
  ?contrib a bf:Contribution ;
           bf:agent ?agent .
  OPTIONAL {{ ?contrib bf:role ?role . }}
  BIND(URI(CONCAT(STR(?work), "_CRM_Expression"))                       AS ?exprNode)
  BIND(URI(CONCAT(STR(?work), "_F28_Creation"))                         AS ?creationEvent)
  BIND(URI(CONCAT(STR(?work), "_PC14_", STRAFTER(STR(?agent), "gnd/"))) AS ?participation)
}}
""",

    # ------------------------------------------------------------------
    # Q4: Instance → F2_Expression + F3_Manifestation (WEMI chain)
    # bf:Work  bf:hasInstance  bf:Instance
    # ------------------------------------------------------------------
    "Q4_wemi_chain": PREFIX_BLOCK + """
CONSTRUCT {
  ?work lrmoo:R3_is_realised_in ?exprNode .

  ?exprNode a lrmoo:F2_Expression ;
            lrmoo:R4_embodies ?instance .

  ?instance a lrmoo:F3_Manifestation .
}
WHERE {
  ?work a bf:Work ;
        bf:hasInstance ?instance .
  ?instance a bf:Instance .
  BIND(URI(CONCAT(STR(?work), "_CRM_Expression")) AS ?exprNode)
}
""",

    # ------------------------------------------------------------------
    # Q5: Language → E56_Language on Expression
    # MARC 041 $a  →  bf:language
    # ------------------------------------------------------------------
    "Q5_language": PREFIX_BLOCK + """
CONSTRUCT {
  ?exprNode crm:P72_has_language ?lang .
  ?lang a crm:E56_Language ;
        rdfs:label ?langLabel .
}
WHERE {
  ?work a bf:Work ;
        bf:language ?lang .
  OPTIONAL { ?lang rdfs:label ?langLabel . }
  BIND(URI(CONCAT(STR(?work), "_CRM_Expression")) AS ?exprNode)
}
""",

    # ------------------------------------------------------------------
    # Q6: Publication activity → E12_Production (place, publisher, date)
    # MARC 264  →  bf:provisionActivity / bf:Publication
    #              bflc:simplePlace / bflc:simpleAgent / bflc:simpleDate
    # ------------------------------------------------------------------
    "Q6_publication_event": PREFIX_BLOCK + """
CONSTRUCT {
  ?instance crm:P108i_was_produced_by ?pubEvent .

  ?pubEvent a crm:E12_Production ;
            crm:P4_has_time_span ?dateNode ;
            crm:P7_took_place_at ?placeNode ;
            crm:P14_carried_out_by ?publisherNode .

  ?dateNode  a crm:E52_Time-Span ;
             rdfs:label ?pubDate .

  ?placeNode a crm:E53_Place ;
             rdfs:label ?pubPlace .

  ?publisherNode a crm:E40_Legal_Body ;
                 rdfs:label ?pubAgent .
}
WHERE {
  ?instance a bf:Instance ;
            bf:provisionActivity ?pub .
  ?pub a bf:Publication .
  OPTIONAL { ?pub bflc:simpleDate  ?pubDate  . }
  OPTIONAL { ?pub bflc:simplePlace ?pubPlace . }
  OPTIONAL { ?pub bflc:simpleAgent ?pubAgent . }
  BIND(URI(CONCAT(STR(?instance), "_PubEvent"))     AS ?pubEvent)
  BIND(URI(CONCAT(STR(?instance), "_PubDate"))      AS ?dateNode)
  BIND(URI(CONCAT(STR(?instance), "_PubPlace"))     AS ?placeNode)
  BIND(URI(CONCAT(STR(?instance), "_Publisher"))    AS ?publisherNode)
}
""",

    # ------------------------------------------------------------------
    # Q7: Genre / Form → E55_Type on Work
    # MARC 655  →  bf:genreForm
    # ------------------------------------------------------------------
    "Q7_genre": PREFIX_BLOCK + """
CONSTRUCT {
  ?work lrmoo:R67_has_member ?genre .
  ?genre a crm:E55_Type ;
         rdfs:label ?genreLabel .
}
WHERE {
  ?work a bf:Work ;
        bf:genreForm ?genre .
  ?genre rdfs:label ?genreLabel .
}
""",

    # ------------------------------------------------------------------
    # Q8: Subject headings → SKOS:Concept
    # MARC 689 (GBV regional, NAC)  →  not in standard bf: but appears
    # via madsrdf links on genreForm or subject nodes if present.
    # Falls back to any bf:subject link.
    # ------------------------------------------------------------------
    "Q8_subjects": PREFIX_BLOCK + """
CONSTRUCT {
  ?work crm:P129_is_about ?subj .
  ?subj a skos:Concept ;
        skos:prefLabel ?subjLabel .
}
WHERE {
  ?work a bf:Work ;
        bf:subject ?subj .
  OPTIONAL { ?subj rdfs:label ?subjLabel . }
  OPTIONAL { ?subj skos:prefLabel ?subjLabel . }
}
""",

    # ------------------------------------------------------------------
    # Q9: Series → F15_Nomen
    # MARC 830 / 490  →  bf:relation / bf:Relation / bf:associatedResource
    # ------------------------------------------------------------------
    "Q9_series": PREFIX_BLOCK + """
CONSTRUCT {
  ?work lrmoo:R10_member_of_series ?seriesNomen .
  ?seriesNomen a lrmoo:F15_Nomen ;
               rdfs:label ?seriesTitle .
}
WHERE {
  ?work a bf:Work ;
        bf:relation ?rel .
  ?rel a bf:Relation ;
       bf:associatedResource ?assocRes .
  ?assocRes a bf:Series ;
            bf:title ?seriesTitleNode .
  ?seriesTitleNode bf:mainTitle ?seriesTitle .
  BIND(URI(CONCAT("http://example.org/sonar/series/",
                  ENCODE_FOR_URI(?seriesTitle))) AS ?seriesNomen)
}
""",

}

# ---------------------------------------------------------------------------
# Conversion logic
# ---------------------------------------------------------------------------

def bibframe_to_cidoc(input_path: Path, output_path: Path) -> None:
    print(f"📖 Loading BIBFRAME graph: {input_path}")
    source = Graph()
    source.parse(str(input_path), format="turtle")
    print(f"   {len(source)} triples loaded.")

    # Accumulate all CONSTRUCT results into one output graph
    result = Graph()
    result.bind("lrmoo", LRMOO)
    result.bind("crm",   CRM)
    result.bind("rdfs",  RDFS)
    result.bind("skos",  SKOS)
    result.bind("xsd",   XSD)

    print("\n🔄 Running SPARQL CONSTRUCT queries:")
    for name, query in QUERIES.items():
        before = len(result)
        sub = source.query(query)
        for triple in sub:
            result.add(triple)
        added = len(result) - before
        status = f"  {added:>4} triples" if added else "      (no match)"
        print(f"  {name:<35} {status}")

    print(f"\n💾 Serializing to Turtle: {output_path}")
    result.serialize(destination=str(output_path), format="turtle")

    print(f"\n✅ Done. {len(result)} CRM triples → {output_path}")
    print("\n── Entity summary ────────────────────")
    for cls, label in [
        (LRMOO.F1_Work,            "F1_Work"),
        (LRMOO.F2_Expression,      "F2_Expression"),
        (LRMOO.F3_Manifestation,   "F3_Manifestation"),
        (LRMOO.F10_Person,         "F10_Person"),
        (LRMOO.F28_Expression_Creation, "F28_Expression_Creation"),
        (LRMOO.F15_Nomen,         "F15_Nomen (Series)"),
        (CRM.E12_Production,       "E12_Production"),
        (CRM.E35_Title,            "E35_Title"),
        (CRM.E55_Type,             "E55_Type (Genre/Role)"),
        (SKOS.Concept,             "skos:Concept (Subject)"),
    ]:
        count = sum(1 for _ in result.subjects(RDF.type, cls))
        if count:
            print(f"  {label:<35} {count}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert BIBFRAME Turtle to CIDOC CRM / LRMoo Turtle.",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="gbv_single_record.ttl",
        help="BIBFRAME Turtle input (default: gbv_single_record.ttl)",
    )
    parser.add_argument(
        "output",
        nargs="?",
        default="gbv_cidoc_crm.ttl",
        help="CIDOC CRM / LRMoo Turtle output (default: gbv_cidoc_crm.ttl)",
    )
    args = parser.parse_args()

    input_path  = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        sys.exit(f"❌ Input file not found: {input_path}")

    bibframe_to_cidoc(input_path, output_path)


if __name__ == "__main__":
    main()
