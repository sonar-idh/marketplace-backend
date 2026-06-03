# Multi Graph Approach for SoNAR
*Übersetzt mit DeepL.com*
## Introduction
SoNAR sammelt Metadaten aus verschiedenen Datenbanken. Um für die historische Netzwerkforschung leicht zugängliche Daten zu erstellen, sollte SoNAR in der Lage sein, Daten aus verschiedenen Datenbanken zu kombinieren, damit die Informationen umfassend sind.
Beispiel:
Ein Musikwissenschaftler möchte mehr über den Krieg der Romantiker erfahren und ist insbesondere daran interessiert, Netzwerkforschung zu allen beteiligten Personen und der Anzahl der zwischen ihnen ausgetauschten Briefe zu betreiben. 
Dabei stellen sich folgende Fragen:
* Wer sind die beteiligten Personen?
* Wer steht in enger Beziehung zueinander? 
* Wie viele Briefe wurden ausgetauscht?
* Was wissen wir noch über jede Person?
* In welcher Institution sind sie tätig?

Die Metadaten zu den ausgetauschten Briefen sind in **Kalliope** vorhanden, und weitere Informationen zu den Personen und Institutionen sind in **GND** verfügbar.

Dies erfordert die Möglichkeit, die Personen oder Institutionen in Kalliope zu identifizieren und weitere Details aus GND abzurufen. **qlever** bietet den **MULTI_INPUT_JSON**-Ansatz, bei dem beliebig viele Graphen mithilfe eines **Graph-Identifiers** kombiniert werden können. Dadurch bleibt die Ontologie des Graphen erhalten, und gleichzeitig können Sie die Daten aus verschiedenen Triplestores mit einem einzigen **SPARQL**-Befehl abfragen.

Weitere Details finden Sie hier:
- [Qleverfile](./qlever/Qleverfile) – Konfigurationsdatei für qlever
- [Qleverfile-ui.yml](./qlever/Qleverfile-ui.yml) – Konfigurationsdatei für die qlever-Benutzeroberfläche, in der Beispiele verfügbar sind.



## ETL Pipeline
Für die Datenextraktion bietet **Apache Nifi** zahlreiche Funktionen wie **Backpressure, Data Provenance usw.** Da es sich um eine Flow-Programmiersoftware handelt, ist die Datenpipeline tatsächlich leicht zu verstehen.

Die grundlegenden Einheiten von Nifi sind **Processor** und **Flowfile**. **Nifi** verwendet einen **Processor**, um eine bestimmte Aktion auszuführen, sei es das Abrufen, Transformieren oder Speichern der Daten usw. **Flowfiles** leiten die Daten von einem Processor zum nächsten weiter. 

Das Hauptziel dieses Experiments ist es, sich mit der gesamten Pipeline vertraut zu machen. Das obige Beispiel wurde verwendet, um folgende Frage zu testen: 

**„Wie einfach ist es, eine Datenpipeline zu implementieren, die für Forscher im Bereich der historischen Netzwerke einen Mehrwert bietet?“**


### Daten-Extraktions- und -Transformationsablauf
- Mit **GenerateFlowFile** wurde eine zeitgesteuerte Extraktion von **Kalliope**-Daten unter Verwendung des SRU/CQL-Protokolls konfiguriert.
- Die Briefdaten aus **Kalliope** werden iterativ von der **Musikabteilung** abgerufen, und zwar 100 Datensätze im MODS 3.7-Format pro Anfrage unter Verwendung einer Kontrollrate, damit die Datenabrufe nicht blockiert werden.
- **SplitXML** erstellt für jeden Datensatz eine Flowdatei.
- Jede Flowdatei durchläuft nun die folgenden Befehlssequenzen, um sich vom MODS3.7-Format in das RDF-Tripelstore-Format umzuwandeln.

    - XML Starlet verarbeitet die XML-Antwort und gibt das „mods“-Element im Datensatz-Elementbaum zurück.
    - Dieses „mods“-Element wird nun mithilfe der **Saxonica XSLT**-Transformation in die **BIBFRAME-Ontologie (Work, Instance, Item)** konvertiert.
    - Using **Rapper**, each record is now converted to **Tripelstore RDF format(.ttl, .nt, .json-ld)**

