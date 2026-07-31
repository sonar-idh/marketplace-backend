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

Die Ortsangabe P7_took_place_at erfordert hier die EAD-Rollen "Entstehungsort", "PlaceOfOrigin" oder "Absendeort" sowie eine GND-Referenzierung des Ortes. 

XPath: `test="(e:controlaccess/e:persname | e:controlaccess/e:corpname)[@role = 'Verfasser' and @source = 'GND' and @authfilenumber]"`

| EAD               | CRM/CER                                                 |
| ----------------- | ------------------------------------------------------- |
| `@id`             | `sonar:Sending_<@id> a cer:13_Sending`                  |
| `@id`             | `cer:P9_was_intended_use_of kpe:<@id>`                  |
| `@authfilenumber` | `cer:P8_carried_out_by gnd:<@authfilenumber>`           |
| `did/unitdate`    | `cer:P6_has_time-span sonar:Time-Span_<@id>_<$dm?key>`  |
| `controlaccess/geogname/@authfilenumber`    | `cer:P7_took_place_at gnd:<@authfilenumber>`  |

## 14_Receiving

**Bedingung**: Record besitzt mindestens eine als Adressat angegebene Person oder Körperschaft, die zugleich GND-referenziert ist. 

Die Ortsangabe P7_took_place_at erfordert hier die EAD-Rolle "Zielort" sowie eine GND-Referenzierung des Ortes. 

XPath: `test="(e:controlaccess/e:persname | e:controlaccess/e:corpname)[@role = 'Adressat' and @source = 'GND' and @authfilenumber]"`

| EAD               | CRM/CER                                       |
| ----------------- | --------------------------------------------- |
| `@id`             | `sonar:Receiving_<@id> a cer:14_Receiving`  |
| `@id`             | `cer:P9_was_intended_use_of kpe:<@id>`        |
| `@authfilenumber` | `cer:P8_carried_out_by gnd:<@authfilenumber>` |
| `controlaccess/geogname/@authfilenumber`    | `cer:P7_took_place_at gnd:<@authfilenumber>`  |

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

# Anhang: Statistiken

## Wieviel Prozent aller `c`-Elemente besitzen `e:controlaccess/e:persname | e:controlaccess/e:corpname)[@role = 'Adressat']`?

```
python3 analyze_dump/analyze_c_adressat_share.py ~/ead2rico/ead20260217/ead/ 8 
============================================================
Dateien gesamt:                                          60971
Parse-Fehler:                                            0

c-Elemente gesamt:                                       5825641
  davon mit controlaccess/persname|corpname[@role=Adressat]: 4036526 (69.3%)
```

## Wieviel Prozent aller `c`-Elemente besitzen `controlaccess/genreform = 'Brief`? Wie viele der Brief-Verfasser haben keine gültige GND-Referenz? (`@source != 'GND'` oder keine `@authfilenumber`) Wie viele der Brief-Adressaten haben keine gültige GND-Referenz? (`@source != 'GND'` oder keine `@authfilenumber`)?

```
python3 analyze_dump/analyze_c_brief_genreform.py ~/ead2rico/ead20260217/ead/ 8 
============================================================
Dateien gesamt:                                          60971
Parse-Fehler:                                            0

c-Elemente gesamt:                                       5825641
  davon mit controlaccess/genreform = 'Brief':           2748935 (47.2%)

-- Verfasser (persname|corpname[@role='Verfasser']) der Brief-c-Elemente --
  gesamt:                                                2883189
  ohne gueltige GND-Referenz:                            585755 (20.3%)

-- Adressaten (persname|corpname[@role='Adressat']) der Brief-c-Elemente --
  gesamt:                                                2830907
  ohne gueltige GND-Referenz:                            411894 (14.5%)
```

## Wie viele der `c`-Elemente besitzen `controlaccess/geogname`? Wie viele dieser Elemente besitzen wiederum das Attribut `@role="Entstehungsort"`? Welche weiteren Werte kann hier das `@role`-Attribut haben? Wie viele der Elemente mit `@role="Entstehungsort"` haben zudem `@source="GND"`? 

