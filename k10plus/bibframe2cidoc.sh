#!/usr/bin/env bash

# BIBFRAME RDF to CIDOC-CRM transformation pipeline for larger dataset.
# This script:
# 1. Converts each chunk to cidoc using SPARQL construct queries.
# 2. Save the final cidoc graph.
# 3. Validate the cidoc graph using shacl.

set -euo pipefail

input_dir_bibframe="./data/bibframe"
output_dir_cidoc="./data/cidoc"

mkdir -p "$output_dir_cidoc"

time for chunk in "$input_dir_bibframe"/*.ttl; do
    echo "Processing $chunk..."
    uv run python bibframe_to_cidoc.py -i "$chunk" -o "$output_dir_cidoc/$(basename "$chunk" .ttl)_cidoc.ttl"
done

# validate the graph
time uv run pyshacl -s data/shacl.ttl -m -i rdfs -a -j -f human data/cidoc/kxp_chunk_*.ttl > data/cidoc/shacl_errors.log
