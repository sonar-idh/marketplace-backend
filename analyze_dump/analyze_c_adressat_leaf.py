#!/usr/bin/env python3
"""
Analysiert, wie oft ein <c>-Element mit controlaccess/persname/@role="Adressat"
bzw. controlaccess/corpname/@role="Adressat" KEIN Blatt-Element ist, also noch
weitere <c>-Elemente als direkte Kinder enthaelt (Verzeichnungseinheit mit
Adressatenangabe, die selbst wieder Unterverzeichnungseinheiten hat).

Betrachtet werden nur die direkten controlaccess-Kinder des jeweiligen
<c>-Elements (nicht die von verschachtelten Kind-c-Elementen).

Aufruf:
    python3 analyze_c_adressat_leaf.py <verzeichnis> [anzahl_prozesse] [ergebnis.pkl]

Beispiel:
    python3 analyze_c_adressat_leaf.py /home/p01776/ead2rico/ead20260217/ead 8 result_c_adressat_leaf.pkl
"""
import sys
import os
import pickle
from collections import Counter
from multiprocessing import Pool
from lxml import etree

NS = {"e": "urn:isbn:1-931666-22-9"}
MAX_EXAMPLE_FILES = 50


def has_direct_adressat(c, tag):
    """Prueft, ob c einen direkten controlaccess-Kind-Container hat, der ein
    <tag @role="Adressat">-Element als direktes Kind enthaelt."""
    for ca in c.findall("e:controlaccess", NS):
        for el in ca.findall(f"e:{tag}", NS):
            if el.get("role") == "Adressat":
                return True
    return False


def analyze_file(path):
    fname = os.path.basename(path)
    try:
        tree = etree.parse(path)
    except Exception as e:
        return {"fname": fname, "parse_error": str(e)}

    root = tree.getroot()

    n_persname_adressat = 0
    n_persname_adressat_nonleaf = 0
    n_corpname_adressat = 0
    n_corpname_adressat_nonleaf = 0
    n_either_adressat = 0
    n_either_adressat_nonleaf = 0
    nonleaf_level_counter = Counter()
    nonleaf_examples = []  # (fname, level, n_child_c, has_persname, has_corpname)

    for c in root.findall(".//e:c", NS):
        has_pers = has_direct_adressat(c, "persname")
        has_corp = has_direct_adressat(c, "corpname")
        if not (has_pers or has_corp):
            continue

        child_c = c.findall("e:c", NS)
        is_nonleaf = bool(child_c)

        if has_pers:
            n_persname_adressat += 1
            if is_nonleaf:
                n_persname_adressat_nonleaf += 1
        if has_corp:
            n_corpname_adressat += 1
            if is_nonleaf:
                n_corpname_adressat_nonleaf += 1

        n_either_adressat += 1
        if is_nonleaf:
            n_either_adressat_nonleaf += 1
            nonleaf_level_counter[c.get("level", "<kein @level>")] += 1
            if len(nonleaf_examples) < MAX_EXAMPLE_FILES:
                nonleaf_examples.append(
                    (fname, c.get("level", "<kein @level>"), len(child_c), has_pers, has_corp)
                )

    return {
        "fname": fname,
        "parse_error": None,
        "n_persname_adressat": n_persname_adressat,
        "n_persname_adressat_nonleaf": n_persname_adressat_nonleaf,
        "n_corpname_adressat": n_corpname_adressat,
        "n_corpname_adressat_nonleaf": n_corpname_adressat_nonleaf,
        "n_either_adressat": n_either_adressat,
        "n_either_adressat_nonleaf": n_either_adressat_nonleaf,
        "nonleaf_level_counter": nonleaf_level_counter,
        "nonleaf_examples": nonleaf_examples,
    }


