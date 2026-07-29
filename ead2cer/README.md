# Transformation Kalliope-EAD → Correspondence and Epistolary Research (CER) Ontology

Basierend auf der [Definition of the Correspondence and Epistolary Research (CER) Ontology, Version 2.0](https://zenodo.org/records/17431730).

Verarbeitet sämtliche `c`-Elemente des Kalliope-Dumps mit Typ 'Brief' (`controlaccess/genreform = 'Brief'`) und legt die jeweils entsprechenden Entitäten und Relationen aus CER und CRM an.

## 1_Letter

| EAD             | CRM/CER                                |
| --------------- | -------------------------------------- |
| `@id`           | `kpe:<@id> a cer:1_Letter`             |
| `did/unittitle` | `crm:P102_has_title "<did/unittitle>"` |

## 13_Sending

**Bedingung**: Record besitzt mindestens eine als Verfasser angegebene Person oder Körperschaft, die zugleich GND-referenziert ist. 

XPath: `test="(e:controlaccess/e:persname | e:controlaccess/e:corpname)[@role = 'Verfasser' and @source = 'GND' and @authfilenumber]"`

| EAD               | CRM/CER                                                 |
| ----------------- | ------------------------------------------------------- |
| `@id`             | `sonar:Sending_<@id> a cer:13_Sending`                |
| `@id`             | `cer:P9_was_intended_use_of kpe:<@id>`                  |
| `@authfilenumber` | `cer:P8_carried_out_by gnd:<@authfilenumber>`           |
| `did/unitdate`    | `cer:P6_has_time-span sonar:Time-Span_<@id>_<$dm?key>` |

## 14_Receiving

**Bedingung**: Record besitzt mindestens eine als Adressat angegebene Person oder Körperschaft, die zugleich GND-referenziert ist. 

XPath: `test="(e:controlaccess/e:persname | e:controlaccess/e:corpname)[@role = 'Adressat' and @source = 'GND' and @authfilenumber]"`

| EAD               | CRM/CER                                       |
| ----------------- | --------------------------------------------- |
| `@id`             | `sonar:Receiving_<@id> a cer:14_Receiving`  |
| `@id`             | `cer:P9_was_intended_use_of kpe:<@id>`        |
| `@authfilenumber` | `cer:P8_carried_out_by gnd:<@authfilenumber>` |

## 18_Time-Span

**Zeitangaben** erfolgen CER-konform in Form von Zeitspannen, die durch Entitäten der Klassen 26_Start-Date und 27_End-Date definiert werden und einer Aktivität (z.B. 13_Sending, 14_Receiving) zugerechnet werden. Da Brief-Records meist lediglich eine Angabe des Entstehungsdatums `c/did/unitdate/@label = "Entstehungsdatum"` enthalten, wird diese Zeitangabe in 13_Sending integriert. `c/did/unitdate/@normal` entspricht einer normalisierten Datumsangabe (i.d.R. YYYY, YYYYMM oder YYYYYMMDD, "/" gibt Laufzeit an, z.B. YYYYMMDD/YYYY). Die Verarbeitung dieses Datums erfolgt in [`cer_dates.xsl`](https://github.com/sonar-idh/marketplace-backend/blob/feat/149-ead2cer/ead2cer/cer_dates.xsl#L37-L251), wo das Datumsformat, Monatslängen und Schaltjahre, sowie die Validität der Angabe überprüft werden. Ergebnis ist die Map `$dm` mit folgenden Key-Value-Paaren:

```
'prec' : @normal-Angabe als Laufzeit, Jahr, Monat oder Tag
'key'  : Eindeutiger Schlüssel der beschriebenen Zeitspanne
'begin': Startdatum als xs:date
'end'  : Enddatum als xs:date
```

| EAD                     | CRM/CER                                                                             |
| ----------------------- | ----------------------------------------------------------------------------------- |
| `@id` und `$dm?key`     | `sonar:Time-Span_<@id>_<$dm?key> a cer:18_Time-Span`                              |
| `did/unitdate`          | `rdfs:label "<did/unitdate>"`                                                       | 
| `did/unitdate/@normal`  | `cer:P19_had_duration sonar:Start_Date_<$dm?begin>, sonar:End_Date_<$dm?end>` |

## 26_Start-Date

**Hinweis**: Die CER spezifiziert keine Datatype Property, mit der bei 26_Start_Date und 27_End_Date das Datum als Literalwert angegeben werden kann. Daher kann diese in `cer_dates.xsl` als [Parameter](https://github.com/sonar-idh/marketplace-backend/blob/feat/149-ead2cer/ead2cer/cer_dates.xsl#L23) angegeben werden und wird per default der CRM entnommen. 

| EAD               | CRM/CER                                       |
| ----------------- | --------------------------------------------- |
| `$dm?begin`       | `sonar:Start_Date_<$dm?begin> a cer:26_Start_Date`  |
| `$dm?begin`       | `crm:P90_has_value "<$dm?begin>"^^xs:date`       |


## 27_End-Date

| EAD               | CRM/CER                                       |
| ----------------- | --------------------------------------------- |
| `$dm?end`       | `sonar:End_Date_<$dm?end> a cer:27_End_Date`  |
| `$dm?end`       | `crm:P90_has_value "<$dm?end>"^^xs:date`       |