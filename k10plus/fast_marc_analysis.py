"""
Fast analysis of MARCXML data chunks. Parallel processing for faster analysis.
It counts the occurrences of specific MARC tags and subfields,
calculates GND linking coverage, and validates records for completeness.

Usage:
    uv run python k10plus/fast_marc_analysis.py

Input:
    - Input can be a single .gz file or a directory of .gz files or a directory of .xml files.
    - Pass the directory path or .gz file path as an argument to this script.

Output:
    - k10plus/data/statistics.md - Detailed analysis report (tags, record types, levels, relators, and GND linking coverage).
"""

import gzip
import json
import os
import re
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from lxml import etree
from tqdm import tqdm

from record_sink import RecordSink

SCRIPT_DIR = Path(__file__).resolve().parent

TYPE_OF_RECORD_MAP = {
    "a": "Language material",
    "c": "Notated music",
    "d": "Manuscript notated music",
    "e": "Cartographic material",
    "f": "Manuscript cartographic material",
    "g": "Projected medium",
    "i": "Nonmusical sound recording",
    "j": "Musical sound recording",
    "k": "Two-dimensional nonprojectable graphic",
    "m": "Computer file",
    "o": "Kit",
    "p": "Mixed materials",
    "r": "Three-dimensional artifact or naturally occurring object",
    "t": "Manuscript language material",
}

BIBLIOGRAPHIC_LEVEL_MAP = {
    "a": "Monographic component part",
    "b": "Serial component part",
    "c": "Collection",
    "d": "Subunit",
    "i": "Integrating resource",
    "m": "Monograph/Item",
    "s": "Serial",
}

with open(SCRIPT_DIR / "data/relators.json", "r", encoding="utf-8") as f:
    MARC_RELATORS_CODE = json.load(f)


class ChunkStream:
    """Streams bytes from start to end of file wrapped in a pseudo root element."""

    def __init__(self, file_path: str, start: int, end: int):
        self.f = open(file_path, "rb")
        self.f.seek(start)
        self.end = end
        self.bytes_read = start
        self.prefix_sent = False
        self.suffix_sent = False

    def read(self, size=65536):
        if not self.prefix_sent:
            self.prefix_sent = True
            return b'<root xmlns:marc="http://www.loc.gov/MARC21/slim">'

        if self.bytes_read >= self.end:
            if not self.suffix_sent:
                self.suffix_sent = True
                return b"</root>"
            return b""

        to_read = min(size, self.end - self.bytes_read)
        chunk = self.f.read(to_read)
        self.bytes_read += len(chunk)
        if not chunk:
            if not self.suffix_sent:
                self.suffix_sent = True
                return b"</root>"
            return b""
        return chunk

    def close(self):
        self.f.close()


def find_chunks(file_path: str, num_chunks: int):
    file_size = os.path.getsize(file_path)
    chunk_size = file_size // num_chunks
    chunks = []

    with open(file_path, "rb") as f:
        for i in range(num_chunks):
            start = f.tell()
            if i == num_chunks - 1:
                end = file_size
            else:
                f.seek(start + chunk_size)
                line = f.readline()
                while line and b"<marc:record" not in line and b"<record" not in line:
                    line = f.readline()
                end = f.tell() - len(line)
                if end <= start:
                    end = file_size
            chunks.append((start, end))
            if end >= file_size:
                break
            f.seek(end)

    return chunks


