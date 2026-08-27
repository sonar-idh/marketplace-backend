#!/usr/bin/env python3
"""
Untersucht den Dump auf Briefe von Clara Schumann (1819-1896, Pianistin,
Ehefrau von Robert Schumann; GND 11861164X).

Vorgehen (analog zu analyze_brief_genreform_exact_match.py und
analyze_origination_persname_role.py):
- Für jeden Record (archdesc + alle c-Elemente) werden alle persname-Elemente
  betrachtet, die innerhalb der direkten did/controlaccess-Kinder des Records
  liegen (nicht in verschachtelten Kind-c-Elementen).
- Ein Record gilt als "Treffer", wenn er dort ein persname-Element mit
    a) @role="Verfasser" (Urheberschaft) UND
    b) entweder @source="GND" und @authfilenumber="11861164X" (sichere
       Übereinstimmung) ODER dem Namenstext/@normal nach "Schumann, Clara"
       (unsichere Übereinstimmung, z.B. falls @source/@authfilenumber fehlen)
  enthält.
- Zusätzlich wird geprüft, ob der Record per genreform (lokal, exakt "Brief")
  als Brief klassifiziert ist, um "echte" Einzelbriefe von Sammlungen o.ä.
  zu unterscheiden.
- Records mit einem Clara-Schumann-persname aber einer ANDEREN Rolle
  (z.B. "Adressat") werden separat gezählt, um sie nicht faelschlich als
  "von ihr verfasst" zu werten.

Aufruf:
    python3 analyze_clara_schumann_briefe.py <verzeichnis> [anzahl_prozesse] [ergebnis.pkl]

Beispiel:
    python3 analyze_clara_schumann_briefe.py /home/p01776/ead2rico/ead20260217/ead 8 result_clara_schumann.pkl
"""
import sys
import os
import pickle
from collections import Counter
from multiprocessing import Pool
from lxml import etree

NS = {"e": "urn:isbn:1-931666-22-9"}
NSURI = "urn:isbn:1-931666-22-9"

CLARA_SCHUMANN_GND = "11861164X"
CLARA_SCHUMANN_NAME_HINTS = ("schumann, clara", "clara schumann")

VERFASSER_ROLE = "Verfasser"
BRIEF_EXACT = "Brief"


def local_persnames(record):
    """persname-Elemente, nur innerhalb der direkten did/controlaccess-Kinder
    des Records (steigt NICHT in verschachtelte <c>-Kinder ab)."""
    result = []
    for container_tag in ("did", "controlaccess"):
        for child in record.findall(f"e:{container_tag}", NS):
            for el in child.iter(f"{{{NSURI}}}persname"):
                result.append(el)
    return result


def local_genreform_values(record):
    values = []
    for container_tag in ("did", "controlaccess"):
        for child in record.findall(f"e:{container_tag}", NS):
            for el in child.iter(f"{{{NSURI}}}genreform"):
                values.append((el.text or "").strip())
    return values


def is_clara_schumann(persname_el):
    if persname_el.get("source") == "GND" and persname_el.get("authfilenumber") == CLARA_SCHUMANN_GND:
        return True, "gnd"

    candidates = [persname_el.get("normal") or "", (persname_el.text or "")]
    for c in candidates:
        if c.strip().lower() in CLARA_SCHUMANN_NAME_HINTS:
            return True, "name"
    return False, None


def record_unittitle(record):
    for child in record.findall("e:did", NS):
        for ut in child.findall("e:unittitle", NS):
            if ut.text:
                return ut.text.strip()
    return None


