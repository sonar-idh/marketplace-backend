<?xml version="1.0" encoding="UTF-8"?>
<!--
  ead2rico_main.xsl  —  EAD (Kalliope/EAD 2002) -> RiC-O 1.1 (Turtle)
  XSLT 3.0 (Saxon-HE / SaxonC-HE). saxonb-xslt (Saxon-B) reicht NICHT aus,
  da XSLT-3.0/XPath-3.1-Funktionen genutzt werden.

  Aufruf (Beispiel):
    java -cp /usr/share/java/Saxon-HE.jar net.sf.saxon.Transform \
      -s:ead_DE-1_5364_test.xml -xsl:ead2rico_main.xsl -o:out.ttl
-->
<xsl:stylesheet version="3.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:xs="http://www.w3.org/2001/XMLSchema"
  xmlns:f="urn:local:funcs"
  exclude-result-prefixes="xs f">

  <xsl:output method="text" encoding="UTF-8" />
  <xsl:strip-space elements="*" />

  <!-- ============ Funktionen aus Helper-Stylesheet einbinden ============ -->
  <xsl:include
    href="ead2rico_helpers.xsl" />
  <xsl:include
    href="ead2rico_dates.xsl" />

  <!-- ============ Einstieg ============ -->
  <xsl:template
    match="/">
    <!-- Praefixe -->
    <xsl:text>@prefix rico: &lt;https://www.ica.org/standards/RiC/ontology#&gt; .&#10;</xsl:text>
    <xsl:text>@prefix rdf:  &lt;http://www.w3.org/1999/02/22-rdf-syntax-ns#&gt; .&#10;</xsl:text>
    <xsl:text>@prefix rdfs: &lt;http://www.w3.org/2000/01/rdf-schema#&gt; .&#10;</xsl:text>
    <xsl:text>@prefix xs:   &lt;http://www.w3.org/2001/XMLSchema#&gt; .&#10;</xsl:text>
    <xsl:text>@prefix sonar: &lt;https://data.sbb.spk-berlin.de/sonar/id/&gt; .&#10;</xsl:text>
    <xsl:text>@prefix gnd: &lt;https://d-nb.info/gnd/&gt; .&#10;</xsl:text>
    <xsl:text>@prefix isil: &lt;https://isil.staatsbibliothek-berlin.de/isil/&gt; .&#10;</xsl:text>
    <xsl:text>@prefix kpe: &lt;https://kalliope-verbund.info/ead?ead.id=&gt; .&#10;&#10;</xsl:text>

    <xsl:apply-templates
      select="//*:archdesc" />

  </xsl:template>

  <!-- ============ Bestand (RecordSet) ============ -->

  <xsl:template
    match="*:archdesc">

    <!-- Bestands-IRI extrahieren und als Tripel schreiben -->
    <xsl:variable name="iri" select="string(@id)" />
    <xsl:text>&#10;# ===== Bestand =====&#10;&#10;</xsl:text>
    <xsl:value-of
      select="'kpe:' || $iri || ' a rico:RecordSet'" />

    <!-- Bestandstitel extrahieren und als Tripel schreiben -->
    <xsl:if
      test="*:did/*:unittitle">
      <xsl:value-of
        select="' ;&#10;    rico:title ' ||
        f:lit(string(*:did/*:unittitle))" />
    </xsl:if>

    <!-- falls vorhanden, Bestands-ID extrahieren und als Tripel schreiben -->
    <xsl:if
      test="@id">
      <xsl:value-of
        select="' ;&#10;    rico:identifier ' ||
        f:lit(string(@id))" />
    </xsl:if>

    <!-- Genreformen des Bestands, falls Referenz auf GND vorhanden ist -->
    <xsl:for-each
      select="*:controlaccess/*:genreform[@source='GND' and @authfilenumber]">
      <xsl:value-of
        select="' ;&#10;    rico:hasRecordSetType gnd:' || @authfilenumber" />
    </xsl:for-each>

    <!-- OPTIONAL: falls vorhanden, Bestandsumfang extrahieren und als Tripel schreiben -->
    <!-- <xsl:if test="*:did/*:physdesc/*:extent">
      <xsl:value-of select="' ;&#10;    rico:recordResourceExtent ' ||
        f:lit(string(*:did/*:physdesc/*:extent[1]))"/>
    </xsl:if> -->

    <!-- OPTIONAL: falls vorhanden, Beschreibung der Bestandsinhalte extrahieren und als Tripel
    schreiben -->
    <!-- <xsl:if test="*:scopecontent/*:p">
      <xsl:value-of select="' ;&#10;    rico:scopeAndContent ' ||
        f:lit(string-join(*:scopecontent/*:p,' '))"/>
    </xsl:if> -->

    <!-- OPTIONAL: falls vorhanden, Bemerkung zum Bestand extrahieren und als Tripel schreiben -->
    <!-- <xsl:if test="*:did/*:note/*:p">
      <xsl:value-of select="' ;&#10;    rico:history ' ||
        f:lit(string-join(*:did/*:note/*:p,' '))"/>
    </xsl:if> -->

    <!-- did/repository/corpname auf rico:hasOrHadHolder abbilden. Nur ISIL-referenzierte
    Institutionen werden momentan erfasst -->
    <xsl:for-each
      select="*:did/*:repository/*:corpname">
      <xsl:if
        test="@source='ISIL' and @authfilenumber">
        <xsl:value-of select="' ;&#10;    rico:hasOrHadHolder ' || 'isil:' || @authfilenumber" />
      </xsl:if>
    </xsl:for-each>

    <!-- GND-referenzierte Bestandsbildner werden extrahiert und auf rico:hasOrganicProvenance
    abgebildet. Hier sollte Analyse von did/origination erfolgen, um Werteverteilung der role- und
    source-Attribute bei persname/corpname besser zu verstehen -->
    <xsl:for-each
      select="*:did/*:origination/*:persname[@role='Bestandsbildner' and @source='GND' and @authfilenumber]">
      <xsl:value-of select="' ;&#10;    rico:hasOrganicProvenance gnd:' || @authfilenumber" />
    </xsl:for-each>

    <!-- Verweise auf enthaltene Brief-Records hinzufügen. c-Verschachtelungsstruktur momentan
    ausgeblendet. Soll rico:includesOrIncluded oder ricoIncludesTransitive hier verwendet werden? -->
    <xsl:for-each
      select="*:dsc//*:c[*:controlaccess/*:genreform = 'Brief']">
      <xsl:value-of select="' ;&#10;    rico:includesTransitive kpe:' || @id" />
      <!-- Hier könnte man noch komma-separierte Angabe der Verzeichnungseinheiten einfuehren -->
    </xsl:for-each>
    <xsl:text> .&#10;</xsl:text>


  <!-- ============ Verzeichnungseinheit (Record) ============ -->

    <xsl:text>&#10;# ===== Verzeichnungseinheiten =====&#10;&#10;</xsl:text>
    <xsl:apply-templates
      select=".//*:c" />
  </xsl:template>

  <xsl:template match="*:c">
    <xsl:if
      test="*:controlaccess/*:genreform = 'Brief'">
      <xsl:variable name="iri" select="string(@id)" />
      <!-- TODO: zeigt momentan immer auf den Bestand statt auf das naechste umschließende <c>,
      da die c-Verschachtelungsstruktur beim Erzeugen der Records noch nicht korrekt
      nachgebildet wird. Spaeter durch echte Verschachtelung ersetzen
      (z. B. wieder (ancestor::*:c[1], ancestor::*:archdesc[1])[1]). -->
      <xsl:variable name="parent"
        select="ancestor::*:archdesc[1]" />

      <xsl:value-of
        select="'kpe:' || $iri || ' a rico:Record'" />

      <!-- Record-Titel extrahieren und als Tripel schreiben -->
      <xsl:value-of
        select="' ;&#10;    rico:title ' ||
        f:lit(string(*:did/*:unittitle))" />

      <!-- falls vorhanden Record-Signatur extrahieren und als Tripel schreiben (das ist nicht der
      Identifier, oder? Gibt es fuer die Signatur eine Entsprechung in RiC-O?) -->
      <!-- <xsl:if
        test="*:did/*:unitid[@label='Signatur']">
        <xsl:value-of
          select="' ;&#10;    rico:identifier ' ||
          f:lit(string(*:did/*:unitid[@label='Signatur'][1]))" />
      </xsl:if> -->

      <!-- Genreformen des Records, falls Referenz auf GND vorhanden ist -->
      <xsl:for-each
        select="*:controlaccess/*:genreform[@source='GND' and @authfilenumber]">
        <xsl:value-of
          select="' ;&#10;    rico:hasDocumentaryFormType gnd:' || @authfilenumber" />
      </xsl:for-each>

      <!-- Entstehungsdatum wird behelfsmaeßig auf rico:beginningDate und rico:endDate statt auf
      rico:creationDate abgebildet. Alternativen müssten disutiert werden. Die Verarbeitung
      verschiedener Input-Datumsformate erfolgt in ead2rico_dates.xsl -->
      <xsl:for-each
        select="*:did/*:unitdate[@label='Entstehungsdatum' and @normal and f:parse-normal(@normal) instance of map(*)]">
        <xsl:variable name="dm" select="f:parse-normal(@normal)" />
        <xsl:value-of
          select="' ;&#10;    rico:beginningDate ' || f:lit(string($dm?begin)) || '^^xs:date'" />
        <xsl:value-of
          select="' ;&#10;    rico:endDate ' || f:lit(string($dm?end)) || '^^xs:date'" />
      </xsl:for-each>

      <!-- Verfasser -> rico:hasAuthor (persname und corpname) -->
      <xsl:for-each
        select="*:controlaccess/(*:persname|*:corpname)[@role='Verfasser' and @source='GND' and @authfilenumber]">
        <xsl:value-of
          select="' ;&#10;    rico:hasAuthor gnd:' || @authfilenumber" />
      </xsl:for-each>

      <!-- Adressat -> rico:hasAddressee (persname und corpname, Unbekannt wird ausgelassen) -->
      <xsl:for-each
        select="*:controlaccess/(*:persname|*:corpname)[@role='Adressat' and @source='GND' and @authfilenumber]">
        <xsl:value-of select="' ;&#10;    rico:hasAddressee gnd:' || @authfilenumber" />
      </xsl:for-each>

      <!-- Entstehungsort -> rico:isAssociatedWithPlace  -->
      <!-- <xsl:for-each
        select="*:controlaccess/*:geogname[@role='Entstehungsort']">
        <xsl:value-of
          select="' ;&#10;    rico:isAssociatedWithPlace ' ||
          f:lit(string(.))" />
      </xsl:for-each> -->

      <!-- Sprache -->
      <!-- <xsl:for-each
        select="*:did/*:langmaterial/*:language[@langcode]">
        <xsl:value-of
          select="' ;&#10;    rico:hasOrHadLanguage &lt;' || $lang-base || @langcode || '&gt;'" />
      </xsl:for-each> -->

      <!-- OPTIONAL: Inhaltsnotiz -> rico:scopeAndContent  -->
      <!-- <xsl:if test="*:did/*:note/*:p">
        <xsl:value-of select="' ;&#10;    rico:scopeAndContent ' ||
          f:lit(string-join(*:did/*:note/*:p,' '),'de')"/>
      </xsl:if> -->

      <!-- Aufbewahrungsort -> rico:hasOrHadHolder -->
      <!-- <xsl:for-each
        select="*:did/*:repository/*:corpname[@role='Aufbewahrungsort']">
        <xsl:value-of select="' ;&#10;    rico:hasOrHadHolder &lt;' || f:agent-iri(.) || '&gt;'" />
      </xsl:for-each> -->

      <!-- Bestandszugehörigkeit -> rico:isOrWasIncludedIn -->
      <xsl:value-of
        select="' ;&#10;    rico:isOrWasIncludedIn kpe:' || string($parent/@id)" />

      <!-- Umfang -> rico:instantiationExtent -->
      <!-- <xsl:if
        test="*:did/*:physdesc/*:extent[@label='Umfang']">
        <xsl:value-of
          select="' ;&#10;    rico:instantiationExtent ' ||
          f:lit(string(*:did/*:physdesc/*:extent[1]))" />
      </xsl:if> -->

      <xsl:text> .&#10;&#10;</xsl:text>
    </xsl:if>

  </xsl:template>

</xsl:stylesheet>
