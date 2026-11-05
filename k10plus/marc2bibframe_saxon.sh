#!/usr/bin/env bash
# MARC XML -> BIBFRAME Turtle, using GNU Parallel, Saxon-HE and rapper.
# Usage:  ./marc2bibframe_saxon.sh [CHUNK_JOBS]      (default 4 chunks converted in parallel)
#         DATA_DIR=... OUT_DIR=... CHUNK_RECORDS=... JVM_HEAP_MB=... ./marc2bibframe_saxon.sh
#
# Input:  input files in $DATA_DIR, plain (*.xml) or gzipped (*.xml.gz)
# Output: $OUT_DIR/<name>_bibframe.ttl.gz, logs in $OUT_DIR/logs/, job table in $OUT_DIR/joblog.tsv

set -euo pipefail

data_dir="${DATA_DIR:-./data/test}"
out_dir="${OUT_DIR:-./data/bibframe}"
log_dir="$out_dir/logs"
work_dir="$out_dir/work"

JOBS=${JOBS:-1}                                     # input files processed at the same time
CHUNK_JOBS=${1:-4}                                  # chunks converted at the same time
CHUNK_RECORDS="${CHUNK_RECORDS:-10000}"
JVM_HEAP_MB="${JVM_HEAP_MB:-2048}"                  # per Saxon JVM (two per chunk); rapper needs more on top
JAVA_OPTS="${JAVA_OPTS:--XX:+UseSerialGC}"          # ~15% less CPU per chunk than the default GC
MEMFREE_MB="${MEMFREE_MB:-3072}"                    # free RAM parallel waits for before starting a chunk
SAXON_JAR="${SAXON_JAR:-./SaxonHE12-10J/saxon-he-12.10.jar}"
M2B="${M2B:-./marc2bibframe2-3.1.0}"
BASEURI="https://opac.k10plus.de/PPNSET/PPN/"

[[ -f "$SAXON_JAR" ]] || { echo "Saxon jar not found: $SAXON_JAR" >&2; exit 1; }
[[ -d "$M2B/xsl" ]] || { echo "marc2bibframe2 not found: $M2B/xsl" >&2; exit 1; }
mkdir -p "$log_dir" "$work_dir"

# Split input file $1 into gzipped chunks in dir $2, each with the input's header (XML declaration
# + <collection>) and a closing tag. Assumes each record starts on its own line.
# Writes the record count to $2/count.
split_input() {
    gzip -cdf "$1" | awk -v n="$CHUNK_RECORDS" -v dir="$2" '
        BEGIN { close_tag = "</collection>" }
        !started && /<marc:collection/ { close_tag = "</marc:collection>" }
        !started && /<marc:record/ { started = 1 }
        !started { hdr = hdr $0 "\n"; next }
        /^<\/(marc:)?collection>/ { next }
        /<marc:record/ {
            if (c % n == 0) {
                if (cmd != "") { printf "%s\n", close_tag | cmd; close(cmd) }
                cmd = sprintf("gzip > %s/p_%05d.xml.gz", dir, c / n)
                printf "%s", hdr | cmd
            }
            c++
        }
        { print | cmd }
        END {
            if (cmd != "") { printf "%s\n", close_tag | cmd; close(cmd) }
            print c + 0 > (dir "/count")
        }'
}

# Converts one chunk to <chunk>.ttl.gz (written as .tmp, renamed when complete, so a re-run
# skips finished chunks).
transform_marc() {
    set -o pipefail
    local chunk="$1" out="${1%.xml.gz}.ttl.gz"
    [[ -s "$out" ]] && return 0
    gzip -cd "$chunk" \
        | java $JAVA_OPTS "-Xmx${JVM_HEAP_MB}m" -jar "$SAXON_JAR" -s:- -xsl:"$M2B/xsl/ConvSpec-Preprocess0-Splitting.xsl" \
        | java $JAVA_OPTS "-Xmx${JVM_HEAP_MB}m" -jar "$SAXON_JAR" -s:- -xsl:"$M2B/xsl/marc2bibframe2.xsl" baseuri="$BASEURI" \
        | rapper -q -i rdfxml -o turtle - "$BASEURI" \
        | gzip > "$out.tmp" \
        && mv "$out.tmp" "$out" \
        || { echo "FAILED chunk $(basename "$chunk")" >&2; rm -f "$out.tmp"; return 1; }
}

