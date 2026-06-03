# Qlever

## Setup
```bash
sudo apt update && sudo apt install -y wget gpg ca-certificates
wget -qO - https://packages.qlever.dev/pub.asc | gpg --dearmor | sudo tee /usr/share/keyrings/qlever.gpg > /dev/null
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/qlever.gpg] https://packages.qlever.dev/ $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") main" | sudo tee /etc/apt/sources.list.d/qlever.list
sudo apt update
sudo apt install qlever
```

```bash
# inside a virtual environment
qlever setup-config olympics # Get Qleverfile (config file) for this dataset
# qlever get-data              # Download the dataset, not needed in our case
qlever index                 # Build index data structures for this dataset
qlever start                 # Start a QLever server using that index
qlever query                 # optional: Launch an example query
qlever ui  
```

## Quick Test for qlever
```bash
# to get data using SRU, transform using XSLT and save to .rdf
curl -s "https://kalliope-verbund.info/sru?version=1.2&operation=searchRetrieve&query=ead.id=DE-611-HS-2557262&recordSchema=mods37" | xmlstarlet sel -N m="http://www.loc.gov/mods/v3" -t -c "//m:mods" | java -jar saxon-he-12.9.jar -s:- -xsl:/home/komal.vendidandi/Downloads/MODS3-7_Bibframe2-0_XSLT2-0_20230505.xsl -o:kalliope_bibframe.rdf baseuri="https://kalliope-verbund.info/"

# RDF to qlever formats
rapper -o ntriples SaxonHE12-9J/kalliope_bibframe.rdf > kalliope_bibframe.nt

qlever index
qlever start
```