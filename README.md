# Datenfluss von Kalliope zu QLever mit Apache NiFi
- Durchstich exemplarisch anhand der Briefsammlung der Musikabteilung in Kalliope
- Das Zusammenspiel von NiFi und QLever legt nahe, dass Inbetriebnahme und fortlaufende Aktualisierung der Graphdatenbank in zwei separate Phasen aufgeteilt werden:
	1. **Initiales Retrieval**: Alle vorliegenden Einträge bis zu einem gewissen Cutoff-Datum werden mithilfe von Skripten via SRU abgefragt und in das Turtle-Zielformat transformiert. Daraufhin erfolgt auf dieser Datengrundlage die Initialisierung der Graphdatenbank.
	2. **Kontinuierliche Aktualisierung**: Im Laufe des Betrieb wird mittels Apache NiFi periodisch geprüft, ob sich seit dem letzten Cutoff-Datum Einträge geändert haben. Falls ja, werden diese Einträge abgefragt, transformiert, und in die Datenbank geladen. Zudem muss auch in periodischen Zeitabständen geprüft werden, ob der Index der Datenbank neu berechnet werden muss. 
- Im Folgenden werden relevante Dateien sowie der Workflow der beiden Phasen dargestellt 
## 0. Vorbereitung
### Python-Umgebung
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install lxml
pip install saxonche
```
### `rapper`
```bash
sudo apt-get update 
sudo apt-get install raptor2-utils
```

## 1. Initiales Retrieval
### `get_paginated_initial_records.sh`
- Ruft alle Kalliope-Einträge **vor** dem Cutoff-Datum (100 Einträge jede halbe Sekunde) im MODS37-Format ab und speichert sie im Ordner `./initial_dump_raw` — dauert für circa 146000 Testeinträge etwa 20 Minuten
### `transform_to_rdf_optimized.py`
- verarbeitet die in `./initial_dump_raw` abgelegten Einträge via Multiprocessing: Worker-Funktion `process_page` verarbeitet eine Inputdatei, extrahiert mit der Library `lxml` mods-Wurzelelemente, saxon transformiert mods zu BIBFRAME-RDFXML, `rapper` letzteres nach Turtle. Einträge werden im Ordner `bibframe_ttl` zwischengespeichert und am Ende in der zentralen Datei `initial_dump.ttl` zusammengeführt. Dauer lokal circa 5 Minuten. 
### Indexierung: Initialer QLever-Datensatz
```bash
export QLEVER_ACCESS_TOKEN="YOUR_ACCESS_TOKEN" 
cd db/
qlever index
qlever start
```
- `initial_dump.ttl` wird als Inputfile in `db/Qleverfile` angegeben, dann `qlever index` — Dauer lokal etwa 43 Sekunden 
## 2. Kontinuierliche Aktualisierung 

- Flow Definition kann durch die Datei `checkKalliope.json` direkt in NiFi importiert werden

### 1. GenerateFlowFile
- als CRON-Job jeden Tag eine leere FlowFile erzeugen 
	- (um manuell Retrieval in NiFi zu starten, entweder hier *RunOnce* oder bei Folgeprozessor direkt *Create FlowFile*)
### 2. Letztes Modifikationsdatum: State lesen mit ExecuteScript in Groovy
- Groovy ist eine Programmiersprache, die auf der **Java Virtual Machine (JVM)** läuft — also derselben Umgebung wie NiFi selbst. Groovy-Code kann direkt auf NiFi-interne Java-Objekte zugreifen, ohne Umwege.
#### Groovy-Skript
```groovy
import org.apache.nifi.components.state.Scope

// State dieses Prozessors lesen (LOCAL = nur auf dieser NiFi-Instanz)
def stateMap = context.stateManager.getState(Scope.LOCAL).toMap()

// last.run.date lesen, Fallback: 20250101 (unser initialer Cutoff)
def lastDate = stateMap['last.run.date'] ?: '20250101'

// Das FlowFile vom Input holen (das leere vom GenerateFlowFile)
def ff = session.get()
if (!ff) return

// Datum als Attribut der FlowFile hinzufügen
ff = session.putAttribute(ff, 'sru.from.date', lastDate)

