# Analyse des Kalliope-EAD-Dumps 

Kurz Einführung in EAD, seine Ausgestaltung im Kontext von Kalliope sowie Abwägungen zu resultierenden Modellierungsentscheidungen.

Wichtige Ressourcen: 

- [EAD-Anwenderprofil des Verbundkatalogs Kalliope](https://kalliope-verbund.info/files/480b012f45a0f002ec3095b6819ef8aea33078de.pdf)
- [Ressourcenerschließung mit Normdaten
in Archiven und Bibliotheken (RNAB) für Personen-, Familien-, Körperschaftsarchive und Sammlungen. Kontrollierte Vokabulare und Glossar](https://d-nb.info/1347313419/34)


## Hierarchie: `archdesc` und (verschachtelte) `c` 

Die wichtigsten Elemente sind:

`archdesc`: Top-Level, enthält Beschreibung des Bestands (z.B. Teilnachlass)

`c`: Mehrfach in `archdesc` enthalten, repräsentiert die Beschreibung einer Verzeichnungseinheit des Bestandes (z.B. Brief). Kann mehrfach ineinander verschachtelt sein. 
                
`archdesc/@level="collection"`: Enthalten in allen 60.971 Dateien. 

`c/@level`-Verteilung über alle 5.825.641 c-Elemente (ermittelt via `analyze_level.py`):

| Wert    | Anzahl    | Bedeutung                             |
| ------- | --------- | ------------------------------------- |
| `item`  | 5.035.960 | Verzeichnungseinheit (Einzelobjekt)   |
| `file`  | 664.354   | Verzeichnungseinheit (Akte, Konvolut) |
| `class` | 123.366   | Systematikpunkt                       |
| `fonds` | 1.961     | Teilbestand/-sammlung                 |

Ein Beispiel für eine solche XML-Datei findet sich auf [GitHub](https://github.com/sonar-idh/marketplace-backend/blob/feat/11-EAD2RiCO/ead2rico/ead_DE-1_5364_test.xml). Der gesamte Dump besteht aus 60971 XML-Dateien, von denen jede das Findbuch eines Bestands darstellt. 

Auf RiC-O-Modellierungsebene entsprechen Bestände der Entitätsklasse ``RecordSet`` und Verzeichnungseinheiten `Record`. Sie haben jeweils verschiedene Attribute (z.B. 'Bestandshaltende Institution', 'Entstehungsort'), deren aktuelle RiC-O-Übersetzung im entsprechenden [GitHub-Branch](https://github.com/sonar-idh/marketplace-backend/blob/feat/11-EAD2RiCO/ead2rico/readme.md) nachgeschlagen werden kann. 

Hier sieht man schon, dass `@role`-Attribute als Funktionsbezeichnungen eine wichtige Rolle für die Konversion spielen. Dieses Attribut kommt nur bei den Elementen ``persname`` (Personen),  ``corpname`` (Körperschaften) und ``geogname`` (Geographika) vor. (Entsprechen in etwa MARC Relator Codes, im Gegensatz zu diesen aber kein kontrolliertes Vokabular.) (Daten der Tabelle wurden via `analyze_role_coverage.py` ermittelt.)

| Element      | gesamt     | mit `@role` | ohne `@role` | % ohne `@role |
| ------------ | ---------- | ----------- | ------------ | ----------- |
| ``persname`` | 10.587.653 | 10.514.109  | 73.544       | 0,7%        |
| ``corpname`` | 7.593.677  | 7.539.825   | 53.852       | 0,7%        |
| ``geogname`` | 4.632.745  | 4.472.970   | 159.775      | 3,4%        |


## Personenrollen

 Distinkte Werte: 2026; Davon kommen 1701 (84%) seltener als 15 mal vor im Dump. Siehe auch `rollen_persname.tsv`.
 
```
4811759	Verfasser
3841631	Adressat
292672	Behandelt
287399	Korrespondenzpartner
205116	Erwähnt
172063	Dokumentiert
134508	Bestandsbildner
101037	Erwähnte Person
86398	Schreiber
42571	Behandelte Person
```

## Körperschaftsrollen

Distinkte Rollen: 423; Davon kommen 322 (76,1%) seltener als 15 mal vor im Dump. Siehe auch `rollen_corpname.tsv`.

```
3702502	Aufbewahrungsort
1522724	Bestandshaltende Institution
609697	Verfasser
506706	Adressat
350106	Bestandshaltende Einrichtung
306660	Besitzende Institution
184288	Korrespondenzpartner
78042	Behandelt
63066	Dokumentiert
50077	Eigentümer
```

**Frage: 'Aufbewahrungsort', 'Bestandshaltende Institution', 'besitzende Institution' und 'Eigentümer' unterscheiden und überschneiden sich semantisch. (Ähnlich wie 'Adressat' und 'Korrespondenzpartner'). Das Anwenderprofil gibt hierzu keine Erläuterung und die Felder werden häufig (aber nicht immer) in der Rolle des jeweils anderen verwendet. Die Angabe von 'Bestandshaltende Institution' sollte außerdem laut Anwenderprofil obligatorisch sein, ist de facto aber nur in 5137 (8,4%) der Dateien enthalten. Wer entscheidet, wie diese Rollenwerte behandelt werden? (Beispielsweise, ob sie zu einem Attribut zusammengeführt oder auf mehrere aufgeteilt werden?)**



## Geographika

 Distinkte Werte: 54; Davon kommen 44 (81,4%) seltener als 15 mal vor im Dump. Siehe auch `rollen_geogname.tsv`.

```
3708200	Entstehungsort
707339	PlaceOfOrigin
31104	Absendeort
11875	Zielort
5888	Erwähnter Ort
3425	Erscheinungsort
2232	Erwähnt
1486	Veranstaltungsort
862	Standort
300	Behandelt
```

## Normdatei- & Registerquelle `@source`

Neben der Rollenangabe `@role` können Personen, Körperschaften und Geographika auch ein Attribut zur Angabe einer Normdatei- oder Registerreferenz aufweisen. Daten auf Grundlage von `analyze_source.py` erzeugt, detaillierte Ergebnisse in `source_werte.tsv`.

```
-- <persname>: 10587653 Elemente gesamt --
      8188781  ( 77.3%)  'GND'  
      1140550  ( 10.8%)  'KPE' <-- Kalliope
       448999  (  4.2%)  '<kein @source-Attribut>'
       437803  (  4.1%)  'DE-2498' <-- ISIL DLA Marbach
       222576  (  2.1%)  'SLA' <-- Scweizerisches Literaturarchiv
       109803  (  1.0%)  'HelveticArchives'
        29862  (  0.3%)  'DE-MUS-853418-Objektdatenbank'
         9279  (  0.1%)  'DE-MUS-853418-Personendatenbank'

-- <corpname>: 7593677 Elemente gesamt --
      5875535  ( 77.4%)  'ISIL'
      1160913  ( 15.3%)  'GND'  
       341733  (  4.5%)  'KPE' <-- Kalliope
       113760  (  1.5%)  'DE-2498' <-- ISIL DLA Marbach
        75753  (  1.0%)  'SLA' <-- Scweizerisches Literaturarchiv
        17864  (  0.2%)  '<kein @source-Attribut>'
         4444  (  0.1%)  'DE-MUS-853418-Objektdatenbank' <-- ISIL SM Leipzig
         3675  (  0.0%)  'DE-MUS-853418-Personendatenbank' <-- ISIL SM Leipzig

-- <geogname>: 4632745 Elemente gesamt --
      3115275  ( 67.2%)  '<kein @source-Attribut>'
      1370584  ( 29.6%)  'GND'  
       146886  (  3.2%)  'DE-611' <-- ISIL Kalliope-Verbund
```

**Frage: Alle Quellen außer GND und ISIL sind nicht dereferenzierbar, da keine externen IDs angegeben wurden. Daraus folgt ein Modellierungsdilemma: Nicht-ISIL/GND-Agenten sind nur in begrenztem Umfang bzw. mit erheblichem Aufwand deduplizierbar (z.B, Rechtschreibfehler, verschiedene Schreibvarianten) → Konsequenz wäre, dass viele Agenten als zwei oder mehr Entitäten in die Datenbank eingehen würden, was die Enduser-Suche verkompliziert (und bei künftiger Einbindung der GND-Daten zu weiteren Problemen führen könnte). Alternativ könnte man pauschal alle Nicht-ISIL/GND-Agenten von der Transformation ausschließen, was mit einem erheblichen Datenverlust einhergehen würde.**   

**Frage: Wie mit KPE-Werten 'Unbekannt' (191.301) und 'Verschiedene' (2.763) umgehen?** (siehe `kpe_persname_werte.tsv` und `kpe_corpname_werte.tsv` aus `analyze_kpe_names.py`)

### `genreform` als Gattungsangabe 


5.905.748 `genreform`-Elemente, 622 distinkte Werte. Daten auf Grundlage von `analyze_genreform_values_source.py` erzeugt, detaillierte Ergebnisse in `genreform_werte_source.tsv`.

| Wert            | Anzahl    | Anteil | mit `@source` | Anteil mit `@source` |
| --------------- | --------- | ------ | ------------- | -------------------- |
| `Brief`         | 2.782.161 | 47,1 % | 2.774.154     | 99,7 %               |
| `Briefe`        | 726.868   | 12,3 % | 0             | 0,0 %                |
| `Dokument`      | 264.299   | 4,5 %  | 264.299       | 100,0 %              |
| `Handschrift`   | 233.730   | 4,0 %  | 21.929        | 9,4 %                |
| `Briefsammlung` | 200.143   | 3,4 %  | 379           | 0,2 %                |
| `Werk`          | 175.719   | 3,0 %  | 175.719       | 100,0 %              |
| `Verschiedenes` | 146.757   | 2,5 %  | 0             | 0,0 %                |
| `Autograf`      | 142.325   | 2,4 %  | 8.554         | 6,0 %                |
| `Korrespondenz` | 125.869   | 2,1 %  | 125.869       | 100,0 %              |
| `Prosa`         | 96.269    | 1,6 %  | 28.526        | 29,6 %


**Frage: Wie mit unterschiedlicher Erschließungstiefe, also der Existenz singulärer 'Brief'-Typen und Sammlungstypen wie 'Briefe', 'Korrespondenz' und 'Briefwechsel' umgehen? Entscheidet man sich dafür, Korrespondenzbeziehungen, die nur auf Sammlungsebene in Kalliope enthalten sind (also Sammlungen unabhängig von enthaltenen Einzelbriefen), auch abzubilden (und wenn ja, wie)?**

**Frage: `genreform`-Element-Werte haben oft auch GND-Referenzierung über `@source` und `@authfilenumber`. Allerdings wie oben in der Tabelle dargestellt nicht für alle Gattungstypen und nicht durchgehend. Nur Gattungs-String erfassen?**

## Wie sollen Korrespondenzbeziehungen dargestellt werden?

Kalliope enthält 5.886.612 Einheiten (`archdesc` und `c`), davon enthalten 4.348.337 (73,87%) eine Adressatenangabe (ermittelt mit `analyze_adressat.py`). (Davon enthalten 91% eine genreform-Angabe). Wie oben ersichtlich, existieren 2.782.161 Brief-Entitäten (von denen 96,4% eine Adressatenangabe beinhalten, siehe `analyze_genreform_values.py` und `analyze_brief_genreform_exact_match.py`). Daraus lässt sich folgern, dass es noch weitere `genreform`-Typen gibt, bei denen Adressaten angegeben wurden (z.B. 'Autograph', 'Kriegsbrief').

Vorschlag: Sämtliche Einheiten, die über eine Adressatenangabe über `@role` verfügen, für das Korrespondenznetzwerk nutzen.

**Offene Fragen:**

1. Wie mit uneinheitlich verwendeten Rollen umgehen? ('Aufbewahrungsort', 'Bestandshaltende Institution', 'besitzende Institution' und 'Eigentümer', zusammenführen oder differenzieren?) ('Adressat' und 'Korrespondenzpartner') - *Antwort: Es existiert ein kontrolliertes Vokabular für diese Attribute. Es werden nur Felder aufgenommen, die diesem Vokabular entsprechen. Für fehlende Felder 'undefined' angeben.*
2. Wie mit nicht über ISIL oder GND referenzierten Agenten und Geographika umgehen? Mögliche Vielfachaufnahme (Varianten, Rechtschreibfehler) in Kauf nehmen oder exkludieren? - *Antwort: Laut Projektantrag können nur referenzierte Entitäten aufgenommen werden.*
	1. Bei Präferenz für Aufnahme nicht-referenzierter Agenten: Ideen für Deduplikationstechniken? - *Antwort: Nicht notwendig, falls nur referenzierte Entitäten aufgenommen werden.*
3. Wie sollen die Adressatenwerte 'Unbekannt' (19000) und 'Verschiedene' (2673) modelliert werden? (Zu einer Entität zusammenführen oder exkludieren?) - *Antwort: Nachrangig, falls nur referenzierte Entitäten aufgenommen werden.*
4. Erschließungstiefe: Wie mit der Existenz singulärer 'Brief'-Typen und Sammlungstypen wie 'Briefe', 'Korrespondenz' und 'Briefwechsel' umgehen? Korrespondenzbeziehungen, die nur auf Sammlungsebene in Kalliope enthalten sind (also Sammlungen ohne enthaltene Einzelbriefe), abbilden, oder exkludieren (und wenn ja, wie)? - *Antwort: Nur referenzierte Gattungstypen aufnehmen, und davon vorrangig den singulären Brieftyp.*
5.  Nur `genreform`-Gattungs-Strings erfassen oder auch Normdateireferenzen? - *Antwort:*

## Analyse der Bestandshalter-Angabe

Gibt es im Dump eine einheitliche Angabe der bestandshaltenden Institution für jedes Findbuch? Dazu muss man prüfen, ob `archdesc/did/repository/corpname` in jedem Findbuch (genau einmal) vorkommt, ob es ein `@role`-Element enthält (und mit welchen Ausprägungen), ob es ein `@source`-Element enthält (und mit welchen Ausprägungen), sowie ob es ein `@authfilenumber`-Element enthält. Dies kann mit `analyze_repository_corpname_source.py` ermittelt werden.  

Ergebnis:

```
python3 analyze_dump/analyze_repository_corpname_source.py ead20260217/ead/ 8 
======================================================================
Dateien gesamt:                                          60971
Parse-Fehler:                                            0
archdesc/did/repository/corpname-Elemente gesamt:       60971

-- Vorkommen pro Findbuch --
  Dateien mit genau einem Element:                       60971
  Dateien OHNE das Element:                              0
  Dateien mit mehreren Elementen:                        0

-- @role-Werte --
      53139  ( 87.2%)  'Aufbewahrungsort'
       5137  (  8.4%)  'Bestandshaltende Institution'
       2486  (  4.1%)  'Bestandshaltende Einrichtung'
        174  (  0.3%)  'Besitzende Institution'
         20  (  0.0%)  'Vorbesitzer'
         15  (  0.0%)  'Eigentümer'
  davon mit @role-Attribut:                              60971
  davon OHNE @role-Attribut:                             0

-- @source-Werte --
      60971  (100.0%)  'ISIL'
  davon mit @source-Attribut:                            60971
  davon OHNE @source-Attribut:                           0

-- @authfilenumber-Attribut --
  davon mit @authfilenumber-Attribut:                    60971
  davon OHNE @authfilenumber-Attribut:                   0
```
