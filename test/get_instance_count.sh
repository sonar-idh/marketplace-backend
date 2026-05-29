curl -Gs http://127.0.0.1:7019 \
  --data-urlencode "query=PREFIX bf: <http://id.loc.gov/ontologies/bibframe/>SELECT (COUNT(?s) AS ?count) WHERE { ?s a bf:Instance }"