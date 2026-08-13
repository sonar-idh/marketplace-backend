"""
This script is for analysis of MARCXML data.
It counts the occurrences of specific MARC tags and subfields, calculates GND linking coverage,
and validates records for completeness.

Usage:
    uv run python k10plus/marc_dump_analysis.py

Input:
    schumann.xml - MARCXML file containing bibliographic records.

Output:
    - k10plus/data/statistics.txt - Detailed analysis report (tags, record types, levels, relators, and GND linking coverage).
"""

import json
import logging
from collections import Counter
from pathlib import Path

from marcxml_utils import FilteredXMLStream
from pymarc import map_xml

SCRIPT_DIR = Path(__file__).resolve().parent

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(SCRIPT_DIR / "data/analysis.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

# Reference: https://www.loc.gov/marc/bibliographic/bdleader.html
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


def marc_analyser(file_path: str, tags: list, subfields: list, output_path: str = None):
    tag_counts = Counter()
    record_counts = Counter()
    role_counts = Counter()
    bibliographic_level_counts = Counter()
    type_of_record_counts = Counter()
    gnd_stats = Counter()
    complete_records_count = 0
    date_counts = Counter()
    record_dates = {}

    record_idx = 0

    def complete_record(record):
        """
        A record is complete, if it atleast has one contrbution and all the contributors (100 or 700) have a GND ID.
        - Person entries (no subfield $t) require a role code ($4) and a GND ID ($0).
        - Name-Title entries (has subfield $t) only require a GND ID ($0) and do not need a role code ($4), as the role is taken from the tag (100 or 700).
        """
        matching_fields = record.get_fields("100") + record.get_fields("700")
        if not matching_fields:
            return False, ["Missing all contributor fields (100 or 700)"]

        errors = []
        for field in matching_fields:
            tag = field.tag
            name = (
                field.get_subfields("a")[0]
                if field.get_subfields("a")
                else "Unknown name"
            )
            sub0 = field.get_subfields("0")  # GND
            sub4 = field.get_subfields("4")  # role
            has_title = len(field.get_subfields("t")) > 0

            # Check that there is at least one non-empty identifier
            if not any(val.strip() for val in sub0):
                errors.append(f"Tag {tag} ({name}) - Missing identifier ($0)")
            else:
                # Check if ANY subfield 0 starts with (DE-588)
                has_gnd = any(val.startswith("(DE-588") for val in sub0)
                if not has_gnd:
                    errors.append(
                        f"Tag {tag} ({name}) - Missing GND ID (found other IDs: {sub0})"
                    )

            # If it is a person entry (no $t), we also require a non-empty role code ($4)
            if not has_title and not any(val.strip() for val in sub4):
                errors.append(f"Tag {tag} ({name}) - Missing role code ($4)")

        if errors:
            return False, errors
        return True, []

    def get_record_date(record):
        """
        Get the record date
        Uses this logic:
            1. Identify whether the record is a reproduction by checking for tag 534. If it is present, then the original details are in this tag because the reproduction details are not of use to us.
            2. Else look for control field 008 to get machine readable date by parsing it.
                - Char position 06-17 --> Date
            3. Fall back: if control field 008 contains uuuu or 19uu, check tag 264$C and 260$c.
        """
        record_id = record["001"].value() if "001" in record else "unknown"
        field_534 = record.get_fields("534")
        date = None
        if len(field_534) > 1:
            logger.info(f"Found {len(field_534)} instances of tag 534")
        if field_534:
            logger.info(
                f"Using 534 field to get the record date: {field_534[0].get_subfields('c')}"
            )
            date = field_534[0].get_subfields("c")[0]
        else:
            field_008 = record.get_fields("008")[0].value()
            raw_date = field_008[7:11]
            date = raw_date.replace("u", "X")
            logger.info(
                f"Using 008 field (with 'u' replaced by 'X') to get the record date: {date}"
            )
        if date is None:
            logger.error(f"Could not find the record date for record {record_id}")
        return date

    # iterating over each record in MARC file --> iteration over Tags --> get all the fields and subfields --> add to the counter --> print statistics
    def process_record(record):
        nonlocal record_idx, complete_records_count
        record_idx += 1
        record_id = record["001"].value() if "001" in record else "unknown"
        logger.info(f"===== Record {record_idx}: {record_id} =====")

        type_of_record, bibliographic_level = (
            record.leader.type_of_record,
            record.leader.bibliographic_level,
        )
        logger.info(
            f"Type of record: {type_of_record}, Bibliographic level: {bibliographic_level}"
        )

        # Check completeness and log if incomplete
        is_complete, errors = complete_record(record)
        if is_complete:
            complete_records_count += 1
        else:
            logger.error(f"Record {record_idx} (ID: {record_id}) is incomplete")
            for err in errors:
                logger.error(f"  - {err}")

        bibliographic_level_counts[bibliographic_level] += 1
        type_of_record_counts[type_of_record] += 1

        # # Log if record is missing Tag 100
        # if not record.get_fields('100'):
        #     # getting record id from 001
        #     record_id = record['001'].value() if '001' in record else "unknown"
        #     issues_file.write(f"Record {record_idx} (ID: {record_id}): Missing Tag 100\n")

        record_date = get_record_date(record)
        if record_date:
            date_counts[record_date] += 1
            record_dates[record_id] = record_date

        # iterating over required tags
        for tag in tags:
            matching_fields = record.get_fields(tag)
            if matching_fields:
                tag_counts[tag] += len(matching_fields)
                record_counts[tag] += 1
                logger.info(f"Found {len(matching_fields)} instances of tag {tag}")

                if tag in tags:
                    for j, field in enumerate(matching_fields):
                        # multiple roles in a single tag 700 or 100 is possible
                        # tag 100 contains data of single person
                        for subfield_code in subfields:
                            roles = field.get_subfields(subfield_code)
                            if roles and field.get_subfields("0"):
                                sub0_ids = field.get_subfields("0")
                                if any(val.startswith("(DE-588") for val in sub0_ids):
                                    gnd_stats[f"{tag}_{subfield_code}"] += len(roles)

                            if roles:
                                # counting different relator types with blank relator handling
                                for r in roles:
                                    if r.strip():
                                        # Retain only alphabetic characters, lowercase, and keep first 3 chars
                                        r_clean = "".join(
                                            [c for c in r if c.isalpha()]
                                        ).lower()[:3]
                                        role_name = MARC_RELATORS_CODE.get(r_clean)
                                        if role_name:
                                            role_counts[f"{tag}_{role_name}"] += 1
                                        else:
                                            role_counts[
                                                f"{tag}_unknown_relator_{r_clean}"
                                            ] += 1
                                            logger.info(
                                                f"Record {record_idx}, Tag: {tag}, Position: {j}: Unknown relator code '{r}'"
                                            )
                                            logger.info(
                                                f"Record {record_idx}, Tag: {tag}, Position: {j}: Unknown relator code '{r}'"
                                            )

                                    else:
                                        # counting blank_relator for sanity check
                                        role_counts[f"{tag}_blank_relator"] += 1
                                        # tracking blank relator info directly to issues file
                                        logger.info(
                                            f"Record {record_idx}, Tag: {tag}, Position: {j}: Blank relator"
                                        )
                                tag_counts[f"{tag}_{subfield_code}"] += len(roles)
                                logger.info(
                                    f"  - {tag} instance {j + 1}: subfield ${subfield_code} values: {roles}"
                                )
                            else:
                                logger.info(
                                    f"  - {tag} instance {j + 1}: missing subfield ${subfield_code}"
                                )
            else:
                logger.info(f"Missing tag {tag}")

    with open(file_path, "rb") as f:
        stream = FilteredXMLStream(f)
        map_xml(process_record, stream)

    if output_path is None:
        output_path = SCRIPT_DIR / "data/statistics.txt"

    # Statistics documentation
    with open(output_path, "w") as f:
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

        f.write("=" * 80 + "\n")
        f.write("BIBLIOGRAPHIC LEVEL COUNTS (Sorted by Frequency)\n")
        f.write("=" * 80 + "\n")
        sorted_levels = sorted(
            BIBLIOGRAPHIC_LEVEL_MAP.keys(),
            key=lambda x: bibliographic_level_counts[x],
            reverse=True,
        )
        for level in sorted_levels:
            count = bibliographic_level_counts[level]
            if count > 0:
                pct = (count / record_idx * 100) if record_idx > 0 else 0
                label = BIBLIOGRAPHIC_LEVEL_MAP[level]
                f.write(f"- {label:<40}: {count:,} ({pct:.2f}%)\n")
        f.write("\n")

        f.write("=" * 80 + "\n")
        f.write("TYPE OF RECORD COUNTS (Sorted by Frequency)\n")
        f.write("=" * 80 + "\n")
        sorted_records = sorted(
            TYPE_OF_RECORD_MAP.keys(),
            key=lambda x: type_of_record_counts[x],
            reverse=True,
        )
        for record in sorted_records:
            count = type_of_record_counts[record]
            if count > 0:
                pct = (count / record_idx * 100) if record_idx > 0 else 0
                label = TYPE_OF_RECORD_MAP[record]
                f.write(f"- {label:<40}: {count:,} ({pct:.2f}%)\n")
        f.write("\n")

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
            pct = (record_counts[tag] / record_idx * 100) if record_idx > 0 else 0
            f.write(
                f"- Tag {tag} ({label:<20}): {tag_counts[tag]:,} instances across {record_counts[tag]:,} records,    ({pct:.2f}%) of total records\n"
            )
        f.write("\n")

        f.write("=" * 80 + "\n")
        f.write("RELATOR COVERAGE SUMMARY\n")
        f.write("=" * 80 + "\n")
        f.write(f"Total Relators Found    : {role_counts.total():,}\n")
        for tag in sorted(tags):
            total_instances = tag_counts.get(tag, 0)
            tag_sub4 = tag_counts.get(f"{tag}_4", 0)
            if total_instances > 0:
                pct = tag_sub4 / total_instances * 100
                f.write(
                    f"- Tag {tag} ($4 codes defined)  : {tag_sub4:,} defined relators across {total_instances:,} instances ({pct:.2f}%)\n"
                )
        f.write("\n")

        f.write("=" * 80 + "\n")
        f.write("RELATOR DETAIL BREAKDOWN (Sorted by Frequency)\n")
        f.write("=" * 80 + "\n")
        # Group by tags first
        total_100 = tag_counts.get("100_4", 0)
        total_110 = tag_counts.get("110_4", 0)
        total_700 = tag_counts.get("700_4", 0)

        for group_tag, group_total in [
            ("100", total_100),
            ("110", total_110),
            ("700", total_700),
        ]:
            group_keys = [k for k in role_counts if k.startswith(group_tag)]
            if not group_keys:
                continue

            f.write(f"\nTag {group_tag} Relators:\n")
            f.write("-" * 40 + "\n")
            sorted_group = sorted(
                group_keys, key=lambda x: role_counts[x], reverse=True
            )
            for k in sorted_group:
                count = role_counts[k]
                pct = (count / group_total * 100) if group_total > 0 else 0
                role_name = k.split("_", 1)[1].replace("_", " ").title()
                f.write(f"  - {role_name:<30}: {count:,} ({pct:.2f}%)\n")
        f.write("\n")

        f.write("=" * 80 + "\n")
        f.write("GND LINKING COVERAGE (Percentage of subfields mapped to a GND ID)\n")
        f.write("=" * 80 + "\n")
        for tag in sorted(gnd_stats.keys()):
            count = gnd_stats[tag]
            parent_tag = tag.split("_")[0]
            total_roles = tag_counts[tag]
            pct = (count / total_roles * 100) if total_roles > 0 else 0
            f.write(
                f"- Tag {parent_tag} Subfield $4             : {count:,} of {total_roles:,} defined relators have GND IDs ({pct:.2f}%)\n"
            )

        # Date Statistics
        f.write("\n")
        sorted_dates = sorted(
            date_counts.keys(), key=lambda x: date_counts[x], reverse=True
        )
        # Extract only 4-digit numeric years
        numeric_dates = [d for d in date_counts.keys() if d.isdigit() and len(d) == 4]
        min_date = min(numeric_dates) if numeric_dates else "Unknown"
        max_date = max(numeric_dates) if numeric_dates else "Unknown"
        numeric_dates_pct = (
            sum([date_counts[d] for d in numeric_dates])
            / sum(date_counts.values())
            * 100
        )
        non_numeric_dates = [
            d for d in date_counts.keys() if not d.isdigit() or len(d) != 4
        ]
        non_numeric_dates_pct = (
            sum([date_counts[d] for d in non_numeric_dates])
            / sum(date_counts.values())
            * 100
        )

        f.write("=" * 80 + "\n")
        f.write("DATE STATISTICS\n")
        f.write("=" * 80 + "\n")
        f.write("\n Overview\n")
        f.write("-" * 40 + "\n")
        f.write("Time span: " + min_date + " - " + max_date + "\n")
        f.write(f"Total date entries: {sum(date_counts.values())}\n")
        f.write(
            f"Total numeric dates instances: {sum([date_counts[d] for d in numeric_dates])}\n"
        )
        f.write(
            f"Total non-numeric dates instances: {sum([date_counts[d] for d in non_numeric_dates])}\n"
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
            pct = count / sum(date_counts.values()) * 100
            f.write(f"- {date}: {count:,} ({pct:.2f}%)\n")
        # write date counts to json file
        with open("data/date_counts_marc.json", "w", encoding="utf-8") as f:
            json.dump(date_counts, f, indent=4)
        with open("data/dates_with_recordID_marc.json", "w", encoding="utf-8") as f:
            json.dump(record_dates, f, indent=4)


if __name__ == "__main__":
    tags = ["100", "700"]
    subfields = ["4"]
    marc_analyser("data/schumann.xml", tags, subfields)
