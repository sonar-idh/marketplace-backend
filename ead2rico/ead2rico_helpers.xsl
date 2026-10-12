<xsl:stylesheet version="3.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:xs="http://www.w3.org/2001/XMLSchema"
  xmlns:f="urn:local:funcs"
  exclude-result-prefixes="xs f">

  <!-- ============ Hilfsfunktionen ============ -->

  <!-- RDF-Literal schreiben -->
  <xsl:function
    name="f:lit" as="xs:string">
    <xsl:param name="t" as="xs:string?" />
    <xsl:sequence
      select="'&quot;' || f:esc(normalize-space($t)) || '&quot;'" />
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

  <xsl:variable
    name="gnd-anchored" as="xs:string"
    select="'^(?:1[0-4]?[0-9]{7}[0-9X]|[47][0-9]{6}-[0-9]|[1-9][0-9]{0,7}-[0-9X]|3[0-9]{7}[0-9X])$'" />

  <xsl:function
    name="f:gnd-ids" as="xs:string*">
    <!-- GND-Nummer-Validitaetspruefung -->
    <xsl:param name="value" as="xs:string?" />
    <xsl:sequence
      select="distinct-values(
      tokenize($value, '[^0-9X\-]+')[matches(., $gnd-anchored)])" />
  </xsl:function>

</xsl:stylesheet>