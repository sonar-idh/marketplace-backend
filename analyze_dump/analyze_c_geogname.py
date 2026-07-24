#!/usr/bin/env python3
"""
Analysiert EAD-XML-Dateien (analog zu den anderen Skripten in diesem Ordner):

Betrachtet werden nur direkte controlaccess/geogname-Kinder des jeweiligen
<c>-Elements (nicht die von verschachtelten Kind-c-Elementen).

- Wie viele <c>-Elemente besitzen mind. ein controlaccess/geogname?
- Wie viele dieser <c>-Elemente besitzen darunter mind. ein geogname mit
  @role="Entstehungsort"?
- Welche @role-Werte kommen auf den geogname-Elementen sonst noch vor
  (Verteilung auf Element-Ebene)?
- Wie viele der geogname-Elemente mit @role="Entstehungsort" haben zudem
  @source="GND"?

Aufruf:
    python3 analyze_c_geogname.py <verzeichnis> [anzahl_prozesse] [ergebnis.pkl]

Beispiel:
    python3 analyze_c_geogname.py /home/p01776/ead2rico/ead20260217/ead 8 result_c_geogname.pkl
"""
import sys
import os
import pickle
from collections import Counter
from multiprocessing import Pool
from lxml import etree

NS = {"e": "urn:isbn:1-931666-22-9"}
NO_ROLE = "<kein @role-Attribut>"


def direct_geognames(c):
    """Direkte geogname-Kinder der direkten controlaccess-Kinder von c
    (steigt nicht in verschachtelte Kind-c-Elemente ab)."""
    result = []
    for ca in c.findall("e:controlaccess", NS):
        result.extend(ca.findall("e:geogname", NS))
    return result


def analyze_file(path):
    fname = os.path.basename(path)
    try:
        tree = etree.parse(path)
    except Exception as e:
        return {"fname": fname, "parse_error": str(e)}

    root = tree.getroot()

    n_c = 0
    n_c_geogname = 0
    n_c_geogname_entstehungsort = 0
    role_counter = Counter()  # ueber alle geogname-Elemente
    n_entstehungsort_elements = 0
    n_entstehungsort_with_gnd = 0

    for c in root.findall(".//e:c", NS):
        n_c += 1
        geognames = direct_geognames(c)
        if not geognames:
            continue
        n_c_geogname += 1

        c_has_entstehungsort = False
        for g in geognames:
            role = g.get("role")
            role_counter[role if role is not None else NO_ROLE] += 1
            if role == "Entstehungsort":
                c_has_entstehungsort = True
                n_entstehungsort_elements += 1
                if g.get("source") == "GND":
                    n_entstehungsort_with_gnd += 1

        if c_has_entstehungsort:
            n_c_geogname_entstehungsort += 1

    return {
        "fname": fname,
        "parse_error": None,
        "n_c": n_c,
        "n_c_geogname": n_c_geogname,
        "n_c_geogname_entstehungsort": n_c_geogname_entstehungsort,
        "role_counter": role_counter,
        "n_entstehungsort_elements": n_entstehungsort_elements,
        "n_entstehungsort_with_gnd": n_entstehungsort_with_gnd,
    }


def main():
    directory = sys.argv[1]
    nworkers = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    out_pickle = sys.argv[3] if len(sys.argv) > 3 else None

    files = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(".xml")]
    files.sort()
    n_files = len(files)
    print(f"Verarbeite {n_files} Dateien mit {nworkers} Prozessen...", file=sys.stderr)

    n_c_total = 0
    n_c_geogname_total = 0
    n_c_geogname_entstehungsort_total = 0
    role_counter = Counter()
    n_entstehungsort_elements_total = 0
    n_entstehungsort_with_gnd_total = 0
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

            n_c_total += res["n_c"]
            n_c_geogname_total += res["n_c_geogname"]
            n_c_geogname_entstehungsort_total += res["n_c_geogname_entstehungsort"]
            role_counter.update(res["role_counter"])
            n_entstehungsort_elements_total += res["n_entstehungsort_elements"]
            n_entstehungsort_with_gnd_total += res["n_entstehungsort_with_gnd"]

    result = {
        "n_files": n_files,
        "n_c_total": n_c_total,
        "n_c_geogname_total": n_c_geogname_total,
        "n_c_geogname_entstehungsort_total": n_c_geogname_entstehungsort_total,
        "role_counter": role_counter,
        "n_entstehungsort_elements_total": n_entstehungsort_elements_total,
        "n_entstehungsort_with_gnd_total": n_entstehungsort_with_gnd_total,
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
    print(f"c-Elemente gesamt:                                       {n_c_total}")
    print(f"  davon mit controlaccess/geogname:                      {n_c_geogname_total} "
          f"({pct(n_c_geogname_total, n_c_total):.1f}%)")
    print(f"    davon mit geogname[@role='Entstehungsort']:          {n_c_geogname_entstehungsort_total} "
          f"({pct(n_c_geogname_entstehungsort_total, n_c_geogname_total):.1f}% der c mit geogname)")
    print()

    total_geognames = sum(role_counter.values())
    print(f"-- @role-Werte der geogname-Elemente (gesamt {total_geognames} Elemente) --")
    for val, cnt in role_counter.most_common():
        print(f"  {cnt:9d}  ({pct(cnt, total_geognames):5.1f}%)  {val!r}")
    print()

    print("-- geogname[@role='Entstehungsort'] --")
    print(f"  Elemente gesamt:                                       {n_entstehungsort_elements_total}")
    print(f"    davon mit @source='GND':                             {n_entstehungsort_with_gnd_total} "
          f"({pct(n_entstehungsort_with_gnd_total, n_entstehungsort_elements_total):.1f}%)")
    print()

    if result["files_with_parse_errors"]:
        print("-- Parse-Fehler (erste 20) --")
        for fname, err in result["files_with_parse_errors"][:20]:
            print(f"  {fname}: {err}")


if __name__ == "__main__":
    main()
