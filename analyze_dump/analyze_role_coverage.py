#!/usr/bin/env python3
"""
Zaehlt fuer persname, corpname, geogname (nach lokalem Elementnamen, unabhaengig
von Namespace-Deklaration) wie oft sie insgesamt vorkommen und wie oft davon
mit einem @role-Attribut.

Aufruf:
    python3 analyze_role_coverage.py <verzeichnis> [anzahl_prozesse]
"""
import sys
import os
from collections import Counter
from multiprocessing import Pool
from lxml import etree

TAGS = ("persname", "corpname", "geogname")


def analyze_file(path):
    try:
        tree = etree.parse(path)
    except Exception as e:
        return {"parse_error": str(e)}

    total = Counter()
    with_role = Counter()

    for elem in tree.iter():
        if not isinstance(elem.tag, str):
            continue
        local = etree.QName(elem).localname
        if local in TAGS:
            total[local] += 1
            if elem.get("role") is not None:
                with_role[local] += 1

    return {"parse_error": None, "total": total, "with_role": with_role}


def main():
    directory = sys.argv[1]
    nworkers = int(sys.argv[2]) if len(sys.argv) > 2 else 8

    files = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(".xml")]
    files.sort()
    n_files = len(files)
    print(f"Verarbeite {n_files} Dateien mit {nworkers} Prozessen...", file=sys.stderr)

    total = Counter()
    with_role = Counter()
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
            total.update(res["total"])
            with_role.update(res["with_role"])

    print(f"Parse-Fehler: {errors}")
    print(f"{'Element':10s} {'gesamt':>12s} {'mit @role':>12s} {'ohne @role':>12s}")
    for tag in TAGS:
        t = total[tag]
        r = with_role[tag]
        print(f"{tag:10s} {t:12d} {r:12d} {t - r:12d}")


if __name__ == "__main__":
    main()