process_input() {
    set -o pipefail
    local input="$1" base chunk_dir out tmp log records chunks
    base=$(basename "$input"); base="${base%.gz}"; base="${base%.xml}"
    out="$out_dir/${base}_bibframe.ttl.gz"
    tmp="$out.tmp"
    log="$log_dir/$base.log"
    chunk_dir="$work_dir/${base}_$CHUNK_RECORDS"      # kept after a failure so a re-run resumes

    if [[ -s "$out" ]]; then
        echo "Skipping $base (already done)"
        return 0
    fi

    fail() { echo "FAILED $input ($1, see $log)" >&2; rm -f "$tmp"; }
    
    # Split input into chunks
    rm -f "$tmp"
    SECONDS=0
    if [[ ! -s "$chunk_dir/count" ]]; then
        rm -rf "$chunk_dir"; mkdir -p "$chunk_dir"; : > "$log"
        split_input "$input" "$chunk_dir" 2>> "$log" || { fail "split"; return 1; }
    fi
    records=$(<"$chunk_dir/count")
    chunks=$(find "$chunk_dir" -name 'p_*.xml.gz' | wc -l)
    (( chunks > 0 )) || { fail "no records found"; return 1; }
    echo "Processing $base: $records records in $chunks chunks of $CHUNK_RECORDS ($CHUNK_JOBS chunks at a time, heap ${JVM_HEAP_MB}m per JVM)..."
    
    # Transform Chunks in parallel
    find "$chunk_dir" -name 'p_*.xml.gz' | sort \
        | parallel --jobs "$CHUNK_JOBS" --noswap --memfree "${MEMFREE_MB}M" transform_marc {} 2>> "$log" \
        || { fail "chunk conversion"; return 1; }

    # Chunks are numbered, so concatenating in order keeps the record order.
    cat "$chunk_dir"/p_*.ttl.gz > "$tmp" 2>> "$log" || { fail "concat"; return 1; }
    gzip -t "$tmp" 2>> "$log" || { fail "corrupt output"; return 1; }
    mv "$tmp" "$out"
    rm -rf "$chunk_dir"
    echo "DONE $base: $records records, $chunks chunks, ${SECONDS}s ($(( records / (SECONDS > 0 ? SECONDS : 1) )) rec/s)"
}

export -f split_input transform_marc process_input
export CHUNK_JOBS MEMFREE_MB out_dir log_dir work_dir SAXON_JAR M2B BASEURI CHUNK_RECORDS JVM_HEAP_MB JAVA_OPTS

# Check for input files
mapfile -t inputs < <(find -L "$data_dir" -maxdepth 1 -type f \( -name '*.xml' -o -name '*.xml.gz' \) | sort)
[[ ${#inputs[@]} -gt 0 ]] || { echo "No *.xml or *.xml.gz inputs in $data_dir" >&2; exit 1; }

# Run the pipeline in parallel
echo "Starting pipeline: ${#inputs[@]} inputs ($JOBS at a time), $CHUNK_JOBS chunks in parallel, $CHUNK_RECORDS records per chunk, ${MEMFREE_MB}M free RAM required per chunk start (Saxon: $SAXON_JAR)..."
failed=0
time printf '%s\n' "${inputs[@]}" \
    | parallel --jobs "$JOBS" --tag --noswap --memfree "${MEMFREE_MB}M" \
        --joblog "$out_dir/joblog.tsv" process_input {} || failed=$?

if (( failed > 0 )); then
    echo "$failed input(s) failed, see $out_dir/joblog.tsv and $log_dir. Re-run to retry only those." >&2
    exit 1
fi
echo "All ${#inputs[@]} inputs done."
