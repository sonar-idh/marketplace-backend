#!/usr/bin/env python3
"""
Findet ALLE <persname>- und <corpname>-Elemente mit @source="KPE" im gesamten
Corpus und zaehlt, wie oft jeder Textwert vorkommt.

Aufruf:
    python3 analyze_kpe_names.py <verzeichnis> [anzahl_prozesse]

Ausgabe:
    - kpe_persname_werte.tsv, kpe_corpname_werte.tsv im aktuellen Verzeichnis
"""
import sys
import os
import csv
from collections import Counter
from multiprocessing import Pool
from lxml import etree

NSURI = "urn:isbn:1-931666-22-9"
TAGS = ("persname", "corpname")


def analyze_file(path):
    try:
        tree = etree.parse(path)
    except Exception as e:
        return {"parse_error": str(e)}

    root = tree.getroot()
    value_counters = {tag: Counter() for tag in TAGS}

    for tag in TAGS:
        for el in root.iter(f"{{{NSURI}}}{tag}"):
            if el.get("source") == "KPE":
                text = (el.text or "").strip()
                value_counters[tag][text] += 1

    return {"parse_error": None, "value_counters": value_counters}


def main():
    directory = sys.argv[1]
    nworkers = int(sys.argv[2]) if len(sys.argv) > 2 else 8

    files = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(".xml")]
    files.sort()
    n_files = len(files)
    print(f"Verarbeite {n_files} Dateien mit {nworkers} Prozessen...", file=sys.stderr)

    value_counters = {tag: Counter() for tag in TAGS}
    errors = 0

    done = 0
    with Pool(nworkers) as pool:
        for res in pool.imap_unordered(analyze_file, files, chunksize=50):
            done += 1
            if done % 10000 == 0:
                print(f"  ... {done}/{n_files}", file=sys.stderr)
            if res["parse_error"] is not None:
                errors += 1
                continue
            for tag in TAGS:
                value_counters[tag].update(res["value_counters"][tag])

    print(f"Parse-Fehler: {errors}")

    for tag in TAGS:
        tsv_path = f"kpe_{tag}_werte.tsv"
        with open(tsv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerow(["wert", "haeufigkeit"])
            for val, cnt in value_counters[tag].most_common():
                writer.writerow([val, cnt])
        total = sum(value_counters[tag].values())
        print(f"<{tag}> mit source=KPE: {total} gesamt, {len(value_counters[tag])} distinkte Werte -> {tsv_path}")


if __name__ == "__main__":
    main()
