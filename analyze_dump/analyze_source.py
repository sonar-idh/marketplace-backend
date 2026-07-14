#!/usr/bin/env python3
"""
Analysiert EAD-XML-Dateien (analog zu den anderen Skripten in diesem Ordner):
- Findet ALLE <persname>-, <corpname>- und <geogname>-Elemente im gesamten
  Corpus (unabhaengig von Record-Grenzen, also auch verschachtelt in c/c/c/...)
- Zaehlt pro Elementtyp, wie oft welcher @source-Wert vorkommt
  (inkl. der Faelle, in denen gar kein @source-Attribut gesetzt ist)

Aufruf:
    python3 analyze_source.py <verzeichnis> [anzahl_prozesse] [ergebnis.pkl]

Beispiel:
    python3 analyze_source.py /home/p01776/ead2rico/ead20260217/ead 8 result_source.pkl
"""
import sys
import os
import pickle
from collections import Counter
from multiprocessing import Pool
from lxml import etree

NSURI = "urn:isbn:1-931666-22-9"
TAGS = ("persname", "corpname", "geogname")
NO_SOURCE = "<kein @source-Attribut>"


def analyze_file(path):
    fname = os.path.basename(path)
    try:
        tree = etree.parse(path)
    except Exception as e:
        return {"fname": fname, "parse_error": str(e)}

    root = tree.getroot()

    tag_counter = Counter()  # tag -> Gesamtanzahl
    source_counter = Counter()  # (tag, source_wert) -> Anzahl

    for tag in TAGS:
        for el in root.iter(f"{{{NSURI}}}{tag}"):
            tag_counter[tag] += 1
            src = el.get("source")
            source_counter[(tag, src if src is not None else NO_SOURCE)] += 1

    return {
        "fname": fname,
        "parse_error": None,
        "tag_counter": tag_counter,
        "source_counter": source_counter,
    }


def main():
    directory = sys.argv[1]
    nworkers = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    out_pickle = sys.argv[3] if len(sys.argv) > 3 else None

    files = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(".xml")]
    files.sort()
    n_files = len(files)
    print(f"Verarbeite {n_files} Dateien mit {nworkers} Prozessen...", file=sys.stderr)

    tag_counter = Counter()
    source_counter = Counter()
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

            tag_counter.update(res["tag_counter"])
            source_counter.update(res["source_counter"])

    result = {
        "n_files": n_files,
        "tag_counter": tag_counter,
        "source_counter": source_counter,
        "files_with_parse_errors": files_with_parse_errors,
    }

    if out_pickle:
        with open(out_pickle, "wb") as f:
            pickle.dump(result, f)

    print("=" * 70)
    print(f"Dateien gesamt:      {result['n_files']}")
    print(f"Parse-Fehler:        {len(result['files_with_parse_errors'])}")
    print()

    for tag in TAGS:
        total = tag_counter[tag]
        print(f"-- <{tag}>: {total} Elemente gesamt --")
        per_tag_sources = {
            src: cnt for (t, src), cnt in source_counter.items() if t == tag
        }
        for src, cnt in sorted(per_tag_sources.items(), key=lambda kv: -kv[1]):
            pct = 100 * cnt / total if total else 0
            marker = "  <-- GND" if src == "GND" else ""
            print(f"    {cnt:9d}  ({pct:5.1f}%)  {src!r}{marker}")
        print()

    if result["files_with_parse_errors"]:
        print("-- Parse-Fehler (erste 20) --")
        for fname, err in result["files_with_parse_errors"][:20]:
            print(f"  {fname}: {err}")


if __name__ == "__main__":
    main()
