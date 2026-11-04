#!/usr/bin/env bash
# Download K10Plus dumps
# Input:  https://swblod.bsz-bw.de/od/SA-MARC-verbund-001..073.xml.gz
# Output: data/raw/SA-MARC-verbund-001..073.xml.gz
set -euo pipefail

RAW=data/raw

mkdir -p "$RAW"

# 1. Download k10plus with 4 parallel processes
seq -f "%03g" 1 73 | xargs -P 4 -I{} wget -c -nv -P "$RAW" \
  "https://swblod.bsz-bw.de/od/SA-MARC-verbund-{}.xml.gz"
    