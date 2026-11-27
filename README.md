# QLever Data Ingestion Workflow 

This routine describes the workflow of creating a new QLever index for SoNAR. 

## Donwload GND Data

```bash
cd input_data
curl --output-dir ./gnd_data --create-dirs --remote-name-all -fL https://data.dnb.de/opendata/authorities-gnd-koerperschaft_lds.ttl.gz https://data.dnb.de/opendata/authorities-gnd-person_lds.ttl.gz https://data.dnb.de/opendata/authorities-gnd-sachbegriff_lds.ttl.gz
# This step will probably not be necessary in the future as GND dumps will be archived with Fedora 
```

## Remove existing export index files and start export index build

```bash
cd export_index
find . -mindepth 1 -maxdepth 1  ! -name Qleverfile ! -name Qleverfile-ui.yml -exec rm -rf {} +
qlever index # currently running instances of qlever-server should be stopped before
```

## Insert correspondence relation quads via script (repeat for insert_lifeDates.rq, insert_occupationLabels.rq, insert_relationTypes.rq)

```bash
qlever start
cd ../sparql_queries
curl -s "<host>:<port>"   --data-urlencode "update@insert_correspondence.rq"   --data-urlencode "timeout=3600s"   --data-urlencode "access-token=<token>"
# insert_relationTypes.rq should be part of input data in the future 
```

## Export inserted quads to .nq

```bash
curl -s http://<host>:<port> -H "Accept: text/tab-separated-values" --data-urlencode query@export_correspondence.rq --data-urlencode timeout=3600s --data-urlencode access-token=<token> | tail -n +2 | awk -F'\t' '{print $1" "$2" "$3" "$4" ."}' > corr.nq
```

## Check whether export ran without errors:

```bash
grep -c "An error has occurred" corr.nq  # hast to be 0
```

## Export aggregated attribute triples (lifeDates, occupationLabels) to .ttl

```bash
curl -s http://<host>:<port> -H "Accept: text/turtle" --data-urlencode query@export_aggRelations.rq > aggRel.ttl
```

## Format exported quad-datetypes to prevent ingestion error

```bash
sed -E 's#^(<[^>]*> <info:date> )(-?[0-9]{4}-[0-9]{2}-[0-9]{2})( <[^>]*> \.)$#\1"\2"^^<http://www.w3.org/2001/XMLSchema\#date>\3#' corr.nq > corr_fix.nq
rm corr.nq
mv corr_fix.nq corr.nq
grep -vE '^<[^>]*> <[^>]*> (<|")' corr.nq | head # Check if format is correct
```
 
 
## Move exported relation data to full index input data dir

```bash
mkdir ../input data/exported_data
mv corr.nq aggRel.ttl ../input data/exported_data/
```
 
## Build full index from all triples and quads

```bash
cd ../export_index
qlever stop
cd ../full_index
qlever index
```

