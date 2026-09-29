"""
This script generates statistics reports from MARCXML data.

Usage:
    uv run python k10plus/generate_report.py

Input:
    - data/statistics.json - Statistics collected from MARCXML data.

Output:
    - data/statistics.txt - Detailed analysis report.

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

with open(SCRIPT_DIR / "data/relators.json", "r", encoding="utf-8") as f:
    MARC_RELATORS_CODE = json.load(f)


def aggregate_stats(directory_path: str | Path = None):
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


def generate_report_from_json(
    stats_json_path: str | Path = None,
    output_path: str | Path = None,
    tags: list = None,
):
    if tags is None:
        tags = ["100", "110", "111", "700", "710", "711"]

    if stats_json_path is None:
        stats_json_path = SCRIPT_DIR / "data/statistics.json"

    if output_path is None:
        output_path = SCRIPT_DIR / "data/statistics.txt"

    with open(stats_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    record_idx = data["total_records"]
    complete_records_count = data["complete_records_total"]
    records_with_genre_forms_total = data["records_with_genre_forms_total"]
    tag_counts = data["tag_counts"]
    record_counts = data["record_counts"]
    role_counts = data["role_counts"]
    bibliographic_level_counts = data["bibliographic_level_counts"]
    type_of_record_counts = data["type_of_record_counts"]
    gnd_stats = data["gnd_stats"]
    date_counts = data["date_counts"]
    genre_form_counts = data["genre_form_counts"]
    # record_dates = data.get("record_dates", {})

    with open(output_path, "w", encoding="utf-8") as f:
        start_time = time.time()
        print("Starting statistics collection from JSON...")
        f.write("=" * 80 + "\n")
        f.write("                                 MARC ANALYSIS SUMMARY\n")
        f.write("=" * 80 + "\n")
        f.write(f"Total Records Processed : {record_idx:,}\n")
        pct_complete = (
            (complete_records_count / record_idx * 100) if record_idx > 0 else 0
        )
        pct_incomplete = 100 - pct_complete
        f.write(
            f"Complete Records        : {complete_records_count:,} ({pct_complete:.2f}%)\n"
        )
        f.write(
            f"Incomplete Records      : {record_idx - complete_records_count:,} ({pct_incomplete:.2f}%)\n"
        )
        f.write("\n")

        # genre form counts
        f.write("=" * 80 + "\n")
        f.write("GENRE FORM COUNTS (Sorted by Frequency)\n")
        f.write("=" * 80 + "\n")
        f.write(
            f"Total records with Genre Forms: {records_with_genre_forms_total:,} ({records_with_genre_forms_total / record_idx * 100:.2f}%)\n"
        )
        f.write(
            f"Missing Genre Forms: {(record_idx - records_with_genre_forms_total):,} ({(record_idx - records_with_genre_forms_total) / record_idx * 100:.2f}%)\n"
        )
        f.write(f"Total Genre Forms: {sum(genre_form_counts.values()):,}\n")
        f.write("\n")
        sorted_genre_forms = sorted(
            genre_form_counts.keys(),
            key=lambda x: genre_form_counts[x],
            reverse=True,
        )

        for genre_form in sorted_genre_forms:
            cleaned_genre_form = genre_form.replace("(DE-588)", "")
            try:
                preferred_name = get_gnd_entity_type(cleaned_genre_form)
            except Exception as e:
                print(e)
                preferred_name = genre_form

            count = genre_form_counts[genre_form]
            if count > 0:
                pct = (count / record_idx * 100) if record_idx > 0 else 0
                display_label = preferred_name if preferred_name else genre_form
                f.write(f"- {display_label:<80}: {count:,} ({pct:.2f}%)\n")
        f.write("\n")

        # bibliographic level counts
        f.write("=" * 80 + "\n")
        f.write("BIBLIOGRAPHIC LEVEL COUNTS (Sorted by Frequency)\n")
        f.write("=" * 80 + "\n")
        sorted_levels = sorted(
            BIBLIOGRAPHIC_LEVEL_MAP.keys(),
            key=lambda x: bibliographic_level_counts.get(x, 0),
            reverse=True,
        )
        for level in sorted_levels:
            count = bibliographic_level_counts.get(level, 0)
            if count > 0:
                pct = (count / record_idx * 100) if record_idx > 0 else 0
                label = BIBLIOGRAPHIC_LEVEL_MAP[level]
                f.write(f"- {label:<40}: {count:,} ({pct:.2f}%)\n")
        f.write("\n")

        # type of record counts
        f.write("=" * 80 + "\n")
        f.write("TYPE OF RECORD COUNTS (Sorted by Frequency)\n")
        f.write("=" * 80 + "\n")
        sorted_records = sorted(
            TYPE_OF_RECORD_MAP.keys(),
            key=lambda x: type_of_record_counts.get(x, 0),
            reverse=True,
        )
        for rec in sorted_records:
            count = type_of_record_counts.get(rec, 0)
            if count > 0:
                pct = (count / record_idx * 100) if record_idx > 0 else 0
                label = TYPE_OF_RECORD_MAP[rec]
                f.write(f"- {label:<40}: {count:,} ({pct:.2f}%)\n")
        f.write("\n")

        # tag frequency
        f.write("=" * 80 + "\n")
        f.write("TAG FREQUENCY\n")
        f.write("=" * 80 + "\n")
        tag_labels = {
            "100": "Person Main Entry",
            "110": "Corporate Main Entry",
            "700": "Person Added Entry",
        }
        for tag in sorted(tags):
            label = tag_labels.get(tag, f"Tag {tag}")
            pct = (
                (record_counts.get(tag, 0) / record_idx * 100) if record_idx > 0 else 0
            )
            f.write(
                f"- Tag {tag} ({label:<20}): {tag_counts.get(tag, 0):,} instances across {record_counts.get(tag, 0):,} records,    ({pct:.2f}%) of total records\n"
            )
        f.write("\n")

        # relator coverage summary
        f.write("=" * 80 + "\n")
        f.write("RELATOR COVERAGE SUMMARY\n")
        f.write("=" * 80 + "\n")
        f.write(f"Total Relators Found    : {sum(role_counts.values()):,}\n")
        for tag in sorted(tags):
            total_instances = tag_counts.get(tag, 0)
            tag_sub4 = tag_counts.get(f"{tag}_4", 0)
            if total_instances > 0:
                pct = tag_sub4 / total_instances * 100
                f.write(
                    f"- Tag {tag} ($4 codes defined)  : {tag_sub4:,} defined relators across {total_instances:,} instances ({pct:.2f}%)\n"
                )
        f.write("\n")

        # relator detail breakdown
        f.write("=" * 80 + "\n")
        f.write("RELATOR DETAIL BREAKDOWN (Sorted by Frequency)\n")
        f.write("=" * 80 + "\n")
        for t in tags:
            total_t = tag_counts.get(f"{t}_4", 0)
            group_keys = [k for k in role_counts if k.startswith(t)]
            if not group_keys:
                continue

            f.write(f"\nTag {t} Relators:\n")
            f.write("-" * 40 + "\n")
            sorted_group = sorted(
                group_keys, key=lambda x: role_counts[x], reverse=True
            )
            for k in sorted_group:
                count = role_counts[k]
                pct = (count / total_t * 100) if total_t > 0 else 0
                role_name = k.split("_", 1)[1].replace("_", " ").title()
                f.write(f"  - {role_name:<30}: {count:,} ({pct:.2f}%)\n")
        f.write("\n")

        # gnd linking coverage
        f.write("=" * 80 + "\n")
        f.write("GND LINKING COVERAGE (Percentage of subfields mapped to a GND ID)\n")
        f.write("=" * 80 + "\n")
        for tag in sorted(tags):
            count = gnd_stats.get(f"{tag}_has_gnd", 0)
            total_roles = tag_counts.get(f"{tag}_4", 0)
            pct = (count / total_roles * 100) if total_roles > 0 else 0
            f.write(
                f"- Tag {tag} Subfield $4             : {count:,} of {total_roles:,} defined relators have GND IDs ({pct:.2f}%)\n"
            )

        # Date Statistics
        f.write("\n")
        sorted_dates = sorted(
            date_counts.keys(), key=lambda x: date_counts[x], reverse=True
        )
        numeric_dates = [d for d in date_counts.keys() if d.isdigit() and len(d) == 4]
        min_date = min(numeric_dates) if numeric_dates else "Unknown"
        max_date = max(numeric_dates) if numeric_dates else "Unknown"
        total_date_entries = sum(date_counts.values()) or 1
        numeric_dates_pct = (
            sum([date_counts[d] for d in numeric_dates]) / total_date_entries * 100
        )
        non_numeric_dates = [
            d for d in date_counts.keys() if not d.isdigit() or len(d) != 4
        ]
        non_numeric_dates_pct = (
            sum([date_counts[d] for d in non_numeric_dates]) / total_date_entries * 100
        )

        f.write("=" * 80 + "\n")
        f.write("DATE STATISTICS\n")
        f.write("=" * 80 + "\n")
        f.write("\n Overview\n")
        f.write("-" * 40 + "\n")
        f.write("Time span: " + min_date + " - " + max_date + "\n")
        f.write(f"Total date entries: {sum(date_counts.values()):,}\n")
        f.write(
            f"Total numeric dates instances: {sum([date_counts[d] for d in numeric_dates]):,}\n"
        )
        f.write(
            f"Total non-numeric dates instances: {sum([date_counts[d] for d in non_numeric_dates]):,}\n"
        )
        f.write(
            f"Unique numeric dates: {len(numeric_dates)} ({numeric_dates_pct:.2f}%)\n"
        )
        f.write(
            f"Unique non-numeric dates: {len(non_numeric_dates)} ({non_numeric_dates_pct:.2f}%)\n"
        )

        f.write("\n")
        f.write("\nDate Breakdown (Sorted by Frequency):\n")
        f.write("-" * 40 + "\n")
        for date in sorted_dates:
            count = date_counts[date]
            pct = count / total_date_entries * 100
            f.write(f"- {date}: {count:,} ({pct:.2f}%)\n")

        # with open(
        #     SCRIPT_DIR / "data/date_counts_marc.json", "w", encoding="utf-8"
        # ) as json_f:
        #     json.dump(date_counts, json_f, indent=4)
        #     json_f.write("\n")

        # if record_dates:
        #     with open(
        #         SCRIPT_DIR / "data/dates_with_recordID_marc.json",
        #         "w",
        #         encoding="utf-8",
        #     ) as json_f:
        #         json.dump(record_dates, json_f, indent=4)
        #         json_f.write("\n")

        print(
            f"Time taken for report generation: {time.time() - start_time:.2f} seconds"
        )


if __name__ == "__main__":
    # aggregate_stats()
    generate_report_from_json()
