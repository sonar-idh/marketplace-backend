#!/bin/bash
baseUrl="https://kalliope-verbund.info/sru"
cutoffDate="20250101"
query="ead.genre.index=(\"Brief\") AND ead.repository.index=(\"Staatsbibliothek zu Berlin. Musikabteilung\") AND ead.modificationdate.normal < \"${cutoffDate}\""
pageSize=100
startRecord=1
total=999999  
outDir="initial_dump_raw"

mkdir -p "$outDir"

while [ "$startRecord" -le "$total" ]; do
  outFile="${outDir}/records_$(printf '%06d' $startRecord).xml"
  
  echo "Getting records ${startRecord}–$((startRecord + pageSize - 1))..."
  
  curl -s -G "$baseUrl" \
    --data-urlencode "version=1.2" \
    --data-urlencode "operation=searchRetrieve" \
    --data-urlencode "recordSchema=mods37" \
    --data-urlencode "startRecord=${startRecord}" \
    --data-urlencode "maximumRecords=${pageSize}" \
    --data-urlencode "query=${query}" \
    -o "$outFile"
  
  # Read total number of records for this query 
  if [ "$startRecord" -eq 1 ]; then
    total=$(grep -oP '(?<=<srw:numberOfRecords>)\d+' "$outFile")
    echo "Total: $total records"
  fi
  
  startRecord=$((startRecord + pageSize))
  sleep 0.5  
done

echo "Done. $(ls $outDir | wc -l) files in ./$outDir/"