```
python3 analyze_dump/analyze_c_geogname.py ~/ead2rico/ead20260217/ead/ 8 
============================================================
Dateien gesamt:                                          60971
Parse-Fehler:                                            0

c-Elemente gesamt:                                       5825641
  davon mit controlaccess/geogname:                      4159896 (71.4%)
    davon mit geogname[@role='Entstehungsort']:          3411696 (82.0% der c mit geogname)

-- @role-Werte der geogname-Elemente (gesamt 4574661 Elemente) --
    3708180  ( 81.1%)  'Entstehungsort'
     707339  ( 15.5%)  'PlaceOfOrigin'
     102392  (  2.2%)  '<kein @role-Attribut>'
      31104  (  0.7%)  'Absendeort'
      11875  (  0.3%)  'Zielort'
       5207  (  0.1%)  'Erwähnter Ort'
       3425  (  0.1%)  'Erscheinungsort'
       2232  (  0.0%)  'Erwähnt'
       1486  (  0.0%)  'Veranstaltungsort'
        862  (  0.0%)  'Standort'
        300  (  0.0%)  'Behandelt'
        184  (  0.0%)  'Abgebildet'
         11  (  0.0%)  'AbsenderIn'
          6  (  0.0%)  'Zürich (Stadt)'
          4  (  0.0%)  'Genève/Genf (Ville/Stadt)'
          4  (  0.0%)  'AdressatIn'
          4  (  0.0%)  'Gunten'
          4  (  0.0%)  'Neuchâtel/Neuenburg'
          3  (  0.0%)  'Barcelona'
          3  (  0.0%)  'Philadelphia, Pa.'
          2  (  0.0%)  'London'
          1  (  0.0%)  'Reinach (Aargau)'
          1  (  0.0%)  'Zürich-Höngg'
          1  (  0.0%)  'Schlanders'
          1  (  0.0%)  'Zürich'
          1  (  0.0%)  'Schwyz (Stadt)'
          1  (  0.0%)  'Appenzell'
          1  (  0.0%)  'Bern'
          1  (  0.0%)  'Wil (Kanton Sankt Gallen)'
          1  (  0.0%)  'Palma de Mallorca'
          1  (  0.0%)  'Küsnacht (Kanton Zürich)'
          1  (  0.0%)  'Frankfurt am Main'
          1  (  0.0%)  'Putz'
          1  (  0.0%)  'Albany, NY'
          1  (  0.0%)  'Canton, Ohio'
          1  (  0.0%)  'Rochester, NY'
          1  (  0.0%)  'Montréal'
          1  (  0.0%)  'Paris'
          1  (  0.0%)  'Breganzona'
          1  (  0.0%)  'Geroldswil'
          1  (  0.0%)  'Berlin'
          1  (  0.0%)  'La Neuveville'
          1  (  0.0%)  'Middletown, Conn.'
          1  (  0.0%)  'Goch'
          1  (  0.0%)  'Ansbach'
          1  (  0.0%)  'New York- Bronx'
          1  (  0.0%)  'Kopenhagen'
          1  (  0.0%)  'Saint-Sulpice (Waadt)'
          1  (  0.0%)  'Basel (Stadt)'
          1  (  0.0%)  'Berlin-Wannsee'
          1  (  0.0%)  'Douarnenez'
          1  (  0.0%)  'Lausanne'
          1  (  0.0%)  'Zürich-Enge'
          1  (  0.0%)  'Vufflens-la-Ville'
          1  (  0.0%)  'Montagnola'

-- geogname[@role='Entstehungsort'] --
  Elemente gesamt:                                       3708180
    davon mit @source='GND':                             1364725 (36.8%)
```

## Wie viele der `c`-Elemente mit `controlaccess/genreform = "Brief"` haben `did/unitdate/@label = "Entstehungsdatum"`? Welche anderen Labels kommen hier noch wie oft vor? Wie oft hat `did/unitdate` das Attribut `@normal`? Welche Formate haben die Werte dieses Attributs?

