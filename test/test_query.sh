#!/bin/bash
curl -Gs http://127.0.0.1:7019 \
  --data-urlencode "query=SELECT * WHERE { ?s ?p ?o } LIMIT 10"

