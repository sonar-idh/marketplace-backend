#!/usr/bin/env python3
"""
Analysiert fuer den Pfad c/did/repository/corpname (auf allen Verschachtelungsebenen
von <c>, nicht nur archdesc/did/repository/corpname):
- wie viele c-Elemente pro Verschachtelungstiefe vorkommen
- wie viele davon ein did/repository/corpname-Element haben (0/1/mehrere)
- ob es ein @role-Attribut hat (und mit welchen Ausprägungen), je Tiefe
- ob es ein @source-Attribut hat (und mit welchen Ausprägungen), je Tiefe
- ob es ein @authfilenumber-Attribut hat, je Tiefe

Verschachtelungstiefe: 1 = <c> ist direktes Kind von archdesc, 2 = <c> in <c>, usw.

Aufruf:
    python3 analyze_c_repository_corpname_source.py <verzeichnis> [anzahl_prozesse] [ergebnis.pkl]

Beispiel:
    python3 analyze_c_repository_corpname_source.py /home/p01776/ead2rico/ead20260217/ead 8 result_c_repo_corpname.pkl
"""
import sys
import os
import pickle
from collections import Counter, defaultdict
from multiprocessing import Pool
from lxml import etree

NS = {"e": "urn:isbn:1-931666-22-9"}
NSURI = "urn:isbn:1-931666-22-9"
C_TAG = f"{{{NSURI}}}c"
NO_SOURCE = "<kein @source-Attribut>"
NO_ROLE = "<kein @role-Attribut>"


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

    # depth -> stats
    c_count_by_depth = Counter()
    repocorp_count_by_depth = Counter()
    source_counter_by_depth = defaultdict(Counter)
    role_counter_by_depth = defaultdict(Counter)
    n_with_authfilenumber_by_depth = Counter()
    n_without_authfilenumber_by_depth = Counter()
    n_c_without_repocorp_by_depth = Counter()
    n_c_with_multiple_repocorp_by_depth = Counter()

    for c, depth in iter_c_with_depth(root):
        c_count_by_depth[depth] += 1

        corpnames = c.findall("e:did/e:repository/e:corpname", NS)
        n = len(corpnames)
        if n == 0:
            n_c_without_repocorp_by_depth[depth] += 1
        elif n > 1:
            n_c_with_multiple_repocorp_by_depth[depth] += 1

        for corp in corpnames:
            repocorp_count_by_depth[depth] += 1

            src = corp.get("source")
            source_counter_by_depth[depth][src if src is not None else NO_SOURCE] += 1

            role = corp.get("role")
            role_counter_by_depth[depth][role if role is not None else NO_ROLE] += 1

            if corp.get("authfilenumber") is not None:
                n_with_authfilenumber_by_depth[depth] += 1
            else:
                n_without_authfilenumber_by_depth[depth] += 1

    return {
        "fname": fname,
        "parse_error": None,
        "c_count_by_depth": c_count_by_depth,
        "repocorp_count_by_depth": repocorp_count_by_depth,
        "source_counter_by_depth": source_counter_by_depth,
        "role_counter_by_depth": role_counter_by_depth,
        "n_with_authfilenumber_by_depth": n_with_authfilenumber_by_depth,
        "n_without_authfilenumber_by_depth": n_without_authfilenumber_by_depth,
        "n_c_without_repocorp_by_depth": n_c_without_repocorp_by_depth,
        "n_c_with_multiple_repocorp_by_depth": n_c_with_multiple_repocorp_by_depth,
    }


