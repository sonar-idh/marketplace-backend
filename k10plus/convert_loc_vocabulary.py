"""
This script converts a Library of Congress controlled vocabulary (JSON-LD) into a
flat code -> label map.

Usage:
    uv run python k10plus/convert_loc_vocabulary.py countries.json data/loc_countries.json

Input:
    - JSON-LD download of a vocabulary from id.loc.gov, e.g.
      https://id.loc.gov/vocabulary/countries.json
      https://id.loc.gov/vocabulary/languages.json

Output:
    - JSON file mapping each MARC code to its authoritative label, sorted by code,
      e.g. {"gw": "Germany", "xxk": "United Kingdom"}.

"""

import json
import sys
from pathlib import Path

MADS = "http://www.loc.gov/mads/rdf/v1#"


def convert_vocabulary(input_path: str | Path, output_path: str | Path) -> int:
    with open(input_path, "r", encoding="utf-8") as f:
        entries = json.load(f)

    code_map = {}
    for entry in entries:
        if f"{MADS}code" not in entry:
            continue
        code = entry[f"{MADS}code"][0]["@value"]
        label = entry.get(f"{MADS}authoritativeLabel", [{}])[0].get("@value")
        if label:
            code_map[code] = label

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dict(sorted(code_map.items())), f, indent=2, ensure_ascii=False)
        f.write("\n")
    return len(code_map)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(f"Usage: {sys.argv[0]} <input.json> <output.json>")
    count = convert_vocabulary(sys.argv[1], sys.argv[2])
    print(f"Wrote {count} codes to {sys.argv[2]}")
