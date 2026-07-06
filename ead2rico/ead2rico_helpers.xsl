<xsl:stylesheet version="3.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:e="urn:isbn:1-931666-22-9"
    xmlns:f="urn:local:funcs"
    exclude-result-prefixes="xs e f">

  <!-- ============ Hilfsfunktionen ============ -->

  <!-- Literale Turtle-konform escapen -->
  <xsl:function name="f:esc" as="xs:string">
    <xsl:param name="t" as="xs:string?"/>
    <xsl:sequence select="
      replace(replace(replace(replace(replace(string($t),
        '\\','\\\\'), '&quot;','\\&quot;'),
        '&#10;','\\n'), '&#13;','\\r'), '&#9;','\\t')"/>
  </xsl:function>

  <!-- Literal schreiben mit optionalem Sprach-Tag-Parameter -->
  <xsl:function name="f:lit" as="xs:string">
    <xsl:param name="t" as="xs:string?"/>
    <xsl:param name="lang" as="xs:string?"/>
    <xsl:sequence select="concat('&quot;', f:esc(normalize-space($t)), '&quot;',
                                  if ($lang != '') then concat('@',$lang) else '')"/>
  </xsl:function>

  <!-- Kurzform: ohne Sprach-Tag -->
<xsl:function name="f:lit" as="xs:string">
  <xsl:param name="t" as="xs:string?"/>
  <xsl:sequence select="f:lit($t, '')"/>
</xsl:function>

  <!-- Slug für lokale IRIs -->
  <xsl:function name="f:slug" as="xs:string">
    <xsl:param name="t" as="xs:string?"/>
    <xsl:sequence select="
      replace(replace(lower-case(normalize-space(string($t))),
              '[^a-z0-9]+','-'), '(^-|-$)','')"/>
  </xsl:function>

  <!-- IRI einer Ressource (archdesc oder c) aus @id extrahieren -->
  <xsl:function name="f:res-iri" as="xs:string">
    <xsl:param name="n" as="element()"/>
    <xsl:sequence select="concat($base, $n/@id)"/>
  </xsl:function>

  <!-- Gruppierungsschlüssel eines Agenten -->
  <xsl:function name="f:agent-key" as="xs:string">
    <xsl:param name="n" as="element()"/>
    <xsl:sequence select="
      if ($n/@source='GND' and $n/@authfilenumber!='')
        then concat('GND:', $n/@authfilenumber)
        else concat($base, f:slug(($n/@normal, $n)[1]))"/>
  </xsl:function>

  <!-- IRI eines Agenten ermitteln: GND-URI oder lokal -->
  <xsl:function name="f:agent-iri" as="xs:string">
    <xsl:param name="n" as="element()"/>
    <xsl:sequence select="
      if ($n/@source='GND' and $n/@authfilenumber!='')
        then concat($gnd, $n/@authfilenumber)
        else concat($base, 'agent/', f:slug(($n/@normal, $n)[1]))"/>
  </xsl:function>

  <!-- Prüfen, ob Agent spezifizierte Person darstellt ('Unbekannt' wird ausgefiltert - Eventuell auf Literalausgabe statt Filterung umstellen) -->
  <xsl:function name="f:known-agent" as="xs:boolean">
    <xsl:param name="n" as="element()"/>
    <xsl:sequence select="not(normalize-space($n/@normal)='Unbekannt'
                               or normalize-space($n)='Unbekannt')"/>
  </xsl:function>

  <!-- Datum aus @normal in typisiertes Turtle-Literal -->
  <xsl:function name="f:date-lit" as="xs:string">
    <xsl:param name="raw" as="xs:string?"/>
    <xsl:variable name="d" select="normalize-space(string($raw))"/>
    <xsl:sequence select="
      if (matches($d,'^\d{8}$'))
        then concat('&quot;', substring($d,1,4),'-',substring($d,5,2),'-',substring($d,7,2),
                    '&quot;^^xs:date')
      else if (matches($d,'^\d{4}-\d{2}-\d{2}$')) then concat('&quot;',$d,'&quot;^^xs:date')
      else if (matches($d,'^\d{6}$'))
        then concat('&quot;', substring($d,1,4),'-',substring($d,5,2),'&quot;^^xs:gYearMonth')
      else if (matches($d,'^\d{4}-\d{2}$'))  then concat('&quot;',$d,'&quot;^^xs:gYearMonth')
      else if (matches($d,'^\d{4}$'))        then concat('&quot;',$d,'&quot;^^xs:gYear')
      else f:lit($d,'')"/>
  </xsl:function>

  <!-- Lebensdaten aus Anzeigeform 'Name (1874-1951)' ziehen -->
  <xsl:function name="f:years" as="xs:string*">
    <xsl:param name="t" as="xs:string?"/>
    <xsl:analyze-string select="string($t)" regex="\((\d{{4}})\s*-\s*(\d{{4}})\)">
      <xsl:matching-substring>
        <xsl:sequence select="regex-group(1)"/>
        <xsl:sequence select="regex-group(2)"/>
      </xsl:matching-substring>
    </xsl:analyze-string>
  </xsl:function>

</xsl:stylesheet>