#!/usr/bin/env python3
"""
Vergleicht das ISIL @authfilenumber von archdesc/did/repository/corpname
(Bestandshaltende Institution des gesamten Findbuchs) mit dem ISIL
@authfilenumber von c/did/repository/corpname auf allen Verschachtelungsebenen
von <c>.

Fragestellung: Wie oft und wo weicht der c-Level-ISIL-Wert vom
archdesc-Level-ISIL-Wert ab (z.B. weil eine Verzeichnungseinheit an anderer
Stelle aufbewahrt wird als der Bestand insgesamt)?

Nur corpname-Elemente mit @source="ISIL" werden verglichen (auf beiden Seiten).

Verschachtelungstiefe: 1 = <c> ist direktes Kind von archdesc, 2 = <c> in <c>, usw.

Aufruf:
    python3 analyze_c_vs_archdesc_isil_authfilenumber.py <verzeichnis> [anzahl_prozesse] [ergebnis.pkl]

Beispiel:
    python3 analyze_c_vs_archdesc_isil_authfilenumber.py /home/p01776/ead2rico/ead20260217/ead 8 result_c_vs_archdesc_isil.pkl
"""
import sys
import os
import pickle
from collections import Counter
from multiprocessing import Pool
from lxml import etree

NS = {"e": "urn:isbn:1-931666-22-9"}
NSURI = "urn:isbn:1-931666-22-9"
C_TAG = f"{{{NSURI}}}c"
ISIL = "ISIL"
MAX_EXAMPLES_PER_PAIR = 10
MAX_EXAMPLE_FILES = 50


def iter_c_with_depth(root):
    """Liefert alle <c>-Elemente unter root zusammen mit ihrer Verschachtelungstiefe
    (1 = direktes Kind von archdesc). Ein einziger Baumdurchlauf, O(n)."""
    stack = [(root, 0)]
    while stack:
        el, d = stack.pop()
        for child in el:
            if not isinstance(child.tag, str):
                continue
            nd = d + 1 if child.tag == C_TAG else d
            if child.tag == C_TAG:
                yield child, nd
            stack.append((child, nd))


def analyze_file(path):
    fname = os.path.basename(path)
    try:
        tree = etree.parse(path)
    except Exception as e:
        return {"fname": fname, "parse_error": str(e)}

    root = tree.getroot()

    archdesc_isil = root.findall("e:archdesc/e:did/e:repository/e:corpname[@source='ISIL']", NS)
    if len(archdesc_isil) != 1:
        return {
            "fname": fname,
            "parse_error": None,
            "archdesc_ambiguous": True,
            "n_archdesc_isil": len(archdesc_isil),
        }
    archdesc_val = archdesc_isil[0].get("authfilenumber")

    n_c_isil_by_depth = Counter()
    n_match_by_depth = Counter()
    n_mismatch_by_depth = Counter()
    n_missing_authfilenumber_by_depth = Counter()
    mismatch_pairs = Counter()  # (archdesc_val, c_val) -> count
    mismatch_examples = []  # (fname, depth, archdesc_val, c_val)

    for c, depth in iter_c_with_depth(root):
        for corp in c.findall("e:did/e:repository/e:corpname[@source='ISIL']", NS):
            n_c_isil_by_depth[depth] += 1
            c_val = corp.get("authfilenumber")

            if c_val is None:
                n_missing_authfilenumber_by_depth[depth] += 1
                continue

            if c_val == archdesc_val:
                n_match_by_depth[depth] += 1
            else:
                n_mismatch_by_depth[depth] += 1
                mismatch_pairs[(archdesc_val, c_val)] += 1
                if len(mismatch_examples) < MAX_EXAMPLES_PER_PAIR * 20:
                    mismatch_examples.append((fname, depth, archdesc_val, c_val))

    return {
        "fname": fname,
        "parse_error": None,
        "archdesc_ambiguous": False,
        "archdesc_val": archdesc_val,
        "n_c_isil_by_depth": n_c_isil_by_depth,
        "n_match_by_depth": n_match_by_depth,
        "n_mismatch_by_depth": n_mismatch_by_depth,
        "n_missing_authfilenumber_by_depth": n_missing_authfilenumber_by_depth,
        "mismatch_pairs": mismatch_pairs,
        "mismatch_examples": mismatch_examples,
        "has_mismatch": bool(n_mismatch_by_depth),
    }


