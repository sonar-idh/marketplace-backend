## FEDORA
*Flexible Extensible Digital Object Repository Architecture*

Reference:https://docs.fcrepo.org/
### Intro
Fedora is a middleware used for digital preservation. It provides REST API for data management. Uses OCFL format to preserve objects.

*Fedora with OCFL supports versioning, automated fixity provisioning and verification, and a variety of storage technologies, including S3.  Fedora also provides an optional audit service, to track changes to resources over time and document provenance.*

- **Automated fixity provisioning and verification** - calculates a checksum for every object when it is created and verifies it regularly to check for data corruption.
- **S3** - Storage where the data resides.
- **Audit Service** - plays a key role for SoNAR in terms of data transparency.
- **Versioning** is done automatically.

 Objects are stored in binary format and can take the following forms:
- Single Object - Binary format
- Container - Collection of several independent Objects
- Archive - Collection of objects acts a single object.
### Data Size
- Smaller data can be stored in Fedora server directly
- Big Data should not be ingested using Fedora rather provide a S3 link (pointer) to where the data is residing. As handling big data can choke Fedora API. aka [Side Loading](https://wiki.lyrasis.org/spaces/FEDORA6x/pages/199525662/RESTful+HTTP+API+-+Side+Loading)
- In cases, where big data is pre-zipped to chunks, it is recommended to store in a container, as it looks logically clean.
### Metadata
The metadata is always in RDF format.
### Creating a container
*Note: Before you run this command, change "My Container title" and "INSERT NAME HERE"*

```bash
sparql='<> <http://purl.org/dc/terms/title> "My container title" .'
curl -i -X POST -H "Content-Type: text/turtle" -H "Slug: INSERT NAME HERE" --data-binary "$sparql" "$fedora_sonar_base" -u "$cred"
```
*Slug* : defines the  name and path to the new container.
    - Put the name of the container after "Slug:"
	- Default path: *$fedora_test_base/new-container*
After running this command, fedora creates a container with some default metadata and given data.

#### Checking whether the container exists
```bash
curl "$fedora_sonar_base" -u "$cred"
```

look for created container in one of the *ldp:contains*  output.

### Putting Objects inside a container
```bash
curl -i -X PUT -u "$cred" \
  -H "Link: <http://www.w3.org/ns/ldp#NonRDFSource>; rel=\"type\"" \
  -H "Content-Type: application/gzip" \
  --data-binary "@schumann_example.xml.gz" \
  "$fedora_sonar_base/K10PLUS/schumann_example"
```

### Deleting Objects
```bash
# 1. Delete the resource
curl -i -X DELETE -u "$cred" "$fedora_sonar_base/K10PLUS/schumann_example"


# 2. Clear out the tombstone marker so you can reuse the path
curl -i -X DELETE -u "$cred" "$fedora_sonar_base/K10PLUS/schumann_example/fcr:tombstone"
```
*Tombstone: when you delete data that links to other data, fedora keeps it but makes it unavailable to preserve data integrity*