// FlowFile weiterschicken
session.transfer(ff, REL_SUCCESS)
```

### 3. State mit aktuellem Abfragedatum updaten
- Neues Cutoff-Datum wird auf das Datum der laufenden Aktualisierung gesetzt
#### Groovy-Skript
```groovy
import org.apache.nifi.components.state.Scope
import java.time.LocalDate
import java.time.format.DateTimeFormatter

def ff = session.get()
if (!ff) return

// Heutiges Datum im Format YYYYMMDD
def today = LocalDate.now().format(DateTimeFormatter.ofPattern('yyyyMMdd'))

// State aktualisieren
def stateManager = context.stateManager
def currentState = stateManager.getState(Scope.LOCAL).toMap()

// Neuen State mit aktuellem Datum erstellen
def newState = new HashMap(currentState)
newState['last.run.date'] = today

// State speichern
stateManager.setState(newState, Scope.LOCAL)

// Datum auch als Attribut mitgeben 
ff = session.putAttribute(ff, 'sru.to.date', today)

session.transfer(ff, REL_SUCCESS)
```
### 4. Gesamtzahl der geänderten Einträge abfragen mit InvokeHTTP
##### Teilschritt A: URL zusammenbauen — UpdateAttribute
- URL als neues Attribut mit letztem Modifikationsdatum erzeugen

| Attributname | Wert                                                                                                                                                                                                                                                                                                           |
| ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `sru.url`    | `https://kalliope-verbund.info/sru?version=1.2&operation=searchRetrieve&recordSchema=mods37&maximumRecords=1&query=ead.genre.index%3D(%22Brief%22)%20AND%20ead.repository.index%3D(%22Staatsbibliothek%20zu%20Berlin.%20Musikabteilung%22)%20AND%20ead.modificationdate.normal%20%3E%20%22${sru.from.date}%22` |

##### Teilschritt B: HTTP-Request abschicken — InvokeHTTP
**Connections:**

InvokeHTTP hat mehrere Ausgänge:

| Relation   | Bedeutung                            | Verbinden mit                        |     |
| ---------- | ------------------------------------ | ------------------------------------ | --- |
| `Response` | HTTP-Antwort (das XML)               | → nächster Prozessor (EvaluateXPath) |     |
| `Success`  | Das originale FlowFile (unverändert) | → `LogAttribute` oder terminieren    |     |
| `Failure`  | Verbindungsfehler                    | → `LogAttribute`                     |     |
| `No Retry` | HTTP-Fehler (4xx)                    | → `LogAttribute`                     |     |
| `Retry`    | Temporäre Fehler (5xx)               | → zurück zu InvokeHTTP               |     |
*Hier Ist wichtig, dass die Proxyeinstellungen für SPK auf NiFi stimmen: ``StandardProxyConfigurationService`` anlegen und dann:*

| Feld | Wert |
| --- | --- | 
|Proxy Type | `HTTP`
|Proxy Server Host | `proxy.spk-berlin.de`
|Proxy Server Port | `3128`

- außerdem bei allen InvokeHTTP Request User-Agent: `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36` und Response Cookie Strategy ACCEPT_ALL
### 5. Record-Gesamtzahl aus XML mit EvaluateXPath lesen

**Tab "Properties":**

|Einstellung|Wert|Erklärung|
|---|---|---|
|Destination|`flowfile-attribute`|Ergebnis als Attribut speichern, nicht den Inhalt ersetzen|
|Return Type|`string`|Wir wollen einen Text-Wert, keine XML-Node|

Dann **"+" klicken** für das neue Attribut:

|Attributname|XPath-Ausdruck|
|---|---|
|`sru.total`|`//*[local-name()='numberOfRecords']/text()`|

---

#### Was bedeutet dieser XPath-Ausdruck?

```
//*[local-name()='numberOfRecords']/text()
```

|Teil|Bedeutung|
|---|---|
|`//`|Suche überall im Dokument, egal wie tief|
|`*`|Irgendein Element|
|`[local-name()='numberOfRecords']`|...dessen Name `numberOfRecords` ist|
|`/text()`|Gib mir den Textinhalt davon|

