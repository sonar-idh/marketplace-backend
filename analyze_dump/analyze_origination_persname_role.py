#!/usr/bin/env python3
"""
Analysiert fuer den Pfad archdesc/did/origination/persname:
- welche Ausprägungen das @role-Attribut hat (und wie häufig)
- wie viele Elemente kein @role-Attribut besitzen
- wie oft das Element gültig GND-referenziert ist (@source="GND" UND
  @authfilenumber vorhanden)

Aufruf:
    python3 analyze_origination_persname_role.py <verzeichnis> [anzahl_prozesse] [ergebnis.pkl]

Beispiel:
    python3 analyze_origination_persname_role.py /home/p01776/ead2rico/ead20260217/ead 8
"""
import sys
import os
import pickle
from collections import Counter
from multiprocessing import Pool
from lxml import etree

NS = {"e": "urn:isbn:1-931666-22-9"}
NO_ROLE = "<kein @role-Attribut>"


def analyze_file(path):
    fname = os.path.basename(path)
    try:
        tree = etree.parse(path)
    except Exception as e:
        return {"fname": fname, "parse_error": str(e)}

    root = tree.getroot()
    n_total = 0
    role_counter = Counter()
    n_gnd_valid = 0

    for el in root.findall("e:archdesc/e:did/e:origination/e:persname", NS):
        n_total += 1

        role = el.get("role")
        role_counter[role if role is not None else NO_ROLE] += 1

        if el.get("source") == "GND" and el.get("authfilenumber") is not None:
            n_gnd_valid += 1

    return {
        "fname": fname,
        "parse_error": None,
        "n_total": n_total,
        "role_counter": role_counter,
        "n_gnd_valid": n_gnd_valid,
    }


def main():
    directory = sys.argv[1]
    nworkers = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    out_pickle = sys.argv[3] if len(sys.argv) > 3 else None

    files = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(".xml")]
    files.sort()
    n_files = len(files)
    print(f"Verarbeite {n_files} Dateien mit {nworkers} Prozessen...", file=sys.stderr)

    n_total = 0
    role_counter = Counter()
    n_gnd_valid = 0
    files_with_parse_errors = []
    files_without_element = []
    files_with_multiple = []  # (fname, anzahl)

    done = 0
    with Pool(nworkers) as pool:
        for res in pool.imap_unordered(analyze_file, files, chunksize=50):
            done += 1
            if done % 5000 == 0:
                print(f"  ... {done}/{n_files} Dateien verarbeitet", file=sys.stderr)

            if res["parse_error"] is not None:
                files_with_parse_errors.append((res["fname"], res["parse_error"]))
                continue

            n_total += res["n_total"]
            role_counter.update(res["role_counter"])
            n_gnd_valid += res["n_gnd_valid"]

            if res["n_total"] == 0:
                files_without_element.append(res["fname"])
            elif res["n_total"] > 1:
                files_with_multiple.append((res["fname"], res["n_total"]))

    n_files_ok = len(files) - len(files_with_parse_errors)
    n_files_exactly_one = n_files_ok - len(files_without_element) - len(files_with_multiple)

    result = {
        "n_files": n_files,
        "n_total": n_total,
        "role_counter": role_counter,
        "n_gnd_valid": n_gnd_valid,
        "files_with_parse_errors": files_with_parse_errors,
        "files_without_element": files_without_element,
        "files_with_multiple": files_with_multiple,
    }

    if out_pickle:
        with open(out_pickle, "wb") as f:
            pickle.dump(result, f)

    n_with_role = n_total - role_counter.get(NO_ROLE, 0)

    print("=" * 70)
    print(f"Dateien gesamt:                                          {result['n_files']}")
    print(f"Parse-Fehler:                                            {len(result['files_with_parse_errors'])}")
    print(f"archdesc/did/origination/persname-Elemente gesamt:      {n_total}")
    print()

    print("-- Vorkommen pro Findbuch --")
    print(f"  Dateien mit genau einem Element:                       {n_files_exactly_one}")
    print(f"  Dateien OHNE das Element:                              {len(files_without_element)}")
    print(f"  Dateien mit mehreren Elementen:                        {len(files_with_multiple)}")
    print()

    print("-- @role-Werte --")
    for val, cnt in role_counter.most_common():
        pct = 100 * cnt / n_total if n_total else 0
        print(f"  {cnt:9d}  ({pct:5.1f}%)  {val!r}")
    print(f"  davon mit @role-Attribut:                              {n_with_role}")
    print(f"  davon OHNE @role-Attribut:                             {role_counter.get(NO_ROLE, 0)}")
    print()

    pct_gnd = 100 * n_gnd_valid / n_total if n_total else 0
    print("-- Gültige GND-Referenzierung (@source='GND' UND @authfilenumber vorhanden) --")
    print(f"  {n_gnd_valid:9d}  ({pct_gnd:5.1f}%)  gültig GND-referenziert")
    print(f"  {n_total - n_gnd_valid:9d}  ({100 - pct_gnd:5.1f}%)  nicht gültig GND-referenziert")

    if result["files_without_element"]:
        print("\n-- Dateien ohne das Element (erste 20) --")
        for fname in result["files_without_element"][:20]:
            print(f"  {fname}")

    if result["files_with_multiple"]:
        print("\n-- Dateien mit mehreren Elementen (erste 20) --")
        for fname, cnt in result["files_with_multiple"][:20]:
            print(f"  {fname}: {cnt}")

    if result["files_with_parse_errors"]:
        print("\n-- Parse-Fehler (erste 20) --")
        for fname, err in result["files_with_parse_errors"][:20]:
            print(f"  {fname}: {err}")


if __name__ == "__main__":
    main()
