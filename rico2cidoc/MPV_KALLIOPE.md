# MVP: Kalliope
*Updated: 24.08.2026*

## RiC-O to CIDOC-CRM: Data Modeling
Data considered:
- Record Title
- Record ID
- Authors / Recipients


| Source RiC-O Element | Graph Pattern (SPARQL) | Target CIDOC CRM Class | Target CIDOC CRM Property | Description / Minting Pattern |
| :--- | :--- | :--- | :--- | :--- |
| `rico:Record` | `?letterURI a rico:Record` | `crm:E73_Information_Object`, `cer:1_Letter` | - | The record itself; the source URI is reused unchanged. URI: `?letterURI` |
| `rico:Record` (implicit, via URI) | `BIND(STRAFTER(STR(?letterURI), STR(kpe:)) AS ?letterId)` | `crm:E42_Identifier` | `crm:P1_is_identified_by` | Identifier extracted from the tail of the record's own URI (no explicit `rico:identifier` triple exists in the source), linked via a blank node with `crm:P190_has_symbolic_content`. |
| `rico:title` | `?letterURI rico:title ?titleName` | `crm:E35_Title` | `crm:P102_has_title` | Links the record to its title via a blank node with `crm:P190_has_symbolic_content`. |
| `rico:Record` (Event Creation) | `?letterURI a rico:Record` | `crm:E65_Creation` | `crm:P94_has_created` | The creation event of the record. URI: `kpe:{letterId}-CreationEvent` |
| `rico:hasAuthor` / `rico:hasAddressee` | `?letterURI rico:hasAuthor\|rico:hasAddressee ?agentURI` | `crm:PC14_Carried_Out_By` | - | Reified participation node representing an agent's role. URI: `kpe:{letterId}-RoleAssignment_{SHA1(agentURI+roleURI)}` |
| `rico:hasAuthor` / `rico:hasAddressee` (Domain) | same pattern | `crm:PC14_Carried_Out_By` | `crm:P01_has_domain` | Links the reified relationship to the creation event (`crm:E65_Creation`). |
| `rico:hasAuthor` / `rico:hasAddressee` (Range) | same pattern | `crm:E21_Person` | `crm:P02_has_range` | Links the reified relationship to the agent, reusing the agent's URI as-is from the source graph (e.g. GND). |
| — (not read from source, statically bound) | `BIND(rel:aut AS ?roleURI)` / `BIND(rel:rcp AS ?roleURI)` | `crm:E55_Type` | `crm:P14.1_in_the_role_of` | Role is not taken from the data but hardcoded per predicate: `rico:hasAuthor` → `rel:aut`, `rico:hasAddressee` → `rel:rcp`. |

> **Note:** Time-span modeling (`crm:E52_Time_Span` / `crm:P4_has_time-span`) is not yet active since rico:Records do not implement year primitives so far.

