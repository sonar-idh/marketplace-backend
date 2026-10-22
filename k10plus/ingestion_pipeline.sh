#!/usr/bin/env bash
# Download K10Plus dumps, filter RDA records into shards, archive shards in Fedora.
#
# Usage:  fedora_test_cred=user:pass fedora_test_base=https://... ./ingestion_pipeline.sh
# Input:  https://swblod.bsz-bw.de/od/SA-MARC-verbund-001..073.xml.gz
# Output: data/filtered/<dump>_<offset>_<shard>.xml.gz (written by record_sink.py)
set -euo pipefail
cd "$(dirname "$0")"

: "${fedora_test_cred:?set fedora_test_cred}"
: "${fedora_test_base:?set fedora_test_base}"

RAW=data/raw
OUT=data/filtered
mkdir -p "$RAW" "$OUT"

# 1. Download k10plus with 4 parallel processes
seq -f "%03g" 1 73 | xargs -P 4 -I{} wget -c -nv -P "$RAW" \
  "https://swblod.bsz-bw.de/od/SA-MARC-verbund-{}.xml.gz"

# 2. Filter RDA records; one task per dump, RecordSink writes the shards (no separate chunking)
uv run python3 fast_marc_analysis.py "$RAW"

# 3. Archive shards in Fedora Repo
for f in "$OUT"/*.xml.gz; do
  name="$(basename "${f%.xml.gz}")"
  code=$(curl -s -o /dev/null -w "%{http_code}" -X PUT -u "$fedora_test_cred" \
    -H "Link: <http://www.w3.org/ns/ldp#NonRDFSource>; rel=\"type\"" \
    -H "Content-Type: application/gzip" \
    --data-binary "@$f" \
    "$fedora_test_base/K10-Plus-Test/$name")
  echo "$code $f"
  case "$code" in
    201|204) echo "$f" >> "$OUT/fedora_uploaded.txt" ;;
    *)       echo "$f" >> "$OUT/fedora_failed.txt" ;;
  esac
done