def main():
    directory = sys.argv[1]
    nworkers = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    out_pickle = sys.argv[3] if len(sys.argv) > 3 else None

    files = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(".xml")]
    files.sort()
    n_files = len(files)
    print(f"Verarbeite {n_files} Dateien mit {nworkers} Prozessen...", file=sys.stderr)

    n_c_isil_by_depth = Counter()
    n_match_by_depth = Counter()
    n_mismatch_by_depth = Counter()
    n_missing_authfilenumber_by_depth = Counter()
    mismatch_pairs = Counter()
    mismatch_examples = []
    files_with_parse_errors = []
    files_archdesc_ambiguous = []  # (fname, n_archdesc_isil)
    files_with_mismatch = []

    done = 0
    with Pool(nworkers) as pool:
        for res in pool.imap_unordered(analyze_file, files, chunksize=50):
            done += 1
            if done % 5000 == 0:
                print(f"  ... {done}/{n_files} Dateien verarbeitet", file=sys.stderr)

            if res["parse_error"] is not None:
                files_with_parse_errors.append((res["fname"], res["parse_error"]))
                continue

            if res["archdesc_ambiguous"]:
                files_archdesc_ambiguous.append((res["fname"], res["n_archdesc_isil"]))
                continue

            n_c_isil_by_depth.update(res["n_c_isil_by_depth"])
            n_match_by_depth.update(res["n_match_by_depth"])
            n_mismatch_by_depth.update(res["n_mismatch_by_depth"])
            n_missing_authfilenumber_by_depth.update(res["n_missing_authfilenumber_by_depth"])
            mismatch_pairs.update(res["mismatch_pairs"])
            if len(mismatch_examples) < MAX_EXAMPLE_FILES:
                mismatch_examples.extend(res["mismatch_examples"])

            if res["has_mismatch"]:
                n_mismatches_in_file = sum(res["n_mismatch_by_depth"].values())
                files_with_mismatch.append((res["fname"], n_mismatches_in_file))

    result = {
        "n_files": n_files,
        "n_c_isil_by_depth": n_c_isil_by_depth,
        "n_match_by_depth": n_match_by_depth,
        "n_mismatch_by_depth": n_mismatch_by_depth,
        "n_missing_authfilenumber_by_depth": n_missing_authfilenumber_by_depth,
        "mismatch_pairs": mismatch_pairs,
        "mismatch_examples": mismatch_examples,
        "files_with_parse_errors": files_with_parse_errors,
        "files_archdesc_ambiguous": files_archdesc_ambiguous,
        "files_with_mismatch": files_with_mismatch,
    }

    if out_pickle:
        with open(out_pickle, "wb") as f:
            pickle.dump(result, f)

    n_total_c_isil = sum(n_c_isil_by_depth.values())
    n_total_match = sum(n_match_by_depth.values())
    n_total_mismatch = sum(n_mismatch_by_depth.values())
    n_total_missing = sum(n_missing_authfilenumber_by_depth.values())

    print("=" * 70)
    print(f"Dateien gesamt:                                          {result['n_files']}")
    print(f"Parse-Fehler:                                            {len(result['files_with_parse_errors'])}")
    print(f"Dateien mit uneindeutigem archdesc-ISIL (0 oder >1):     {len(result['files_archdesc_ambiguous'])}")
    print()
    print(f"c/did/repository/corpname[@source=ISIL] gesamt:          {n_total_c_isil}")
    print(f"  davon uebereinstimmend mit archdesc-ISIL:               {n_total_match}")
    print(f"  davon abweichend von archdesc-ISIL:                     {n_total_mismatch}")
    print(f"  davon ohne @authfilenumber:                             {n_total_missing}")
    print()
    print(f"Dateien mit mindestens einer Abweichung:                 {len(result['files_with_mismatch'])}")
    print()

    depths = sorted(n_c_isil_by_depth.keys())
    print("-- Aufschluesselung nach c-Verschachtelungstiefe --")
    for depth in depths:
        n_total = n_c_isil_by_depth[depth]
        n_match = n_match_by_depth.get(depth, 0)
        n_mismatch = n_mismatch_by_depth.get(depth, 0)
        n_missing = n_missing_authfilenumber_by_depth.get(depth, 0)
        pct_mismatch = 100 * n_mismatch / n_total if n_total else 0
        print(f"  c-Ebene {depth:2d}:  gesamt={n_total:9d}  match={n_match:9d}  "
              f"mismatch={n_mismatch:7d} ({pct_mismatch:5.1f}%)  ohne @authfilenumber={n_missing}")
    print()

    if result["mismatch_pairs"]:
        print("-- Haeufigste abweichende Wertepaare (archdesc-ISIL -> c-ISIL) --")
        for (archdesc_val, c_val), cnt in result["mismatch_pairs"].most_common(30):
            print(f"  {cnt:7d}x  {archdesc_val!r} -> {c_val!r}")
        print()

    if result["files_with_mismatch"]:
        print(f"-- Dateien mit Abweichungen (erste 20 von {len(result['files_with_mismatch'])}) --")
        for fname, cnt in sorted(result["files_with_mismatch"], key=lambda x: -x[1])[:20]:
            print(f"  {fname}: {cnt} Abweichung(en)")
        print()

    if result["mismatch_examples"]:
        print(f"-- Beispiel-Abweichungen (erste 20) --")
        for fname, depth, archdesc_val, c_val in result["mismatch_examples"][:20]:
            print(f"  {fname}  (c-Ebene {depth}):  archdesc={archdesc_val!r}  c={c_val!r}")
        print()

    if result["files_archdesc_ambiguous"]:
        print(f"-- Dateien mit uneindeutigem archdesc-ISIL (erste 20) --")
        for fname, n in result["files_archdesc_ambiguous"][:20]:
            print(f"  {fname}: {n} archdesc/did/repository/corpname[@source=ISIL]-Elemente")
        print()

    if result["files_with_parse_errors"]:
        print("-- Parse-Fehler (erste 20) --")
        for fname, err in result["files_with_parse_errors"][:20]:
            print(f"  {fname}: {err}")


if __name__ == "__main__":
    main()
