# Notes on MARC Datadump Processing

## Issues with subfield $4 and $e
```
# presence of new and old formats
# sum in $4 does not match with $e
# $e combined has sometimes more entries than $4
Tag 700_Übersetzer: 9
Tag 700_ÜbersetzerIn: 7
Tag 700_trl: 7

Tag 100_Komponist: 1
Tag 100_KomponistIn: 225
Tag 100_cmp: 225

Tag 100_Künsterln: 1
Tag 100_KünstlerIn: 14
Tag 100_art: 15

=== Relators Summary ===
Total Roles:5920
Total 700_4 : 2498
Total 100_4 : 1749
Total 700_e : 1232
Total 100_e : 441
# In total $4 has more entries than $e. $4 is more standardised, less prone to cataloguing errors.
```
```
L149538
# Single Tag can have multiple $4 subfields
    <marc:datafield tag="100" ind1="1" ind2=" ">
      <marc:subfield code="a">Lecerf, Emilie</marc:subfield>
      <marc:subfield code="d">1795-</marc:subfield>
      <marc:subfield code="e">VerfasserIn</marc:subfield>
      <marc:subfield code="e">WidmendeR</marc:subfield>
      <marc:subfield code="0">(DE-588)1187291226</marc:subfield>
      <marc:subfield code="0">(DE-627)1666429945</marc:subfield>
      <marc:subfield code="4">aut</marc:subfield>
      <marc:subfield code="4">dto</marc:subfield>
```

## Simple Datamodel

**Record URI** - PICA Prod Nr(PPN) --> P1_is_identified_by
P1-->range->E41
E42 is subclass of E41
so instantiating E42 makes it an E41 automatically.
*A URI is not a creation event. It is an identifier.*
240 provides the standard link to the record either in DNB or K10 plus or anyother
245 gives the title for that biblographic record and it must be present in every record. $a and $b are titles.

**Tag 100(Primary Contributor): can be mythological, fictional or real person.**


    - $a(name) --> E39(Actor) covers mythological, fictional(pseudonyms, stage names) and real people.
    - $4(relators) --> P14.1
    - $0(DE-588==DNB, GND ID)--> P14
*In our case, it would be mostly real people. One use GND ID and get type to verify. Example:Gott(pxg), pxl: fictional literature characters*

**Tag 700 (Co-Contributor):**

    - $a(name) --> E39(Actor)
    - $4(relators) --> P14.1
    - $0(DE-588==DNB, GND ID) --> P14

**Tag 245(Title):**

    -$a(name) --> E35_Title

*$a are needed for frontend to display the names*

converted to bibframe, and then sparql construct to CIDOC and then add into qlever and then SPARQL query to check the data.

use RDF grapher to visualise

extend to the whole database

**Tag 534:**
*contains the details of the original, if the bibliogrpahic record deals with reproduction. For example: Date*

## CIDOC CRM
*E: Classes and P: Properties -- https://cidoc-crm.org/html/cidoc_crm_v7.1.3.html*

- E1 is the base class of all classes.
- E2, 52, 53, 54, 59, 77, 92 are the sub classes of E1.
- E65(creation)-->E7-->E5(event)
- E7(Activity): describes the actions carried out by E39
    - E7 has P14(carried_out_by)
    - *The painting of the Sistine Chapel (E7) carried out by Michelangelo Buonaroti (E21) in the role of master craftsman (E55).*
    -E55 defines controlled vocabularies or concepts.
### Rules
- E39(Actor) is subclass of E77(Persistence Item). No need to instantiate E77 explicitly, directly use E39.
- E39 is a superclass of E21(person), E74(Group/Corporate Body).
- Range defines to which class the property is pointing.
- Domain defines in which class a property is defined.
   - You cannot use that property unless the starting node is an instance of that domain class (or its subclasses).



*The above tripels state: book is an activity. book is carried by the person with GNDID. book has the role of hnr*

The last sentence is logically wrong, as it should be linked to the person not the book.


Inorder to link the roles, intermediates nodes need to be created that link role of person to the activity. This process is called Reification.

