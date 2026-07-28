<xsl:stylesheet version="3.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:xs="http://www.w3.org/2001/XMLSchema"
  xmlns:f="urn:local:funcs"
  exclude-result-prefixes="xs f">

  <!-- ============ Hilfsfunktionen ============ -->

  <!-- Literal schreiben mit optionalem Sprach-Tag-Parameter -->
  <xsl:function
    name="f:lit" as="xs:string">
    <xsl:param name="t" as="xs:string?" />
    <xsl:sequence
      select="concat('&quot;', f:esc(normalize-space($t)), '&quot;')" />
  </xsl:function>

  <!-- Datum aus @normal in typisiertes Turtle-Literal -->
  <xsl:function
    name="f:date-lit" as="xs:string">
    <xsl:param name="raw" as="xs:string?" />
    <xsl:variable name="d"
      select="normalize-space(string($raw))" />
    <xsl:sequence
      select="
      if (matches($d,'^\d{8}$'))
        then concat('&quot;', substring($d,1,4),'-',substring($d,5,2),'-',substring($d,7,2),
                    '&quot;^^xs:date')
      else if (matches($d,'^\d{4}-\d{2}-\d{2}$')) then concat('&quot;',$d,'&quot;^^xs:date')
      else if (matches($d,'^\d{6}$'))
        then concat('&quot;', substring($d,1,4),'-',substring($d,5,2),'&quot;^^xs:gYearMonth')
      else if (matches($d,'^\d{4}-\d{2}$'))  then concat('&quot;',$d,'&quot;^^xs:gYearMonth')
      else if (matches($d,'^\d{4}$'))        then concat('&quot;',$d,'&quot;^^xs:gYear')
      else f:lit($d)" />
  </xsl:function>

  <!-- Text in eine IRI-taugliche Kurzform ueberfuehren -->
  <xsl:function
    name="f:slug" as="xs:string">
    <xsl:param name="t" as="xs:string?" />
    <xsl:variable name="s" as="xs:string" select="lower-case(normalize-space(string($t)))" />
    <xsl:sequence
      select="replace(replace($s, '[^a-z0-9]+', '-'), '^-+|-+$', '')" />
  </xsl:function>

  <!-- Literale Turtle-konform escapen -->
  <xsl:function
    name="f:esc" as="xs:string">
    <xsl:param name="t" as="xs:string?" />
    <!-- Backslashes, Anführungszeichen, Zeilenumbrüche, Carriage Returns und Tabs escapen -->
    <xsl:sequence
      select="
      replace(
      replace(
      replace(
      replace(
      replace(
      string($t),
        '\\','\\\\'),
        '&quot;','\\&quot;'),
        '&#10;','\\n'),
        '&#13;','\\r'),
        '&#9;','\\t')" />
  </xsl:function>

</xsl:stylesheet>