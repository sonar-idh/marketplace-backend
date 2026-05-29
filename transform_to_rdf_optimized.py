from pathlib import Path
from lxml import etree
from saxonche import PySaxonProcessor
import subprocess
import time
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed

RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
MODS = "http://www.loc.gov/mods/v3"
XSLT = str(Path("../MODS3-7_Bibframe2-0_XSLT2-0_20230505.xsl").resolve())
IN_DIR = Path("initial_dump_raw")
TTL_DIR = Path("bibframe_ttl")
OUT_TTL = Path("db/initial_dump.ttl")
WORKERS = 8


def process_page(xml_file_str):
    """Runs in worker process: transform entire modsCollection of raw dump file to Turtle."""
    xml_file = Path(xml_file_str)
    ttl_file = Path(str(TTL_DIR)) / xml_file.with_suffix(".ttl").name

    if ttl_file.exists():
        return xml_file.name, 0  # bereits verarbeitet

    tree = etree.parse(xml_file)
    mods_elements = tree.findall(f".//{{{MODS}}}mods")
    if not mods_elements:
        return xml_file.name, 0

    # Alle mods-Elemente in eine modsCollection — eine XSLT-Transformation pro Page
    collection = etree.Element(f"{{{MODS}}}modsCollection")
    for mods in mods_elements:
        collection.append(mods)
    collection_str = etree.tostring(collection, encoding="unicode")

    with PySaxonProcessor(license=False) as proc:
        xslt_proc = proc.new_xslt30_processor()
        executable = xslt_proc.compile_stylesheet(stylesheet_file=XSLT)
        xdm = proc.parse_xml(xml_text=collection_str)
        rdfxml = executable.apply_templates_returning_string(xdm_value=xdm)

    if not rdfxml:
        return xml_file.name, 0

    result = subprocess.run(
        ["rapper", "-q", "-i", "rdfxml", "-o", "turtle", "-", "http://example.org/"],
        input=rdfxml,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"rapper error ({xml_file.name}): {result.stderr[:200]}")

    ttl_file.write_text(result.stdout)
    return xml_file.name, len(mods_elements)


if __name__ == "__main__":
    TTL_DIR.mkdir(exist_ok=True)
    xml_files = [str(f) for f in sorted(IN_DIR.glob("*.xml"))]
    start = time.time()
    count = 0
    skipped = 0

    ctx = mp.get_context("spawn")
    with ProcessPoolExecutor(max_workers=WORKERS, mp_context=ctx) as pool:
        futures = {pool.submit(process_page, f): f for f in xml_files}
        for future in as_completed(futures):
            name, n = future.result()
            if n == 0:
                skipped += 1
            else:
                count += n
                if count % 500 == 0:
                    print(f"Transformed: {count} records")

    elapsed = time.time() - start
    print(
        f"Transformed: {count} new records ({skipped} pages skipped) in {elapsed:.1f}s"
    )

    print("Merging TTL files...")
    with OUT_TTL.open("w") as out:
        for ttl_file in sorted(TTL_DIR.glob("*.ttl")):
            out.write(ttl_file.read_text())
    print(f"Done. Saved in {OUT_TTL}")
