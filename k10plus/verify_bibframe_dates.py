import json
import logging
from pathlib import Path

import rdflib

SCRIPT_DIR = Path(__file__).resolve().parent

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


def generate_bibframe_statistics(rdf_path, output_path):
    logger.info(f"Parsing BIBFRAME RDF: {rdf_path}...")
    g = rdflib.Graph()
    g.parse(rdf_path, format="turtle")
    logger.info("Parsed! Querying dates...")

    query = """
    PREFIX bf: <http://id.loc.gov/ontologies/bibframe/>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?correctDate ?id WHERE {
      ?instance a bf:Instance .

      # 1. Attempt to get original date note (e.g. tag 534)
      OPTIONAL {
        ?instance bf:note ?note .
        ?note a <http://id.loc.gov/vocabulary/mnotetype/orig> ;
              rdfs:label ?origDate .
      }

      # 2. Attempt to get publication date (e.g. tag 264/260/008)
      OPTIONAL {
        ?instance bf:provisionActivity/bf:date ?pubDate .
      }

      # 3. Prioritize original date, fallback to publication date
      BIND(COALESCE(?origDate, ?pubDate) AS ?correctDate)

      # 4. Getting the ID of the instance from the URI
	  BIND(REPLACE(STR(?instance), ".*/PPN/([^#]+)#.*", "$1") AS ?id)

      FILTER(BOUND(?correctDate))
    }
    """

    date_counts = {}
    record_dates = {}
    total_entries = 0

    for row in g.query(query):
        raw_date = str(row[0])
        record_id = str(row[1])
        # Clean/extract the 4-digit start year to align with MARC logic
        cleaned_date = raw_date[:4] if len(raw_date) >= 4 else raw_date
        date_counts[cleaned_date] = date_counts.get(cleaned_date, 0) + 1
        # tracking date for every records for tests
        record_dates[record_id] = cleaned_date
        total_entries += 1

    # Sort dates
    sorted_dates = sorted(
        date_counts.keys(), key=lambda x: date_counts[x], reverse=True
    )
    # Write to file
    with open("data/date_counts_bibframe.json", "w", encoding="utf-8") as f:
        json.dump(date_counts, f, indent=4)
    with open("data/dates_with_recordID_bibframe.json", "w", encoding="utf-8") as f:
        json.dump(record_dates, f, indent=4)

    numeric_dates = [d for d in date_counts.keys() if d.isdigit() and len(d) == 4]
    non_numeric_dates = [
        d for d in date_counts.keys() if not d.isdigit() or len(d) != 4
    ]

    min_date = min(numeric_dates) if numeric_dates else "Unknown"
    max_date = max(numeric_dates) if numeric_dates else "Unknown"

    numeric_instances = sum(date_counts[d] for d in numeric_dates)
    non_numeric_instances = sum(date_counts[d] for d in non_numeric_dates)

    numeric_pct = (numeric_instances / total_entries * 100) if total_entries > 0 else 0
    non_numeric_pct = (
        (non_numeric_instances / total_entries * 100) if total_entries > 0 else 0
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("BIBFRAME DATE STATISTICS\n")
        f.write("=" * 80 + "\n")
        f.write("\n Overview\n")
        f.write("-" * 40 + "\n")
        f.write(f"Time span: {min_date} - {max_date}\n")
        f.write(f"Total date entries: {total_entries}\n")
        f.write(f"Total numeric dates instances: {numeric_instances}\n")
        f.write(f"Total non-numeric dates instances: {non_numeric_instances}\n")
        f.write(f"Unique numeric dates: {len(numeric_dates)} ({numeric_pct:.2f}%)\n")
        f.write(
            f"Unique non-numeric dates: {len(non_numeric_dates)} ({non_numeric_pct:.2f}%)\n"
        )
        f.write("\n")
        f.write("Date Breakdown (Sorted by Frequency):\n")
        f.write("-" * 40 + "\n")
        for d in sorted_dates:
            count = date_counts[d]
            pct = (count / total_entries * 100) if total_entries > 0 else 0
            f.write(f"- {d}: {count} ({pct:.2f}%)\n")

    logger.info(f"Generated BIBFRAME statistics at: {output_path}")
    return date_counts


def compare_statistics(marc_json_path, bf_json_path):
    logger.info("Comparing MARC and BIBFRAME date statistics from JSON...")
    with open(marc_json_path, "r", encoding="utf-8") as f:
        marc_dates = json.load(f)
    with open(bf_json_path, "r", encoding="utf-8") as f:
        bf_dates = json.load(f)

    all_keys = set(marc_dates.keys()) | set(bf_dates.keys())
    mismatches = []

    for k in sorted(all_keys):
        m_val = marc_dates.get(k, 0)
        b_val = bf_dates.get(k, 0)
        if m_val != b_val:
            mismatches.append((k, m_val, b_val))

    logger.info(f"\nTotal compared dates: {len(all_keys)}")
    logger.info(f"Total mismatches: {len(mismatches)}")
    if mismatches:
        logger.info("Mismatch Details:(Date: MARC_Count vs BIBFRAME_Count)")
        for k, m, b in mismatches:
            logger.error(f"  - {k}: MARC={m}, BIBFRAME={b} (diff={abs(m-b)})")
    else:
        logger.info("\nSUCCESS: All date counts match perfectly!")

    return len(mismatches) == 0


def deep_compare_statistics(marc_json_path, bf_json_path):
    logger.info("Comparing MARC and BIBFRAME date statistics from JSON...")
    with open(marc_json_path, "r", encoding="utf-8") as f:
        marc_records_with_dates = json.load(f)
    with open(bf_json_path, "r", encoding="utf-8") as f:
        bf_records_with_dates = json.load(f)

    assert set(marc_records_with_dates.keys()) == set(
        bf_records_with_dates.keys()
    ), "Records IDs don't match in both files"

    mismatches = []

    for k in marc_records_with_dates.keys():
        m_val = marc_records_with_dates.get(k)
        b_val = bf_records_with_dates.get(k)
        if m_val != b_val:
            mismatches.append((k, m_val, b_val))

    logger.info(f"Total compared dates: {len(marc_records_with_dates.keys())}")
    logger.info(f"Total mismatches: {len(mismatches)}")
    if mismatches:
        logger.info("Mismatch Details:")
        for k, m, b in mismatches:
            logger.error(f"record id {k}: MARC={m}, BIBFRAME={b}")
    else:
        logger.info("SUCCESS: All records have same date in MARC and BIBFRAME!")

    return len(mismatches) == 0


if __name__ == "__main__":
    rdf_file = SCRIPT_DIR / "data/schumann_bib.ttl"
    bf_output = SCRIPT_DIR / "data/statistics_bibframe.txt"
    marc_json = SCRIPT_DIR / "data/date_counts_marc.json"
    bf_json = SCRIPT_DIR / "data/date_counts_bibframe.json"
    deep_marc_json = SCRIPT_DIR / "data/dates_with_recordID_marc.json"
    deep_bf_json = SCRIPT_DIR / "data/dates_with_recordID_bibframe.json"

    generate_bibframe_statistics(rdf_file, bf_output)
    compare_statistics(marc_json, bf_json)
    deep_compare_statistics(deep_marc_json, deep_bf_json)
