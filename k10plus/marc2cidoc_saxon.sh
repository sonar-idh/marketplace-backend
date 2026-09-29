#!/usr/bin/env bash

# Transformation pipeline for larger dataset using GNU Parallel and Saxon-HE.
# Steps per chunk:
# 1. Transform MARC XML chunk to BIBFRAME RDF/XML using Saxon-HE.
# 2. Save intermediate BIBFRAME RDF/XML file to ./data/bibframe/
# 3. Stream BIBFRAME RDF/XML directly to bibframe_to_cidoc.py to produce both BIBFRAME Turtle & CIDOC CRM Turtle.

set -euo pipefail

data_dir="./data/"
output_dir_bibframe="./data/bibframe"
output_dir_cidoc="./data/cidoc"

# TODO: Extend based on number of files and cores
JOBS=${1:-4}

mkdir -p "$output_dir_bibframe"
mkdir -p "$output_dir_cidoc"

SAXON_JAR="./SaxonHE12-9J/saxon-he-12.9.jar"
export SAXON_JAR

process_chunk() {
    chunk="$1"
    base=$(basename "$chunk" .xml)
    bibframe_ttl="$output_dir_bibframe/${base}_bibframe.ttl"
    cidoc_ttl="$output_dir_cidoc/${base}_cidoc.ttl"
    log_file="$output_dir_cidoc/shacl_${base}.log"

    echo "Processing $chunk with Saxon-HE (Worker PID: $$)..."

    java -Xmx3g -jar "$SAXON_JAR" -s:"$chunk" -xsl:marc2bibframe2/xsl/ConvSpec-Preprocess0-Splitting.xsl \
        | java -Xmx3g -jar "$SAXON_JAR" -s:- -xsl:marc2bibframe2/xsl/marc2bibframe2.xsl baseuri="https://opac.k10plus.de/PPNSET/PPN/" \
        | rapper -i rdfxml -o turtle - "https://opac.k10plus.de/PPNSET/PPN/" \
        | tee "$bibframe_ttl" \
        | uv run python bibframe2cidoc.py -i - -o "$cidoc_ttl"
    uv run pyshacl -s data/shacl.ttl -m -i rdfs -a -j -f human "$cidoc_ttl" > "$log_file"
}

export -f process_chunk
export output_dir_bibframe
export output_dir_cidoc

echo "Starting pipeline with $JOBS parallel jobs using Saxon JAR ($SAXON_JAR)..."
time ls "$data_dir"/*.xml | parallel --jobs "$JOBS" --tag --noswap --memfree 2G process_chunk {}
