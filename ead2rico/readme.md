# Überblick Transformation EAD → RiC-O

`ead2rico_main.xsl` transformiert archivische Findmittel im Format **EAD 2002** nach **Records in Contexts – Ontology (RiC-O) 1.1** und gibt sie als **Turtle (RDF)** aus. 

- **Eingabe:** ein EAD-Dokument mit `<archdesc>` (Bestand) und beliebig tief verschachtelten `<c>`-Elementen (Verzeichnungseinheiten).
- **Ausgabe:** Turtle-Serialisierung in drei Sektionen: Bestand, Verzeichnungseinheiten und Agenten.
- **XSLT-Prozessor:** Saxon-HE bzw. SaxonC-HE (XSLT 3.0).

Die Transformation erfolgt über zwei Stylesheets. Während `ead2rico_main.xsl` den Einstiegspunkt und sämtliche Mapping-Regeln enthält, werden in `ead2rico_helpers.xsl` einige Hilfsfunktionen definiert. 

# Aufruf

```bash
saxonb-xslt -s:ead_DE-1_5364_test.xml -xsl:ead2rico_main.xsl -o:out.ttl
```

Oder über die SaxonC-HE-Python-Bindung:

```python
from saxonche import PySaxonProcessor
with PySaxonProcessor(license=False) as proc:
    exe = proc.new_xslt30_processor().compile_stylesheet(
        stylesheet_file="ead2rico_main.xsl")
    exe.transform_to_file(source_file="ead_DE-1_5364_test.xml",
                          output_file="out.ttl")
```

`ead2rico_helpers.xsl` muss im gleichen Verzeichnis wie `ead2rico_main.xsl` liegen (relativer `xsl:include href="ead2rico_helpers.xsl"`).

# Parameter

Folgende Parameter sind beim Aufruf überschreibbar (`base=…` etc.).

| Parameter   | Default                                     | Bedeutung                                                                                 |
| ----------- | ------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `base`      | `https://kalliope-verbund.info/ead?ead.id=` | Basis-IRI für Kalliope-Ressourcen (Records, Agenten, die nicht in der GND enthalten sind) |
| `gnd`       | `https://d-nb.info/gnd/`                    | Präfix für GND-Normdaten-URIs                                                             |
| `lang-base` | `http://id.loc.gov/vocabulary/iso639-2/`    | Präfix für ISO-639-2-Sprach-URIs                                                          |

# Verarbeitungsablauf

1. **`match="/"`** — schreibt die `@prefix`-Deklarationen, ruft das `archdesc`-Template auf und anschließend das benannte Template `agenten`.
2. **`match="e:archdesc"`** — erzeugt den `rico:RecordSet` (Bestand) und ruft per `apply-templates` alle `.//e:c` für die Verzeichnungseinheiten auf.
3. **`match="e:c"`** — erzeugt je einen `rico:Record`.
4. **`name="agenten"`** — sammelt alle Personen und Körperschaften aus dem gesamten Dokument, dedupliziert sie und schreibt einen Block pro Agent.

# Mapping EAD → RiC-O

## Bestandsebene: `archdesc` → `rico:RecordSet`

| EAD-Quelle                                               | RiC-O                       | Anmerkung                                   |
| -------------------------------------------------------- | --------------------------- | ------------------------------------------- |
| `@id`                                                    | (Subjekt-IRI)               | via `f:res-iri` → `base` + `@id`            |
| `did/unittitle`                                          | `rico:title`                | Literal                                     |
| `eadheader/eadid/@identifier`                            | `rico:identifier`           | nur falls vorhanden                         |
| `controlaccess/genreform[@source='GND']/@authfilenumber` | `rico:hasRecordSetType`     | GenreForm-GND-URI                           |
| `did/repository/corpname[@role='Aufbewahrungsort']`      | `rico:hasOrHadHolder`       | Agent-IRI                                   |
| `did/origination/persname[@role='Bestandsbildner']`      | `rico:hasOrganicProvenance` | nur „bekannte" Agenten (s. `f:known-agent`) |
| `dsc/c` (direkte Kinder)                                 | `rico:directlyIncludes`     | Verweis auf enthaltene Verzeichnungseinheit |

