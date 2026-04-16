# SoNAR data provenance documentation

Data currently available in SoNAR is based on a subset of KALLIOPE. KALLIOPE is a Union Catalog for Archival Holdings. The focus is on personal papers, publisher‘s archives, and manuscript collections. The subset is restricted to those holdings [cataloged by the music department of the Berlin State Library](https://kalliope-verbund.info/query?q=&htmlFull=false&fq=ead.genre.index%3A%28%22Brief%22%29&lang=de&fq=ead.repository.index%3A%28%22Staatsbibliothek%20zu%20Berlin.%20Musikabteilung%22%29&lastparam=true).

The data is processed using [Apache NiFi](https://nifi.apache.org/) and imported into a [Qlever](https://docs.qlever.dev/) RDF-Store. NiFi implements an SRU-Crawler and transforms the source [MODS 3.7 to BIBFRAME 2.0 Conversion (2023 Version) as defined by the LOC](https://www.loc.gov/standards/mods/modsrdf/mods3-7-bibframe2-0-mapping.html). The transformation is implemented using XSLT and the [saxonb-xslt](https://manpages.debian.org/testing/libsaxonb-java/saxonb-xslt.1.en.html) processor. The exact transformation definition can be found in [SONAR_flowfile.json](./SONAR_flowfile.json).

Data from GND is used to enrich data about professions of Persons. The data is extracted from the [SPARQL Endpoint provided by DNB](https://sparql.dnb.de/gnd/) with the following query:

```sparql
CONSTRUCT {
  ?s <https://d-nb.info/standards/elementset/gnd#professionOrOccupationAsLiteral> ?o .
}
WHERE {
  ?s <https://d-nb.info/standards/elementset/gnd#professionOrOccupationAsLiteral> ?o .
}
```

The GND-Data is injected into the Qlever RDF-Store alongside the BIBFRAME RDF-Data. The integrated RDF-Data is transformed to CSV using the following SPARQL-Query in Qlever:

```sparql
PREFIX bf: <http://id.loc.gov/ontologies/bibframe/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT ?source ?sourceLabels ?sourceType ?sourceProfession ?target ?targetLabels ?targetType ?targetProfession ?direction ?relation ?reference ?date WHERE {
  BIND (STR("directed") AS ?direction)
  BIND (STR("hasCorrespondent") AS ?relation)
  ?work a bf:Work ;
        bf:contribution ?c1, ?c2 ;
        bf:originDate ?date ;
        bf:hasInstance ?instance .
  ?c1 bf:agent ?source ;
      bf:role <http://id.loc.gov/vocabulary/relators/cre> .
  ?source a ?sourceType .
  VALUES ?sourceType { <http://id.loc.gov/ontologies/bibframe/Person> <http://id.loc.gov/ontologies/bibframe/Organization> }
  ?c2 bf:agent ?target ;
      bf:role <http://id.loc.gov/vocabulary/relators/rcp> .
  ?target a ?targetType .
  VALUES ?targetType { <http://id.loc.gov/ontologies/bibframe/Person> <http://id.loc.gov/ontologies/bibframe/Organization> }
  FILTER (?c1 != ?c2)
  FILTER (DATATYPE(?date) = xsd:string || DATATYPE(?date) = "")
  # Referenz/Signatur von der Instance
  ?instance bf:identifiedBy [ rdf:value ?reference ] .
  # Labels ohne Zeilenexplosion: je Agent einmal voraggregieren
  {
    SELECT ?source (GROUP_CONCAT(DISTINCT STR(?l); SEPARATOR=" | ") AS ?sourceLabels) WHERE {
      OPTIONAL {
        ?source rdfs:label ?l
      }
    }
    GROUP BY ?source
  }
  {
    SELECT ?target (GROUP_CONCAT(DISTINCT STR(?l); SEPARATOR=" | ") AS ?targetLabels) WHERE {
      OPTIONAL {
        ?target rdfs:label ?l
      }
    }
    GROUP BY ?target
  }
  # Professions ohne Zeilenexplosion: je Agent einmal voraggregieren
  {
    SELECT ?source (GROUP_CONCAT(DISTINCT STR(?p); SEPARATOR=" | ") AS ?sourceProfession) WHERE {
      OPTIONAL {
        ?source <https://d-nb.info/standards/elementset/gnd#professionOrOccupationAsLiteral> ?p
      }
    }
    GROUP BY ?source
  }
  {
    SELECT ?target (GROUP_CONCAT(DISTINCT STR(?p); SEPARATOR=" | ") AS ?targetProfession) WHERE {
      OPTIONAL {
        ?target <https://d-nb.info/standards/elementset/gnd#professionOrOccupationAsLiteral> ?p
      }
    }
    GROUP BY ?target
  }
}
ORDER BY ?reference ?source ?target
```
