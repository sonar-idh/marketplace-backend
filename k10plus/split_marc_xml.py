#!/usr/bin/env python3
"""
Split the KXP MARC XML file into smaller chunks of ~50 MB

Usage:
    python split_marc_xml.py -i /path/to/marc.xml -o /path/to/output/dir -p chunk_prefix
"""

import argparse
import os
import re
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from tqdm import tqdm

XML_HEADER = b'<?xml version="1.0" encoding="UTF-8"?>\n<marc:collection xmlns:marc="http://www.loc.gov/MARC21/slim">\n'
XML_FOOTER = b"\n</marc:collection>\n"

CHUNK_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB per chunk


SEAM_PATTERN = re.compile(
    rb"</(?:marc:)?collection>\s*|\s*<\?xml[^>]*\?>\s*|\s*<(?:marc:)?collection[^>]*>\s*"
)


def find_record_chunks(input_file: Path) -> list[tuple[int, int]]:
    """Split input_file into ~50 MB byte-range slices, always breaking on record boundaries."""
    file_size = os.path.getsize(input_file)
    chunks = []

    with open(input_file, "rb") as f:
        buf = f.read(65536)
        idx1 = buf.find(b"<marc:record")
        idx2 = buf.find(b"<record")
        indices = [i for i in (idx1, idx2) if i != -1]
        start = min(indices) if indices else 0

        while start < file_size:
            target_end = start + CHUNK_SIZE_BYTES
            if target_end >= file_size:
                chunks.append((start, file_size))
                break

            f.seek(target_end)
            lookahead = f.read(1024 * 1024)
            if not lookahead:
                chunks.append((start, file_size))
                break

            idx1 = lookahead.find(b"<marc:record")
            idx2 = lookahead.find(b"<record")
            indices = [i for i in (idx1, idx2) if i != -1]
            if indices:
                end = target_end + min(indices)
            else:
                end = file_size

            chunks.append((start, end))
            start = end

    return chunks


def write_binary_chunk(args: tuple) -> Path:
    input_file, output_path, start, end = args

    with open(input_file, "rb") as infile:
        infile.seek(start)
        raw_data = infile.read(end - start)
        cleaned_data = SEAM_PATTERN.sub(b"", raw_data)

    with open(output_path, "wb") as outfile:
        outfile.write(XML_HEADER)
        outfile.write(cleaned_data)
        outfile.write(XML_FOOTER)

    return output_path


def split_marc_xml_fast(
    input_file: Path,
    output_dir: Path,
    prefix: str = "kxp_chunk",
    num_workers: int | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    file_size = os.path.getsize(input_file)

    print(
        f"Splitting '{input_file}' ({file_size / (1024 ** 3):.2f} GB) into ~50 MB chunks…"
    )
    start_time = time.time()

    chunk_bounds = find_record_chunks(input_file)
    actual_chunks = len(chunk_bounds)

    if num_workers is None:
        num_workers = min(os.cpu_count() or 4, actual_chunks)

    print(f"Computed {actual_chunks} chunks — using {num_workers} CPU cores")

    tasks = [
        (input_file, output_dir / f"{prefix}_{idx:03d}.xml", start, end)
        for idx, (start, end) in enumerate(chunk_bounds, start=1)
    ]

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(write_binary_chunk, t) for t in tasks]
        with tqdm(total=len(tasks), desc="Writing Chunks", unit="chunk") as pbar:
            for future in as_completed(futures):
                future.result()
                pbar.update(1)

    elapsed = time.time() - start_time
    print(
        f"\nDone! {actual_chunks} chunks written to '{output_dir}/' in {elapsed:.2f}s"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fast parallel binary splitter for large MARC XML files (fixed 50 MB chunks)."
    )
    parser.add_argument(
        "-i",
        "--input",
        type=Path,
        default=Path("data/kxp001.xml"),
        help="Path to input MARC XML file",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("data/chunks/SA-MARC-verbund-001/"),
        help="Directory to write chunk files into",
    )
    parser.add_argument(
        "-p",
        "--prefix",
        type=str,
        default="kxp_chunk",
        help="Filename prefix for chunk files (default: kxp_chunk)",
    )
    parser.add_argument(
        "-w",
        "--workers",
        type=int,
        default=None,
        help="Number of parallel worker processes (default: number of CPU cores)",
    )

    args = parser.parse_args()
    split_marc_xml_fast(args.input, args.output_dir, args.prefix, args.workers)


if __name__ == "__main__":
    main()
