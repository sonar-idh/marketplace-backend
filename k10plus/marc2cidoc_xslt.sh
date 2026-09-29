#!/usr/bin/env bash

# Transformation pipeline for larger dataset using GNU Parallel and Saxon-HE.
# Steps per chunk:
# 1. Transform MARC XML chunk to BIBFRAME RDF/XML using Saxon-HE.
# 2. Save intermediate BIBFRAME RDF/XML file to ./data/bibframe/
# 3. Stream BIBFRAME RDF/XML directly to bibframe_to_cidoc.py to produce both BIBFRAME Turtle & CIDOC CRM Turtle.

set -euo pipefail

data_dir="./data/chunks"
output_dir_bibframe="./data/bibframe"
output_dir_cidoc="./data/cidoc"

JOBS=${1:-4}

mkdir -p "$output_dir_bibframe"
mkdir -p "$output_dir_cidoc"


process_chunk() {
    chunk="$1"
    base=$(basename "$chunk" .xml)
    bibframe_ttl="$output_dir_bibframe/${base}_bibframe.ttl"
    cidoc_ttl="$output_dir_cidoc/${base}_cidoc.ttl"

    echo "Processing $chunk with xsltproc (Worker PID: $$)..."
    xsltproc marc2bibframe2/xsl/ConvSpec-Preprocess0-Splitting.xsl "$chunk" \
        | xsltproc --stringparam baseuri "https://opac.k10plus.de/PPNSET/PPN/" marc2bibframe2/xsl/marc2bibframe2.xsl - \
        | rapper -i rdfxml -o turtle - "https://opac.k10plus.de/PPNSET/PPN/" \
        | tee "$bibframe_ttl" \
        | uv run python bibframe_to_cidoc.py -i - -o "$cidoc_ttl"
}


export -f process_chunk
export output_dir_bibframe
export output_dir_cidoc

echo "Starting pipeline with $JOBS parallel jobs using xsltproc..."
time ls "$data_dir"/*.xml | parallel --jobs "$JOBS" --tag --noswap --memfree 2G process_chunk {}

# Helper function to validate a single CIDOC file with pyshacl
validate_chunk() {
    file="$1"
    base=$(basename "$file" .ttl)
    log_file="data/cidoc/shacl_${base}.log"
    uv run pyshacl -s data/shacl.ttl -m -i rdfs -a -j -f human "$file" > "$log_file"
}
export -f validate_chunk

# Validate output graphs in parallel
echo "Validating CIDOC CRM graphs in parallel..."
time ls "$output_dir_cidoc"/*.ttl | parallel --jobs "$JOBS" validate_chunk {}
cat data/cidoc/shacl_*.log > data/cidoc/shacl_errors.log