def process_chunk(args):
    file_path, start, end, tags, *rest = args
    # Optional plug-in: directory to stream matching full records into (see record_sink.py)
    save_dir = rest[0] if rest else None
    sink = (
        RecordSink(save_dir, tag=f"{Path(file_path).name.split('.')[0]}_{start}")
        if save_dir    
        else None
    )

    tag_counts = Counter()
    record_counts = Counter()
    role_counts = Counter()
    bibliographic_level_counts = Counter()
    type_of_record_counts = Counter()
    encoding_level_counts = Counter()
    gnd_stats = Counter()
    date_counts = Counter()
    specific_date_counts = Counter()
    genre_form_counts = Counter()
    cataloging_source = Counter()
    total_records_rda_ger_encoding = 0
    records_with_genre_forms_count = 0
    # complete_records_count = 0
    record_idx = 0
    place_of_publication_count = Counter()
    language_counts = Counter()
    function_of_entity_counts = Counter()
    

    if file_path.endswith(".gz"):
        stream = gzip.open(file_path, "rb")
    else:
        stream = ChunkStream(file_path, start, end)

    try:
        context = etree.iterparse(stream, events=("end",), recover=True)
        for event, elem in context:
            tag_name = elem.tag.rsplit("}", 1)[-1]
            if tag_name != "record":
                continue

            record_idx += 1
            field_008_val = ""
            field_534_c = None
            has_tags = False
            all_tags_gnd = True
            has_genre_form = False
            keep_record = False
            encoding_level=""
            record_id = None

            seen_tags_in_record = set()
            for child in elem:
                c_tag = child.tag.rsplit("}", 1)[-1]
                if c_tag == "controlfield":
                    c_attr_tag = child.get("tag")
                    if c_attr_tag == "001" and child.text:
                        record_id = child.text.strip()
                    if c_attr_tag == "008" and child.text:
                        field_008_val = child.text
                elif c_tag == "leader":
                    if child.text and len(child.text) >= 18:
                        type_of_record_counts[child.text[6]] += 1
                        bibliographic_level_counts[child.text[7]] += 1
                        encoding_level_counts[child.text[17]] += 1
                        encoding_level=child.text[17]
                elif c_tag == "datafield":
                    d_attr_tag = child.get("tag")

                    # Track fields in given tags for GND completeness
                    if d_attr_tag in tags:
                        has_tags = True
                        df_has_gnd = False
                        roles = []
                        for sf in child:
                            code = sf.get("code")
                            val = sf.text
                            if val:
                                if code == "0" and (
                                    val.startswith("(DE-588)")
                                    or val.startswith("http://d-nb.info/gnd/")
                                ):
                                    df_has_gnd = True
                                elif code == "4":
                                    roles.append(val)

                        if not df_has_gnd:
                            all_tags_gnd = False

                        if d_attr_tag not in seen_tags_in_record:
                            record_counts[d_attr_tag] += 1
                            seen_tags_in_record.add(d_attr_tag)
                        tag_counts[d_attr_tag] += 1
                        if roles:
                            for r in roles:
                                role_name = MARC_RELATORS_CODE.get(r, f"Unknown ({r})")
                                role_counts[f"{d_attr_tag}_{role_name}"] += 1
                                if df_has_gnd:
                                    gnd_stats[f"{d_attr_tag}_has_gnd"] += 1
                                else:
                                    gnd_stats[f"{d_attr_tag}_missing_gnd"] += 1
                            tag_counts[f"{d_attr_tag}_4"] += len(roles)

                    # Track 264 $c
                    if d_attr_tag == "264":
                        function_of_entity_counts[child.get("ind2")] += 1
                        for sf in child:
                            if sf.get("code") == "c" and sf.text:
                                specific_date_counts[sf.text.strip()] += 1
                    
                    # Track 041 $a
                    if d_attr_tag == "041":
                        for sf in child:
                            if sf.get("code") == "a" and sf.text:
                                language_counts[sf.text.strip()] += 1

                    # Track 534 $c
                    if d_attr_tag == "534":
                        for sf in child:
                            if sf.get("code") == "c" and sf.text:
                                field_534_c = sf.text.strip()

                    # Track 655
                    if d_attr_tag == "655":
                        for sf in child:
                            if (
                                sf.get("code") == "0"
                                and sf.text
                                and sf.text.startswith("(DE-588")
                            ):
                                genre_form_counts[sf.text] += 1
                                has_genre_form = True
                    
                    # Track 040
                    if d_attr_tag == "040":
                        has_rda=False
                        has_ger=False
                        for sf in child:
                            code=sf.get("code")
                            value=sf.text
                            if code == "e" and value == "rda":
                                has_rda=True
                            if code == "b" and value == "ger":
                                has_ger=True
                        if has_rda and has_ger:
                            cataloging_source["rda_ger"] += 1
                            if encoding_level == " ":
                            #if len(field_008_val) > 17 and field_008_val[17] == " ":
                                total_records_rda_ger_encoding += 1
                                keep_record = True
                            

            if keep_record and sink is not None:
                sink.write(elem)  # streamed to disk; must precede elem.clear()

            # if has_tags and all_tags_gnd:
            #     complete_records_count += 1

            # leader 008 statistics
            # dates and place of publication
            # Reference: https://www.loc.gov/marc/countries/countries_code.html
            leader_date = None
            field_008_place_of_publication = ""
            if len(field_008_val) >= 18: # commenting this, check L273:and field_008_val[6] == "r":
                leader_date = field_008_val[7:11].strip() + "/" + field_008_val[11:15].strip()
                field_008_place_of_publication = field_008_val[15:18].strip()
                # Commented this to propagate the original data without any replacement
                # if d2 and d2 != "uuuu":
                #     leader_date = d2.replace("u", "X")

            # commented out as it needs a strategy on: how to combine many copies of the same work.
            # if not leader_date and field_534_c:
            #     years = re.findall(r"\b(1[5-9]\d{2}|20\d{2})\b", field_534_c)
            #     if len(years) > 1:
            #         leader_date = f"{years[0]}/{years[1]}"
            #     elif years:
            #         leader_date = years[0]
            #     else:
            #         leader_date = field_534_c

            # if not leader_date and len(field_008_val) >= 11:
            #     d1 = field_008_val[7:11]
            #     if d1.strip():
            #         leader_date = d1.replace("u", "X")

            if leader_date:
                date_counts[leader_date] += 1

            if field_008_place_of_publication:
                place_of_publication_count[field_008_place_of_publication] += 1

            if has_genre_form:
                records_with_genre_forms_count += 1

            elem.clear()
            while elem.getprevious() is not None:
                del elem.getparent()[0]

    finally:
        stream.close()
        if sink is not None:
            sink.close()

    return {
        "record_idx": record_idx,
        "tag_counts": tag_counts,
        "record_counts": record_counts,
        "role_counts": role_counts,
        "bibliographic_level_counts": bibliographic_level_counts,
        "type_of_record_counts": type_of_record_counts,
        "encoding_level_counts": encoding_level_counts,
        "gnd_stats": gnd_stats,
        "date_counts": date_counts,
        "specific_date_counts": specific_date_counts,
        "function_of_entity_counts": function_of_entity_counts,
        "place_of_publication_count": place_of_publication_count,
        "language_counts": language_counts,
        "genre_form_counts": genre_form_counts,
        "cataloging_source": cataloging_source,
        "total_records_rda_ger_encoding": total_records_rda_ger_encoding,
        "records_with_genre_forms_count": records_with_genre_forms_count,
    }


