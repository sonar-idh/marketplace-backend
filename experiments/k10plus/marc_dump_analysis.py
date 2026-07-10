"""
This script is for analysis of MARCXML data.
It counts the occurrences of specific MARC tags and subfields.

Update MARC_TAGS to check for different tags.

Usage:
python3 marc_dump_analysis.py

Input:
clara_schumann.xml - MARCXML file containing records.

Output: 
- Tags Summary
- Relators Summary
- debug_output.txt - detailed output for each record
- statistics.txt - detailed analysis on tags, subfields and relators
- issues.txt - list of issues encountered during the analysis

"""
import io
import xml.etree.ElementTree as ET

from pymarc import parse_xml_to_array
from collections import Counter

with open("./data/schumann.xml") as f:
    marcxml_data = f.read()
    records = parse_xml_to_array(io.StringIO(marcxml_data))

MARC_TAGS = ["100", "700"]

tag_counts = Counter()
record_counts = Counter()
role_counts = Counter()
blank_relator = []

with open("./data/debug_output.txt", "w") as debug_file:
    for i, record in enumerate(records):
        for tag in MARC_TAGS:
            matching_fields = record.get_fields(tag)
            if matching_fields:
                tag_counts[tag] += len(matching_fields)
                record_counts[tag] += 1
                
                debug_file.write(f"Record {i+1}: Found {len(matching_fields)} instances of tag {tag}\n")
                if tag == "700" or tag == "100":
                    for j, field in enumerate(matching_fields):
                        # multiple roles in a single tag 700 or 100 is possible
                        roles = field.get_subfields("4")
                        if roles:
                            # counting different relator types with blank relator handling
                            for r in roles: 
                                if r.strip(): 
                                    role_counts[f"{tag}_{r}"] +=1
                                else:
                                    # counting blank_relator for sanity check
                                    role_counts[f"{tag}_blank_relator"] +=1
                                    # tracking blank relator info
                                    blank_relator_info = {"recordID": i+1, "tag":tag, "tag_position":j}
                                    blank_relator.append(blank_relator_info)
                            tag_counts[f"{tag}_4"] += len(roles)
                            debug_file.write(f"  - {tag} field {j+1}: subfield $4 values: {roles}\n")
                        else:
                            debug_file.write(f"  - {tag} field {j+1}: missing subfield $4\n")
            else:
                debug_file.write(f"Record {i+1}: missing tag {tag}\n")

# Issues documentation
with open("./data/issues.txt", "w") as f:
    f.write(str(blank_relator))
# Statistics documentation
with open("./data/statistics.txt", "w") as f:
    f.write("\n=== Tags Summary ===\n")
    f.write(f"Tag 100: {tag_counts['100']} occurrences across {record_counts['100']} records\n")
    f.write(f"Tag 700: {tag_counts['700']} occurrences across {record_counts['700']} records\n")
    f.write("\n=== Relators Summary ===\n")
    f.write(f"Total Relators:{role_counts.total()}\n")
    f.write(f"Total 700_4 : {tag_counts['700_4']}\n")
    f.write(f"Total 100_4 : {tag_counts['100_4']}\n")
    f.write("\n=== Detailed Relator Counts ===\n")
    for tag in sorted(role_counts.keys()):
        f.write(f"Tag {tag}: {role_counts[tag]}\n")
# CLI output
print("\n=== Final Tag Count Summary ===")
if not tag_counts:
    print("Warning: Counter is empty!")
else:
    for tag in MARC_TAGS:
        print(f"Tag {tag}: total {tag_counts[tag]} occurrences across {record_counts[tag]} records")


print("\n=== Relators Summary ===")
print(f"Total Roles:{role_counts.total()}")
print(f"Total 700_4 : {tag_counts['700_4']}")
print(f"Total 100_4 : {tag_counts['100_4']}")
print("\n=== Detailed Relator Counts ===")
for tag in sorted(role_counts.keys()):
    print(f"Tag {tag}: {role_counts[tag]}")