#!/usr/bin/env bash
set -uo pipefail

fail_count=0
i=0
OUTDIR="sru_results_ttl"
mkdir -p "$OUTDIR"

for rdf_file in ./sru_results_rdf/*.xml; do
    i=$((i+1))
    outfile="${OUTDIR}/result_$(printf '%04d' "$i").ttl"
    rapper -i rdfxml -o turtle -q $rdf_file > $outfile 
done