Warum `local-name()` statt einfach `srw:numberOfRecords`? Weil XPath Namespaces kennen muss, wenn `srw:` verwendet wird. Mit `local-name()` umgehst man das.
### 6. Paginierte FlowFiles erstellen
- Groovy-Skript liest `sru.total` (z.B. `250`), also die Anzahl der Treffer für die in Schritt 4b abgeschickte Anfrage, und rechnet aus wie viele Seiten das sind, und erzeugt **für jede Seite ein eigenes FlowFile** mit dem passenden `startRecord`-Attribut. Danach laufen alle FlowFiles **parallel** durch die Pipeline.
#### Skript
```groovy
import org.apache.nifi.components.state.Scope
import java.net.URLEncoder

def ff = session.get()
if (!ff) return

// Gesamtzahl und Datum aus den Attributen lesen
int total = ff.getAttribute('sru.total') as int
def fromDate = ff.getAttribute('sru.from.date')
int pageSize = 100

// Wenn keine Records geändert wurden: FlowFile wegwerfen und aufhören
if (total == 0) {
    log.info('Keine geänderten Records gefunden.')
    session.remove(ff)
    return
}

// Für jede Seite ein neues FlowFile erzeugen
(1..total).step(pageSize) { startRecord ->

    // URL für diese Seite bauen
    def query = 'ead.genre.index=("Brief") AND ' +
                'ead.repository.index=("Staatsbibliothek zu Berlin. Musikabteilung") AND ' +
                'ead.modificationdate.normal > "' + fromDate + '"'

    def encodedQuery = URLEncoder.encode(query, 'UTF-8')
    def pageUrl = 'https://kalliope-verbund.info/sru' +
                  '?version=1.2' +
                  '&operation=searchRetrieve' +
                  '&recordSchema=mods37' +
                  '&startRecord=' + startRecord +
                  '&maximumRecords=' + pageSize +
                  '&query=' + encodedQuery

    // Neues FlowFile erzeugen (Kopie des originalen)
    def newFF = session.create(ff)
    newFF = session.putAttribute(newFF, 'sru.start.record', startRecord as String)
    newFF = session.putAttribute(newFF, 'sru.page.url', pageUrl)
    newFF = session.putAttribute(newFF, 'sru.from.date', fromDate)

    session.transfer(newFF, REL_SUCCESS)
}

// Das originale FlowFile entfernen — wir brauchen es nicht mehr
session.remove(ff)
```
### 7. Alle SRU-Pages mit InvokeHTTP abrufen

- zuvor ControlRate-Prozessor mit TimeOut (z.B. 3s), um SRU nicht zu überlasten.

| Property              | Value           |
| --------------------- | --------------- |
| Rate Control Criteria | flowfile count  |
| Time Duration         | 3 s             |
| Maximum Rate          | 1               |

**HTTP-Konfiguration**

| Property | Value           |
| -------- | --------------- |
| HTTP URL | ${sru.page.url} |
### 8. modsCollection aus SRU-Pages extrahieren
- **Ziel**: aus der SRU-Antwort nur die `mods:mods`-Elemente rausziehen und per XSLT-Transformation (TransformXml-Prozessor) in eine `modsCollection` einwickeln
#### XSLT-Datei
```xml
<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:mods="http://www.loc.gov/mods/v3">
  <xsl:output method="xml" encoding="UTF-8" indent="yes"/>
  <xsl:template match="/">
    <mods:modsCollection>
      <xsl:copy-of select="//mods:mods"/>
    </mods:modsCollection>
  </xsl:template>
</xsl:stylesheet>
```
### 9. Transformation von MODS nach BIBFRAME RDF/XML mit Saxon

ExecuteScript: XSLT-2.0-Transformation mit Saxon HE

1. FlowFile holen (das resultierende XML aus Schritt 8)
2. Inhalt als Text auslesen
3. Kurze Prüfung: Ist es MODS?
4. Saxon initialisieren
5. Das Übersetzungsrezept (XSLT) laden
6. Transformation ausführen. Das Ergebnis ist RDF/XML
7. Das RDF/XML in das FlowFile zurückschreiben (ersetzt das MODS-XML)
8. FlowFile weiterschicken

---

#### 1. Modul-Ordner anlegen und Saxon HE herunterladen

Saxon darf **nicht** in `lib/` liegen — dort würde es sich als System-XML-Transformer registrieren und NiFi am Starten hindern. Stattdessen kommt es in einen separaten Modul-Ordner, der nur für den ExecuteScript-Processor sichtbar ist:

