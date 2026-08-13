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
      select="concat('&quot;', f:esc(normalize-space($t)), '&quot;')" />
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