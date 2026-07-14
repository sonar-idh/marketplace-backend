#!/usr/bin/env python3
"""
Analysiert EAD-XML-Dateien:
- Findet alle Elemente mit @role="Adressat" (z.B. persname, corpname)
- Ermittelt den umschliessenden "Record" (das naechste <c>- oder <archdesc>-Element)
- Prueft, ob dieser Record (nur die direkten did/controlaccess-Kinder, nicht
  verschachtelte Kind-c-Elemente) auch ein <genreform>-Element enthaelt
- Sammelt die genreform-Werte fuer diese Records

Aufruf:
    python3 analyze_adressat.py <verzeichnis> [anzahl_prozesse] [ergebnis.pkl]

Beispiel:
    python3 analyze_adressat.py /home/p01776/ead2rico/ead20260217/ead 8 result_adressat.pkl
"""
import sys
import os
import pickle
from collections import Counter
from multiprocessing import Pool
from lxml import etree

NS = {"e": "urn:isbn:1-931666-22-9"}
NSURI = "urn:isbn:1-931666-22-9"


def local_children_with_role_adressat(record):
    """Sucht role='Adressat'-Elemente nur innerhalb der direkten did/controlaccess
    Kinder des Records (steigt NICHT in verschachtelte <c>-Kinder ab)."""
    hits = []
    for container_tag in ("did", "controlaccess"):
        for child in record.findall(f"e:{container_tag}", NS):
            for el in child.iter():
                if el.get("role") == "Adressat":
                    hits.append(el)
    return hits


def local_genreform(record):
    genres = []
    for container_tag in ("did", "controlaccess"):
        for child in record.findall(f"e:{container_tag}", NS):
            for el in child.iter(f"{{{NSURI}}}genreform"):
                genres.append((el.text or "").strip())
    return genres


def analyze_file(path):
    fname = os.path.basename(path)
    try:
        tree = etree.parse(path)
    except Exception as e:
        return {"fname": fname, "parse_error": str(e)}

    root = tree.getroot()

    # Alle "Records": archdesc + alle c-Elemente im ganzen Dokument
    records = []
    archdesc = root.find("e:archdesc", NS)
    if archdesc is not None:
        records.append(archdesc)
    records.extend(root.findall(".//e:c", NS))

    n_records = len(records)
    n_records_with_adressat = 0
    n_records_with_adressat_and_genreform = 0
    adressat_tag_counter = Counter()
    adressat_value_counter = Counter()
    genreform_value_counter = Counter()  # nur fuer Records MIT Adressat
    n_adressat_elements = 0

    for record in records:
        adressat_hits = local_children_with_role_adressat(record)
        if not adressat_hits:
            continue

        n_records_with_adressat += 1
        n_adressat_elements += len(adressat_hits)
        for el in adressat_hits:
            tag = etree.QName(el).localname
            adressat_tag_counter[tag] += 1
            text = (el.text or "").strip()
            adressat_value_counter[text] += 1

        genres = local_genreform(record)
        if genres:
            n_records_with_adressat_and_genreform += 1
            for g in genres:
                genreform_value_counter[g] += 1

    return {
        "fname": fname,
        "parse_error": None,
        "n_records": n_records,
        "n_records_with_adressat": n_records_with_adressat,
        "n_records_with_adressat_and_genreform": n_records_with_adressat_and_genreform,
        "n_adressat_elements": n_adressat_elements,
        "adressat_tag_counter": adressat_tag_counter,
        "adressat_value_counter": adressat_value_counter,
        "genreform_value_counter": genreform_value_counter,
    }


def main():
    directory = sys.argv[1]
    nworkers = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    out_pickle = sys.argv[3] if len(sys.argv) > 3 else None

    files = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(".xml")]
    files.sort()
    n_files = len(files)
    print(f"Verarbeite {n_files} Dateien mit {nworkers} Prozessen...", file=sys.stderr)

    n_records = 0
    n_records_with_adressat = 0
    n_records_with_adressat_and_genreform = 0
    n_adressat_elements = 0
    adressat_tag_counter = Counter()
    adressat_value_counter = Counter()
    genreform_value_counter = Counter()
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

            n_records += res["n_records"]
            n_records_with_adressat += res["n_records_with_adressat"]
            n_records_with_adressat_and_genreform += res["n_records_with_adressat_and_genreform"]
            n_adressat_elements += res["n_adressat_elements"]
            adressat_tag_counter.update(res["adressat_tag_counter"])
            adressat_value_counter.update(res["adressat_value_counter"])
            genreform_value_counter.update(res["genreform_value_counter"])

    result = {
        "n_files": n_files,
        "n_records": n_records,
        "n_records_with_adressat": n_records_with_adressat,
        "n_records_with_adressat_and_genreform": n_records_with_adressat_and_genreform,
        "n_adressat_elements": n_adressat_elements,
        "adressat_tag_counter": adressat_tag_counter,
        "adressat_value_counter": adressat_value_counter,
        "genreform_value_counter": genreform_value_counter,
        "files_with_parse_errors": files_with_parse_errors,
    }

    if out_pickle:
        with open(out_pickle, "wb") as f:
            pickle.dump(result, f)

    print("=" * 70)
    print(f"Dateien gesamt:                                   {result['n_files']}")
    print(f"Parse-Fehler:                                     {len(result['files_with_parse_errors'])}")
    print(f"Records (archdesc+c) gesamt:                       {result['n_records']}")
    print(f"Elemente mit role='Adressat' gesamt:               {result['n_adressat_elements']}")
    print(f"Records (c/archdesc) mit role='Adressat':          {result['n_records_with_adressat']}")
    print(f"  davon auch mit genreform:                        {result['n_records_with_adressat_and_genreform']}")
    if result["n_records_with_adressat"]:
        pct = 100 * result["n_records_with_adressat_and_genreform"] / result["n_records_with_adressat"]
        print(f"  Anteil:                                          {pct:.1f}%")
    print()

    print("-- Tag-Namen der role='Adressat'-Elemente --")
    for tag, cnt in result["adressat_tag_counter"].most_common():
        print(f"  {tag:15s} {cnt}")
    print()

    print("-- genreform-Werte (nur Records MIT Adressat), Top 50 --")
    for val, cnt in result["genreform_value_counter"].most_common(50):
        print(f"  {val!r:30s} {cnt}")
    print(f"  ... insgesamt {len(result['genreform_value_counter'])} unterschiedliche genreform-Werte")
    print()

    print("-- Haeufigste Adressat-Textwerte (Top 20) --")
    for val, cnt in result["adressat_value_counter"].most_common(20):
        print(f"  {val!r:40s} {cnt}")
    print()

    if result["files_with_parse_errors"]:
        print("-- Parse-Fehler (erste 20) --")
        for fname, err in result["files_with_parse_errors"][:20]:
            print(f"  {fname}: {err}")


if __name__ == "__main__":
    main()
