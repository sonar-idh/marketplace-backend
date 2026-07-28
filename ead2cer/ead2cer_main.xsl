<?xml version="1.0" encoding="UTF-8"?>
<!--
  ead2cer.xsl  —  EAD (Kalliope/EAD 2002) -> Correspondence and Epistolary Research Ontology 2.0
(Turtle)
  XSLT 3.0 (Saxon-HE / SaxonC-HE).

  Aufruf (Beispiel):
    saxonb-xslt -s:ead_DE-1_5364_test.xml -xsl:ead2cer_main.xsl -o:out.ttl
  Parameter (per -base:... etc. überschreibbar):
    base       Basis-IRI für lokal geprägte Ressourcen 
-->
<xsl:stylesheet version="3.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:xs="http://www.w3.org/2001/XMLSchema"
  xmlns:f="urn:local:funcs"
  xmlns:cer="http://sonar.staatsbibliothek-berlin.de/ns/templates"
  exclude-result-prefixes="xs f cer">

  <xsl:output method="text" encoding="UTF-8" />
  <xsl:strip-space
    elements="*" />

  <!-- ============ Funktionen aus Helper-Stylesheet einbinden ============ -->
  <xsl:include href="ead2cer_helpers.xsl" />
  <xsl:include href="cer_dates.xsl" />

  <!-- ============ Einstieg ============ -->
  <xsl:template
    match="/">
    <!-- Präfixe -->
    <xsl:text>@prefix cer: &lt;https://lod.academy/cer/vocab/ontology/#&gt; .&#10;</xsl:text>
    <xsl:text>@prefix crm: &lt;http://www.cidoc-crm.org/cidoc-crm/#&gt; .&#10;</xsl:text>
    <xsl:text>@prefix sonar: &lt;https://data.sbb.spk-berlin.de/sonar/id/&gt; .&#10;</xsl:text>
    <xsl:text>@prefix gnd: &lt;https://d-nb.info/gnd/&gt; .&#10;</xsl:text>
    <xsl:text>@prefix kpe: &lt;https://kalliope-verbund.info/ead?ead.id=&gt; .&#10;</xsl:text>
    <xsl:text>@prefix rdf:  &lt;http://www.w3.org/1999/02/22-rdf-syntax-ns#&gt; .&#10;</xsl:text>
    <xsl:text>@prefix rdfs: &lt;http://www.w3.org/2000/01/rdf-schema#&gt; .&#10;</xsl:text>
    <xsl:text>@prefix xs:   &lt;http://www.w3.org/2001/XMLSchema#&gt; .&#10;&#10;</xsl:text>

    <xsl:text>&#10;# ===== Briefe =====&#10;</xsl:text>

    <xsl:apply-templates
      select="//*:c" />
    <!-- <xsl:call-template name="agenten" /> -->

  </xsl:template>

  <!-- ============ Verzeichnungseinheit  ============ -->

  <!-- sämtliche c-Elemente des Bestands finden -->
  <xsl:template match="*:c">
    <!-- Bedingung: c-Element hat genreform Brief -->
    <xsl:if
      test="*:controlaccess/*:genreform = 'Brief'">
      <!-- Funktionsaufruf: Brief-URI aus KPE-Identifier konstruieren -->
      <xsl:variable name="record_id" select="@id" />
      <xsl:value-of
        select="concat('kpe:', $record_id, ' a cer:1_Letter')" />
      <!-- did/unittitle als rdfs:label oder crm:P102_has_title schreiben -->
      <xsl:value-of
        select="concat(' ;&#10;    crm:P102_has_title ', f:lit(string(*:did/*:unittitle)))" />
      <xsl:text> .&#10;&#10;</xsl:text>

      <!-- Sending-Event: Sämtliche Verfasser auflisten -->
      <xsl:if
        test="(*:controlaccess/*:persname | *:controlaccess/*:corpname)[@role = 'Verfasser' and @source = 'GND' and @authfilenumber]">
        <xsl:value-of
          select="concat('sonar:Sending_', $record_id, ' a cer:13_Sending')" />
        <!-- Referenz auf Brief-Entität -->
        <xsl:value-of
          select="concat(' ;&#10;    cer:P9_was_intended_use_of ', 'kpe:', $record_id)" />
        <!-- Sämtliche Verfasserknoten auswerten -->
        <xsl:for-each
          select="(*:controlaccess/*:persname | *:controlaccess/*:corpname)
                      [@role = 'Verfasser' and @source = 'GND' and @authfilenumber]">
          <xsl:choose>
            <xsl:when test="position() = 1">
              <xsl:value-of
                select="concat(' ;&#10;    cer:P8_carried_out_by ', 'gnd:', @authfilenumber)" />
            </xsl:when>
            <xsl:otherwise>
              <xsl:value-of
                select="concat(', gnd:', @authfilenumber)" />
            </xsl:otherwise>
          </xsl:choose>
        </xsl:for-each>
        <!-- Entstehungsdatum als Time-Span an Sending-Entität anhängen  -->
        <xsl:call-template name="cer:link-all-timespans">
          <xsl:with-param name="unitdates" select="*:did/*:unitdate[@label = 'Entstehungsdatum']" />
          <xsl:with-param name="record-id" select="$record_id" />
        </xsl:call-template>
        <xsl:text> .&#10;&#10;</xsl:text>
        <!-- Time-Span-Entitäten des Briefs instanziieren -->
        <xsl:call-template name="cer:emit-all-timespans">
          <xsl:with-param name="unitdates" select="*:did/*:unitdate[@label = 'Entstehungsdatum']" />
          <xsl:with-param name="record-id" select="$record_id" />
        </xsl:call-template>
      </xsl:if>

      <!-- Receiving-Event: Sämtliche Verfasser auflisten -->
      <xsl:if
        test="(*:controlaccess/*:persname | *:controlaccess/*:corpname)[@role = 'Adressat' and @source = 'GND' and @authfilenumber]">
        <xsl:value-of
          select="concat('sonar:Receiving_', $record_id, ' a cer:14_Receiving')" />
        <xsl:value-of
          select="concat(' ;&#10;    cer:P9_was_intended_use_of ', 'kpe:', $record_id)" />
        <xsl:for-each
          select="(*:controlaccess/*:persname | *:controlaccess/*:corpname)
                      [@role = 'Adressat' and @source = 'GND' and @authfilenumber]">
          <xsl:choose>
            <xsl:when test="position() = 1">
              <xsl:value-of
                select="concat(' ;&#10;    cer:P8_carried_out_by ', 'gnd:', @authfilenumber)" />
            </xsl:when>
            <xsl:otherwise>
              <xsl:value-of
                select="concat(', gnd:', @authfilenumber)" />
            </xsl:otherwise>
          </xsl:choose>
        </xsl:for-each>
        <xsl:text> .&#10;&#10;</xsl:text>
      </xsl:if>

    </xsl:if>

  </xsl:template>


</xsl:stylesheet>