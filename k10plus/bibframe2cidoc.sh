#!/usr/bin/env bash

# BIBFRAME RDF to CIDOC-CRM transformation pipeline for larger dataset.
# This script:
# 1. Converts each chunk to cidoc using SPARQL construct queries.
# 2. Save the final cidoc graph.
# 3. Validate the cidoc graph using shacl.

set -euo pipefail

input_dir_bibframe="./data/bibframe"
output_dir_cidoc="./data/cidoc"

JOBS=${1:-4}

mkdir -p "$output_dir_cidoc"

bibframe2cidoc() {
    chunk=$1
    base=$(basename "$chunk" .ttl)
    cidoc_ttl="$output_dir_cidoc/${base}_cidoc.ttl"
    echo "Processing $chunk..."
    uv run python bibframe2cidoc.py -i "$chunk" -o "$cidoc_ttl"
}

export -f bibframe2cidoc
export output_dir_cidoc

time ls "$input_dir_bibframe"/*.ttl | parallel --jobs "$JOBS" bibframe2cidoc {}

# validate the graph
validate_chunk() {
    file="$1"
    base=$(basename "$file" .ttl)
    log_file="data/cidoc/shacl_${base}.log"
    uv run pyshacl -s data/shacl.ttl -m -i rdfs -a -j -f human "$file" > "$log_file"
}
export -f validate_chunk

echo "Validating CIDOC CRM graphs in parallel..."
time ls "$output_dir_cidoc"/*.ttl | parallel --jobs "$JOBS" validate_chunk {}
cat data/cidoc/shacl_kxp_chunk_*.log > data/cidoc/shacl_errors.log