## Step 1: How to represent record ID in CIDOC-CRM?
*E42_Identifier(Identifier) --> P190_has_symbolic_content*
```
@prefix crm: <http://cidoc-crm.org> .
@prefix ex:  <http://example.org> .

# ex:k10plus_record_1973483270 is URI minting
ex:k10plus_record_1973483270 crm:P1_is_identified_by [
    a crm:E42_Identifier ;
    crm:P190_has_symbolic_content "1973483270"
] .
```

```
# Visual representation
[ ex:k10plus_record_1973483270 ] ──( crm:P1_is_identified_by )──➔ [ Blank Node ]
                                                                        │
                                                                        ├── rdf:type ──➔ crm:E42_Identifier
                                                                        │
                                                                        └── crm:P190_has_symbolic_content
```
*blank nodes save space and avoid duplicacy, for big datasets.*

> The above is a valid example in CIDOC-CRM, but is not useful for Author networks. Every author is a person(E21) and E21 is a subclass of E39(Actor). If we define the record as an activity(E7), then the record can be linked to E21s with P14.

## Step 2: How to represent people in CIDOC-CRM?
*E21_Person --> E39_Actor(Actor) and E20(Biological Object)*
```
@prefix crm: <http://cidoc-crm.org> .
@prefix ex:  <http://example.org> .
@prefix gnd: <http://d-nb.info/> .

# The master block chains all fields using semicolons
ex:k10plus_record_1973483270 a crm:E7_Activity ;

    # 1. Record ID (PPN)
    crm:P1_is_identified_by [
        a crm:E42_Identifier ;
        crm:P190_has_symbolic_content "1973483270"
    ] ;

    # 2. Tag 100 Primary Contributor (GND Anchor)
    crm:P14_carried_out_by gnd:11861164X ;

    # 3. Tag 700 Co-Contributor (GND Anchor)
    crm:P14_carried_out_by gnd:118603817 ;

gnd:11861164X a crm:E21_Person .
gnd:118603817 a crm:E21_Person .
```

*Note: One can also initialise the record as E65_Creation and it is still valid as E65 is subclass of E7.*

## Step 3: How to represent roles of people in CIDOC-CRM?
CIDOC CRM has PC (Property Class) implementation to define roles. It follows N-ary relationship and defines role type as a class.

```
 [DOMAIN: P14_carried_out_by ] ─── ( P14.1_in_the_role_of )───➔ [ RANGE: E55 ]
```
In the above example, it is not possible to
- chain P14.1 to P14 as it breaks the RDF (Subject, predicate, object) syntax. (as it adds a 4th element)
- one can't attach directly p14.1 to the record as it should be always linked to p14.

To add role, intermediate nodes are needed. This process is called Reification. The process of creating a new unique node is called URI Minting

```
@prefix crm: <http://cidoc-crm.org> .
@prefix ex:  <http://example.org> .
@prefix gnd: <http://d-nb.info> .
@prefix rel: <http://loc.gov> .

# 1. The Creation Event
ex:record_1973483270 a crm:E65_Creation ;
    # 1. Record ID (PPN)
    crm:P1_is_identified_by [
        a crm:E42_Identifier ;
        crm:P190_has_symbolic_content "1973483270"
    ] ;

# 2. Reified Node for Primary Author (Tag 100)
ex:assignment_1973483270_100_01 a crm:PC14_Carried_Out_By ;
    crm:P01_has_domain ex:record_1973483270 ;
    crm:P02_has_range gnd:11861164X ;
    crm:P14.1_in_the_role_of rel:aut .

# 3. Reified Node for Co-Author (Tag 700)
ex:assignment_1973483270_700_01 a crm:PC14_Carried_Out_By ;
    crm:P01_has_domain ex:record_1973483270 ;
    crm:P02_has_range gnd:118603817 ;
    crm:P14.1_in_the_role_of rel:ctb .

# Syntax Validation
gnd:11861164X a crm:E21_Person .
gnd:118603817 a crm:E21_Person .

rel:aut a crm:E55_Type .
rel:ctb a crm:E55_Type .

```
URI Minting follows the pattern- *ex:DB-RecordID-Tag-Counter*