```
python3 analyze_c_brief_unitdate.py /home/p01776/ead2rico/ead20260217/ead 8
======================================================================
Dateien gesamt:                                          60971
Parse-Fehler:                                            0

c-Elemente gesamt:                                       5825641
  davon mit controlaccess/genreform = 'Brief':           2748935 (47.2%)

-- did/unitdate/@label bei Brief-c-Elementen --
  Brief-c mit @label='Entstehungsdatum':                 2655545 (96.6%)
    davon mit MEHR ALS EINEM unitdate/@label='Entstehungsdatum': 83 (0.0%)

  Verteilung aller @label-Werte auf unitdate-Elementen von Brief-c (ein c kann mehrere unitdate/labels haben):
         2655670  'Entstehungsdatum'
            9463  '<kein @label>'

-- did/unitdate/@normal (bei Brief-c-Elementen) --
  unitdate-Elemente gesamt:                              2665133
  davon mit @normal-Attribut:                            2550053 (95.7%)

  Formate der @normal-Werte:
         2112262  YYYYMMDD (82.8%)
          196570  YYYY (7.7%)
          113491  Bereich (YYYY/YYYY) (4.5%)
           92739  Bereich (YYYYMMDD/YYYYMMDD) (3.6%)
           29573  YYYY-MM (1.2%)
             879  Bereich (YYYYMMDD/YYYY-MM) (0.0%)
             819  Bereich (YYYY/YYYYMMDD) (0.0%)
             746  Bereich (YYYY-MM/YYYY-MM) (0.0%)
             740  Bereich (YYYYMMDD/YYYY) (0.0%)
             731  Bereich (YYYY-MM/YYYYMMDD) (0.0%)
             675  YYYY-MM-DD (0.0%)
             653  Bereich (YYYY-MM-DD/YYYY-MM-DD) (0.0%)
              50  Bereich (YYYY-MM-DD/YYYY-MM) (0.0%)
              41  Bereich (YYYY/YYYY-MM) (0.0%)
              41  Bereich (YYYY-MM/YYYY) (0.0%)
              22  Bereich (YYYY-MM/YYYY-MM-DD) (0.0%)
              13  Bereich (YYYY-MM-DD/YYYY) (0.0%)
               8  Bereich (YYYY/YYYY-MM-DD) (0.0%)
```

## Welche genreform-Werte kommen wie häufig unter Records mit einem Tag mit @role="Adressat" vor?

```
Dateien gesamt:                                   60971
Parse-Fehler:                                     0
Records (archdesc+c) gesamt:                       5886612
Elemente mit role='Adressat' gesamt:               4348337
Records (c/archdesc) mit role='Adressat':          4036546
  davon auch mit genreform:                        3675809
  Anteil:                                          91.1%

-- Tag-Namen der role='Adressat'-Elemente --
  persname        3841631
  corpname        506706

-- genreform-Werte (nur Records MIT Adressat), Top 50 --
  'Brief'                        2699926    62.09%
  'Briefe'                       726793     16.71%
  'Briefsammlung'                175365      4.03%
  'Handschrift'                  164377      3.78%
  'Autograf'                     106949      2.46%
  'Postkarte'                    74364       1.71%
  'Verschiedenes'                26307       0.60%
  'Dokument'                     26196       0.60%
  'Stammbucheintragung'          20559       0.47%
  'Korrespondenz'                17376       0.40%
  'Abschrift'                    11956       0.27%
  'Werk'                         9537        0.22%
  'Entwurf'                      7815        0.18%
  'Telegramm'                    6576        0.15%
  'Ansichtspostkarte'            6268        0.14%
  'Visitenkarte'                 5671        0.13%
  'Lyrik'                        5520        0.13%
  'Eintragung'                   5349        0.12%
  'Feldpost'                     5063        0.12%
  'Albumblatt'                   4851        0.11%
  'Rundschreiben'                4832        0.11%
  'Rechnung'                     4770        0.11%
  'Illustration'                 4357        0.10%
  'Glückwunsch'                  4134        0.10%
  'Quittung'                     3685        0.08%
  'Briefumschlag'                3520        0.08%
  'Fragebogen'                   3501        0.08%
  'Fotografie'                   3363        0.08%
  'Telefax'                      3137        0.07%
  'Autogramm'                    2550        0.06%
  'Mitteilung'                   2517        0.06%
  'Dedikation'                   2026        0.05%
  'Bearbeitung'                  1955        0.04%
  'Prosa'                        1828        0.04%
  'Geschäftsbrief'               1680        0.04%
  'Notiz'                        1636        0.04%
  'Kunst'                        1531        0.04%
  'Gästebuch'                    1474        0.03%
  'Kondolenz'                    1443        0.03%
  'Zeichnung'                    1425        0.03%
  'Bescheinigung'                1398        0.03%
  'E-Mail'                       1391        0.03%
  'Bericht'                      1364        0.03%
  'Akte'                         1310        0.03%
  'Zeitschriftenaufsatz'         1301        0.03%
  'Zeitungsartikel'              1256        0.03%
  'Stammbuchblatt'               1077        0.02%
  'Vertrag'                      1063        0.02%
  'Anzeige'                      1027        0.02%
  'Karte'                        887         0.02%
  ... insgesamt 295 unterschiedliche genreform-Werte
```
