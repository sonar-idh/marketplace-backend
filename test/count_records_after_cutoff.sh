#!/bin/bash
baseUrl="https://kalliope-verbund.info/sru"
cutoffDate="${1:-20250101}"
query="ead.genre.index=(\"Brief\") AND ead.repository.index=(\"Staatsbibliothek zu Berlin. Musikabteilung\") AND ead.modificationdate.normal < \"${cutoffDate}\""

response=$(curl -s -G "$baseUrl" \
  --data-urlencode "version=1.2" \
  --data-urlencode "operation=searchRetrieve" \
  --data-urlencode "recordSchema=mods37" \
  --data-urlencode "maximumRecords=1" \
  --data-urlencode "query=${query}")

count=$(echo "$response" | grep -oP '(?<=<srw:numberOfRecords>)\d+')

if [ -z "$count" ]; then
  echo "Fehler: Keine Antwort oder unerwartetes Format."
  echo "$response" | head -20
  exit 1
fi

echo "Records nach cutoff-Datum ${cutoffDate}: $count"