## RDF Validation
- SHACL: Data graphs(Real RDF) are validated against Shape Graphs(schema)
- shape graph helps in understanding the whole data instead of a single test case
-

## Step 4: How to represent institutions in CIDOC-CRM?
*E74_Group*

## Issues found while converting
- missing GND IDs are minted in bibframe as #Agent100-{random number}
- if a record has multiple titles, then the conversion has many titles
- a person can have many roles. should not be limited to 1 in shape graph
- nested filters using UNION etc. take a long time is sparql: answer is to create two separate filters.
- differentiating primary and secondary authors using gnd or rel:aut or rel:ctb is ambiguous.
- key errors in $4. For example com. instead of com

### Wrong Triples (from my draft)
```
ex:1973483270 a crm:E7_Activity ; # wrong. Book ID cannot be an activity
    crm:P14_carried_out_by gnd:1038112575 ;
    crm:P14.1_in_the_role_of rel:hnr .
```

## Graph Validation Rules:
- Classes are either subjects or objects of the triples.
- Properties are predicates in the triples.
- First order logic should be verified to make sure that the triples are consistent with the ontology rules.

## References:
- https://cidoc-crm.org/sites/default/files/Roles.pdf
- https://docs.swissartresearch.net/pattern/general/
-


### 1. The Intellectual Content (The "Work" or "Expression")
* **`crm:E73_Information_Object`** / **`crm:E33_Linguistic_Object`**: Represents the text, music, or content.
* **`crm:E35_Title`**: Represents the title(s) of the work.
* **`crm:E42_Identifier`**: Represents identifiers like the GND ID, local system ID, or ISBN.

### 2. The Creative Act (The "Creation")
* **`crm:E65_Creation`**: Represents the event of creating the work.
* **`crm:E21_Person`** / **`crm:E39_Actor`**: The author(s), composer(s), or editor(s).
* **`crm:PC14_Carried_Out_By`**: A special class to specify *roles* (e.g., author, editor, illustrator)

### 3. The Publication & Manufacture (The "Instance")
* **`crm:E12_Production`** / **`crm:F32_Carrier_Production_Event`**: Represents the physical printing, publishing, or manufacturing event.
* **`crm:E39_Actor`**: The publisher or printer.
* **`crm:E52_Time-Span`**: The date of publication.

### 4. The Physical Carrier (The "Item")
* **`crm:E22_Human-Made_Object`**: Represents the specific copy sitting on a library shelf.
* **`crm:E53_Place`**: The physical location or shelfmark where the book resides.

In MARC 21, the type of resource (e.g., whether it is a book, a paper, a journal, a map, or a CD-ROM) is determined by looking at the Leader (LDR)—specifically character positions 06 and 07.

The Leader is the first line of any MARC record (24 characters long, 0-indexed).

1. Leader Position 06 (Type of Record)
This specifies the format of the content:

a = Language material (printed text, books, articles, etc.)
e = Cartographic material (maps)
g = Projected medium (videos, films)
m = Computer file (software, datasets)
2. Leader Position 07 (Bibliographic Level)
This specifies the structural relationship of the item:

m = Monograph/Item (a single standalone publication, like a book)
s = Serial (a repeating publication, like a journal or magazine)
a = Monographic component part (an article or paper inside a larger book or journal)

```
Position:  01234 5 6 7 8 9 ...
Content:   _____ c c m _ a ...
                   │ │
                   │ └─ Position 07: Bibliographic Level ('m')
                   └─── Position 06: Type of Record ('c')
```
for ticket 130:
As CIDOC-CRM is event based, the event captures the relationship of people involved. The next step is to differentiate primary(Tag 100) and secondary contributions (700) Example:

=================================
Tags
=================================
Tag 100 (96.24%): 1717 instances across 1717 of 1784 records
Other works could be from institutions rather than individuals and could be without a primary author, needs to be investigated
Tag 700 (151.12%): 2696 instances across 1604 of 1784 records
A record can any number of contributors
=================================
Relators
=================================
Total Relators: 4247
Total 700_4 (92.66%): 2498 defined relators across 2696 instances
some cases are title entry rather than person entry
Total 100_4 (101.86%): 1749 defined relators across 1717 instances
primary author can have multiple roles
