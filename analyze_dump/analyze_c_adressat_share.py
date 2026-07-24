#!/usr/bin/env python3
"""
Zaehlt, wie viele <c>-Elemente es insgesamt im Dump gibt und wie viel Prozent
davon ein direktes
    e:controlaccess/e:persname[@role='Adressat'] | e:controlaccess/e:corpname[@role='Adressat']
besitzen (nur direkte controlaccess-Kinder des jeweiligen <c>, nicht von
verschachtelten Kind-c-Elementen).

Aufruf:
    python3 analyze_c_adressat_share.py <verzeichnis> [anzahl_prozesse] [ergebnis.pkl]

Beispiel:
    python3 analyze_c_adressat_share.py /home/p01776/ead2rico/ead20260217/ead 8 result_c_adressat_share.pkl
"""
import sys
import os
import pickle
from multiprocessing import Pool
from lxml import etree

NS = {"e": "urn:isbn:1-931666-22-9"}


def has_direct_adressat(c):
    """Prueft, ob c einen direkten controlaccess-Kind-Container hat, der ein
    persname- oder corpname-Element mit @role='Adressat' als direktes Kind
    enthaelt."""
    for ca in c.findall("e:controlaccess", NS):
        for tag in ("persname", "corpname"):
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

    n_c = 0
    n_c_adressat = 0

    for c in root.findall(".//e:c", NS):
        n_c += 1
        if has_direct_adressat(c):
            n_c_adressat += 1

    return {
        "fname": fname,
        "parse_error": None,
        "n_c": n_c,
        "n_c_adressat": n_c_adressat,
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
    n_c_adressat_total = 0
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
            n_c_adressat_total += res["n_c_adressat"]

    result = {
        "n_files": n_files,
        "n_c_total": n_c_total,
        "n_c_adressat_total": n_c_adressat_total,
        "files_with_parse_errors": files_with_parse_errors,
    }

    if out_pickle:
        with open(out_pickle, "wb") as f:
            pickle.dump(result, f)

    pct = 100 * n_c_adressat_total / n_c_total if n_c_total else 0

    print("=" * 70)
    print(f"Dateien gesamt:                                          {result['n_files']}")
    print(f"Parse-Fehler:                                            {len(result['files_with_parse_errors'])}")
    print()
    print(f"c-Elemente gesamt:                                       {n_c_total}")
    print(f"  davon mit controlaccess/persname|corpname[@role=Adressat]: {n_c_adressat_total} "
          f"({pct:.1f}%)")
    print()

    if result["files_with_parse_errors"]:
        print("-- Parse-Fehler (erste 20) --")
        for fname, err in result["files_with_parse_errors"][:20]:
            print(f"  {fname}: {err}")


if __name__ == "__main__":
    main()