```bash
mkdir -p ~/your_nifi_folder/modules
cd ~/your_nifi_folder/modules
wget https://artefakt.dev.sbb.berlin/repository/maven-central/net/sf/saxon/Saxon-HE/12.7/Saxon-HE-12.7.jar
```

#### 2. Abhängigkeit xmlresolver hinzufügen

Saxon 12.x braucht die `xmlresolver`-Bibliothek. Sie liegt bereits in NiFi's internen Paketen und kann direkt kopiert werden:

```bash
cp ~/your_nifi_folder/work/nar/extensions/nifi-standard-nar-2.9.0.nar-unpacked/NAR-INF/bundled-dependencies/xmlresolver-5.3.3.jar ~/nifi-2.9.0/modules/
cp ~your_nifi_folder/work/nar/extensions/nifi-standard-nar-2.9.0.nar-unpacked/NAR-INF/bundled-dependencies/xmlresolver-5.3.3-data.jar ~/nifi-2.9.0/modules/
```

Der `modules/`-Ordner enthält danach:

```
modules/
├── Saxon-HE-12.7.jar
├── xmlresolver-5.3.3.jar
└── xmlresolver-5.3.3-data.jar
```

#### 3. XSLT-Ordner anlegen mit korrekter Struktur

Das Stylesheet referenziert intern die Datei `conf/languageCrosswalk.xml` als relativen Pfad. Diese muss als Unterordner neben dem Stylesheet liegen:

```bash
mkdir -p ~/your_nifi_folder/xslt/conf
cp MODS3-7_Bibframe2-0_XSLT2-0_20230505.xsl ~/your_nifi_folder/xslt/
cp languageCrosswalk.xml ~/your_nifi_folder/xslt/conf/
```

Resultierende Struktur:

```
xslt/
├── MODS3-7_Bibframe2-0_XSLT2-0_20230505.xsl
└── conf/
    └── languageCrosswalk.xml
```

#### 4. NiFi neu starten

```bash
~/your_nifi_folder/bin/nifi.sh restart
```

#### 5. ExecuteScript-Processor konfigurieren

| Tab        | Property         | Wert                         |
| ---------- | ---------------- | ---------------------------- |
| Properties | Script Engine    | `Groovy`                     |
| Properties | Module Directory | `~/your_nifi_folder/modules` |

Ohne `Module Directory` findet Groovy die Saxon-Klassen nicht.

#### 6. ExecuteScript-Body

```groovy
import net.sf.saxon.s9api.*
import javax.xml.transform.stream.StreamSource

// 1. Das aktuelle FlowFile aus der Warteschlange holen
def ff = session.get()
if (!ff) return  // Wenn keins da ist: nichts tun

// 2. Den XML-Inhalt des FlowFiles als Text lesen
def xmlContent = ''
session.read(ff, { inputStream ->
    xmlContent = inputStream.text
} as InputStreamCallback)

// 3. Prüfen ob überhaupt MODS-Daten drin sind
if (!xmlContent.contains('modsCollection')) {
    log.warn("Kein MODS-Inhalt gefunden, FlowFile wird verworfen")
    session.remove(ff)
    return
}

try {
    // 4. Saxon starten — vollständiger Klassenname nötig, da NiFi ein eigenes
    //    Processor-Interface hat, das sonst Vorrang hätte
    def proc = new net.sf.saxon.s9api.Processor(false)  // false = HE, keine Lizenz nötig

    // 5. Das XSLT-Stylesheet laden und kompilieren
    def xsltFile = new File(System.getProperty("user.home"), "your_nifi_folder/xslt/MODS3-7_Bibframe2-0_XSLT2-0_20230505.xsl")
    def executable = proc.newXsltCompiler().compile(new StreamSource(xsltFile))

    // 6. Transformer starten und XML transformieren
    def transformer = executable.load30()
    def source = new StreamSource(new java.io.StringReader(xmlContent))
    def baos = new java.io.ByteArrayOutputStream()
    transformer.applyTemplates(source, proc.newSerializer(baos))
    def rdfXml = baos.toString('UTF-8')

    // 7. Das Ergebnis (RDF/XML) als neuen FlowFile-Inhalt schreiben
    ff = session.write(ff, { out ->
        out.write(rdfXml.getBytes('UTF-8'))
    } as OutputStreamCallback)

    // 8. Metadatum setzen: "Inhalt ist jetzt RDF/XML"
    ff = session.putAttribute(ff, 'mime.type', 'application/rdf+xml')
    session.transfer(ff, REL_SUCCESS)  // FlowFile weiterschicken

} catch (Exception e) {
    log.error("Transformation fehlgeschlagen: ${e.message}", e)
    session.transfer(ff, REL_FAILURE)  // Bei Fehler: Failure-Ausgang
}
```
### 10. Konvertierung von RDF/XML nach Turtle mit rapper