def main():
    directory = sys.argv[1]
    nworkers = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    out_pickle = sys.argv[3] if len(sys.argv) > 3 else None

    files = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(".xml")]
    files.sort()
    n_files = len(files)
    print(f"Verarbeite {n_files} Dateien mit {nworkers} Prozessen...", file=sys.stderr)

    n_persname_adressat = 0
    n_persname_adressat_nonleaf = 0
    n_corpname_adressat = 0
    n_corpname_adressat_nonleaf = 0
    n_either_adressat = 0
    n_either_adressat_nonleaf = 0
    nonleaf_level_counter = Counter()
    nonleaf_examples = []
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

            n_persname_adressat += res["n_persname_adressat"]
            n_persname_adressat_nonleaf += res["n_persname_adressat_nonleaf"]
            n_corpname_adressat += res["n_corpname_adressat"]
            n_corpname_adressat_nonleaf += res["n_corpname_adressat_nonleaf"]
            n_either_adressat += res["n_either_adressat"]
            n_either_adressat_nonleaf += res["n_either_adressat_nonleaf"]
            nonleaf_level_counter.update(res["nonleaf_level_counter"])
            if len(nonleaf_examples) < MAX_EXAMPLE_FILES:
                nonleaf_examples.extend(res["nonleaf_examples"])

    result = {
        "n_files": n_files,
        "n_persname_adressat": n_persname_adressat,
        "n_persname_adressat_nonleaf": n_persname_adressat_nonleaf,
        "n_corpname_adressat": n_corpname_adressat,
        "n_corpname_adressat_nonleaf": n_corpname_adressat_nonleaf,
        "n_either_adressat": n_either_adressat,
        "n_either_adressat_nonleaf": n_either_adressat_nonleaf,
        "nonleaf_level_counter": nonleaf_level_counter,
        "nonleaf_examples": nonleaf_examples,
        "files_with_parse_errors": files_with_parse_errors,
    }

    if out_pickle:
        with open(out_pickle, "wb") as f:
            pickle.dump(result, f)

    def pct(part, total):
        return 100 * part / total if total else 0

    print("=" * 70)
    print(f"Dateien gesamt:                                          {result['n_files']}")
    print(f"Parse-Fehler:                                            {len(result['files_with_parse_errors'])}")
    print()

    print("-- controlaccess/persname[@role=Adressat] --")
    print(f"  c-Elemente mit diesem Element:                         {n_persname_adressat}")
    print(f"    davon KEIN Blatt (enthalten weitere c-Elemente):     {n_persname_adressat_nonleaf} "
          f"({pct(n_persname_adressat_nonleaf, n_persname_adressat):.1f}%)")
    print()

    print("-- controlaccess/corpname[@role=Adressat] --")
    print(f"  c-Elemente mit diesem Element:                         {n_corpname_adressat}")
    print(f"    davon KEIN Blatt (enthalten weitere c-Elemente):     {n_corpname_adressat_nonleaf} "
          f"({pct(n_corpname_adressat_nonleaf, n_corpname_adressat):.1f}%)")
    print()

    print("-- persname ODER corpname mit @role=Adressat (Vereinigung) --")
    print(f"  c-Elemente mit mind. einem der beiden:                 {n_either_adressat}")
    print(f"    davon KEIN Blatt (enthalten weitere c-Elemente):     {n_either_adressat_nonleaf} "
          f"({pct(n_either_adressat_nonleaf, n_either_adressat):.1f}%)")
    print()

    if result["nonleaf_level_counter"]:
        print("-- @level der Nicht-Blatt-c-Elemente mit Adressat --")
        for val, cnt in result["nonleaf_level_counter"].most_common():
            print(f"  {cnt:9d}  {val!r}")
        print()

    if result["nonleaf_examples"]:
        print(f"-- Beispiele Nicht-Blatt-c mit Adressat (erste 20 von {len(result['nonleaf_examples'])}) --")
        for fname, level, n_child_c, has_pers, has_corp in result["nonleaf_examples"][:20]:
            tags = []
            if has_pers:
                tags.append("persname")
            if has_corp:
                tags.append("corpname")
            print(f"  {fname}  level={level!r}  #Kind-c={n_child_c}  ueber: {', '.join(tags)}")
        print()

    if result["files_with_parse_errors"]:
        print("-- Parse-Fehler (erste 20) --")
        for fname, err in result["files_with_parse_errors"][:20]:
            print(f"  {fname}: {err}")


if __name__ == "__main__":
    main()
