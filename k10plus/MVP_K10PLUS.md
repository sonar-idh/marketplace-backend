# MVP: K10Plus
*Updated: 14.08.2026*

## Data Transformation Pipeline

  ```mermaid
flowchart LR
    subgraph MARC2BIBFRAME[MARC2BIBFRAME Converter XSLT]
        direction LR
        m1[Preprocessing: format and split] --> m2[MARC to BIBFRAME]
    end
    subgraph RDF2CIDOC[BIBFRAME RDF to CIDOC Converter]
        direction LR
        f --> t2[/HNR Graph/]
    end
    subgraph BIBFRAME2[BIBFRAME Graph]
        direction LR
    m2 --> r[/RDF/]
    r -->|rapper| t[/.ttl/]

    end

    s1[/K10Plus MARC XML/] --> m1
    t --> f[Data Filter: SPARQL Construct]
  ```
Presentation Flow:
- MARC Data Dump Analysis
- BIBFRAME to CIDOC-CRM: Data Modeling
- Qlever Triple Store: Indexing and Examples

## MARC Data Dump Analysis
*Data Dump: schumann.xml*

Detailed Analyis of this data dump is available [here](./data/statistics.txt).

### Cataloging Issues
- $e: describes human readable role description
- $4: Standardised & Machine readable relator
```bash
# Issue 1: Presence of RAK and RDA(DACH) formats
# Issue 2: Total of $4 != $e
# Issue 3: $e combined(RAK+RDA) has in some cases more entries than $4

# Issue 1 & 3: Example
Tag 700_Übersetzer: 9
Tag 700_ÜbersetzerIn: 7
Tag 700_trl: 7

# Issue 2 & 3: Example
Tag 100_Komponist: 1
Tag 100_KomponistIn: 225
Tag 100_cmp: 225

# Issue 1: Example where the totals match
Tag 100_Künsterln: 1
Tag 100_KünstlerIn: 14
Tag 100_art: 15

=== Relators Summary ===
Total Roles:5920
Total 700_4 : 2498
Total 100_4 : 1749
Total 700_e : 1232
Total 100_e : 441

# In total $4 has more entries than $e. $4 is more standardised, less prone to cataloging errors.
```


## BIBFRAME to CIDOC-CRM: Data Modeling
Data considered:
- Record Title
- Record ID
- Contributors (Tag 100 & Tag 700) and their roles.
- Creation / Publication Date (Tag 534 original date or Tag 264/260/008 publication date).

| MARC Field / Tag | Source BIBFRAME Element | XPath / Graph Pattern | Target CIDOC CRM Class | Target CIDOC CRM Property | Description / Minting Pattern |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Tag 001` | `bf:Work` | `?work a bf:Work` | `crm:E65_Creation` | `crm:P94_has_created` | The creation event of the work. URI: `{objectURI}#CreationEvent` |
| `Tag 001` | `bf:Work` | `?work a bf:Work` | `crm:E73_Information_Object` | - | Represents the bibliographic item / work. URI: `https://opac.k10plus.de/PPNSET?PPN={titleId}` |
| `Tag 001` | `bf:identifiedBy` | `bf:adminMetadata/bf:identifiedBy/rdf:value` | `crm:E42_Identifier` | `crm:P1_is_identified_by` | Links the work to its identifier (PPN) via a blank node with `crm:P190_has_symbolic_content`. |
| `Tag 245` | `bf:title` | `bf:title/bf:mainTitle` | `crm:E35_Title` | `crm:P102_has_title` | Links the work to its main title via a blank node with `crm:P190_has_symbolic_content`. |
| `Tag 100` / `Tag 700` | `bf:contribution` | `bf:contribution` | `crm:PC14_Carried_Out_By` | - | Reified participation node representing an agent's role. URI: `{objectURI}#RoleAssignment_{SHA1(agentURI)}` |
| `Tag 100` / `Tag 700` | `bf:contribution` (Domain) | `bf:contribution` | `crm:PC14_Carried_Out_By` | `crm:P01_has_domain` | Links the reified relationship to the creation event (`crm:E65_Creation`). |
| `Tag 100` / `Tag 700` (`$0` starting with `DE-588`) | `bf:agent` | `bf:contribution/bf:agent` | `crm:E21_Person` | `crm:P02_has_range` | Links the reified relationship to the person's GND URI. |
| `Tag 100` / `Tag 700` (`$4`) | `bf:role` | `bf:contribution/bf:role` | `crm:E55_Type` | `<http://www.cidoc-crm.org/cidoc-crm/P14.1_in_the_role_of>` | Links the reified relationship to the role type (Relator URI). |
| `Tag 264` / `Tag 260` / `Tag 008` | `bf:Instance` (Time-Span) | `?instance` (via `bf:hasInstance`) | `crm:E52_Time_Span` | `crm:P4_has_time-span` | Links the creation event (`crm:E65_Creation`) to its time-span node. URI: `{objectURI}#TimeSpan` |
| `Tag 534` / `Tag 264` / `Tag 260` / `Tag 008` | `bf:note` / `bf:date` | `origDate` or `pubDate` | `crm:E61_Time_Primitive` | `crm:P170i_time_is_defined_by` | Year primitive (4-digit string typed as `crm:E61_Time_Primitive`) defining the time-span. |

