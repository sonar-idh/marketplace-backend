"""
Splits a (possibly concatenated) MARCXML dump into smaller chunk files
suitable for the marc2bibframe converter.

Usage:
    uv run python split_xml.py

Input:
    data/kxp.mrcxml  - MARCXML dump (may contain multiple concatenated
                       <?xml ...?><marc:collection>...</marc:collection> documents)

Output:
    data/chunks/kxp_chunk_NNN.xml  - Chunk files with records_per_file records each
"""

import os
from pathlib import Path

import pymarc
from marcxml_utils import FilteredXMLStream

SCRIPT_DIR = Path(__file__).resolve().parent
INPUT_PATH = SCRIPT_DIR / "data/kxp.mrcxml"
OUTPUT_DIR = SCRIPT_DIR / "data/chunks"


def split_dump(input_path, output_dir, records_per_file=10000):
    os.makedirs(output_dir, exist_ok=True)

    file_idx = 1
    record_count = 0
    writer = None

    def flush_chunk():
        nonlocal writer, file_idx, record_count
        if writer is not None:
            writer.close()
        writer = None
        file_idx += 1
        record_count = 0

    def process_record(record):
        nonlocal writer, file_idx, record_count

        if writer is None:
            out_path = os.path.join(output_dir, f"kxp_chunk_{file_idx:03d}.xml")
            writer = pymarc.XMLWriter(open(out_path, "wb"))

        writer.write(record)
        record_count += 1

        if record_count >= records_per_file:
            out_path = os.path.join(output_dir, f"kxp_chunk_{file_idx:03d}.xml")
            print(f"Wrote {out_path}")
            flush_chunk()

    with open(input_path, "rb") as f:
        stream = FilteredXMLStream(f)
        pymarc.map_xml(process_record, stream)

    # Close and report the last (possibly partial) chunk
    if writer is not None:
        out_path = os.path.join(output_dir, f"kxp_chunk_{file_idx:03d}.xml")
        writer.close()
        print(f"Wrote {out_path}")


if __name__ == "__main__":
    print(f"Splitting {INPUT_PATH}...")
    split_dump(INPUT_PATH, OUTPUT_DIR)
    print("Done splitting!")
