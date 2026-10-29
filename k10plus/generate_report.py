"""
This script generates statistics reports from MARCXML data.

Usage:
    uv run python k10plus/generate_report.py

Input:
    - data/statistics.json - Statistics collected from MARCXML data.

Output:
    - data/statistics.md - Detailed analysis report (Markdown).

"""

import json
import time
from pathlib import Path

from gnd_entity_service import get_gnd_entity_type

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

ENCODING_LEVEL_MAP = {
    " ": "Full level",
    "1": "Full level, material not examined",
    "2": "Less-than-full level, material not examined",
    "3": "Abbreviated level",
    "4": "Core level",
    "5": "Partial (preliminary) level",
    "7": "Minimal level",
    "8": "Prepublication level",
    "u": "Unknown",
    "z": "Not applicable",
}

# 264 second indicator
FUNCTION_OF_ENTITY_MAP = {
    "0": "Production",
    "1": "Publication",
    "2": "Distribution",
    "3": "Manufacture",
    "4": "Copyright notice date",
    " ": "Undefined",
}

with open(SCRIPT_DIR / "data/relators.json", "r", encoding="utf-8") as f:
    MARC_RELATORS_CODE = json.load(f)

# 041 $a language codes (MARC Code List for Languages, id.loc.gov)
with open(SCRIPT_DIR / "data/loc_languages.json", "r", encoding="utf-8") as f:
    LANGUAGE_MAP = json.load(f)

# 008/15-17 place of publication (MARC Code List for Countries, id.loc.gov)
with open(SCRIPT_DIR / "data/loc_countries.json", "r", encoding="utf-8") as f:
    COUNTRY_MAP = json.load(f)

TAG_LABELS = {
    "040": "Cataloging Source",
    "100": "Person Main Entry",
    "110": "Corporate Main Entry",
    "111": "Meeting Main Entry",
    "700": "Person Added Entry",
    "710": "Corporate Added Entry",
    "711": "Meeting Added Entry",
}
TOP_SPECIFIC_DATES = 50


def aggregate_stats(directory_path: str | Path | None = None):
    if directory_path is None:
        directory_path = SCRIPT_DIR / "data"

    def merge_dicts(acc: dict, src: dict):
        for key, value in src.items():
            if isinstance(value, dict):
                if key not in acc or not isinstance(acc[key], dict):
                    acc[key] = {}
                merge_dicts(acc[key], value)
            elif isinstance(value, (int, float)):
                if key not in acc:
                    acc[key] = 0
                acc[key] += value

    aggregated_data = {}
    json_files = list(Path(directory_path).glob("stats*.json"))
    for file in json_files:
        print(f"Reading {file}...")
        with open(file, "r", encoding="utf-8") as f:
            stats = json.load(f)
        merge_dicts(aggregated_data, stats)

    with open(
        SCRIPT_DIR / "data/statistics_aggregated.json", "w", encoding="utf-8"
    ) as f:
        json.dump(aggregated_data, f, indent=4)


def _pct(count: int, total: int) -> float:
    return count / total * 100 if total > 0 else 0


def _by_frequency(counts: dict) -> list[tuple[str, int]]:
    return sorted(counts.items(), key=lambda x: x[1], reverse=True)


def _cell(value) -> str:
    return str(value).replace("|", "\\|")


def _section(f, title: str, level: int = 2):
    f.write(f"{'#' * level} {title}\n\n")


def _table(f, headers: list[str], rows: list[list], numeric: int = 2):
    """Write a Markdown table; the last `numeric` columns are right-aligned."""
    if not rows:
        f.write("_No data._\n\n")
        return
    aligns = ["---"] * (len(headers) - numeric) + ["---:"] * numeric
    f.write("| " + " | ".join(headers) + " |\n")
    f.write("| " + " | ".join(aligns) + " |\n")
    for row in rows:
        f.write("| " + " | ".join(_cell(c) for c in row) + " |\n")
    f.write("\n")


def _count_row(label, count: int, total: int) -> list:
    return [label, f"{count:,}", f"{_pct(count, total):.2f}%"]


def _write_summary(f, data: dict):
    total = data["total_records"]
    complete = data.get("complete_records_total", data.get("complete_records_count", 0))
    f.write("# MARC Analysis Summary\n\n")
    _table(
        f,
        ["Metric", "Count"],
        [
            ["Total records processed", f"{total:,}"],
            #_count_row("Complete records", complete, total),
            #_count_row("Incomplete records", total - complete, total),
        ],
    )


