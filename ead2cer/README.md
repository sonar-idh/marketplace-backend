# Mapping Kalliope-EAD → Correspondence and Epistolary Research (CER) Ontology

Basierend auf der [Definition of the Correspondence and Epistolary Research (CER) Ontology, Version 2.0](https://zenodo.org/records/17431730).

## 1_Letter

| EAD             | CRM/CER                              |
| --------------- | ------------------------------------ |
| `@id`           | `kpe:<@id> a cer:1_Letter`           |
| `did/unittitle` | `crm:P102_has_title <did/unittitle>` |

## 13_Sending

**Bedingung**: Record besitzt mindestens eine als Verfasser angegebene Person oder Körperschaft, die zugleich GND-referenziert ist. 

XPath: `test="(e:controlaccess/e:persname | e:controlaccess/e:corpname)[@role = 'Verfasser' and @source = 'GND' and @authfilenumber]"`

| EAD               | CRM/CER                                       |
| ----------------- | --------------------------------------------- |
| `@id`             | `sonar:Sending_<@id> a a cer:13_Sending`      |
| `@id`             | `cer:P9_was_intended_use_of kpe:<@id>`        |
| `@authfilenumber` | `cer:P8_carried_out_by gnd:<@authfilenumber`> |

## 14_Receiving

**Bedingung**: Record besitzt mindestens eine als Adressat angegebene Person oder Körperschaft, die zugleich GND-referenziert ist. 

XPath: `test="(e:controlaccess/e:persname | e:controlaccess/e:corpname)[@role = 'Adressat' and @source = 'GND' and @authfilenumber]"`

| EAD               | CRM/CER                                       |
| ----------------- | --------------------------------------------- |
| `@id`             | `sonar:Receiving_<@id> a a cer:14_Receiving`  |
| `@id`             | `cer:P9_was_intended_use_of kpe:<@id>`        |
| `@authfilenumber` | `cer:P8_carried_out_by gnd:<@authfilenumber`> |