- Mit **MergeContent** werden zeit- oder größenbasierte Datensätze erstellt, die anschließend komprimiert und in den Speicher geschrieben werden.
- GND-, ZDB- und DNB-Katalogdaten liegen bereits im Triplestore-Format mit eigener Ontologie vor. Diese Datensätze werden derzeit anhand der Prüfsumme überprüft und bei Änderungen heruntergeladen.


### Datentransformation
 Die aktuelle Datentransformation basiert nur dann auf der **BIBFRAME-Ontologie**, wenn kein Datendump im Triplestore-Format verfügbar ist. Für bestehende Triplestore-Datenbanken wie GND, ZDB und DNB wurde die vorhandene Ontologie unverändert übernommen.

### Datenindexierung
Sobald die Daten in einem der Triplestore-Formate vorliegen, lassen sie sich mit qlever leicht indexieren, indem man die Qleverfile-Datei anpasst, wie in der [`Einführung`](#introduction) beschrieben. 

## Ergebnisse

Die aktuellen Experimente beantworten nur einige wenige Fragen aus der ursprünglichen Hypothese in der [`Einführung`](#introduction), nämlich:

- Erlangung weiterer Informationen zu den beteiligten Personen und Institutionen.


#### SPARQL-Abfrage in qlever, die integrierte Triplestores aus Kalliope, GND und ZDB anzeigt

![SPARQL-Abfrage in qlever, die integrierte Triplestores aus Kalliope, GND und ZDB anzeigt](./qlever/qlever_total_triples.png)

#### Multi-Graph-Suche
Eine GND-ID von Kalliope verwenden und weitere Informationen zu derselben GND-ID im GND Tripelstore abrufen.
![SPARQL-Abfrage in qlever, die integrierte Triplestores aus Kalliope, GND und ZDB anzeigt](./qlever/qlever_multi_graph_search.png)

## Setup
Für dieses Experiment werden **Nifi**, **xmlstarlet**, **Saxonica XSLT**, **rapper** und **Qlever** benötigt.

```bash

sudo apt update && sudo apt install -y openjdk-21-jdk
wget https://dlcdn.apache.org/nifi/2.9.0/nifi-2.9.0-bin.zip
wget https://downloads.apache.org/nifi/2.9.0/nifi-2.9.0-bin.zip.asc
wget https://downloads.apache.org/nifi/2.9.0/nifi-2.9.0-bin.zip.sha512
# verify keys
if echo "$(cat nifi-2.9.0-bin.zip.sha512) nifi-2.9.0-bin.zip" | sha512sum -c - &> /dev/null; then
    echo "Hash match verified! Unzipping file..."
    unzip nifi-2.9.0-bin.zip
else
    echo "ERROR: Hash mismatch!" >&2
    exit 1
fi

# chnage the conf/properties manually
# Network properties for NIFI
# hostname -I
#nifi.web.https.host=<ip address>
#nifi.web.https.port=<port>

# Access control properties
#nifi.web.proxy.host=<ip_address>:<port>

# Get the first IP address from hostname -I
SERVER_IP=$(hostname -I | awk '{print $1}')

# 2. Replace the lines dynamically in nifi.properties
sed -i "s|^.*nifi.web.https.host=.*|#nifi.web.https.host=${SERVER_IP}|" conf/nifi.properties
sed -i "s|^.*nifi.web.https.port=.*|#nifi.web.https.port=8443|" conf/nifi.properties
sed -i "s|^.*nifi.web.proxy.host=.*|#nifi.web.proxy.host=${SERVER_IP}:8443|" conf/nifi.properties

# 3. Verify the changes
grep -E "nifi.web.https.host|nifi.web.https.port|nifi.web.proxy.host" conf/nifi.properties

# Run Nifi
# ./nifi-2.9.0/bin/nifi.sh start

sudo apt-get install libsaxonhe-java
sudo apt-get install xmlstarlet
sudo apt-get install raptor2-utils
sudo apt update && sudo apt install -y wget gpg ca-certificates
wget -qO - https://packages.qlever.dev/pub.asc | gpg --dearmor | sudo tee /usr/share/keyrings/qlever.gpg > /dev/null
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/qlever.gpg] https://packages.qlever.dev/ $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") main" | sudo tee /etc/apt/sources.list.d/qlever.list
sudo apt update
sudo apt install qlever

```
```bash
# Run Nifi
./nifi-2.9.0/bin/nifi.sh start
```

```bash
# Run qlever (only for manual testing)
# qlever indexing and starting is controlled using Apache Nifi
qlever index
qlever start
```