### Core Modeling Principles

* **Class Hierarchy / Taxonomy**: Classes are organized hierarchically where subclasses inherit all properties of their parent classes. For example, because `crm:E65_Creation` is a subclass of `crm:E7_Activity`, any creation event inherits properties for actors, time, and location.
* **Domain and Range**: Properties define directed relationships. The **domain** is the class that a property starts from (subject), and the **range** is the class the property must point to (object).
* **First-Order Logic / RDF Inference**: By defining a resource with a specific subclass (e.g., `crm:E21_Person`), the system automatically infers that it belongs to all its superclasses (e.g., `crm:E39_Actor` and `crm:E1_Entity`), preserving logical consistency across the graph.
* **Blank Nodes vs. Minted URIs**: Unique, stable entities that are referenced globally (like a person's GND URI or `#CreationEvent`) use **Minted URIs**. Nested or auxiliary structures unique to a single record (like a title block or an identifier value) use **Blank Nodes** to simplify graph density.
* **Property Classes (PC) and .1 Properties**: In CIDOC CRM, relationships can be qualified using **Property Classes** (prefixed with `PC`, e.g., `crm:PC14_Carried_Out_By`) and special **.1 properties** (like `crm:P14.1_in_the_role_of`) to assign properties to a relationship (reification).


### Reification
Because RDF triples only connect a subject and an object, the standard `crm:P14_carried_out_by` property has no direct way to attach what role they had. To preserve these specific roles (e.g., editor vs. author), we model the relationship using the reified class `crm:PC14_Carried_Out_By` to link each agent and their role to the creation event.

### Time-Span Modeling
Dates are associated with the creation event (`crm:E65_Creation`) via a time-span node (`crm:E52_Time_Span`):
1. **Date Resolution Prioritization**: `COALESCE(?origDate, ?pubDate)` prioritizes the original date note (MARC Tag 534, `mnotetype/orig`) over the publication/provision date (MARC Tag 264/260/008).
2. **Year Primitive Formatting**: Extracted dates are truncated to a 4-digit year primitive (`SUBSTR(STR(?correctDate), 1, 4)`) and typed as `crm:E61_Time_Primitive`.
3. **Graph Linkage**:
   ```ttl
   <#CreationEvent> crm:P4_has_time-span <#TimeSpan> .
   <#TimeSpan> a crm:E52_Time_Span ;
       crm:P170i_time_is_defined_by "1841"^^crm:E61_Time_Primitive .
   ```

## Qlever Triple Store: Indexing and Examples
The converted data is available [here](./data/schumann_cidoc.ttl) and it is indexed in Qlever triple store.

## Next Steps
- Differentiating primary (Tag 100) and secondary (Tag 700) contributions.
- Testing with a bigger data dump.
- Place modeling.
- Implementing Title Entry (Tag 700 $a $b $n) in SPARQL CONSTRUCT.