def fast_marc_analyser(
    target: str | list | Path,
    tags: list,
    output_path: str | Path | None = None,
    num_workers: int | None = None,
    save_dir: str | Path | None = None,
):
    start_time = time.time()

    # Expand target into a list of file tasks
    tasks = []
    if isinstance(target, (str, Path)):
        p = Path(target)
        if p.is_dir():
            files = sorted(
                list(p.glob("*.xml")) + list(p.glob("*.xml.gz")) + list(p.glob("*.gz"))
            )
            files = sorted(list(set(files)))
            # chunking for single file
            if (
                len(files) == 1
                and not files[0].name.endswith(".gz")
                and (num_workers is None or num_workers > 1)
            ):
                workers = num_workers or (os.cpu_count() or 4)
                chunks = find_chunks(str(files[0]), workers)
                tasks = [(str(files[0]), start, end, tags) for start, end in chunks]
            # no chunking for multiple files
            else:
                for f in files:
                    tasks.append((str(f), 0, os.path.getsize(f), tags))

        # every gzipped file is a task
        elif p.is_file():
            if p.name.endswith(".gz"):
                tasks.append((str(p), 0, os.path.getsize(p), tags))
            else:
                workers = num_workers or (os.cpu_count() or 4)
                if workers == 1:
                    tasks.append((str(p), 0, os.path.getsize(p), tags))
                else:
                    chunks = find_chunks(str(p), workers)
                    tasks = [(str(p), start, end, tags) for start, end in chunks]
        else:
            raise FileNotFoundError(f"Target path '{target}' not found.")
    elif isinstance(target, list):
        for f in target:
            tasks.append((str(f), 0, os.path.getsize(f), tags))

    if save_dir:
        tasks = [t + (str(save_dir),) for t in tasks]

    if num_workers is None:
        num_workers = min(os.cpu_count() or 4, max(1, len(tasks)))

    print(
        f"Starting Fast MARC Analysis on {len(tasks)} task(s) using {num_workers} CPU cores..."
    )

    tag_counts = Counter()
    record_counts = Counter()
    role_counts = Counter()
    bibliographic_level_counts = Counter()
    type_of_record_counts = Counter()
    encoding_level_counts = Counter()
    gnd_stats = Counter()
    date_counts = Counter()
    place_of_publication_count = Counter()
    specific_date_counts = Counter()
    function_of_entity_counts = Counter()
    genre_form_counts = Counter()
    cataloging_source = Counter()
    language_counts = Counter()
    total_records_rda_ger_encoding = 0
    # record_dates = {}

    total_records = 0
    records_with_genre_forms_total = 0
    complete_records_total = 0

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(process_chunk, task) for task in tasks]
        with tqdm(total=len(tasks), desc="Processing XML Chunks", unit="chunk") as pbar:
            for future in as_completed(futures):
                res = future.result()
                total_records += res["record_idx"]
                #complete_records_total += res["complete_records_count"]
                records_with_genre_forms_total += res["records_with_genre_forms_count"]
                tag_counts.update(res["tag_counts"])
                record_counts.update(res["record_counts"])
                role_counts.update(res["role_counts"])
                bibliographic_level_counts.update(res["bibliographic_level_counts"])
                type_of_record_counts.update(res["type_of_record_counts"])
                encoding_level_counts.update(res["encoding_level_counts"])
                gnd_stats.update(res["gnd_stats"])
                date_counts.update(res["date_counts"])
                genre_form_counts.update(res["genre_form_counts"])
                cataloging_source.update(res["cataloging_source"])
                place_of_publication_count.update(res["place_of_publication_count"])
                language_counts.update(res["language_counts"])
                specific_date_counts.update(res["specific_date_counts"])
                function_of_entity_counts.update(res["function_of_entity_counts"])
                total_records_rda_ger_encoding += res["total_records_rda_ger_encoding"]
                pbar.update(1)

    elapsed_time = time.time() - start_time
    print(
        f"Finished processing {total_records:,} records in {elapsed_time:.2f} seconds ({total_records / elapsed_time if elapsed_time > 0 else 0:,.0f} rec/s)!"
    )

    aggregated_stats = {
        "total_records": total_records,
        "total_records_rda_ger_encoding": total_records_rda_ger_encoding,
        "total_records_rda_ger_encoding_percentage": (total_records_rda_ger_encoding / total_records * 100 if total_records > 0 else 0),
        "cataloging_source": dict(sorted(cataloging_source.items())),
        "encoding_level_counts": dict(sorted(encoding_level_counts.items())),
        "place_of_publication_count": dict(sorted(place_of_publication_count.items())),
        "language_counts": dict(sorted(language_counts.items())),
        "function_of_entity_counts": dict(sorted(function_of_entity_counts.items())),
        "specific_date_counts": dict(sorted(specific_date_counts.items())),
        "records_with_genre_forms_total": records_with_genre_forms_total,
        "complete_records_total": complete_records_total,
        "genre_form_counts": dict(sorted(genre_form_counts.items())),
        "tag_counts": dict(sorted(tag_counts.items())),
        "record_counts": dict(sorted(record_counts.items())),
        "role_counts": dict(sorted(role_counts.items())),
        "bibliographic_level_counts": dict(sorted(bibliographic_level_counts.items())),
        "type_of_record_counts": dict(sorted(type_of_record_counts.items())),
        "gnd_stats": dict(sorted(gnd_stats.items())),
        "date_counts": dict(sorted(date_counts.items())),
    }

    if output_path is None:
        output_path = SCRIPT_DIR / "data/statistics.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(aggregated_stats, f, indent=2)

    print(f"Saved aggregated stats to '{output_path}'")
    return elapsed_time


if __name__ == "__main__":
    tags = ["100", "110", "111", "700", "710", "711", "040"]
    # Optional: input dir/file as first arg (default: data/chunks/)
    target = sys.argv[1] if len(sys.argv) > 1 else "data/mvp_data.xml"
    fast_marc_analyser(target, tags, save_dir="data/filtered")
