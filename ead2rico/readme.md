# Überblick Transformation EAD → RiC-O

`ead2rico_main.xsl` transformiert archivische Findmittel im Format **EAD 2002** nach **Records in Contexts – Ontology (RiC-O) 1.1** und gibt sie als **Turtle (RDF)** aus. 

- **Eingabe:** ein EAD-Dokument mit `<archdesc>` (Bestand) und beliebig tief verschachtelten `<c>`-Elementen (Verzeichnungseinheiten).
- **Ausgabe:** Turtle-Serialisierung in zwei Sektionen: Bestand und Verzeichnungseinheiten.
- **XSLT-Prozessor:** Saxon-HE bzw. SaxonC-HE (XSLT 3.0).

Die Transformation erfolgt über mehrere Stylesheets. `ead2rico_main.xsl` bildet den Einstiegspunkt und enthält die grundlegenden Mapping-Regeln.  `ead2rico_helpers.xsl` definiert Hilfsfunktionen zum Schreiben von RDF-Tripeln und `ead2rico_dates.xsl` enthält die Logik zur Verarbeitung der verschiedenen in Kalliope vorkommenden Datumsformate. 

# Aufruf

```bash
java -cp /usr/share/java/Saxon-HE.jar net.sf.saxon.Transform \
      -s:ead_DE-1_5364_test.xml -xsl:ead2rico_main.xsl -o:out.ttl
```

Oder über die SaxonC-HE-Python-Bindung:

```python
from saxonche import PySaxonProcessor

with PySaxonProcessor(license=False) as proc:
    exe = proc.new_xslt30_processor().compile_stylesheet(
        stylesheet_file="ead2rico_main.xsl"
    )
    exe.transform_to_file(source_file="ead_DE-1_5364_test.xml", output_file="out.ttl")
```

`ead2rico_helpers.xsl` und `ead2rico_dates.xsl` müssen im gleichen Verzeichnis wie `ead2rico_main.xsl` liegen (relative `xsl:include href="..."`).

# Präfixe

Die `@prefix`-Deklarationen werden fest im Stylesheet (`match="/"`) geschrieben:

| Präfix  | IRI                                              | Verwendung                                            |
| ------- | ------------------------------------------------- | ------------------------------------------------------ |
| `rico`  | `https://www.ica.org/standards/RiC/ontology#`     | RiC-O-Klassen und -Properties                           |
| `xs`    | `http://www.w3.org/2001/XMLSchema#`               | Datumstypisierung                                       |
| `gnd`   | `https://d-nb.info/gnd/`                          | GND-Normdaten (Personen, Körperschaften, Genreformen)   |
| `isil`  | `https://isil.staatsbibliothek-berlin.de/isil/`   | ISIL-referenzierte Aufbewahrungsorte                    |
| `kpe`   | `https://kalliope-verbund.info/ead?ead.id=`       | Kalliope-eigene Ressourcen (Bestand, Verzeichnungseinheiten) |
| `rdf`, `rdfs`, `sonar` | – | deklariert, aktuell aber im Mapping ungenutzt (siehe „Bekannte Einschränkungen") |

# Verarbeitungsablauf

1. **`match="/"`** — schreibt die `@prefix`-Deklarationen und ruft das `archdesc`-Template auf.
2. **`match="*:archdesc"`** — erzeugt den `rico:RecordSet` (Bestand) und ruft per `apply-templates` alle `.//*:c` im Dokument auf (nicht nur direkte `dsc/c`-Kinder).
3. **`match="*:c"`** — erzeugt einen `rico:Record` **nur**, wenn `controlaccess/genreform` den Wert `Brief` hat; alle anderen `<c>`-Elemente werden ignoriert.

Es gibt aktuell kein Template zur Erzeugung eigener Agenten-Ressourcen (`rico:Person`/`rico:CorporateBody`) mehr, da Personen und Körperschaften nur noch als externe IRI (GND/ISIL) referenziert werden, siehe „IRI-Strategie" unten.

# Mapping EAD → RiC-O

## Bestandsebene: `archdesc` → `rico:RecordSet`

| EAD-Quelle                                                          | RiC-O                       | Anmerkung                                                        |
| --------------------------------------------------------------------- | ---------------------------- | ------------------------------------------------------------------ |
| `@id`                                                                | (Subjekt-IRI)                | `kpe:` + `@id`                                                    |
| `did/unittitle`                                                      | `rico:title`                 | Literal                                                            |
| `@id`                                                                | `rico:identifier`            | Literal (derselbe Wert wie die Subjekt-IRI)                        |
| `controlaccess/genreform[@source='GND']/@authfilenumber`            | `rico:hasRecordSetType`      | als `gnd:<authfilenumber>`                                        |
| `did/repository/corpname[@source='ISIL']/@authfilenumber`           | `rico:hasOrHadHolder`        | als `isil:<authfilenumber>`; `@role` wird nicht mehr geprüft       |
| `did/origination/persname[@role='Bestandsbildner' und @source='GND']/@authfilenumber` | `rico:hasOrganicProvenance` | als `gnd:<authfilenumber>`                                        |
| `dsc//c[controlaccess/genreform='Brief']`                           | `rico:includesTransitive`    | über alle Ebenen, gefiltert auf Brief-Verzeichnungseinheiten; offene Frage im Code, ob stattdessen `rico:includesOrIncluded` passender wäre |

Optional (auskommentiert): `rico:recordResourceExtent`, `rico:scopeAndContent`, `rico:history`.

## Verzeichnungseinheiten: `c` → `rico:Record`

Wird nur erzeugt, wenn `controlaccess/genreform = 'Brief'`.

| EAD-Quelle                                                | RiC-O                         | Anmerkung                                                  |
| ------------------------------------------------------------ | ------------------------------- | ------------------------------------------------------------ |
| `@id`                                                       | (Subjekt-IRI)                  | `kpe:` + `@id`                                              |
| `did/unittitle`                                             | `rico:title`                   | Literal                                                      |
| `controlaccess/genreform[@source='GND']/@authfilenumber`   | `rico:hasDocumentaryFormType`  | als `gnd:<authfilenumber>`                                  |
| `did/unitdate[@label='Entstehungsdatum']/@normal`          | `rico:beginningDate`, `rico:endDate` | beide immer `^^xs:date`, siehe „Datumsverarbeitung"    |
| `controlaccess/persname[@role='Verfasser' und @source='GND']/@authfilenumber` | `rico:hasAuthor`  | als `gnd:<authfilenumber>`                                  |
| `controlaccess/persname[@role='Adressat' und @source='GND']/@authfilenumber`  | `rico:hasAddressee` | als `gnd:<authfilenumber>`                                  |
| (Elternelement)                                             | `rico:isOrWasIncludedIn`       | zeigt derzeit immer auf den Bestand, siehe unten             |

Das Elternelement wird über `ancestor::*:archdesc[1]` ermittelt: `isOrWasIncludedIn` zeigt momentan bei jedem `rico:Record` auf den Bestand, unabhängig von der `<c>`-Verschachtelungstiefe im Quelldokument. Das ist ein bewusster Platzhalter (siehe „Bekannte Einschränkungen") — die korrekte Nachbildung der Verschachtelungsstruktur (Verweis auf das jeweils umschließende `<c>`, falls dieses selbst ein `rico:Record` ist) ist ein offener Folgeschritt.

Aktuell auskommentiert (nicht aktiv): `rico:identifier` aus `unitid[@label='Signatur']`, `rico:isAssociatedWithPlace` aus `geogname[@role='Entstehungsort']`, `rico:hasOrHadLanguage` aus `langmaterial/language/@langcode`, `rico:scopeAndContent`, `rico:hasOrHadHolder` (Record-Ebene), `rico:instantiationExtent`.

# Hilfsfunktionen (`ead2rico_helpers.xsl`)

| Funktion         | Zweck                                                                 |
| ------------------ | ------------------------------------------------------------------------ |
| `f:lit($t)`      | Baut ein Turtle-String-Literal (`normalize-space` + Escaping via `f:esc`) |
| `f:esc($t)`      | Escaped `\`, `"`, Zeilenumbruch, CR und Tab Turtle-konform                |

Frühere Hilfsfunktionen zur IRI-Bildung, Agenten-Deduplizierung und Datumstypisierung (`f:res-iri`, `f:slug`, `f:agent-key`, `f:agent-iri`, `f:known-agent`, `f:date-lit`, `f:years`) gibt es nicht mehr — IRIs werden inline gebildet (s. u.), die Datumslogik liegt vollständig in `ead2rico_dates.xsl`.

# Datumsverarbeitung (`ead2rico_dates.xsl`)

Verarbeitet `unitdate/@normal`-Werte in drei Schritten:

1. **`f:parse-normal($normal)`** — Einstiegspunkt. Erkennt Zeitspannen (`.../ ...`-getrennt) und ruft für Einzeldaten bzw. beide Enden einer Zeitspanne `f:token()` auf. Bei einer Zeitspanne werden `begin`/`end` über `min()`/`max()` gebildet statt direkt aus dem ersten/zweiten Token übernommen — das fängt in Kalliope vorkommende vertauschte Bereichsgrenzen ab (`swapped`-Flag im Ergebnis).
2. **`f:token($raw)`** — erkennt das Eingabeformat per Regex (`YYYY-MM-DD`, `YYYY-MM`, `YYYYMMDD`, `YYYYMM`, `YYYY`) und ruft `f:ymd()` mit den erkannten Werten auf.
3. **`f:ymd($y, $m, $d)`** — löst die Präzision auf: `$m = 0` → Jahrespräzision (`begin` = 1.1., `end` = 31.12.), `$d = 0` → Monatspräzision (`begin`/`end` = erster/letzter Tag des Monats via `f:last-day`), sonst Tagespräzision. Kalendarisch ungültige Tagesangaben (z. B. `20130231`) werden nicht verworfen, sondern über `f:day-safe` erkannt und auf Monatspräzision zurückgeführt (`prec: 'month-repaired'`).

Rückgabe ist jeweils eine `map(*)` mit `prec` (`year`/`month`/`day`/`month-repaired`/`range`), `key`, `begin` und `end` (beide `xs:date`), oder `()` bei leerem/nicht erkanntem Wert.

**Wichtig:** `rico:beginningDate`/`rico:endDate` werden unabhängig von der erkannten Präzision immer als `xs:date` ausgegeben (Jahres-/Monatsangaben werden auf die jeweilige Vollzeitspanne aufgelöst), nicht als `xs:gYear`/`xs:gYearMonth`. Nur so können vergleichende Datumsabfragen via SPARQL gewährleistet werden.

# IRI-Strategie

Es gibt keine lokale Agenten-Materialisierung oder -Deduplizierung mehr. Ressourcen-IRIs werden direkt aus den Quelldaten gebildet:

- **Eigene Ressourcen** (Bestand, Verzeichnungseinheiten): `kpe:` + `@id`.
- **GND-referenzierte Entitäten** (Personen, Körperschaften, Genreformen): `gnd:` + `@authfilenumber`, nur wenn `@source='GND'` und `@authfilenumber` vorhanden sind. Es wird lediglich auf die GND-IRI verwiesen, es entsteht kein eigenes `rico:Person`/`rico:CorporateBody`-Tripel im Output.
- **ISIL-referenzierte Aufbewahrungsorte**: `isil:` + `@authfilenumber`.
- Alles ohne GND-/ISIL-Referenz (z. B. „Unbekannt", reine KPE-Angaben) wird bei den entsprechenden Properties schlicht nicht geschrieben.

# Tests

`tests/test_ead_xslt.py` (pytest) ruft `ead2rico_main.xsl` per Saxon-HE-Subprozess auf zwei Quelldateien auf und prüft den resultierenden Turtle-Output mit `rdflib`:


| Fixture | Quelldatei | Zweck |
| --------- | ------------ | ------- |
| `graph` | `ead_DE-1_5364_test.xml` | realer Kalliope-Auszug; prüft das Mapping am tatsächlichen Datenbild |
| `transform_snippet` | `tests/ead_test_snippet.xml` | minimales, handgeschriebenes EAD-Dokument für gezielte Einzelfälle, die im realen Auszug nicht vorkommen |

**Abgedeckte Fälle:**

- **Turtle-Validität** — Output ist parsebares, nicht-leeres Turtle
- **Bestand (RecordSet)** — `rico:title`, `rico:identifier`, `rico:hasRecordSetType`, `rico:hasOrHadHolder`, `rico:hasOrganicProvenance` (mehrere Bestandsbildner), `rico:includesTransitive` (Anzahl muss zur Anzahl der Brief-`<c>` im Testdatensatz passen)
- **Verzeichnungseinheiten (Record)** — Anzahl der erzeugten `rico:Record` passend zur Anzahl Brief-`<c>`, `rico:isOrWasIncludedIn`, `rico:hasAuthor`/`rico:hasAddressee`, sowie dass ein Adressat ohne GND-Referenz (z. B. „Unbekannt") korrekt **nicht** übernommen wird
- **Filterlogik** — ein `<c>` ohne `genreform='Brief'` erzeugt keinen `rico:Record` (`ead_test_snippet.xml`)
- **Escaping** — Titel mit Anführungszeichen/Backslash überstehen die Turtle-Serialisierung und lassen sich unverändert zurückparsen (`ead_test_snippet.xml`)
- **Datumsverarbeitung** — Jahres-, Monats- und Tagespräzision, Zeitspannen (auch mit vertauschten Grenzen), kalendarisch ungültige Tage (Rückfall auf Monatsgrenzen), fehlendes/nicht erkennbares `@normal` (keine Datums-Tripel), sowie dass `rico:beginningDate`/`rico:endDate` im gesamten Output immer als `^^xs:date` typisiert sind

# Beispiel-Output (Auszug)

```turtle
@prefix rico: <https://www.ica.org/standards/RiC/ontology#> .
@prefix xs:   <http://www.w3.org/2001/XMLSchema#> .
@prefix gnd:  <https://d-nb.info/gnd/> .
@prefix isil: <https://isil.staatsbibliothek-berlin.de/isil/> .
@prefix kpe:  <https://kalliope-verbund.info/ead?ead.id=> .

kpe:DE-611-BF-5364 a rico:RecordSet ;
    rico:title "N.Mus.Nachl. 15 (Teilnachlass Arnold Schönberg)" ;
    rico:identifier "DE-611-BF-5364" ;
    rico:hasRecordSetType gnd:4123811-4 ;
    rico:hasOrHadHolder isil:DE-1 ;
    rico:hasOrganicProvenance gnd:118610023 ;
    rico:includesTransitive kpe:DE-611-HS-3685983 ,
                             kpe:DE-611-HS-3859381 .

kpe:DE-611-HS-3859381 a rico:Record ;
    rico:title "Brief von Arnold Schönberg an Josef Rufer, 18.12.1947" ;
    rico:hasDocumentaryFormType gnd:4008240-4 ;
    rico:beginningDate "1947-12-18"^^xs:date ;
    rico:endDate "1947-12-18"^^xs:date ;
    rico:hasAuthor gnd:118610023 ;
    rico:hasAddressee gnd:116701218 ;
    rico:isOrWasIncludedIn kpe:DE-611-BF-5364 .
```

# Bekannte Einschränkungen und offene Punkte

- **Nur `<c>` mit `genreform = 'Brief'` werden zu `rico:Record`.** `rico:isOrWasIncludedIn` zeigt deshalb bewusst und einheitlich auf den übergeordneten Bestand (`ancestor::*:archdesc[1]`), statt auf das nächste umschließende `<c>`. Das umgeht vorerst das Problem hängender Referenzen auf `<c>`-Elemente, die selbst kein `rico:Record` sind. Die korrekte `<c>`-Verschachtelungsstruktur (Records innerhalb von Records) soll später nachgebildet werden; markiert mit TODO in `ead2rico_main.xsl`.
- **Keine Agenten-Entitäten mehr im Output.** Personen und Körperschaften werden nur noch als GND-/ISIL-IRI referenziert, es entstehen keine eigenen `rico:Person`/`rico:CorporateBody`-Tripel mehr. Agenten ohne GND-/ISIL-Nummer (z. B. „Unbekannt") tauchen im Output gar nicht mehr auf.
- **`rico:includesTransitive` vs. `rico:includesOrIncluded`** — Welche Property soll für Beziehungen zwischen Bestand und Verzeichnungseinheit benutzt werden? (`ead2rico_main.xsl`). Außerdem wird die `c`-Verschachtelungsstruktur beim Erzeugen dieser Kante aktuell ausgeblendet.
- **Mehrere Properties sind auskommentiert/inaktiv:** `rico:identifier` (Signatur), `rico:isAssociatedWithPlace`, `rico:hasOrHadLanguage`, `rico:scopeAndContent`, `rico:hasOrHadHolder` auf Record-Ebene, `rico:instantiationExtent`. Auch offen: ob `unitid[@label='Signatur']` überhaupt als `rico:identifier` sinnvoll ist, oder ob es dafür eine eigene RiC-O-Entsprechung bräuchte.
- **`did/repository/corpname[@role='Aufbewahrungsort']`** wird bislang nur auf Bestandsebene ausgewertet.
