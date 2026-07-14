#!/usr/bin/env python3
"""
Analysiert EAD-XML-Dateien (analog zu analyze_adressat.py):
- Findet alle "Records" (archdesc + c-Elemente), deren genreform-Wert(e)
  EXAKT "Brief" sind (kein Substring-Match -> "Briefe", "Briefsammlung",
  "Briefwechsel" etc. zaehlen hier NICHT mit, siehe dazu die Regex-Variante
  analyze_brief_genreform.py). Wie bei genreform/role wird nur innerhalb der
  direkten did/controlaccess-Kinder des Records gesucht, nicht in
  verschachtelten Kind-c-Elementen.
- Zaehlt, wie viele dieser "Brief"-Records zusaetzlich
    a) ein Element mit @source="GND" enthalten
    b) ein Element mit @role="Adressat" enthalten

Aufruf:
    python3 analyze_brief_genreform_exact_match.py <verzeichnis> [anzahl_prozesse] [ergebnis.pkl]

Beispiel:
    python3 analyze_brief_genreform_exact_match.py /home/p01776/ead2rico/ead20260217/ead 8 result_brief_exact.pkl
"""
import sys
import os
import pickle
from collections import Counter
from multiprocessing import Pool
from lxml import etree

NS = {"e": "urn:isbn:1-931666-22-9"}
NSURI = "urn:isbn:1-931666-22-9"

BRIEF_EXACT = "Brief"


def local_genreform_values(record):
    """genreform-Texte, nur innerhalb der direkten did/controlaccess-Kinder
    des Records (steigt NICHT in verschachtelte <c>-Kinder ab)."""
    values = []
    for container_tag in ("did", "controlaccess"):
        for child in record.findall(f"e:{container_tag}", NS):
            for el in child.iter(f"{{{NSURI}}}genreform"):
                values.append((el.text or "").strip())
    return values


def local_elements_with_attr(record, attr_name, attr_value=None):
    """Elemente mit gesetztem Attribut attr_name (optional == attr_value),
    nur innerhalb der direkten did/controlaccess-Kinder des Records."""
    hits = []
    for container_tag in ("did", "controlaccess"):
        for child in record.findall(f"e:{container_tag}", NS):
            for el in child.iter():
                val = el.get(attr_name)
                if val is None:
                    continue
                if attr_value is None or val == attr_value:
                    hits.append(el)
    return hits


def analyze_file(path):
    fname = os.path.basename(path)
    try:
        tree = etree.parse(path)
    except Exception as e:
        return {"fname": fname, "parse_error": str(e)}

    root = tree.getroot()

    records = []
    archdesc = root.find("e:archdesc", NS)
    if archdesc is not None:
        records.append(archdesc)
    records.extend(root.findall(".//e:c", NS))

    n_records = len(records)
    n_brief_records = 0
    n_brief_with_source_gnd = 0
    n_brief_with_adressat = 0
    brief_genreform_value_counter = Counter()  # welche genreform-Werte wurden als "Brief" erfasst

    for record in records:
        genres = local_genreform_values(record)
        brief_genres = [g for g in genres if g == BRIEF_EXACT]
        if not brief_genres:
            continue

        n_brief_records += 1
        for g in brief_genres:
            brief_genreform_value_counter[g] += 1

        if local_elements_with_attr(record, "source", "GND"):
            n_brief_with_source_gnd += 1

        if local_elements_with_attr(record, "role", "Adressat"):
            n_brief_with_adressat += 1

    return {
        "fname": fname,
        "parse_error": None,
        "n_records": n_records,
        "n_brief_records": n_brief_records,
        "n_brief_with_source_gnd": n_brief_with_source_gnd,
        "n_brief_with_adressat": n_brief_with_adressat,
        "brief_genreform_value_counter": brief_genreform_value_counter,
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
    n_brief_records = 0
    n_brief_with_source_gnd = 0
    n_brief_with_adressat = 0
    brief_genreform_value_counter = Counter()
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
            n_brief_records += res["n_brief_records"]
            n_brief_with_source_gnd += res["n_brief_with_source_gnd"]
            n_brief_with_adressat += res["n_brief_with_adressat"]
            brief_genreform_value_counter.update(res["brief_genreform_value_counter"])

    result = {
        "n_files": n_files,
        "n_records": n_records,
        "n_brief_records": n_brief_records,
        "n_brief_with_source_gnd": n_brief_with_source_gnd,
        "n_brief_with_adressat": n_brief_with_adressat,
        "brief_genreform_value_counter": brief_genreform_value_counter,
        "files_with_parse_errors": files_with_parse_errors,
    }

    if out_pickle:
        with open(out_pickle, "wb") as f:
            pickle.dump(result, f)

    print("=" * 70)
    print(f"Dateien gesamt:                                       {result['n_files']}")
    print(f"Parse-Fehler:                                         {len(result['files_with_parse_errors'])}")
    print(f"Records (archdesc+c) gesamt:                          {result['n_records']}")
    print(f"Records mit genreform == 'Brief' (exakt):             {result['n_brief_records']}")
    if result["n_brief_records"]:
        pct_gnd = 100 * result["n_brief_with_source_gnd"] / result["n_brief_records"]
        pct_adr = 100 * result["n_brief_with_adressat"] / result["n_brief_records"]
        print(f"  davon mit @source='GND':                            {result['n_brief_with_source_gnd']} ({pct_gnd:.1f}%)")
        print(f"  davon mit @role='Adressat':                         {result['n_brief_with_adressat']} ({pct_adr:.1f}%)")
    print()

    print("-- genreform-Werte, die exakt 'Brief' entsprechen (zur Kontrolle) --")
    for val, cnt in result["brief_genreform_value_counter"].most_common(50):
        print(f"  {val!r:30s} {cnt}")
    print(f"  ... insgesamt {len(result['brief_genreform_value_counter'])} unterschiedliche Werte")

    if result["files_with_parse_errors"]:
        print("\n-- Parse-Fehler (erste 20) --")
        for fname, err in result["files_with_parse_errors"][:20]:
            print(f"  {fname}: {err}")


if __name__ == "__main__":
    main()
