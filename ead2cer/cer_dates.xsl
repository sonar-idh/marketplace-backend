<?xml version="1.0" encoding="UTF-8"?>
<!--
  cer_dates.xsl  –  Datumsverarbeitung EAD unitdate/@normal  ->  CER 2.0
  Einzubinden per <xsl:include href="cer_dates.xsl"/> in ead2cer_main.xsl
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

  <!-- Wertproperty fuer CER26/CER27 ist in der publizierten Ontologie
       nicht definiert. Zentral parametrisiert, damit sie nach Klaerung
       mit dem CER-Team an EINER Stelle getauscht werden kann. -->
  <xsl:param name="date-value-prop" as="xs:string" select="'crm:P90_has_value'" />

  <!-- Sekundengenaues Ende des Tages fuer P82b -->
  <!-- Funktion wird nur gebraucht, falls CRM-Vierpunkt-Achse implemtiert wird --> 
  <xsl:variable
    name="f:t-start" as="xs:time" select="xs:time('00:00:00Z')" />
  <!-- Funktion wird nur gebraucht, falls CRM-Vierpunkt-Achse implemtiert wird -->
  <xsl:variable name="f:t-end"
    as="xs:time" select="xs:time('23:59:59Z')" />

  <!-- ==================================================================
       Ebene 1: Kalenderprimitive
       ================================================================== -->

  <xsl:function name="f:day" as="xs:date">
    <xsl:param name="y" as="xs:integer" />
    <xsl:param name="m" as="xs:integer" />
    <xsl:param name="d"
      as="xs:integer" />
    <xsl:sequence
      select="xs:date(f:pad($y,4) || '-' || f:pad($m,2) || '-' || f:pad($d,2))" />
  </xsl:function>

  <!-- gibt () zurueck, wenn das Datum kalendarisch nicht existiert -->
  <xsl:function
    name="f:day-safe" as="xs:date?">
    <xsl:param name="y" as="xs:integer" />
    <xsl:param name="m" as="xs:integer" />
    <xsl:param name="d"
      as="xs:integer" />
    <xsl:variable name="s" as="xs:string"
      select="f:pad($y,4) || '-' || f:pad($m,2) || '-' || f:pad($d,2)" />
    <xsl:sequence
      select="if ($s castable as xs:date) then xs:date($s) else ()" />
  </xsl:function>

  <!-- letzter Tag des Monats: Erster des Folgemonats minus ein Tag.
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

  <!-- Funktion wird nur gebraucht, falls CRM-Vierpunkt-Achse implemtiert wird -->
  <xsl:function
    name="f:dt-begin" as="xs:dateTime">
    <xsl:param name="d" as="xs:date" />
    <xsl:sequence select="dateTime($d, $f:t-start)" />
  </xsl:function>

  <!-- Funktion wird nur gebraucht, falls CRM-Vierpunkt-Achse implemtiert wird -->
  <xsl:function
    name="f:dt-end" as="xs:dateTime">
    <xsl:param name="d" as="xs:date" />
    <xsl:sequence select="dateTime($d, $f:t-end)" />
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
           Muell wie '2013-5-1' nicht durchrutscht. -->
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

  <!-- Kern: Nullkomponenten werden auf die tatsaechliche Praezision
       zurueckgefuehrt, nicht als kaputtes Tagesdatum behandelt. -->
  <xsl:function
    name="f:ymd" as="map(*)?">
    <xsl:param name="y" as="xs:integer" />
    <xsl:param name="m" as="xs:integer" />
    <xsl:param name="d"
      as="xs:integer" />
    <xsl:choose>
      <!-- Case: ungültiges Datum -->
      <xsl:when test="$y eq 0 or $m gt 12 or $d gt 31">
        <!-- Möglicher Edge Case: Was passiert mit Datumsangaben vor dem Jahr Null? Momentan nicht
        zulässig. -->
        <xsl:sequence select="()" />
      </xsl:when>

      <!-- YYYY0000 / YYYY  -> Jahrespraezision -->
      <xsl:when test="$m eq 0">
        <xsl:sequence
          select="map{
          'prec' : 'year',
          'key'  : f:pad($y,4),
          'begin': f:day($y,1,1),
          'end'  : f:day($y,12,31)
        }" />
      </xsl:when>

      <!-- YYYYMM00 / YYYY-MM -> Monatspraezision -->
      <xsl:when test="$d eq 0">
        <xsl:sequence
          select="map{
          'prec' : 'month',
          'key'  : f:pad($y,4) || '-' || f:pad($m,2),
          'begin': f:day($y,$m,1),
          'end'  : f:last-day($y,$m)
        }" />
      </xsl:when>

      <!-- Tagespraezision, mit Kalenderpruefung -->
      <xsl:otherwise>
        <xsl:variable name="cand" as="xs:date?" select="f:day-safe($y,$m,$d)" />
        <xsl:choose>
          <xsl:when test="exists($cand)">
            <xsl:sequence
              select="map{
              'prec' : 'day',
              'key'  : string($cand),
              'begin': $cand,
              'end'  : $cand
            }" />
          </xsl:when>
          <!-- z.B. 20130231: existiert nicht. Nicht verwerfen,
               sondern auf Monat degradieren und markieren. -->
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
       Ebene 3: kompletter @normal-Wert, inkl. Bereiche
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
       IRIs.  Rolle MUSS in die Date-IRI, sonst truege derselbe Knoten
       bei einem Datum, das anderswo Endpunkt ist, rdf:type CER26 UND
       CER27.
       ================================================================== -->

  <!-- record-scoped: gleiches Datum in verschiedenen c-Elementen darf sich
       nicht denselben Time-Span-Knoten teilen, da das rdfs:label vom
       jeweiligen unitdate-Text abhaengt. -->
  <xsl:function
    name="f:ts-iri" as="xs:string">
    <xsl:param name="dm" as="map(*)" />
    <xsl:param name="record-id" as="xs:string" />
    <xsl:sequence
      select="'sonar:Time-Span_' || $record-id || '_' || $dm?key" />
  </xsl:function>

  <xsl:function
    name="f:date-iri" as="xs:string">
    <xsl:param name="d" as="xs:date" />
    <xsl:param name="role" as="xs:string" />
    <xsl:sequence
      select="'sonar:' || $role || '-Date_' || string($d)" />
  </xsl:function>

  <!-- ==================================================================
       Tripel schreiben.  Zwei getrennte Templates, um (1) Time-Spans an Sending-Entitäten der Briefe
  anzubinden und (2) Time-Span-, Start-Date- und End-Date-Entitäten anzulegen und zu verknuepfen.
       ================================================================== -->


  <!-- (1) -->
  <!-- pro Brief: eine P6_has_time-span-Zeile je distinktem Datum des Records. Nach aktuellem Stand
  enthält der Dump Brief-Einträge mit mehr als einer unitdate-Angabe. Werden aktuell dem
  Brief-Sending als mehrere Time-Spans hinzugefuegt -->
  <xsl:template
    name="cer:link-all-timespans">
    <xsl:param name="unitdates" as="element(e:unitdate)*" />
    <xsl:param name="record-id"
      as="xs:string" />
    <xsl:for-each-group
      select="$unitdates[f:parse-normal(@normal) instance of map(*)]"
      group-by="f:parse-normal(@normal)?key">
      <xsl:call-template name="cer:link-timespan">
        <xsl:with-param name="dm" select="f:parse-normal(current-group()[1]/@normal)" />
        <xsl:with-param
          name="record-id" select="$record-id" />
      </xsl:call-template>
    </xsl:for-each-group>
  </xsl:template>

  <!-- pro Entstehungsdatum: Sending-Entitaet mit Time-Span fuer Entstehungsdatum verknuepfen -->
  <xsl:template
    name="cer:link-timespan">
    <xsl:param name="dm" as="map(*)" />
    <xsl:param name="record-id" as="xs:string" />
    <xsl:value-of
      select="' ;&#10;    cer:P6_has_time-span ' || f:ts-iri($dm, $record-id)" />
  </xsl:template>


  <!-- (2) -->
  <!-- ==================================================================
       Deduplizierung: nur innerhalb eines Records (c-Elements). Ueber
       Records hinweg NICHT mehr zusammenfassen, da dasselbe Datum in
       verschiedenen Briefen unterschiedlich formuliert sein kann und
       das rdfs:label den jeweiligen unitdate-Text traegt.
       ================================================================== -->

  <xsl:template
    name="cer:emit-all-timespans">
    <xsl:param name="unitdates" as="element(e:unitdate)*" />
    <xsl:param name="record-id"
      as="xs:string" />
    <xsl:for-each-group
      select="$unitdates[f:parse-normal(@normal) instance of map(*)]"
      group-by="f:parse-normal(@normal)?key">
      <xsl:call-template name="cer:emit-timespan">
        <xsl:with-param name="dm" select="f:parse-normal(current-group()[1]/@normal)" />
        <xsl:with-param
          name="expressed" select="string(current-group()[1])" />
        <xsl:with-param name="record-id"
          select="$record-id" />
      </xsl:call-template>
    </xsl:for-each-group>
  </xsl:template>

  <!-- einmal pro distinktem Datumswert innerhalb eines Records -->
  <xsl:template
    name="cer:emit-timespan">
    <xsl:param name="dm" as="map(*)" />
    <xsl:param name="expressed" as="xs:string" />
    <xsl:param
      name="record-id" as="xs:string" />

    <xsl:variable name="ts" as="xs:string"
      select="f:ts-iri($dm, $record-id)" />
    <xsl:variable name="ds" as="xs:string"
      select="f:date-iri($dm?begin,'start')" />
    <xsl:variable name="de" as="xs:string"
      select="f:date-iri($dm?end,  'end')" />

    <xsl:value-of
      select="$ts || ' a cer:18_Time-Span ;&#10;'" />
    <xsl:value-of
      select="'    rdfs:label ' || f:lit(normalize-space($expressed)) || ' ;&#10;'" />
    <!-- CER-konforme Struktur. Schliesst das Time-Span-Subjekt ab
         (P82a/P82b unten sind auskommentiert). -->
    <xsl:value-of
      select="'    cer:P19_had_duration ' || $ds || ' , ' || $de || ' .&#10;&#10;'" />

    <!-- Alternativ: CRM-Vierpunkt-Achse als einfacher abfragbare Ebene -->
    <!-- <xsl:value-of select="'    crm:P82a_begin_of_the_begin &quot;'
                          || f:dt-begin($dm?begin) || '&quot;^^xs:dateTime ;&#10;'"/>
    <xsl:value-of select="'    crm:P82b_end_of_the_end &quot;'
                          || f:dt-end($dm?end) || '&quot;^^xs:dateTime .&#10;'"/> -->

    <xsl:value-of
      select="$ds || ' a cer:26_Start_Date ;&#10;    ' || $date-value-prop
                          || ' &quot;' || $dm?begin || '&quot;^^xs:date .&#10;'" />
    <xsl:value-of
      select="$de || ' a cer:27_End_Date ;&#10;    ' || $date-value-prop
                          || ' &quot;' || $dm?end || '&quot;^^xs:date .&#10;'" />
    <xsl:text>&#10;</xsl:text>
  </xsl:template>


</xsl:stylesheet>