#!/usr/bin/env python3
"""
Analysiert EAD-XML-Dateien (analog zu den anderen Skripten in diesem Ordner):

1) Zaehlt, wie viele <c>-Elemente es insgesamt im Dump gibt und wie viel
   Prozent davon ein direktes controlaccess/genreform-Kind mit Textwert
   "Brief" besitzen (nur direkte controlaccess-Kinder des jeweiligen <c>,
   nicht von verschachtelten Kind-c-Elementen).

2) Fuer diese "Brief"-c-Elemente: wie viele der Verfasser (persname/corpname
   mit @role="Verfasser") bzw. Adressaten (persname/corpname mit
   @role="Adressat") KEINE gueltige GND-Referenz haben, d.h.
   @source != "GND" oder kein @authfilenumber gesetzt ist.

Aufruf:
    python3 analyze_c_brief_genreform.py <verzeichnis> [anzahl_prozesse] [ergebnis.pkl]

Beispiel:
    python3 analyze_c_brief_genreform.py /home/p01776/ead2rico/ead20260217/ead 8 result_c_brief.pkl
"""
import sys
import os
import pickle
from multiprocessing import Pool
from lxml import etree

NS = {"e": "urn:isbn:1-931666-22-9"}


def direct_controlaccess_children(c, tag):
    """Direkte Kinder <tag> der direkten <controlaccess>-Kinder von c
    (steigt nicht in verschachtelte Kind-c-Elemente ab)."""
    result = []
    for ca in c.findall("e:controlaccess", NS):
        result.extend(ca.findall(f"e:{tag}", NS))
    return result


def is_brief(c):
    for genre in direct_controlaccess_children(c, "genreform"):
        if (genre.text or "").strip() == "Brief":
            return True
    return False


def has_no_valid_gnd(el):
    return el.get("source") != "GND" or not el.get("authfilenumber")


def analyze_file(path):
    fname = os.path.basename(path)
    try:
        tree = etree.parse(path)
    except Exception as e:
        return {"fname": fname, "parse_error": str(e)}

    root = tree.getroot()

    n_c = 0
    n_c_brief = 0
    n_verfasser = 0
    n_verfasser_no_gnd = 0
    n_adressat = 0
    n_adressat_no_gnd = 0

    for c in root.findall(".//e:c", NS):
        n_c += 1
        if not is_brief(c):
            continue
        n_c_brief += 1

        for tag in ("persname", "corpname"):
            for el in direct_controlaccess_children(c, tag):
                role = el.get("role")
                if role == "Verfasser":
                    n_verfasser += 1
                    if has_no_valid_gnd(el):
                        n_verfasser_no_gnd += 1
                elif role == "Adressat":
                    n_adressat += 1
                    if has_no_valid_gnd(el):
                        n_adressat_no_gnd += 1

    return {
        "fname": fname,
        "parse_error": None,
        "n_c": n_c,
        "n_c_brief": n_c_brief,
        "n_verfasser": n_verfasser,
        "n_verfasser_no_gnd": n_verfasser_no_gnd,
        "n_adressat": n_adressat,
        "n_adressat_no_gnd": n_adressat_no_gnd,
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
    n_c_brief_total = 0
    n_verfasser_total = 0
    n_verfasser_no_gnd_total = 0
    n_adressat_total = 0
    n_adressat_no_gnd_total = 0
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
            n_c_brief_total += res["n_c_brief"]
            n_verfasser_total += res["n_verfasser"]
            n_verfasser_no_gnd_total += res["n_verfasser_no_gnd"]
            n_adressat_total += res["n_adressat"]
            n_adressat_no_gnd_total += res["n_adressat_no_gnd"]

    result = {
        "n_files": n_files,
        "n_c_total": n_c_total,
        "n_c_brief_total": n_c_brief_total,
        "n_verfasser_total": n_verfasser_total,
        "n_verfasser_no_gnd_total": n_verfasser_no_gnd_total,
        "n_adressat_total": n_adressat_total,
        "n_adressat_no_gnd_total": n_adressat_no_gnd_total,
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
    print(f"  davon mit controlaccess/genreform = 'Brief':           {n_c_brief_total} "
          f"({pct(n_c_brief_total, n_c_total):.1f}%)")
    print()

    print("-- Verfasser (persname|corpname[@role='Verfasser']) der Brief-c-Elemente --")
    print(f"  gesamt:                                                {n_verfasser_total}")
    print(f"  ohne gueltige GND-Referenz:                            {n_verfasser_no_gnd_total} "
          f"({pct(n_verfasser_no_gnd_total, n_verfasser_total):.1f}%)")
    print()

    print("-- Adressaten (persname|corpname[@role='Adressat']) der Brief-c-Elemente --")
    print(f"  gesamt:                                                {n_adressat_total}")
    print(f"  ohne gueltige GND-Referenz:                            {n_adressat_no_gnd_total} "
          f"({pct(n_adressat_no_gnd_total, n_adressat_total):.1f}%)")
    print()

    if result["files_with_parse_errors"]:
        print("-- Parse-Fehler (erste 20) --")
        for fname, err in result["files_with_parse_errors"][:20]:
            print(f"  {fname}: {err}")


if __name__ == "__main__":
    main()
