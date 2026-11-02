#!/usr/bin/env bash

set -euo pipefail
: "${fedora_test_cred:?set fedora_test_cred}"
: "${fedora_test_base:?set fedora_test_base}"
: "${test_container:?set test_container}"
: "${fedora_test_data:?set fedora_test_data}"

mkdir -p /tmp/fedora

# Archive shards in Fedora Repo
for f in "$fedora_test_data"/*.xml.gz; do
  name="$(basename "${f%.xml.gz}")"
  code=$(curl -s -o /dev/null -w "%{http_code}" -X PUT -u "$fedora_test_cred" \
    -H "Link: <http://www.w3.org/ns/ldp#NonRDFSource>; rel=\"type\"" \
    -H "Content-Type: application/gzip" \
    --data-binary "@$f" \
    "$fedora_test_base/$test_container/$name")
  echo "$code $f"
  case "$code" in
    201|204) echo "$(date +%F) $f" >> "/tmp/fedora/uploaded.txt" ;;
    *)       echo "$f" >> "/tmp/fedora/failed.txt" ;;
  esac
done