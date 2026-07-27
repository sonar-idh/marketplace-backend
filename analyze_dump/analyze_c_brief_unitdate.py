#!/usr/bin/env python3
"""
Analysiert EAD-XML-Dateien (analog zu den anderen Skripten in diesem Ordner):

1) Fuer <c>-Elemente mit einem direkten controlaccess/genreform-Kind mit
   Textwert "Brief": wie viele haben ein did/unitdate mit @label =
   "Entstehungsdatum"? Welche anderen @label-Werte kommen sonst noch vor
   (und wie oft)?

2) Fuer dieselben Brief-c-Elemente: wie oft ist bei ihren did/unitdate-Kindern
   das Attribut @normal gesetzt, und welche Formate haben dessen Werte (grob
   klassifiziert, z.B. YYYY, YYYY-MM-DD, YYYYMMDD, Bereich mit "/", etc.)?

Aufruf:
    python3 analyze_c_brief_unitdate.py <verzeichnis> [anzahl_prozesse] [ergebnis.pkl]

Beispiel:
    python3 analyze_c_brief_unitdate.py /home/p01776/ead2rico/ead20260217/ead 8 result_c_brief_unitdate.pkl
"""
import sys
import os
import re
import pickle
from collections import Counter
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


def direct_unitdates(c):
    """did/unitdate-Elemente, die direkte Kinder des did-Kindes von c sind
    (steigt nicht in verschachtelte Kind-c-Elemente ab)."""
    did = c.find("e:did", NS)
    if did is None:
        return []
    return did.findall("e:unitdate", NS)


def classify_normal(value):
    """Grobe Formatklassifikation eines @normal-Werts."""
    v = value.strip()
    if "/" in v:
        parts = v.split("/")
        if len(parts) == 2:
            return f"Bereich ({classify_normal(parts[0])}/{classify_normal(parts[1])})"
        return "Bereich (sonstig)"
    if re.fullmatch(r"\d{4}", v):
        return "YYYY"
    if re.fullmatch(r"\d{4}-\d{2}", v):
        return "YYYY-MM"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
        return "YYYY-MM-DD"
    if re.fullmatch(r"\d{8}", v):
        return "YYYYMMDD"
    if re.fullmatch(r"\d{6}", v):
        return "YYYYMM"
    if v == "":
        return "<leer>"
    return "sonstig"


def analyze_file(path):
    fname = os.path.basename(path)
    try:
        tree = etree.parse(path)
    except Exception as e:
        return {"fname": fname, "parse_error": str(e)}

    root = tree.getroot()

    n_c = 0
    n_c_brief = 0
    n_c_brief_with_entstehungsdatum = 0
    n_c_brief_with_multiple_entstehungsdatum = 0
    brief_label_counter = Counter()

    n_unitdate = 0
    n_unitdate_with_normal = 0
    normal_format_counter = Counter()

    for c in root.findall(".//e:c", NS):
        n_c += 1
        brief = is_brief(c)
        if brief:
            n_c_brief += 1

        if not brief:
            continue

        uds = direct_unitdates(c)
        n_entstehungsdatum_here = sum(1 for ud in uds if ud.get("label") == "Entstehungsdatum")
        if n_entstehungsdatum_here >= 1:
            n_c_brief_with_entstehungsdatum += 1
        if n_entstehungsdatum_here > 1:
            n_c_brief_with_multiple_entstehungsdatum += 1
        for ud in uds:
            label = ud.get("label")
            if label is not None:
                brief_label_counter[label] += 1
            else:
                brief_label_counter["<kein @label>"] += 1

        for ud in uds:
            n_unitdate += 1
            normal = ud.get("normal")
            if normal is not None:
                n_unitdate_with_normal += 1
                normal_format_counter[classify_normal(normal)] += 1

    return {
        "fname": fname,
        "parse_error": None,
        "n_c": n_c,
        "n_c_brief": n_c_brief,
        "n_c_brief_with_entstehungsdatum": n_c_brief_with_entstehungsdatum,
        "n_c_brief_with_multiple_entstehungsdatum": n_c_brief_with_multiple_entstehungsdatum,
        "brief_label_counter": brief_label_counter,
        "n_unitdate": n_unitdate,
        "n_unitdate_with_normal": n_unitdate_with_normal,
        "normal_format_counter": normal_format_counter,
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
    n_c_brief_with_entstehungsdatum_total = 0
    n_c_brief_with_multiple_entstehungsdatum_total = 0
    brief_label_counter_total = Counter()

    n_unitdate_total = 0
    n_unitdate_with_normal_total = 0
    normal_format_counter_total = Counter()

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
            n_c_brief_with_entstehungsdatum_total += res["n_c_brief_with_entstehungsdatum"]
            n_c_brief_with_multiple_entstehungsdatum_total += res["n_c_brief_with_multiple_entstehungsdatum"]
            brief_label_counter_total.update(res["brief_label_counter"])

            n_unitdate_total += res["n_unitdate"]
            n_unitdate_with_normal_total += res["n_unitdate_with_normal"]
            normal_format_counter_total.update(res["normal_format_counter"])

    result = {
        "n_files": n_files,
        "n_c_total": n_c_total,
        "n_c_brief_total": n_c_brief_total,
        "n_c_brief_with_entstehungsdatum_total": n_c_brief_with_entstehungsdatum_total,
        "n_c_brief_with_multiple_entstehungsdatum_total": n_c_brief_with_multiple_entstehungsdatum_total,
        "brief_label_counter_total": brief_label_counter_total,
        "n_unitdate_total": n_unitdate_total,
        "n_unitdate_with_normal_total": n_unitdate_with_normal_total,
        "normal_format_counter_total": normal_format_counter_total,
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

    print("-- did/unitdate/@label bei Brief-c-Elementen --")
    print(f"  Brief-c mit @label='Entstehungsdatum':                 "
          f"{n_c_brief_with_entstehungsdatum_total} "
          f"({pct(n_c_brief_with_entstehungsdatum_total, n_c_brief_total):.1f}%)")
    print(f"    davon mit MEHR ALS EINEM unitdate/@label='Entstehungsdatum': "
          f"{n_c_brief_with_multiple_entstehungsdatum_total} "
          f"({pct(n_c_brief_with_multiple_entstehungsdatum_total, n_c_brief_with_entstehungsdatum_total):.1f}%)")
    print()
    print("  Verteilung aller @label-Werte auf unitdate-Elementen von Brief-c "
          "(ein c kann mehrere unitdate/labels haben):")
    for label, count in brief_label_counter_total.most_common():
        print(f"      {count:>10}  '{label}'")
    print()

    print("-- did/unitdate/@normal (bei Brief-c-Elementen) --")
    print(f"  unitdate-Elemente gesamt:                              {n_unitdate_total}")
    print(f"  davon mit @normal-Attribut:                            "
          f"{n_unitdate_with_normal_total} ({pct(n_unitdate_with_normal_total, n_unitdate_total):.1f}%)")
    print()
    print("  Formate der @normal-Werte:")
    for fmt, count in normal_format_counter_total.most_common():
        print(f"      {count:>10}  {fmt} "
              f"({pct(count, n_unitdate_with_normal_total):.1f}%)")
    print()

    if result["files_with_parse_errors"]:
        print("-- Parse-Fehler (erste 20) --")
        for fname, err in result["files_with_parse_errors"][:20]:
            print(f"  {fname}: {err}")


if __name__ == "__main__":
    main()
