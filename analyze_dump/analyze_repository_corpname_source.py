#!/usr/bin/env python3
"""
Analysiert fuer den Pfad archdesc/did/repository/corpname:
- ob das Element in jedem Findbuch genau einmal vorkommt
  (bzw. wie oft es fehlt oder mehrfach vorkommt)
- ob es ein @role-Attribut hat (und mit welchen Ausprägungen)
- ob es ein @source-Attribut hat (und mit welchen Ausprägungen)
- ob es ein @authfilenumber-Attribut hat

Aufruf:
    python3 analyze_repository_corpname_source.py <verzeichnis> [anzahl_prozesse] [ergebnis.pkl]

Beispiel:
    python3 analyze_repository_corpname_source.py /home/p01776/ead2rico/ead20260217/ead 8 result_repo_corpname.pkl
"""
import sys
import os
import pickle
from collections import Counter
from multiprocessing import Pool
from lxml import etree

NS = {"e": "urn:isbn:1-931666-22-9"}
NO_SOURCE = "<kein @source-Attribut>"
NO_ROLE = "<kein @role-Attribut>"


def analyze_file(path):
    fname = os.path.basename(path)
    try:
        tree = etree.parse(path)
    except Exception as e:
        return {"fname": fname, "parse_error": str(e)}

    root = tree.getroot()
    n_total = 0
    source_counter = Counter()
    role_counter = Counter()
    n_with_authfilenumber = 0
    n_without_authfilenumber = 0

    for el in root.findall("e:archdesc/e:did/e:repository/e:corpname", NS):
        n_total += 1

        src = el.get("source")
        source_counter[src if src is not None else NO_SOURCE] += 1

        role = el.get("role")
        role_counter[role if role is not None else NO_ROLE] += 1

        if el.get("authfilenumber") is not None:
            n_with_authfilenumber += 1
        else:
            n_without_authfilenumber += 1

    return {
        "fname": fname,
        "parse_error": None,
        "n_total": n_total,
        "source_counter": source_counter,
        "role_counter": role_counter,
        "n_with_authfilenumber": n_with_authfilenumber,
        "n_without_authfilenumber": n_without_authfilenumber,
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
    source_counter = Counter()
    role_counter = Counter()
    n_with_authfilenumber = 0
    n_without_authfilenumber = 0
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
            source_counter.update(res["source_counter"])
            role_counter.update(res["role_counter"])
            n_with_authfilenumber += res["n_with_authfilenumber"]
            n_without_authfilenumber += res["n_without_authfilenumber"]

            if res["n_total"] == 0:
                files_without_element.append(res["fname"])
            elif res["n_total"] > 1:
                files_with_multiple.append((res["fname"], res["n_total"]))

    n_files_ok = len(files) - len(files_with_parse_errors)
    n_files_exactly_one = n_files_ok - len(files_without_element) - len(files_with_multiple)

    result = {
        "n_files": n_files,
        "n_total": n_total,
        "source_counter": source_counter,
        "role_counter": role_counter,
        "n_with_authfilenumber": n_with_authfilenumber,
        "n_without_authfilenumber": n_without_authfilenumber,
        "files_with_parse_errors": files_with_parse_errors,
        "files_without_element": files_without_element,
        "files_with_multiple": files_with_multiple,
    }

    if out_pickle:
        with open(out_pickle, "wb") as f:
            pickle.dump(result, f)

    n_with_source = n_total - source_counter.get(NO_SOURCE, 0)
    n_with_role = n_total - role_counter.get(NO_ROLE, 0)

    print("=" * 70)
    print(f"Dateien gesamt:                                          {result['n_files']}")
    print(f"Parse-Fehler:                                            {len(result['files_with_parse_errors'])}")
    print(f"archdesc/did/repository/corpname-Elemente gesamt:       {n_total}")
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

    print("-- @source-Werte --")
    for val, cnt in source_counter.most_common():
        pct = 100 * cnt / n_total if n_total else 0
        print(f"  {cnt:9d}  ({pct:5.1f}%)  {val!r}")
    print(f"  davon mit @source-Attribut:                            {n_with_source}")
    print(f"  davon OHNE @source-Attribut:                           {source_counter.get(NO_SOURCE, 0)}")
    print()

    print("-- @authfilenumber-Attribut --")
    print(f"  davon mit @authfilenumber-Attribut:                    {n_with_authfilenumber}")
    print(f"  davon OHNE @authfilenumber-Attribut:                   {n_without_authfilenumber}")

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
