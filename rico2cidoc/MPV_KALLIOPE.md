# MVP: Kalliope
*Updated: 25.08.2026*

## RiC-O to CIDOC-CRM: Data Modeling
Data considered:
- Record Title
- Record ID
- Authors / Recipients
- Sending / Receiving (as separate `cer` Activities, decoupled from the Creation event)


| Source RiC-O Element | Graph Pattern (SPARQL) | Target CIDOC CRM Class | Target CIDOC CRM Property | Description / Minting Pattern |
| :--- | :--- | :--- | :--- | :--- |
| `rico:Record` | `?letterURI a rico:Record` | `crm:E73_Information_Object`, `cer:1_Letter` | - | The record itself; the source URI is reused unchanged. URI: `?letterURI` |
| `rico:Record` (implicit, via URI) | `BIND(STRAFTER(STR(?letterURI), STR(kpe:)) AS ?letterId)` | `crm:E42_Identifier` | `crm:P1_is_identified_by` | Identifier extracted from the tail of the record's own URI (no explicit `rico:identifier` triple exists in the source), linked via a blank node with `crm:P190_has_symbolic_content`. |
| `rico:title` | `?letterURI rico:title ?titleName` | `crm:E35_Title` | `crm:P102_has_title` | Links the record to its title via a blank node with `crm:P190_has_symbolic_content`. |
| `rico:Record` (Event Creation) | `?letterURI a rico:Record` | `crm:E65_Creation` | `crm:P94_has_created` | The creation event of the record. URI: `kpe:{letterId}-CreationEvent` |
| `rico:hasAuthor` | `?letterURI rico:hasAuthor ?agentURI` | `crm:PC14_Carried_Out_By` | - | Reified participation node representing the author's role in the *creation* event. URI: `kpe:{letterId}-RoleAssignment_{SHA1(agentURI+roleURI)}`. Note: `rico:hasAddressee` is **not** part of this query as recipients are modeled separately via the Receiving activity below, not as participants in the creation event. *Should be discussed.* |
| `rico:hasAuthor` (Domain) | same pattern | `crm:PC14_Carried_Out_By` | `crm:P01_has_domain` | Links the reified relationship to the creation event (`crm:E65_Creation`). |
| `rico:hasAuthor` (Range) | same pattern | `crm:E21_Person` | `crm:P02_has_range` | Links the reified relationship to the agent, reusing the agent's URI as-is from the source graph (e.g. GND). |
| — (not read from source, statically bound) | `BIND(rel:aut AS ?roleURI)` | `crm:E55_Type` | `crm:P14.1_in_the_role_of` | Role is not taken from the data but hardcoded: `rico:hasAuthor` → `rel:aut`. |
| `rico:hasAuthor` (Sending Event) | `?letterURI rico:hasAuthor ?agentURI` | `cer:13_Sending` | `cer:P9_was_intended_use_of` | Sending activity, separate from the creation event, representing the dispatch of the letter; linked to the record via `cer:P9_was_intended_use_of`. URI: `kpe:Sending_{letterId}` |
| `rico:hasAuthor` (Sending Event, Actor) | same pattern | `crm:E21_Person` (implicit) | `cer:P8_carried_out_by` | Links the Sending activity to the author as the actor who carried it out. |
| `rico:hasAddressee` (Receiving Event) | `?letterURI rico:hasAddressee ?agentURI` | `cer:14_Receiving` | `cer:P9_was_intended_use_of` | Receiving activity, counterpart to Sending; linked to the record via `cer:P9_was_intended_use_of`. URI: `kpe:Receiving_{letterId}` |
| `rico:hasAddressee` (Receiving Event, Actor) | same pattern | `crm:E21_Person` (implicit) | `cer:P8_carried_out_by` | Links the Receiving activity to the addressee as the actor who carried it out. |

> **Note:** Time-span modeling (`crm:E52_Time_Span` / `crm:P4_has_time-span`) is not yet active since rico:Records do not implement year primitives so far.

