<?xml version="1.0" encoding="UTF-8"?>
<!--
  ead2rico_dates.xsl  –  Datumsverarbeitung EAD unitdate/@normal  ->  RiC-O 1.1 (Turtle)
  Einzubinden per <xsl:include href="cer_dates.xsl"/> in ead2rico_main.xsl
-->
<xsl:stylesheet version="3.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:map="http://www.w3.org/2005/xpath-functions/map"
    xmlns:f="urn:local:funcs"
    exclude-result-prefixes="#all"
    expand-text="no">

    <!-- ==================================================================
       Ebene 1: Einstieg - kompletter @normal-Wert, inkl. Laufzeiten
       ================================================================== -->

  <xsl:function
        name="f:parse-normal" as="map(*)?">
        <xsl:param name="normal" as="xs:string?" />
    <xsl:variable name="t" as="xs:string"
            select="normalize-space(($normal,'')[1])" />
    <xsl:choose>
            <!-- Case: @normal nicht vorhanden oder leerer String -->
            <xsl:when test="$t eq ''">
                <xsl:sequence select="()" />
            </xsl:when>
            <!-- Case: Zeitspanne durch '/' angegeben -->
            <xsl:when test="contains($t,'/')">
                <xsl:variable name="a" as="map(*)?" select="f:token(substring-before($t,'/'))" />
        <xsl:variable
                    name="b" as="map(*)?" select="f:token(substring-after($t,'/'))" />
        <xsl:choose>
                    <xsl:when test="empty($a) or empty($b)">
                        <xsl:sequence select="()" />
                    </xsl:when>
                    <xsl:otherwise>
                        <!-- min/max statt a?begin / b?end: faengt vertauschte
                 Bereichsgrenzen (kommt in Kalliope vor) still ab. -->
            <xsl:sequence
                            select="map{
              'prec'   : 'range',
              'key'    : $a?key || '_' || $b?key,
              'begin'  : min(($a?begin, $b?begin)),
              'end'    : max(($a?end,   $b?end)),
              'swapped': $a?begin gt $b?begin
            }" />
                    </xsl:otherwise>
                </xsl:choose>
            </xsl:when>
            <!-- Case: Normaler Datumswert -->
            <xsl:otherwise>
                <xsl:sequence select="f:token($t)" />
            </xsl:otherwise>
        </xsl:choose>
    </xsl:function>

    <!-- ==================================================================
       Ebene 2: Verarbeitung eines singulaeren Datums in Form einzelner @normal-Token. Prueft Datumsformat
  und ruft f:ymd mit den korrekten Parametern auf.
       Rueckgabe: map{'prec','key','begin','end'} oder ()
       ================================================================== -->

  <xsl:function
        name="f:token" as="map(*)?">
        <xsl:param name="raw" as="xs:string" />
    <xsl:variable name="t" as="xs:string"
            select="normalize-space($raw)" />
    <xsl:choose>
            <!-- Extended und Basic werden bewusst getrennt geprueft, damit
           Fehler wie '2013-5-1' nicht durchrutschen. -->
            <!-- Inputformat: YYYY-MM-DD -->
            <xsl:when test="matches($t,'^\d{4}-\d{2}-\d{2}$')">
                <xsl:sequence
                    select="f:ymd(xs:integer(substring($t,1,4)),
                                    xs:integer(substring($t,6,2)),
                                    xs:integer(substring($t,9,2)))" />
            </xsl:when>
            <!-- Inputformat: YYYY-MM -->
            <xsl:when test="matches($t,'^\d{4}-\d{2}$')">
                <xsl:sequence
                    select="f:ymd(xs:integer(substring($t,1,4)),
                                    xs:integer(substring($t,6,2)), 0)" />
            </xsl:when>
            <!-- Inputformat: YYYYMMDD -->
            <xsl:when test="matches($t,'^\d{8}$')">
                <xsl:sequence
                    select="f:ymd(xs:integer(substring($t,1,4)),
                                    xs:integer(substring($t,5,2)),
                                    xs:integer(substring($t,7,2)))" />
            </xsl:when>
            <!-- Inputformat: YYYYMM -->
            <xsl:when test="matches($t,'^\d{6}$')">
                <xsl:sequence
                    select="f:ymd(xs:integer(substring($t,1,4)),
                                    xs:integer(substring($t,5,2)), 0)" />
            </xsl:when>
            <!-- Inputformat: YYYY -->
            <xsl:when test="matches($t,'^\d{4}$')">
                <xsl:sequence select="f:ymd(xs:integer($t), 0, 0)" />
            </xsl:when>
            <xsl:otherwise>
                <xsl:sequence select="()" />
            </xsl:otherwise>
        </xsl:choose>
    </xsl:function>

    <!-- Kern: Validität wird geprueft, Datum wird nach Praezision der Angabe verarbeitet (Jahr,
  Monat, Tag). Nullangaben (YYYYMM00) werden auf die tatsaechliche Praezision zurueckgefuehrt, nicht
  als kaputtes Tagesdatum behandelt. -->
  <xsl:function
        name="f:ymd" as="map(*)?">
        <xsl:param name="y" as="xs:integer" />
    <xsl:param name="m" as="xs:integer" />
    <xsl:param
            name="d"
            as="xs:integer" />
    <xsl:choose>
            <!-- Case: ungültiges Datum -->
            <xsl:when test="$y eq 0 or $m gt 12 or $d gt 31">
                <!-- Moeglicher Edge Case: Was passiert mit Datumsangaben vor dem Jahr Null?
                Momentan nicht zulaessig. -->
        <xsl:sequence select="()" />
            </xsl:when>

            <!-- Case: YYYY0000 / YYYY  -> Jahrespraezision -->
            <xsl:when test="$m eq 0">
                <xsl:sequence
                    select="map{
          'prec' : 'year',
          'key'  : f:pad($y,4),
          'begin': f:day($y,1,1),
          'end'  : f:day($y,12,31)
        }" />
            </xsl:when>

            <!-- Case: YYYYMM00 / YYYY-MM -> Monatspraezision -->
            <xsl:when test="$d eq 0">
                <xsl:sequence
                    select="map{
          'prec' : 'month',
          'key'  : f:pad($y,4) || '-' || f:pad($m,2),
          'begin': f:day($y,$m,1),
          'end'  : f:last-day($y,$m)
        }" />
            </xsl:when>

            <!-- Case: Tagespraezision, mit Kalenderpruefung -->
            <xsl:otherwise>
                <xsl:variable name="cand" as="xs:date?" select="f:day-safe($y,$m,$d)" />
        <xsl:choose>
                    <!-- Subcase: Kalendarisch korrekter Tag -->
                    <xsl:when test="exists($cand)">
                        <xsl:sequence
                            select="map{
              'prec' : 'day',
              'key'  : string($cand),
              'begin': $cand,
              'end'  : $cand
            }" />
                    </xsl:when>
                    <!-- Subcase: Kalendarisch inkorrekter Tag, z.B. 20130231: existiert nicht.
                    Nicht
          verwerfen, sondern auf Monat zurueckfuehren und markieren. -->
                    <xsl:otherwise>
                        <xsl:sequence
                            select="map{
              'prec' : 'month-repaired',
              'key'  : f:pad($y,4) || '-' || f:pad($m,2),
              'begin': f:day($y,$m,1),
              'end'  : f:last-day($y,$m)
            }" />
                    </xsl:otherwise>
                </xsl:choose>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:function>

    <!-- ==================================================================
       Ebene 3: Kalenderprimitive und Hilfsfunktionen
       ================================================================== -->

    <!-- baut xs:Date -->
  <xsl:function
        name="f:day" as="xs:date">
        <xsl:param name="y" as="xs:integer" />
    <xsl:param name="m" as="xs:integer" />
    <xsl:param
            name="d"
            as="xs:integer" />
    <xsl:sequence
            select="xs:date(f:pad($y,4) || '-' || f:pad($m,2) || '-' || f:pad($d,2))" />
    </xsl:function>

    <!-- prueft, ob das Datum kalendarisch existiert, gibt () zurueck, wenn nicht -->
  <xsl:function
        name="f:day-safe" as="xs:date?">
        <xsl:param name="y" as="xs:integer" />
    <xsl:param name="m" as="xs:integer" />
    <xsl:param
            name="d"
            as="xs:integer" />
    <xsl:variable name="s" as="xs:string"
            select="f:pad($y,4) || '-' || f:pad($m,2) || '-' || f:pad($d,2)" />
    <xsl:sequence
            select="if ($s castable as xs:date) then xs:date($s) else ()" />
    </xsl:function>

    <!-- prueft letzten Tag des Monats: Erster des Folgemonats minus ein Tag.
       Erledigt Schaltjahre und den Dezember-Jahreswechsel von selbst. -->
  <xsl:function
        name="f:last-day" as="xs:date">
        <xsl:param name="y" as="xs:integer" />
    <xsl:param name="m" as="xs:integer" />
    <xsl:sequence
            select="f:day($y,$m,1)
                          + xs:yearMonthDuration('P1M')
                          - xs:dayTimeDuration('P1D')" />
    </xsl:function>

    <!-- fuellt Zahl mit fuehrenden Nullen auf: $n ist die Zahl und $w definiert die Gesamtzahl an
  Stellen  -->
  <xsl:function
        name="f:pad" as="xs:string">
        <xsl:param name="n" as="xs:integer" />
    <xsl:param name="w" as="xs:integer" />
    <xsl:sequence
            select="format-number($n, string-join((1 to $w) ! '0'))" />
    </xsl:function>

</xsl:stylesheet>