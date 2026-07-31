<?xml version="1.0" encoding="UTF-8"?>
<!--
  cer_places.xsl  –  Verarbeitung von Ortsangaben EAD controlaccess/geogname  ->  CER 2.0
  Einzubinden per <xsl:include href="cer_places.xsl"/> in ead2cer_main.xsl
-->

<xsl:stylesheet version="3.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:xs="http://www.w3.org/2001/XMLSchema"
  xmlns:map="http://www.w3.org/2005/xpath-functions/map"
  xmlns:f="urn:local:funcs"
  xmlns:cer="http://sonar.staatsbibliothek-berlin.de/ns/templates"
  xmlns:e="urn:isbn:1-931666-22-9"
  exclude-result-prefixes="#all"
  expand-text="no">

  <!-- ==================================================================
       Konfiguration
       ================================================================== -->

  <!-- @role-Werte, die einen Entstehungs-/Absendeort kennzeichnen (an cer:13_Sending
       angehängt). Laut Dump-Analyse (siehe README) die drei häufigsten Synonyme. -->
  <xsl:param name="origin-place-roles" as="xs:string+"
    select="('Entstehungsort', 'PlaceOfOrigin', 'Absendeort')" />

  <!-- @role-Werte, die einen Zielort kennzeichnen (an cer:14_Receiving angehängt). -->
  <xsl:param name="destination-place-roles" as="xs:string+"
    select="('Zielort')" />

  <!-- ==================================================================
       Tripel schreiben
       ================================================================== -->

  <!-- Verknüpft sämtliche normdateireferenzierten geogname-Elemente (@source='GND' und
       @authfilenumber vorhanden, @role in $roles) per cer:P7_took_place_at mit der
       aufrufenden Aktivität (13_Sending oder 14_Receiving). Die GND-Normdatenressource
       wird analog zu Personen/Körperschaften direkt referenziert, ohne eigene
       Place-Entität anzulegen. -->
  <xsl:template
    name="cer:link-places">
    <xsl:param name="geognames" as="element(e:geogname)*" />
    <xsl:param name="roles"
      as="xs:string+" />
    <xsl:for-each
      select="$geognames[@source = 'GND' and @authfilenumber and @role = $roles]">
      <xsl:choose>
        <xsl:when test="position() = 1">
          <xsl:value-of
            select="' ;&#10;    cer:P7_took_place_at gnd:' || @authfilenumber" />
        </xsl:when>
        <xsl:otherwise>
          <xsl:value-of select="', gnd:' || @authfilenumber" />
        </xsl:otherwise>
      </xsl:choose>
    </xsl:for-each>
  </xsl:template>

</xsl:stylesheet>
