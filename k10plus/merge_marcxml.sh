#!/usr/bin/env bash
# Merge concatenated MARCXML documents into one well-formed <collection> and optionally pretty-print it.
#
# Usage:   ./merge_marcxml.sh INPUT.xml OUTPUT.xml [--format]
# Input:   MARCXML file that is several complete documents joined end to end
#          (each with its own <?xml ...?> line and <collection> root), which breaks xmllint/parsers.
# Output:  OUTPUT.xml with a single <?xml?> declaration and a single <collection> root.
#          --format additionally pretty-prints it with xmllint. INPUT.xml is never modified.
set -euo pipefail

if [[ $# -lt 2 || $# -gt 3 ]]; then
    sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//' >&2
    exit 1
fi

in="$1"
out="$2"
fmt="${3:-}"

[[ -f "$in" ]] || { echo "Input not found: $in" >&2; exit 1; }
[[ "$in" != "$out" ]] || { echo "OUTPUT must differ from INPUT" >&2; exit 1; }
[[ -z "$fmt" || "$fmt" == "--format" ]] || { echo "Unknown option: $fmt" >&2; exit 1; }

tmp="$(mktemp "${out}.XXXXXX")"
trap 'rm -f "$tmp"' EXIT

# Remove the seams "</collection><?xml ...?><collection ...>" between documents.
# Works with or without a namespace prefix (marc:collection / collection).
python3 -I - "$in" "$tmp" <<'PY'
import re
import sys

src, dst = sys.argv[1], sys.argv[2]
text = open(src, encoding="utf-8").read()
seam = re.compile(
    r"</(?:\w+:)?collection>\s*(?:<\?xml[^>]*\?>\s*)?<(?:\w+:)?collection\b[^>]*>"
)
text, n = seam.subn("", text)
open(dst, "w", encoding="utf-8").write(text)
print(f"merged {n + 1} document(s)", file=sys.stderr)
PY

xmllint --noout --huge "$tmp"
if [[ "$fmt" == "--format" ]]; then
    xmllint --format --huge "$tmp" -o "$tmp"
fi

mv "$tmp" "$out"
trap - EXIT
echo "wrote $out" >&2
