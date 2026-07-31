import json
import os

import requests


def fetch_marc_relators(url="https://id.loc.gov/vocabulary/relators.json"):
    """
    Fetches the MARC relators from the given URL, parses the JSON-LD structure,
    and returns a clean dictionary of relators.
    """
    try:
        headers = {"Accept": "application/json"}
        r = requests.get(url, headers=headers)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

    data = r.json()
    relators = {}

    # Parse the LoC JSON-LD structure
    # Note: sequence 36, 134, 245 don't have authoritative labels
    for item in data:
        if "@id" in item and "http://id.loc.gov/vocabulary/relators/" in item["@id"]:
            # Extract the 3-letter code
            code = item["@id"].split("/")[-1]

            # Extract the authoritative label
            label_key = "http://www.loc.gov/mads/rdf/v1#authoritativeLabel"
            if item.get(label_key):
                label = item[label_key][0].get("@value")
                if label:
                    relators[code] = label

    return relators


if __name__ == "__main__":
    print("Fetching MARC relators...")
    relator_map = fetch_marc_relators()
    if relator_map:
        output_path = "k10plus/data/relators.json"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(relator_map, f, indent=2, ensure_ascii=False, sort_keys=True)
        print(
            f"Successfully fetched {len(relator_map)} relators and saved to {output_path}"
        )
    else:
        print("Failed to fetch relators.")