def _write_genre_forms(f, data: dict):
    total = data["total_records"]
    with_genre = data["records_with_genre_forms_total"]
    genre_form_counts = data.get("genre_form_counts", {})
    _section(f, "Genre Form Counts")
    _table(
        f,
        ["Metric", "Count", "%"],
        [
            _count_row("Records with genre forms", with_genre, total),
            _count_row("Records missing genre forms", total - with_genre, total),
            ["Total genre forms", f"{sum(genre_form_counts.values()):,}", ""],
        ],
    )
    rows = []
    for genre_form, count in _by_frequency(genre_form_counts):
        if count <= 0:
            continue
        try:
            preferred_name = get_gnd_entity_type(genre_form.replace("(DE-588)", ""))
        except Exception as e:  # noqa: BLE001 - GND lookup is best effort
            print(e)
            preferred_name = genre_form
        rows.append(_count_row(preferred_name or genre_form, count, total))
    _table(f, ["Genre form", "Records", "%"], rows)


def _write_cataloging_source(f, data: dict):
    total = data["total_records"]
    kept = data.get("total_records_rda_ger_encoding", 0)
    _section(f, "Cataloging Source and Encoding Level")
    rows = [
        _count_row(
            "`040 $e rda` and `$b ger`" if source == "rda_ger" else source,
            count,
            total,
        )
        for source, count in _by_frequency(data.get("cataloging_source", {}))
    ]
    rows.append(_count_row("... with full encoding level (kept)", kept, total))
    _table(f, ["Cataloging source", "Records", "%"], rows)

    _section(f, "Encoding level (Leader/17)", 3)
    rows = [
        [
            f"`{level}`" if level.strip() else "_blank_",
            ENCODING_LEVEL_MAP.get(level, "Other"),
            *_count_row("", c, total)[1:],
        ]
        for level, c in _by_frequency(data.get("encoding_level_counts", {}))
    ]
    _table(f, ["Code", "Level", "Records", "%"], rows)


def _write_code_distribution(
    f, title: str, counts: dict, label_map: dict, label_header: str
):
    """Distribution of coded values (language, place) with their labels."""
    total = sum(counts.values())
    _section(f, title)
    rows = [
        [f"`{code}`", label_map.get(code, ""), *_count_row("", count, total)[1:]]
        for code, count in _by_frequency(counts)
    ]
    _table(f, ["Code", label_header, "Entries", "%"], rows)


def _write_function_of_entity(f, data: dict):
    counts = data.get("function_of_entity_counts", {})
    total = sum(counts.values())
    _section(f, "Function of Entity (264 second indicator)")
    rows = [
        [
            f"`{ind}`",
            FUNCTION_OF_ENTITY_MAP.get(ind, "Other"),
            *_count_row("", c, total)[1:],
        ]
        for ind, c in _by_frequency(counts)
    ]
    _table(f, ["Indicator", "Function", "Entries", "%"], rows)


def _write_leader_counts(f, data: dict):
    total = data["total_records"]
    for title, key, label_map in (
        (
            "Bibliographic Level Counts",
            "bibliographic_level_counts",
            BIBLIOGRAPHIC_LEVEL_MAP,
        ),
        ("Type of Record Counts", "type_of_record_counts", TYPE_OF_RECORD_MAP),
    ):
        counts = data[key]
        _section(f, title)
        rows = [
            _count_row(label, counts.get(code, 0), total)
            for code, label in sorted(
                label_map.items(), key=lambda x: counts.get(x[0], 0), reverse=True
            )
            if counts.get(code, 0) > 0
        ]
        _table(f, ["Label", "Records", "%"], rows)


def _write_tag_frequency(f, data: dict, tags: list):
    total = data["total_records"]
    tag_counts, record_counts = data["tag_counts"], data["record_counts"]
    _section(f, "Tag Frequency")
    rows = [
        [
            f"`{tag}`",
            TAG_LABELS.get(tag, f"Tag {tag}"),
            f"{tag_counts.get(tag, 0):,}",
            f"{record_counts.get(tag, 0):,}",
            f"{_pct(record_counts.get(tag, 0), total):.2f}%",
        ]
        for tag in sorted(tags)
    ]
    _table(f, ["Tag", "Label", "Instances", "Records", "% of records"], rows, 3)


def _write_relators(f, data: dict, entity_tags: list):
    tag_counts = data["tag_counts"]
    role_counts = data.get("role_counts", {})

    _section(f, "Relator Coverage Summary")
    f.write(f"Total relators found: **{sum(role_counts.values()):,}**\n\n")
    rows = []
    for tag in sorted(entity_tags):
        instances = tag_counts.get(tag, 0)
        with_role = tag_counts.get(f"{tag}_4", 0)
        if instances > 0:
            rows.append(
                [
                    f"`{tag}`",
                    f"{with_role:,}",
                    f"{instances:,}",
                    f"{_pct(with_role, instances):.2f}%",
                ]
            )
    _table(f, ["Tag", "With `$4` relator", "Instances", "%"], rows, 3)

    _section(f, "Relator Detail Breakdown")
    for tag in entity_tags:
        group = {k: v for k, v in role_counts.items() if k.startswith(tag)}
        if not group:
            continue
        total_t = tag_counts.get(f"{tag}_4", 0)
        _section(f, f"Tag {tag} relators", 3)
        rows = [
            _count_row(key.split("_", 1)[1].replace("_", " ").title(), count, total_t)
            for key, count in _by_frequency(group)
        ]
        _table(f, ["Relator", "Count", "%"], rows)


