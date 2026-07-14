#!/usr/bin/env python3
"""
Zaehlt pro distinktem <genreform>-Textwert im gesamten Corpus, wie oft
dieser Wert insgesamt vorkommt und bei wie vielen dieser Vorkommen ein
Attribut @source gesetzt ist.

Aufruf:
    python3 analyze_genreform_values_source.py <verzeichnis> [anzahl_prozesse] [ergebnis.pkl]

Beispiel:
    python3 analyze_genreform_values_source.py /home/p01776/ead2rico/ead20260217/ead 8 result_genreform_values_source.pkl

Ausgabe:
    - Zusammenfassung auf stdout (Top-Werte mit @source-Anteil)
    - genreform_werte_source.tsv im aktuellen Verzeichnis: alle
      (Wert, Gesamtanzahl, Anzahl mit @source, Anteil mit @source),
      absteigend nach Gesamtanzahl sortiert, tab-getrennt
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
    total_counter = Counter()
    with_source_counter = Counter()

    for el in root.iter(f"{{{NSURI}}}genreform"):
        text = (el.text or "").strip()
        total_counter[text] += 1
        if el.get("source") is not None:
            with_source_counter[text] += 1

    return {
        "fname": fname,
        "parse_error": None,
        "total_counter": total_counter,
        "with_source_counter": with_source_counter,
    }


def main():
    directory = sys.argv[1]
    nworkers = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    out_pickle = sys.argv[3] if len(sys.argv) > 3 else None

    files = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(".xml")]
    files.sort()
    n_files = len(files)
    print(f"Verarbeite {n_files} Dateien mit {nworkers} Prozessen...", file=sys.stderr)

    total_counter = Counter()
    with_source_counter = Counter()
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

            total_counter.update(res["total_counter"])
            with_source_counter.update(res["with_source_counter"])

    result = {
        "n_files": n_files,
        "total_counter": total_counter,
        "with_source_counter": with_source_counter,
        "files_with_parse_errors": files_with_parse_errors,
    }

    if out_pickle:
        with open(out_pickle, "wb") as f:
            pickle.dump(result, f)

    tsv_path = "genreform_werte_source.tsv"
    with open(tsv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["wert", "gesamt", "mit_source", "anteil_mit_source_pct"])
        for val, cnt in total_counter.most_common():
            wsrc = with_source_counter.get(val, 0)
            pct = 100 * wsrc / cnt if cnt else 0
            writer.writerow([val, cnt, wsrc, f"{pct:.2f}"])

    total = sum(total_counter.values())
    total_with_source = sum(with_source_counter.values())
    print("=" * 70)
    print(f"Dateien gesamt:              {n_files}")
    print(f"Parse-Fehler:                {len(files_with_parse_errors)}")
    print(f"genreform-Elemente gesamt:   {total}")
    print(f"davon mit @source:           {total_with_source}")
    print(f"distinkte genreform-Werte:   {len(total_counter)}")
    print()

    print("-- Top 50 genreform-Werte (mit Anteil @source) --")
    for val, cnt in total_counter.most_common(50):
        wsrc = with_source_counter.get(val, 0)
        pct = 100 * wsrc / cnt if cnt else 0
        print(f"  {cnt:9d}  mit @source: {wsrc:9d} ({pct:5.1f}%)  {val!r}")
    print(f"\nVollstaendige Liste geschrieben nach: {tsv_path}")

    if files_with_parse_errors:
        print("\n-- Parse-Fehler (erste 20) --")
        for fname, err in files_with_parse_errors[:20]:
            print(f"  {fname}: {err}")


if __name__ == "__main__":
    main()
