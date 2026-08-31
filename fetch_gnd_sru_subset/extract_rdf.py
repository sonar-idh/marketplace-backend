#!/usr/bin/env python3
"""Extract the embedded rdf:RDF subtree from SRU searchRetrieveResponse XML files.

rapper (and other RDF/XML parsers) require rdf:RDF to be the document's root
element. The GND SRU responses instead wrap it inside
<searchRetrieveResponse><records><record><recordData><rdf:RDF>...</rdf:RDF>,
so it must be pulled out into its own document before parsing.
"""
import sys
from pathlib import Path

from lxml import etree

RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"


def extract(src: Path, dest: Path) -> bool:
    tree = etree.parse(str(src))
    rdf_elems = tree.findall(f".//{{{RDF_NS}}}RDF")
    if not rdf_elems:
        return False

    # Merge all per-record rdf:RDF blocks into a single document, since each
    # SRU response bundles up to ~50 records but only the first was kept
    # previously. Namespaces are unioned since individual records may not
    # all declare the same subset.
    nsmap = {}
    for rdf_elem in rdf_elems:
        nsmap.update(rdf_elem.nsmap)
    merged = etree.Element(f"{{{RDF_NS}}}RDF", nsmap=nsmap)
    for rdf_elem in rdf_elems:
        merged.extend(rdf_elem)

    dest.write_bytes(etree.tostring(merged, xml_declaration=True, encoding="UTF-8"))
    return True


def main():
    src_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("sru_results")
    dest_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("sru_results_rdf")
    dest_dir.mkdir(exist_ok=True)

    ok, skipped = 0, 0
    for src in sorted(src_dir.glob("*.xml")):
        dest = dest_dir / src.name
        if extract(src, dest):
            ok += 1
        else:
            skipped += 1
            print(f"no rdf:RDF found in {src}", file=sys.stderr)
    print(f"extracted {ok} file(s) to {dest_dir}, skipped {skipped}")


if __name__ == "__main__":
    main()