def _write_gnd_coverage(f, data: dict, entity_tags: list):
    tag_counts = data["tag_counts"]
    gnd_stats = data.get("gnd_stats", {})
    _section(f, "GND Linking Coverage")
    f.write("Percentage of defined relators (`$4`) that are mapped to a GND ID.\n\n")
    rows = []
    for tag in sorted(entity_tags):
        count = gnd_stats.get(f"{tag}_has_gnd", 0)
        total_roles = tag_counts.get(f"{tag}_4", 0)
        rows.append(
            [
                f"`{tag}`",
                f"{count:,}",
                f"{total_roles:,}",
                f"{_pct(count, total_roles):.2f}%",
            ]
        )
    _table(f, ["Tag", "With GND ID", "Defined relators", "%"], rows, 3)


def _write_date_statistics(f, data: dict):
    # date_counts keys are "<008/07-10>/<008/11-14>", e.g. "1817/" or "1827/9999"
    date_counts = data["date_counts"]

    def start_year(key: str) -> str:
        return key.split("/", 1)[0]

    numeric = [
        d for d in date_counts if start_year(d).isdigit() and len(start_year(d)) == 4
    ]
    empty = [d for d in date_counts if d == "/"]
    non_numeric = [d for d in date_counts if d not in numeric and d not in empty]
    years = [start_year(d) for d in numeric]
    total = sum(date_counts.values())
    numeric_total = sum(date_counts[d] for d in numeric)
    non_numeric_total = sum(date_counts[d] for d in non_numeric)
    empty_total = sum(date_counts[d] for d in empty)

    _section(f, "Date Statistics (008/07-14)")
    f.write(
        f"Time span (start year): **{min(years, default='Unknown')} - {max(years, default='Unknown')}**\n\n"
    )
    _table(
        f,
        ["Metric", "Instances", "%"],
        [
            _count_row("Numeric start year", numeric_total, total),
            _count_row(
                "Non-numeric start year (e.g. `19uu`)", non_numeric_total, total
            ),
            _count_row("Empty dates", empty_total, total),
            ["Total date entries", f"{total:,}", ""],
            ["Unique numeric date values", f"{len(numeric):,}", ""],
            ["Unique non-numeric date values", f"{len(non_numeric):,}", ""],
        ],
    )

    _section(f, "Date breakdown (sorted by frequency)", 3)
    _table(
        f,
        ["Date", "Count", "%"],
        [_count_row(f"`{d}`", c, total) for d, c in _by_frequency(date_counts)],
    )

    specific = data.get("specific_date_counts", {})
    if specific:
        total_specific = sum(specific.values())
        _section(f, f"Specific Dates (264 `$c`, top {TOP_SPECIFIC_DATES})")
        f.write(
            f"Total entries: {total_specific:,}, unique values: {len(specific):,}\n\n"
        )
        _table(
            f,
            ["Date", "Count", "%"],
            [
                _count_row(f"`{d}`", c, total_specific)
                for d, c in _by_frequency(specific)[:TOP_SPECIFIC_DATES]
            ],
        )


def generate_report_from_json(
    stats_json_path: str | Path | None = None,
    output_path: str | Path | None = None,
    tags: list | None = None,
):
    if tags is None:
        tags = ["100", "110", "111", "700", "710", "711"]
    if stats_json_path is None:
        stats_json_path = SCRIPT_DIR / "data/statistics.json"
    if output_path is None:
        output_path = SCRIPT_DIR / "data/statistics.md"

    with open(stats_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # tag 040 is only collected for cataloging source, it has no $4/$0 to report
    entity_tags = [t for t in tags if t != "040"]

    start_time = time.time()
    print("Starting statistics collection from JSON...")
    with open(output_path, "w", encoding="utf-8") as f:
        _write_summary(f, data)
        _write_cataloging_source(f, data)
        _write_code_distribution(
            f,
            "Language Counts (041 `$a`)",
            data.get("language_counts", {}),
            LANGUAGE_MAP,
            "Language",
        )
        _write_code_distribution(
            f,
            "Place of Publication (008/15-17)",
            data.get("place_of_publication_count", {}),
            COUNTRY_MAP,
            "Place",
        )
        _write_function_of_entity(f, data)
        _write_leader_counts(f, data)
        _write_date_statistics(f, data)
        _write_genre_forms(f, data)
        _write_tag_frequency(f, data, tags)
        _write_relators(f, data, entity_tags)
        _write_gnd_coverage(f, data, entity_tags)


    print(f"Time taken for report generation: {time.time() - start_time:.2f} seconds")


if __name__ == "__main__":
    # aggregate_stats()
    generate_report_from_json()
