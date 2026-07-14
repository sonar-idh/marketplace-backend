#!/usr/bin/env python3
"""
Analysiert EAD-XML-Dateien:
- Zaehlt, in wievielen Dateien <archdesc> das Attribut level="collection" hat
  (und zeigt zur Kontrolle auch andere archdesc/@level-Werte, falls vorhanden)
- Zaehlt ueber alle <c>-Elemente im Corpus, wie oft jeder @level-Wert vorkommt
  (collection, fonds, class, file, item, ...)

Aufruf:
    python3 analyze_level.py <verzeichnis> [anzahl_prozesse] [ergebnis.pkl]

Beispiel:
    python3 analyze_level.py /home/p01776/ead2rico/ead20260217/ead 8 result_level.pkl
"""
import sys
import os
import pickle
from collections import Counter
from multiprocessing import Pool
from lxml import etree

NS = {"e": "urn:isbn:1-931666-22-9"}


def analyze_file(path):
    fname = os.path.basename(path)
    try:
        tree = etree.parse(path)
    except Exception as e:
        return {"fname": fname, "parse_error": str(e)}

    root = tree.getroot()

    archdesc = root.find("e:archdesc", NS)
    archdesc_level = archdesc.get("level", "<kein @level>") if archdesc is not None else "<kein archdesc>"

    c_level_counter = Counter()
    for c in root.findall(".//e:c", NS):
        c_level_counter[c.get("level", "<kein @level>")] += 1

    return {
        "fname": fname,
        "parse_error": None,
        "archdesc_level": archdesc_level,
        "c_level_counter": c_level_counter,
    }


def main():
    directory = sys.argv[1]
    nworkers = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    out_pickle = sys.argv[3] if len(sys.argv) > 3 else None

    files = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(".xml")]
    files.sort()
    n_files = len(files)
    print(f"Verarbeite {n_files} Dateien mit {nworkers} Prozessen...", file=sys.stderr)

    archdesc_level_counter = Counter()  # archdesc/@level-Wert -> Anzahl Dateien
    c_level_counter = Counter()  # c/@level-Wert -> Anzahl Elemente gesamt
    files_with_parse_errors = []

    done = 0
    with Pool(nworkers) as pool:
        for res in pool.imap_unordered(analyze_file, files, chunksize=50):
            done += 1
            if done % 5000 == 0:
                print(f"  ... {done}/{n_files} Dateien verarbeitet", file=sys.stderr)

            if res["parse_error"] is not None:
                files_with_parse_errors.append((res["fname"], res["parse_error"]))
                continue

            archdesc_level_counter[res["archdesc_level"]] += 1
            c_level_counter.update(res["c_level_counter"])

    result = {
        "n_files": n_files,
        "archdesc_level_counter": archdesc_level_counter,
        "c_level_counter": c_level_counter,
        "files_with_parse_errors": files_with_parse_errors,
    }

    if out_pickle:
        with open(out_pickle, "wb") as f:
            pickle.dump(result, f)

    print("=" * 70)
    print(f"Dateien gesamt:      {result['n_files']}")
    print(f"Parse-Fehler:        {len(result['files_with_parse_errors'])}")
    print()

    print("-- archdesc/@level (Anzahl Dateien) --")
    for val, cnt in archdesc_level_counter.most_common():
        marker = "  <-- gefragter Wert" if val == "collection" else ""
        print(f"  {cnt:9d}  {val!r}{marker}")
    print(f"\nDateien mit archdesc/@level='collection': {archdesc_level_counter.get('collection', 0)}")
    print()

    print("-- c/@level (Anzahl Elemente gesamt) --")
    for val, cnt in c_level_counter.most_common():
        print(f"  {cnt:9d}  {val!r}")

    if result["files_with_parse_errors"]:
        print("\n-- Parse-Fehler (erste 20) --")
        for fname, err in result["files_with_parse_errors"][:20]:
            print(f"  {fname}: {err}")


if __name__ == "__main__":
    main()
