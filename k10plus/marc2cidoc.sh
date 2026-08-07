#!/usr/bin/env bash

# Transformation pipeline for larger dataset.
# This script:
# 1. Converts each chunk to bibframe using XSLT transformers.
# 2. Converts bibframe to turtle using rapper.
# 3. Converts each chunk to cidoc using SPARQL construct queries.
# 4. Save the intermediate bibframe and final cidoc graph.
# 5. Validate the cidoc graph using shacl.

set -euo pipefail

data_dir="./data/chunks/"
output_dir_bibframe="./data/bibframe/"
output_dir_cidoc="./data/cidoc/"

mkdir -p "$output_dir_bibframe"
mkdir -p "$output_dir_cidoc"

time for chunk in "$data_dir"/kxp_chunk_*.xml; do
    # Split the xml file into single records and convert to bibframe
    # Then convert to turtle and save to output directory
    echo "Processing $chunk..."
    xsltproc marc2bibframe2/xsl/ConvSpec-Preprocess0-Splitting.xsl "$chunk" \
        | xsltproc --stringparam baseuri "https://opac.k10plus.de/PPNSET/PPN/" marc2bibframe2/xsl/marc2bibframe2.xsl - \
        | rapper -i rdfxml -o turtle - "https://opac.k10plus.de/PPNSET/PPN/" \
        | tee "$output_dir_bibframe/$(basename "$chunk" .xml)_bibframe.ttl" \
        | uv run python bibframe_to_cidoc.py -i - -o - > "$output_dir_cidoc/$(basename "$chunk" .xml)_cidoc.ttl"
done

# validate the graph
time uv run pyshacl -s data/shacl.ttl -m -i rdfs -a -j -f human data/cidoc/kxp_chunk_*.ttl > data/cidoc/shacl_errors.log
