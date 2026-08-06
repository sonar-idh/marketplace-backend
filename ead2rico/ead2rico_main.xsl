<?xml version="1.0" encoding="UTF-8"?>
<!--
  ead2rico.xsl  —  EAD (Kalliope/EAD 2002) -> RiC-O 1.1 (Turtle)
  XSLT 3.0 (Saxon-HE / SaxonC-HE).

  Aufruf (Beispiel):
    saxonb-xslt -s:ead_DE-1_5364_test.xml -xsl:ead2rico.xsl -o:out.ttl
  Parameter (per -base:... etc. überschreibbar):
    base       Basis-IRI für lokal geprägte Ressourcen 
-->
<xsl:stylesheet version="3.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:xs="http://www.w3.org/2001/XMLSchema"
  xmlns:e="urn:isbn:1-931666-22-9"
  xmlns:f="urn:local:funcs"
  exclude-result-prefixes="xs e f">

  <xsl:output method="text" encoding="UTF-8" />
  <xsl:strip-space elements="*" />

  <!-- ============ Parameter ============ -->
  <xsl:param
    name="base" select="'https://kalliope-verbund.info/ead?ead.id='" />
  <xsl:param name="gnd"
    select="'https://d-nb.info/gnd/'" />
  <xsl:param name="lang-base"
    select="'http://id.loc.gov/vocabulary/iso639-2/'" />


  <!-- ============ Funktionen aus Helper-Stylesheet einbinden ============ -->
  <xsl:include href="ead2rico_helpers.xsl" />

  <!-- ============ Einstieg ============ -->
  <xsl:template
    match="/">
    <!-- Präfixe -->
    <xsl:text>@prefix rico: &lt;https://www.ica.org/standards/RiC/ontology#&gt; .&#10;</xsl:text>
    <xsl:text>@prefix rdf:  &lt;http://www.w3.org/1999/02/22-rdf-syntax-ns#&gt; .&#10;</xsl:text>
    <xsl:text>@prefix rdfs: &lt;http://www.w3.org/2000/01/rdf-schema#&gt; .&#10;</xsl:text>
    <xsl:text>@prefix xs:   &lt;http://www.w3.org/2001/XMLSchema#&gt; .&#10;&#10;</xsl:text>

    <xsl:apply-templates
      select="//e:archdesc" />
    <xsl:call-template name="agenten" />

  </xsl:template>

  <!-- ============ Bestand (RecordSet) ============ -->
  <xsl:template
    match="e:archdesc">

    <!-- Bestands-IRI extrahieren und als Tripel schreiben -->
    <xsl:variable name="iri" select="f:res-iri(.)" />
    <xsl:text>&#10;# ===== Bestand =====&#10;</xsl:text>
    <xsl:value-of
      select="concat('&lt;',$iri,'&gt; a rico:RecordSet')" />

    <!-- Bestandstitel extrahieren und als Tripel schreiben -->
    <xsl:value-of
      select="concat(' ;&#10;    rico:title ',
      f:lit(string(e:did/e:unittitle)))" />

    <!-- falls vorhanden, Bestands-ID extrahieren und als Tripel schreiben -->  
    <xsl:if
      test="@id"> 
      <xsl:value-of
        select="concat(' ;&#10;    rico:identifier ',
        f:lit(string(@id)))" />
    </xsl:if>

    <!-- Genreformen des Bestands, falls Referenz auf GND vorhanden ist -->
    <xsl:for-each
      select="e:controlaccess/e:genreform[@source='GND' and @authfilenumber]">
      <xsl:value-of
        select="concat(' ;&#10;    rico:hasRecordSetType &lt;',$gnd,@authfilenumber,'&gt;')" />
    </xsl:for-each>

    <!-- OPTIONAL: falls vorhanden, Bestandsumfang extrahieren und als Tripel schreiben -->
    <!-- <xsl:if test="e:did/e:physdesc/e:extent">
      <xsl:value-of select="concat(' ;&#10;    rico:recordResourceExtent ',
        f:lit(string(e:did/e:physdesc/e:extent[1])))"/>
    </xsl:if> -->

    <!-- OPTIONAL: falls vorhanden, Beschreibung der Bestandsinhalte extrahieren und als Tripel
    schreiben -->
    <!-- <xsl:if test="e:scopecontent/e:p">
      <xsl:value-of select="concat(' ;&#10;    rico:scopeAndContent ',
        f:lit(string-join(e:scopecontent/e:p,' ')))"/>
    </xsl:if> -->

    <!-- OPTIONAL: falls vorhanden, Bemerkung zum Bestand extrahieren und als Tripel schreiben -->
    <!-- <xsl:if test="e:did/e:note/e:p">
      <xsl:value-of select="concat(' ;&#10;    rico:history ',
        f:lit(string-join(e:did/e:note/e:p,' ')))"/>
    </xsl:if> -->

    <!-- Aufbewahrungsort auf Holder abbilden (lokale URI-Resolution inkorrekt, siehe EAD-Datei) -->
    <xsl:for-each
      select="e:did/e:repository/e:corpname[@role='Aufbewahrungsort']">
      <xsl:value-of select="concat(' ;&#10;    rico:hasOrHadHolder &lt;',f:agent-iri(.),'&gt;')" />
    </xsl:for-each>

    <!-- falls vorhanden und nicht als 'Unbekannt' angegeben, werden Bestandsbildner extrahiert und
    auf organische Provenienz abgebildet -->
    <xsl:for-each
      select="e:did/e:origination/e:persname[@role='Bestandsbildner'][f:known-agent(.)]">
      <xsl:value-of
        select="concat(' ;&#10;    rico:hasOrganicProvenance &lt;',f:agent-iri(.),'&gt;')" />
    </xsl:for-each>

    <!-- Verweise auf enthaltene Records hinzufügen -->
    <xsl:for-each
      select="e:dsc/e:c">
      <xsl:value-of select="concat(' ;&#10;    rico:directlyIncludes &lt;',f:res-iri(.),'&gt;')" />
    </xsl:for-each>
    <xsl:text> .&#10;</xsl:text>

    <xsl:text>&#10;# ===== Verzeichnungseinheiten =====&#10;</xsl:text>
    <xsl:apply-templates
      select=".//e:c" />
  </xsl:template>

  <!-- ============ Verzeichnungseinheit (Record) ============ -->
  <xsl:template match="e:c">
    <xsl:variable name="iri" select="f:res-iri(.)" />
    <!-- Parent-Element zur Referenzierung speichern. Prüfen, ob verschachteltes <c>-Element -->
    <xsl:variable name="parent"
      select="(ancestor::e:c[1], ancestor::e:archdesc[1])[1]" />
    
    <xsl:value-of
      select="concat('&lt;',$iri,'&gt; a rico:Record')" />

    <!-- Record-Titel extrahieren und als Tripel schreiben -->
    <xsl:value-of
      select="concat(' ;&#10;    rico:title ',
      f:lit(string(e:did/e:unittitle)))" />

    <!-- falls vorhanden Record-Signatur extrahieren und als Tripel schreiben (das ist nicht der
    Identifier, oder? Gibt es für die Signatur eine Entsprechung in RiC-O?) -->
    <xsl:if
      test="e:did/e:unitid[@label='Signatur']">
      <xsl:value-of
        select="concat(' ;&#10;    rico:identifier ',
        f:lit(string(e:did/e:unitid[@label='Signatur'][1])))" />
    </xsl:if>

    <!-- Genreformen des Records, falls Referenz auf GND vorhanden ist -->
    <xsl:for-each
      select="e:controlaccess/e:genreform[@source='GND' and @authfilenumber]">
      <xsl:value-of
        select="concat(' ;&#10;    rico:hasDocumentaryFormType &lt;',$gnd,@authfilenumber,'&gt;')" />
    </xsl:for-each>

    <!-- Entstehungsdatum -> rico:creationDate -->
    <xsl:if
      test="e:did/e:unitdate[@label='Entstehungsdatum' and @normal]">
      <xsl:value-of
        select="concat(' ;&#10;    rico:creationDate ',
        f:date-lit(string(e:did/e:unitdate/@normal)))" />
    </xsl:if>

    <!-- Verfasser -> rico:hasAuthor -->
    <xsl:for-each
      select="e:controlaccess/e:persname[@role='Verfasser'][f:known-agent(.)]">
      <xsl:value-of select="concat(' ;&#10;    rico:hasAuthor &lt;',f:agent-iri(.),'&gt;')" />
    </xsl:for-each>

    <!-- Adressat -> rico:hasAddressee (Unbekannt wird ausgelassen) -->
    <xsl:for-each
      select="e:controlaccess/e:persname[@role='Adressat'][f:known-agent(.)]">
      <xsl:value-of select="concat(' ;&#10;    rico:hasAddressee &lt;',f:agent-iri(.),'&gt;')" />
    </xsl:for-each>

    <!-- Entstehungsort -> rico:isAssociatedWithPlace  -->
    <xsl:for-each
      select="e:controlaccess/e:geogname[@role='Entstehungsort']">
      <xsl:value-of
        select="concat(' ;&#10;    rico:isAssociatedWithPlace ',
        f:lit(string(.)))" />
    </xsl:for-each>

    <!-- Sprache -->
    <xsl:for-each
      select="e:did/e:langmaterial/e:language[@langcode]">
      <xsl:value-of
        select="concat(' ;&#10;    rico:hasOrHadLanguage &lt;',$lang-base,@langcode,'&gt;')" />
    </xsl:for-each>

    <!-- OPTIONAL: Inhaltsnotiz -> rico:scopeAndContent  -->
    <!-- <xsl:if test="e:did/e:note/e:p">
      <xsl:value-of select="concat(' ;&#10;    rico:scopeAndContent ',
        f:lit(string-join(e:did/e:note/e:p,' '),'de'))"/>
    </xsl:if> -->

    <!-- Aufbewahrungsort -> rico:hasOrHadHolder -->
    <xsl:for-each
      select="e:did/e:repository/e:corpname[@role='Aufbewahrungsort']">
      <xsl:value-of select="concat(' ;&#10;    rico:hasOrHadHolder &lt;',f:agent-iri(.),'&gt;')" />
    </xsl:for-each>

    <!-- Bestandszugehörigkeit -> rico:isOrWasIncludedIn -->
    <xsl:value-of
      select="concat(' ;&#10;    rico:isOrWasIncludedIn &lt;',f:res-iri($parent),'&gt;')" />

    <!-- Umfang -> rico:instantiationExtent -->
    <xsl:if
      test="e:did/e:physdesc/e:extent[@label='Umfang']">
      <xsl:value-of
        select="concat(' ;&#10;    rico:instantiationExtent ',
        f:lit(string(e:did/e:physdesc/e:extent[1])))" />
    </xsl:if>

    <xsl:text> .&#10;</xsl:text>

  </xsl:template>

  <!-- Agenten (dedupliziert) -->
  <xsl:template
    name="agenten">
    <xsl:text>&#10;# ===== Agenten =====&#10;</xsl:text>
    <!-- Agenten werden nach ihrer IRI gruppiert und so dedupliziert -->
    <xsl:for-each-group select="//e:persname[f:known-agent(.)] | //e:corpname"
      group-by="f:agent-key(.)">
      <xsl:variable name="n" select="current-group()[1]" />
      <xsl:variable name="iri"
        select="f:agent-iri($n)" />
      <xsl:value-of
        select="concat('&lt;',$iri,'&gt; a ',
        if (local-name($n)='corpname') then 'rico:CorporateBody' else 'rico:Person')" />
      <xsl:value-of
        select="concat(' ;&#10;    rico:name ', f:lit(($n/@normal,$n)[1]))" />

      <!-- falls vorhanden, GND-ID als rico:identifier -->
      <xsl:if
        test="$n/@authfilenumber!='' and $n/@source='GND'">
        <xsl:value-of
          select="concat(' ;&#10;    rico:identifier ', f:lit(string($n/@authfilenumber)))" />
      </xsl:if>

      <!-- OPTIONAL: Lebensdaten extrahieren - Diese Daten sollten in Zukunft direkt aus der GND
      kommen -->
      <!-- <xsl:variable name="y" select="f:years(string($n))"/>
      <xsl:if test="count($y) ge 2">
        <xsl:value-of select="concat(' ;&#10;    rico:birthDate &quot;',$y[1],'&quot;^^xs:gYear')"/>
        <xsl:value-of select="concat(' ;&#10;    rico:deathDate &quot;',$y[2],'&quot;^^xs:gYear')"/>
      </xsl:if> -->
      
      <xsl:text> .&#10;</xsl:text>
    </xsl:for-each-group>
  </xsl:template>

</xsl:stylesheet>