`ExecuteStreamCommand` ruft das externe Programm `rapper` auf, das den RDF/XML-Inhalt des FlowFiles über Standard-Input entgegennimmt und fertiges Turtle über Standard-Output zurückgibt.
#### 1. rapper installieren (falls nicht vorhanden)

```bash
which rapper || sudo apt install raptor2-utils
```

#### 2. ExecuteStreamCommand konfigurieren

|Tab|Property|Wert|
|---|---|---|
|Properties|Command|`/usr/bin/rapper`|
|Properties|Command Arguments|`-q;-i;rdfxml;-o;turtle;-;http://example.org/`|
|Properties|Argument Delimiter|`;`|
|Properties|Ignore STDIN|`false`|

Die Argumente im Einzelnen:

|Argument|Bedeutung|
|---|---|
|`-q`|Quiet: keine Fortschrittsmeldungen|
|`-i rdfxml`|Input-Format: RDF/XML|
|`-o turtle`|Output-Format: Turtle|
|`-`|Lies von Standard-Input (statt einer Datei)|
|`http://example.org/`|Basis-URI für relative URLs|

> **Wichtig:** `Ignore STDIN` muss auf `false` stehen — sonst bekommt rapper keinen Input und produziert leere Ausgabe.

#### 3. Connections

| Relation          | Verbinden mit | Begründung                                 |
| ----------------- | ------------- | ------------------------------------------ |
| `Output Stream 0` | → Schritt 11  | Turtle-Output bei Exit-Code 0              |
| `Non-Zero Status` | → Schritt 11  | Turtle-Output bei Warnungen (Exit-Code 2)  |
| `Original`        | → Terminieren | Original-FlowFile wird nicht mehr benötigt |

> **Hinweis zu `Non-Zero Status`:** Das BIBFRAME-XSLT erzeugt in manchen Fällen `<rdf:Resource>` als XML-Element, was technisch kein gültiges RDF/XML-Konstrukt ist (`rdf:Resource` darf nur als Wert, nicht als Element-Name auftreten). Rapper meldet dies als Warnung und gibt Exit-Code `2` zurück — der Turtle-Output ist aber vollständig und korrekt. Durch das Verbinden beider Ausgänge verhält sich NiFi wie das Python-Skript, das `result.stdout` unabhängig vom Return-Code weiterverarbeitet.

### Schritt 11: Turtle in QLever laden

- QLever muss bereits gestartet sein, Test (nach erster Indexierung), ob Server antwortet: `source test/test_query.sh`
#### Processor: InvokeHTTP

Füge einen **InvokeHTTP**-Processor nach Schritt 10 ein.

**Konfiguration:**

| Eigenschaft                    | Wert                                                                             |
| ------------------------------ | -------------------------------------------------------------------------------- |
| `HTTP Method`                  | `POST`                                                                           |
| `Remote URL`                   | `http://127.0.0.1:7019/?default&access-token=kalliope_briefe_musik_ACCESS_TOKEN` |
| `Content-Type`                 | `text/turtle`                                                                    |
| `Response Body Attribute Name` | _(leer lassen)_                                                                  |
| `Send Message Body`            | `true`                                                                           |
**Verbindungen**

| Relation   | Ziel                     |
| ---------- | ------------------------ |
| `Response` | LogAttribute / Terminate |
| `Failure`  | LogAttribute / Terminate |
| `No Retry` | LogAttribute / Terminate |
| `Retry`    | LogAttribute / Terminate |
| `Original` | Terminate                |