Optional (Auskommentiert): `rico:recordResourceExtent`, `rico:scopeAndContent`, `rico:history`.

## Verzeichnungseinheiten: `c` → `rico:Record`

| EAD-Quelle                                          | RiC-O                         | Anmerkung                                           |
| --------------------------------------------------- | ----------------------------- | --------------------------------------------------- |
| `@id`                                               | (Subjekt-IRI)                 | via `f:res-iri`                                     |
| `did/unittitle`                                     | `rico:title`                  | Literal                                             |
| `did/unitid[@label='Signatur']`                     | `rico:identifier`             | als offene Frage markiert (Signatur ≠ Identifier?)  |
| `controlaccess/genreform[@source='GND']`            | `rico:hasDocumentaryFormType` | Genreform-GND-URI                                   |
| `did/unitdate[@label='Entstehungsdatum']/@normal`   | `rico:creationDate`           | typisiert via `f:date-lit`                          |
| `controlaccess/persname[@role='Verfasser']`         | `rico:hasAuthor`              | nur bekannte Agenten                                |
| `controlaccess/persname[@role='Adressat']`          | `rico:hasAddressee`           | nur bekannte Agenten („Unbekannt" wird ausgelassen) |
| `controlaccess/geogname[@role='Entstehungsort']`    | `rico:isAssociatedWithPlace`  | derzeit Literal, kein Ort-Ressourcenverweis         |
| `did/langmaterial/language/@langcode`               | `rico:hasOrHadLanguage`       | ISO-639-2-URI                                       |
| `did/repository/corpname[@role='Aufbewahrungsort']` | `rico:hasOrHadHolder`         | Agent-IRI                                           |
| (Elternelement)                                     | `rico:isOrWasIncludedIn`      | nächstes `c` bzw. `archdesc`, siehe unten           |
| `did/physdesc/extent[@label='Umfang']`              | `rico:instantiationExtent`    | Literal                                             |

Das Elternelement wird über `(ancestor::e:c[1], ancestor::e:archdesc[1])[1]` ermittelt: bei verschachtelten `<c>` zeigt `isOrWasIncludedIn` auf das umschließende `c`, sonst auf den Bestand.

## Agenten: `persname` / `corpname` → `rico:Person` / `rico:CorporateBody`

Gruppiert über `xsl:for-each-group … group-by="f:agent-key(.)"`:

| EAD-Quelle                              | RiC-O                                                         |
| --------------------------------------- | ------------------------------------------------------------- |
| `local-name()`                          | `rico:Person` (persname) bzw. `rico:CorporateBody` (corpname) |
| `@normal` bzw. Elementtext              | `rico:name`                                                   |
| `@authfilenumber` (bei `@source='GND'`) | `rico:identifier`                                             |

Optional vorgesehen (auskommentiert): `rico:birthDate`/`rico:deathDate` aus der Anzeigeform `Name (1874–1951)` via `f:years`. Auskommentiert, da diese Daten künftig direkt aus der GND kommen sollen.

# Hilfsfunktionen (`ead2rico_helpers.xsl`)

|Funktion|Zweck|
|---|---|
|`f:esc($t)`|Escaped `\`, `"`, Zeilenumbruch, CR und Tab Turtle-konform|
|`f:lit($t[, $lang])`|Baut ein Turtle-String-Literal; mit optionalem Sprach-Tag. Zweite Signatur ohne `$lang` als Kurzform|
|`f:slug($t)`|Erzeugt Kleinbuchstaben-Slug (`[^a-z0-9]+` → `-`) für lokale IRIs|
|`f:res-iri($n)`|Ressourcen-IRI = `base` + `@id`|
|`f:agent-key($n)`|Gruppierungsschlüssel: `GND:<nr>` bei GND-Normdaten, sonst slug-basierter lokaler Schlüssel|
|`f:agent-iri($n)`|Agent-IRI: GND-URI bei GND-Normdaten, sonst `base` + `agent/` + Slug|
|`f:known-agent($n)`|`false`, wenn `@normal` oder Text exakt `Unbekannt` ist — filtert Pseudo-Agenten|
|`f:date-lit($raw)`|Typisiert `@normal`-Datumswerte (s. u.)|
|`f:years($t)`|Extrahiert via Regex zwei Jahreszahlen aus `(1874-1951)` (derzeit nur durch optionalen Code genutzt)|

## Datumstypisierung (`f:date-lit`)

|Eingabemuster|Ausgabe|
|---|---|
|`JJJJMMTT`|`"JJJJ-MM-TT"^^xs:date`|
|`JJJJ-MM-TT`|`"…"^^xs:date`|
|`JJJJMM`|`"JJJJ-MM"^^xs:gYearMonth`|
|`JJJJ-MM`|`"…"^^xs:gYearMonth`|
|`JJJJ`|`"JJJJ"^^xs:gYear`|
|sonst|untypisiertes Literal via `f:lit`|

## IRI- und Deduplizierungsstrategie

- **GND-Agenten** werden global über ihre GND-Nummer zusammengeführt (`agent-key = GND:<nr>`, `agent-iri = <gnd-präfix><nr>`). Mehrfachnennungen derselben Person im ganzen Dokument ergeben genau einen Agenten-Block.
- **Agenten ohne GND-Nummer** erhalten eine slug-basierte IRI unter `base`. Die Deduplizierung erfolgt hier rein über den Namens-Slug.

# Beispiel-Output (Auszug)

```turtle
@prefix rico: <https://www.ica.org/standards/RiC/ontology#> .
@prefix xs:   <http://www.w3.org/2001/XMLSchema#> .

<https://kalliope-verbund.info/ead?ead.id=DE-611-BF-5364> a rico:RecordSet ;
    rico:title "N.Mus.Nachl. 15 (Teilnachlass Arnold Schönberg)" ;
    rico:identifier "ead_5364_DE-1" ;
    rico:hasRecordSetType <https://d-nb.info/gnd/4123811-4> ;
    rico:hasOrganicProvenance <https://d-nb.info/gnd/118610023> ;
    rico:directlyIncludes <…=DE-611-HS-3685983> .

<…=DE-611-HS-3685983> a rico:Record ;
    rico:title "Brief von Arnold Schönberg an Unbekannt, 11.1934 …" ;
    rico:creationDate "1934-11"^^xs:gYearMonth ;
    rico:hasAuthor <https://d-nb.info/gnd/118610023> ;
    rico:isOrWasIncludedIn <…=DE-611-BF-5364> .

<https://d-nb.info/gnd/118610023> a rico:Person ;
    rico:name "Schönberg, Arnold" ;
    rico:identifier "118610023" .
```

Mit dem Testdatensatz `ead_DE-1_5364_test.xml` (1 Bestand, 39 Verzeichnungseinheiten) entstehen **555 valide Tripel**: 1 `RecordSet`, 39 `Record`, 8 `Person`, 3 `CorporateBody`.

# Bekannte Einschränkungen und offene Punkte

- **Lokale Holder-Deduplizierung greift nicht über Schreibvarianten.** Der Aufbewahrungsort erscheint im Bestand als „Staatsbibliothek zu Berlin. Musikabteilung [Musikabteilung]", in den `c`-Elementen als „Staatsbibliothek zu Berlin. Musikabteilung". Da beide keine GND-Nummer tragen, ergeben die unterschiedlichen Slugs **zwei separate lokale Agenten** für faktisch dieselbe Körperschaft.
- **`isAssociatedWithPlace` ist ein Literal**, kein Verweis auf eine Orts-/GND- Ressource. Orte werden derzeit nicht als eigene Entitäten modelliert.
- **`@source='KPE'`-Agenten** (z. B. „Unbekannt", `authfilenumber` aus KPE) werden über `f:known-agent` herausgefiltert; ihre `authfilenumber` fließt nicht als Identifier ein (nur GND-Quellen werden als `rico:identifier` geschrieben).
- **`unitid[@label='Signatur']` → `rico:identifier`** ist fraglich, ob diese Information für die Forschenden relevant ist. Eine eigene RiC-O-Entsprechung für Signaturen wäre zu prüfen.
- **Lebensdaten** (`f:years`, `rico:birthDate`/`rico:deathDate`) vorgesehener Bezug künftig direkt aus der GND.