def record_unitdate(record):
    for child in record.findall("e:did", NS):
        for ud in child.findall("e:unitdate", NS):
            return (ud.get("normal") or (ud.text or "").strip()) or None
    return None


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
    verfasser_hits = []  # (unittitle, unitdate, match_kind, genreform_values)
    other_role_hits = []  # (unittitle, role, match_kind)

    for record in records:
        clara_persnames = []
        for pn in local_persnames(record):
            found, kind = is_clara_schumann(pn)
            if found:
                clara_persnames.append((pn, kind))

        if not clara_persnames:
            continue

        is_verfasser = any(pn.get("role") == VERFASSER_ROLE for pn, _ in clara_persnames)

        if is_verfasser:
            match_kind = "gnd" if any(k == "gnd" for _, k in clara_persnames) else "name"
            genres = local_genreform_values(record)
            verfasser_hits.append({
                "unittitle": record_unittitle(record),
                "unitdate": record_unitdate(record),
                "match_kind": match_kind,
                "genreform": genres,
                "is_brief_exact": BRIEF_EXACT in genres,
            })
        else:
            for pn, kind in clara_persnames:
                other_role_hits.append({
                    "unittitle": record_unittitle(record),
                    "role": pn.get("role"),
                    "match_kind": kind,
                })

    return {
        "fname": fname,
        "parse_error": None,
        "n_records": n_records,
        "verfasser_hits": verfasser_hits,
        "other_role_hits": other_role_hits,
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
    files_with_parse_errors = []
    all_verfasser_hits = []  # (fname, hit-dict)
    all_other_role_hits = []  # (fname, hit-dict)
    role_counter = Counter()

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
            for hit in res["verfasser_hits"]:
                all_verfasser_hits.append((res["fname"], hit))
            for hit in res["other_role_hits"]:
                all_other_role_hits.append((res["fname"], hit))
                role_counter[hit["role"]] += 1

    n_verfasser_hits = len(all_verfasser_hits)
    n_brief_exact = sum(1 for _, h in all_verfasser_hits if h["is_brief_exact"])
    n_gnd_matches = sum(1 for _, h in all_verfasser_hits if h["match_kind"] == "gnd")
    n_name_only_matches = n_verfasser_hits - n_gnd_matches

    result = {
        "n_files": n_files,
        "n_records": n_records,
        "verfasser_hits": all_verfasser_hits,
        "other_role_hits": all_other_role_hits,
        "role_counter": role_counter,
        "files_with_parse_errors": files_with_parse_errors,
    }

    if out_pickle:
        with open(out_pickle, "wb") as f:
            pickle.dump(result, f)

    print("=" * 70)
    print(f"Dateien gesamt:                                        {n_files}")
    print(f"Parse-Fehler:                                          {len(files_with_parse_errors)}")
    print(f"Records (archdesc+c) gesamt:                           {n_records}")
    print()
    print(f"Records mit Clara Schumann als @role='Verfasser':      {n_verfasser_hits}")
    print(f"  davon per GND (11861164X) sicher identifiziert:      {n_gnd_matches}")
    print(f"  davon nur per Namenstext identifiziert:              {n_name_only_matches}")
    print(f"  davon mit genreform=='Brief' (exakt):                {n_brief_exact}")
    print()

    if n_verfasser_hits:
        print("-- Gefundene Briefe/Records von Clara Schumann --")
        for fname, hit in sorted(all_verfasser_hits, key=lambda x: x[0])[:50]:
            title = hit["unittitle"] or "<ohne unittitle>"
            date = hit["unitdate"] or "?"
            genres = ", ".join(hit["genreform"]) or "<keine genreform>"
            print(f"  [{fname}] ({date}) {title!r} -- genreform: {genres} -- match: {hit['match_kind']}")
        if n_verfasser_hits > 50:
            print(f"  ... insgesamt {n_verfasser_hits} Treffer")
    else:
        print("Keine Records gefunden, bei denen Clara Schumann als Verfasserin gefuehrt wird.")

    if all_other_role_hits:
        print()
        print("-- Clara Schumann in ANDERER Rolle gefunden (zur Info, nicht als Verfasserin) --")
        for role, cnt in role_counter.most_common():
            print(f"  {cnt:6d}  {role!r}")

    if files_with_parse_errors:
        print("\n-- Parse-Fehler (erste 20) --")
        for fname, err in files_with_parse_errors[:20]:
            print(f"  {fname}: {err}")


if __name__ == "__main__":
    main()
