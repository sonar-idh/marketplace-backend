#!/usr/bin/env bash

set -euo pipefail

data_dir="./data/chunks/"
output_dir="./data/cidoc/"

mkdir -p "$output_dir"

for chunk in "$data_dir"/kxp_chunk_*.xml; do
    # Split the xml file into single records and convert to bibframe
    # Then convert to turtle and save to output directory
    echo "Processing $chunk..."
    xsltproc marc2bibframe2/xsl/ConvSpec-Preprocess0-Splitting.xsl "$chunk" \
        | xsltproc marc2bibframe2/xsl/marc2bibframe2.xsl - \
        | rapper -i rdfxml -o turtle - http://example.org/ \
        | uv run python bibframe_to_cidoc.py -i - -o - > "$output_dir/$(basename "$chunk" .xml).ttl"
done

uv run pyshacl -s data/shacl.ttl -m -i rdfs -a -j -f human data/cidoc/kxp_chunk_*.ttl > shacl_errors.txt
