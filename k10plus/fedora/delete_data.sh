#!/usr/bin/env bash
# Delete all data inside a fedora container (the container itself is kept).
#
# Usage:   ./delete_data.sh          # lists children, asks for confirmation
#          ./delete_data.sh -y       # no confirmation
# Input:   env vars fedora_test_cred (user:pass), fedora_test_base, test_container
# Output:  "<http code> <child uri>" per deleted child; tombstones are removed so paths can be reused

set -euo pipefail

: "${fedora_test_cred:?set fedora_test_cred}"
: "${fedora_test_base:?set fedora_test_base}"
: "${test_container:?set test_container}"

url="$fedora_test_base/$test_container"

children=$(curl -sf -u "$fedora_test_cred" -H "Accept: application/n-triples" "$url" \
  | sed -n 's|.*<http://www.w3.org/ns/ldp#contains> <\([^>]*\)> .*|\1|p')

if [[ -z "$children" ]]; then
  echo "No children in $url"
  exit 0
fi

echo "$(wc -l <<<"$children") children in $url"

if [[ "${1:-}" != "-y" ]]; then
  read -r -p "Delete all of them? [y/N] " answer
  [[ "$answer" == "y" ]] || { echo "Aborted"; exit 1; }
fi

while read -r child; do
  code=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE -u "$fedora_test_cred" "$child")
  echo "$code $child"
  # Remove the tombstone so the path can be reused
  curl -s -o /dev/null -X DELETE -u "$fedora_test_cred" "$child/fcr:tombstone"
done <<<"$children"
