#!/usr/bin/env bash
set -uo pipefail

# ----------------------------------------------------------------------------
# Konfiguration
# ----------------------------------------------------------------------------
IDFILE="gnd_ids.txt"          # eine GND-ID pro Zeile, ohne Präfix
BATCH_SIZE=50
OUTDIR="sru_results"
LOGFILE="sru_fetch.log"
SLEEP_BETWEEN=0.5             # Sekunden Pause zwischen Requests
MAX_RETRIES=3
RETRY_SLEEP=5

mkdir -p "$OUTDIR"
: > "$LOGFILE"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOGFILE"
}

# ----------------------------------------------------------------------------
# Batches erzeugen
# ----------------------------------------------------------------------------
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT
split -l "$BATCH_SIZE" "$IDFILE" "${TMPDIR}/batch_"

total=$(find "$TMPDIR" -name 'batch_*' | wc -l)
log "Starte Abruf: $total Batches à max. ${BATCH_SIZE} IDs"

fail_count=0
i=0

for f in "${TMPDIR}"/batch_*; do
  i=$((i+1))

  # Query zusammenbauen: NID=id1 or NID=id2 or ...
  query=$(awk '{printf "%sNID%%3D%s", (NR>1?"+or+":""), $0}' "$f")
  url="https://services.dnb.de/sru/authorities?version=1.1&operation=searchRetrieve&query=${query}&recordSchema=RDFxml&maximumRecords=${BATCH_SIZE}"

  outfile="${OUTDIR}/result_$(printf '%04d' "$i").xml"

  ok=0
  for attempt in $(seq 1 "$MAX_RETRIES"); do
    http_code=$(curl -s -w "%{http_code}" -o "$outfile" "$url")

    if [[ "$http_code" != "200" ]]; then
      log "Batch $i/$total: HTTP $http_code (Versuch $attempt/$MAX_RETRIES)"
      sleep "$RETRY_SLEEP"
      continue
    fi

    # Leere / fehlerhafte Response prüfen
    if [[ ! -s "$outfile" ]]; then
      log "Batch $i/$total: leere Response (Versuch $attempt/$MAX_RETRIES)"
      sleep "$RETRY_SLEEP"
      continue
    fi

    # SRU liefert bei Fehlern <diag:diagnostics> statt <searchRetrieveResponse>
    if grep -q "diagnostics" "$outfile"; then
      log "Batch $i/$total: SRU-Diagnostic-Fehler in Response, siehe $outfile"
      ok=0
      break   # kein Retry, da es meist ein Query-Fehler ist, kein Transientfehler
    fi

    # numberOfRecords extrahieren, um 0-Treffer zu erkennen
    n=$(grep -oP '(?<=<numberOfRecords>)\d+(?=</numberOfRecords>)' "$outfile" || echo "?")
    if [[ "$n" == "0" ]]; then
      log "Batch $i/$total: 0 Treffer (IDs evtl. falsch/nicht in GND) -> $f"
    else
      log "Batch $i/$total: OK, $n Treffer"
    fi

    ok=1
    break
  done

  if [[ "$ok" != "1" ]]; then
    fail_count=$((fail_count+1))
    log "Batch $i/$total: ENDGÜLTIG FEHLGESCHLAGEN nach ${MAX_RETRIES} Versuchen -> Input: $f"
    cp "$f" "${OUTDIR}/FAILED_batch_$(printf '%04d' "$i").ids"
  fi

  sleep "$SLEEP_BETWEEN"
done

log "Fertig. $((total - fail_count))/$total Batches erfolgreich, $fail_count fehlgeschlagen."
if [[ "$fail_count" -gt 0 ]]; then
  log "Fehlgeschlagene ID-Listen liegen in ${OUTDIR}/FAILED_batch_*.ids -- diese ggf. erneut laufen lassen."
fi