def main():
    directory = sys.argv[1]
    nworkers = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    out_pickle = sys.argv[3] if len(sys.argv) > 3 else None

    files = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(".xml")]
    files.sort()
    n_files = len(files)
    print(f"Verarbeite {n_files} Dateien mit {nworkers} Prozessen...", file=sys.stderr)

    c_count_by_depth = Counter()
    repocorp_count_by_depth = Counter()
    source_counter_by_depth = defaultdict(Counter)
    role_counter_by_depth = defaultdict(Counter)
    n_with_authfilenumber_by_depth = Counter()
    n_without_authfilenumber_by_depth = Counter()
    n_c_without_repocorp_by_depth = Counter()
    n_c_with_multiple_repocorp_by_depth = Counter()
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

            c_count_by_depth.update(res["c_count_by_depth"])
            repocorp_count_by_depth.update(res["repocorp_count_by_depth"])
            for depth, cnt in res["source_counter_by_depth"].items():
                source_counter_by_depth[depth].update(cnt)
            for depth, cnt in res["role_counter_by_depth"].items():
                role_counter_by_depth[depth].update(cnt)
            n_with_authfilenumber_by_depth.update(res["n_with_authfilenumber_by_depth"])
            n_without_authfilenumber_by_depth.update(res["n_without_authfilenumber_by_depth"])
            n_c_without_repocorp_by_depth.update(res["n_c_without_repocorp_by_depth"])
            n_c_with_multiple_repocorp_by_depth.update(res["n_c_with_multiple_repocorp_by_depth"])

    result = {
        "n_files": n_files,
        "c_count_by_depth": c_count_by_depth,
        "repocorp_count_by_depth": repocorp_count_by_depth,
        "source_counter_by_depth": dict(source_counter_by_depth),
        "role_counter_by_depth": dict(role_counter_by_depth),
        "n_with_authfilenumber_by_depth": n_with_authfilenumber_by_depth,
        "n_without_authfilenumber_by_depth": n_without_authfilenumber_by_depth,
        "n_c_without_repocorp_by_depth": n_c_without_repocorp_by_depth,
        "n_c_with_multiple_repocorp_by_depth": n_c_with_multiple_repocorp_by_depth,
        "files_with_parse_errors": files_with_parse_errors,
    }

    if out_pickle:
        with open(out_pickle, "wb") as f:
            pickle.dump(result, f)

    n_total_c = sum(c_count_by_depth.values())
    n_total_repocorp = sum(repocorp_count_by_depth.values())

    print("=" * 70)
    print(f"Dateien gesamt:                                          {result['n_files']}")
    print(f"Parse-Fehler:                                            {len(result['files_with_parse_errors'])}")
    print(f"c-Elemente gesamt (alle Ebenen):                        {n_total_c}")
    print(f"c/did/repository/corpname-Elemente gesamt (alle Ebenen): {n_total_repocorp}")
    print()

    depths = sorted(c_count_by_depth.keys())
    for depth in depths:
        n_c = c_count_by_depth[depth]
        n_repocorp = repocorp_count_by_depth.get(depth, 0)
        n_without = n_c_without_repocorp_by_depth.get(depth, 0)
        n_multiple = n_c_with_multiple_repocorp_by_depth.get(depth, 0)
        n_exactly_one = n_c - n_without - n_multiple

        role_counter = role_counter_by_depth.get(depth, Counter())
        source_counter = source_counter_by_depth.get(depth, Counter())
        n_with_role = n_repocorp - role_counter.get(NO_ROLE, 0)
        n_with_source = n_repocorp - source_counter.get(NO_SOURCE, 0)
        n_with_afn = n_with_authfilenumber_by_depth.get(depth, 0)
        n_without_afn = n_without_authfilenumber_by_depth.get(depth, 0)

        print("-" * 70)
        print(f"c-Ebene {depth}")
        print("-" * 70)
        print(f"  c-Elemente auf dieser Ebene:                         {n_c}")
        print(f"  davon ohne did/repository/corpname:                  {n_without}")
        print(f"  davon mit genau einem:                               {n_exactly_one}")
        print(f"  davon mit mehreren:                                  {n_multiple}")
        print(f"  did/repository/corpname-Elemente gesamt:             {n_repocorp}")
        print()

        if n_repocorp:
            print("  -- @role-Werte --")
            for val, cnt in role_counter.most_common():
                pct = 100 * cnt / n_repocorp
                print(f"    {cnt:9d}  ({pct:5.1f}%)  {val!r}")
            print(f"    davon mit @role-Attribut:                          {n_with_role}")
            print(f"    davon OHNE @role-Attribut:                         {role_counter.get(NO_ROLE, 0)}")
            print()

            print("  -- @source-Werte --")
            for val, cnt in source_counter.most_common():
                pct = 100 * cnt / n_repocorp
                print(f"    {cnt:9d}  ({pct:5.1f}%)  {val!r}")
            print(f"    davon mit @source-Attribut:                        {n_with_source}")
            print(f"    davon OHNE @source-Attribut:                       {source_counter.get(NO_SOURCE, 0)}")
            print()

            print("  -- @authfilenumber-Attribut --")
            print(f"    davon mit @authfilenumber-Attribut:                {n_with_afn}")
            print(f"    davon OHNE @authfilenumber-Attribut:               {n_without_afn}")
        print()

    if result["files_with_parse_errors"]:
        print("\n-- Parse-Fehler (erste 20) --")
        for fname, err in result["files_with_parse_errors"][:20]:
            print(f"  {fname}: {err}")


if __name__ == "__main__":
    main()
