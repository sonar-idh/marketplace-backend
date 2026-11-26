# marketplace-backend

# Alte Indexdaten vollständig löschen
cd qlever
find . -mindepth 1 -maxdepth 1 \
  ! -name gnd_data ! -name kpe_data ! -name Qleverfile ! -name Qleverfile-ui.yml \
  -exec rm -rf {} +
  
qlever index

# Korrespondenzrelationen einfügen, danach analog insert_lifeDates.rq, insert_occupationLabels.rq, insert_relationTypes.rq
qlever start
cd ..
curl -s "http://localhost:7019"   --data-urlencode "update@insert_correspondence.rq"   --data-urlencode "timeout=3600s"   --data-urlencode "access-token=sonar_7643543846bXEoUzb4WU9t"

# Korrespondenzdaten exportieren
curl -s http://localhost:7019 -H "Accept: text/tab-separated-values" --data-urlencode query@export_correspondence.rq --data-urlencode timeout=3600s --data-urlencode access-token=sonar_7643543846bXEoUzb4WU9t | tail -n +2 | awk -F'\t' '{print $1" "$2" "$3" "$4" ."}' > corr.nq

# Prüfen, ob alles ohne Fehler exportiert wurde:
grep -c "An error has occurred" corr.nq  # muss 0 sein

# Aggregierte Attribute exportieren
curl -s http://localhost:7019 -H "Accept: text/turtle" --data-urlencode query@export_aggRelations.rq > aggRel.ttl
 
 # Quad-Datumsangaben ins richtige Format bringen
 sed -E 's#^(<[^>]*> <info:date> )(-?[0-9]{4}-[0-9]{2}-[0-9]{2})( <[^>]*> \.)$#\1"\2"^^<http://www.w3.org/2001/XMLSchema\#date>\3#' corr.nq > corr_fix.nq
 rm corr.nq
 mv corr_fix.nq corr.nq
 
 # Prüfen, ob Format korrekt:
 grep -vE '^<[^>]*> <[^>]*> (<|")' corr.nq | head
 
 # Export-Tripel verschieben
 mkdir qlever/export_data
 mv corr.nq aggRel.ttl qlever/export_data/
 
# QLverfile anpassen
# { "cmd": "cat corr.nq", "format": "nq" }, { "cmd": "cat occ.ttl", "format": "ttl", "graph": "-" }
# Textindex aktivieren

# Indexdaten erneut vollständig löschen
cd qlever
find . -mindepth 1 -maxdepth 1 \
  ! -name gnd_data ! -name kpe_data ! -name export_data ! -name Qleverfile ! -name Qleverfile-ui.yml \
  -exec rm -rf {} +
  
qlever stop
qlever index
```