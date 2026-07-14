#!/usr/bin/env python3
"""
Zaehlt, welche Werte das Element <genreform> im gesamten Corpus hat und
wie oft jeder Wert vorkommt (unabhaengig von Record-/c-Grenzen).

Aufruf:
    python3 analyze_genreform_values.py <verzeichnis> [anzahl_prozesse] [ergebnis.pkl]

Beispiel:
    python3 analyze_genreform_values.py /home/p01776/ead2rico/ead20260217/ead 8 result_genreform.pkl

Ausgabe:
    - Zusammenfassung auf stdout (Top-Werte)
    - genreform_werte.tsv im aktuellen Verzeichnis: alle (Wert, Anzahl),
      absteigend sortiert, tab-getrennt
"""
import sys
import os
import csv
import pickle
from collections import Counter
from multiprocessing import Pool
from lxml import etree

NSURI = "urn:isbn:1-931666-22-9"


def analyze_file(path):
    fname = os.path.basename(path)
    try:
        tree = etree.parse(path)
    except Exception as e:
        return {"fname": fname, "parse_error": str(e)}

    root = tree.getroot()
    value_counter = Counter()
    for el in root.iter(f"{{{NSURI}}}genreform"):
        text = (el.text or "").strip()
        value_counter[text] += 1

    return {
        "fname": fname,
        "parse_error": None,
        "value_counter": value_counter,
    }


def main():
    directory = sys.argv[1]
    nworkers = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    out_pickle = sys.argv[3] if len(sys.argv) > 3 else None

    files = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(".xml")]
    files.sort()
    n_files = len(files)
    print(f"Verarbeite {n_files} Dateien mit {nworkers} Prozessen...", file=sys.stderr)

    value_counter = Counter()
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

            value_counter.update(res["value_counter"])

    result = {
        "n_files": n_files,
        "value_counter": value_counter,
        "files_with_parse_errors": files_with_parse_errors,
    }

    if out_pickle:
        with open(out_pickle, "wb") as f:
            pickle.dump(result, f)

    tsv_path = "genreform_werte.tsv"
    with open(tsv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["wert", "haeufigkeit"])
        for val, cnt in value_counter.most_common():
            writer.writerow([val, cnt])

    total = sum(value_counter.values())
    print("=" * 70)
    print(f"Dateien gesamt:              {result['n_files']}")
    print(f"Parse-Fehler:                {len(result['files_with_parse_errors'])}")
    print(f"genreform-Elemente gesamt:   {total}")
    print(f"distinkte genreform-Werte:   {len(value_counter)}")
    print()

    print("-- Top 50 genreform-Werte --")
    for val, cnt in value_counter.most_common(50):
        pct = 100 * cnt / total if total else 0
        print(f"  {cnt:9d}  ({pct:5.1f}%)  {val!r}")
    print(f"\nVollstaendige Liste geschrieben nach: {tsv_path}")

    if result["files_with_parse_errors"]:
        print("\n-- Parse-Fehler (erste 20) --")
        for fname, err in result["files_with_parse_errors"][:20]:
            print(f"  {fname}: {err}")


if __name__ == "__main__":
    main()
