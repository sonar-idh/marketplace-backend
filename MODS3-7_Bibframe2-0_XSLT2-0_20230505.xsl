<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#" 
    xmlns:mods="http://www.loc.gov/mods/v3" 
    xmlns:madsrdf="http://www.loc.gov/mads/rdf/v1#"
    xmlns:bf="http://id.loc.gov/ontologies/bibframe/"
    xmlns:bflc="http://id.loc.gov/ontologies/bflc/" 
    xmlns:identifier="https://id.loc/vocabulary/identifiers/uri"
    xmlns:local="http://www.loc.org/namespace"
    xmlns:xlink="http://www.w3.org/1999/xlink" 
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:http="http://expath.org/ns/http-client"
    version="2.0">
    
    <!--
		1.3	Add languageCrosswalk.xml					                                                  ntra   	05/05/2023 
	  	1.2	Update to match mapping MODS 3.7 -> BIBFRAME                                                  ws		05/05/2023
       
        Version 1.1 2023-05-05 ws
        
        An XSLT 2.0 XSLT stylesheet for converting MODS 3.8 (https://www.loc.gov/standards/mods/) records to BIBFRAME 2.0. 
        The expected input is a MODS record or MODS collection record, and the output is an XML document expressing the data as a set of RDF triples. 
        The XSLT provides an optional entity resolver function, via the EXPath HTTP Client extension library (http://expath.org/modules/http-client/). 
        This extension will need to be installed in order to use the entity resolver. The XSLT may also be run without the HTTP Client extension, 
        in which case entities will receive a programmatically generated URI based on the baseuri parameter.
    
        @param $baseuri - URI for generating unique URIs for entities
        @param $lookup - Use EXPath HTTP Client extension library to resolve authority records. 
                         values: true()/false() 
                         You must have the EXPath HTTP Client extension library extension installed and internet access if this is set to true()
                         
       1.2	Update to match mapping MODS 3.7 -> BIBFRAME                                                        ws   05/05/2023
       
    -->
    
    <xsl:output method="xml" indent="yes" encoding="UTF-8"/>
    
    <xsl:strip-space elements="*"/>
    
    <!-- Base URI for minting RDF URIs -->
    <xsl:param name="baseuri" select="'http://bibframe.example.org/'"/>
    
    <!-- Turn off lookup services by default. To turn them on you will need to install the EXPath extension. and switch param to true()  -->
    <xsl:param name="lookup" select="true()"/>
    
    <!--** HELPER FUNCTIONS local helper functions  ** -->
    <!-- Convert language codes. 
         If @xml:lang or @lang is a two character code, look up iso6392 three character code in conf/languageCrosswalk.xml 
         If @script attribute is present append to iso6392 three character code with a '-'-->
    <xsl:function name="local:langConversion">
        <xsl:param name="langCode"/>
        <!-- Import languageCrosswalk for conversion -->
        <!-- <xsl:variable name="languageMap" select="document('conf/languageCrosswalk.xml')"/> -->
		<xsl:variable name="languageMap" select="document('conf/languageCrosswalk.xml')"/>
        <xsl:choose>
            <!-- Convert two character code to ISO 639-2 three character code used by LOC -->
            <xsl:when test="string-length($langCode) = 2">
                <xsl:choose>
                    <xsl:when test="$languageMap/descendant::*[@xml:lang = $langCode]">
                        <xsl:value-of select="$languageMap/descendant::*[@xml:lang = $langCode]/*[1]"/>
                    </xsl:when>
                    <xsl:when test="$languageMap/descendant::*[@xmllang = $langCode]">
                        <xsl:value-of select="$languageMap/descendant::*[@xmllang = $langCode]/*[1]"/>
                    </xsl:when>
                    <xsl:when test="$languageMap/descendant::*[@iso6391 = $langCode]">
                        <xsl:value-of select="$languageMap/descendant::*[@iso6391 = $langCode]/*[1]"/>                        
                    </xsl:when>
                    <xsl:otherwise>
                        <!-- Trigger exception (Print warning, do not disrupt running code)  -->
                        <xsl:message terminate="no">Language code does not match LOC specifications. Please
                            use an ISO 639-2 the appropriate three character code found here:
                            http://id.loc.gov/vocabulary/languages.html</xsl:message>
                    </xsl:otherwise>
                </xsl:choose>
            </xsl:when>
            <!-- Accept three character code -->
            <xsl:when test="string-length($langCode) = 3">
                <xsl:value-of select="$langCode"/>
            </xsl:when>
            <xsl:otherwise>
                <!-- Trigger exception (Print warning, do not disrupt running code)  -->
                <xsl:message terminate="no">Language code does not match LOC specifications. Please
                    use an ISO 639-2 the appropriate three character code found here:
                    http://id.loc.gov/vocabulary/languages.html</xsl:message>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:function>

    <!-- Build xml:lang attributes, adds @script to language code if present -->
    <xsl:function name="local:buildLangAttribute">
        <xsl:param name="node"/>
        <xsl:variable name="langCode">
            <xsl:choose>
                <xsl:when test="$node/@lang">
                    <xsl:value-of select="$node/@lang"/>
                </xsl:when>
                <xsl:when test="$node/@xml:lang">
                    <xsl:value-of select="$node/@xml:lang"/>
                </xsl:when>
            </xsl:choose>
        </xsl:variable>
        <xsl:variable name="langURI">
            <xsl:variable name="converted" select="local:langConversion($langCode)"/>
            <xsl:choose>
                <xsl:when test="$node/@script">
                    <xsl:value-of select="concat($converted,'-',$node/@script)"/>
                </xsl:when>
                <xsl:otherwise>
                    <xsl:value-of select="$converted"/>
                </xsl:otherwise>
            </xsl:choose>
        </xsl:variable>
        <xsl:if test="$langCode != ''">
            <xsl:attribute name="xml:lang">
                <xsl:value-of select="$langURI"/>
            </xsl:attribute>
        </xsl:if>
    </xsl:function>
    
    <!-- Lookup authority URIs. Requires $lookup = true() AND the EXPath HTTP Client extension library-->
    <xsl:function name="local:authorityLookUp">
        <!-- API endpoint to send request to -->
        <xsl:param name="api"/>
        <!-- Value to send to API -->
        <xsl:param name="value"/>
        <!-- Code to send to API -->
        <xsl:param name="code"/>
        <xsl:if test="$api != ''">
           <xsl:choose>
               <!-- Checks to see if requested lookup contains a link to an LOC authority record -->
               <xsl:when test="contains($api, '//id.loc.gov/') and ends-with($api, '.rdf')">
                   <xsl:variable name="record" select="document($api)"/>
                   <xsl:variable name="uri">
                       <xsl:choose>
                           <xsl:when test="$value != ''">
                               <xsl:if test="$record/descendant-or-self::*:Authority[*:authoritativeLabel[lower-case(.) = lower-case($value)]]">
                                   <xsl:value-of select="$record/descendant-or-self::*:Authority[*:authoritativeLabel[lower-case(.) = lower-case($value)]][1]/@rdf:about"/>
                               </xsl:if> 
                           </xsl:when>
                           <xsl:when test="$code != ''">
                               <xsl:if test="$record/descendant-or-self::*:Authority[@rdf:about = $code]">
                                   <xsl:value-of select="$record/descendant-or-self::*:Authority[@rdf:about = $code][1]"/>
                               </xsl:if>         
                           </xsl:when>
                       </xsl:choose>
                   </xsl:variable>
                   <xsl:if test="$uri != ''"><xsl:value-of select="$uri"/></xsl:if>
               </xsl:when>
               <!-- Sends http request to LOC entity resolver service  -->
               <xsl:when test="$lookup = true()">
                   <xsl:variable name="runRequest" use-when="function-available('http:send-request')">
                       <xsl:variable name="request" as="element(http:request)">
                           <http:request href='{concat($api,encode-for-uri($value))}' method='get'/>
                       </xsl:variable>
                       <xsl:variable name="result" select="http:send-request($request)[1]"/>
                       <xsl:if test="$result[@status='200'] and $result//*:header[@name='x-uri']">
                           <xsl:value-of select="string($result//*:header[@name='x-uri']/@value)"/>
                       </xsl:if>
                   </xsl:variable>
                   <xsl:if test="$runRequest != ''" use-when="function-available('http:send-request')">
                       <xsl:value-of select="$runRequest"/>
                   </xsl:if>
               </xsl:when>
           </xsl:choose>
        </xsl:if>
    </xsl:function>
    
    <!-- 1.2 Unique Record URI used to link instances and works -->
    <xsl:function name="local:recordURI">
        <xsl:param name="node"/>
        <xsl:variable name="modsRoot" select="$node/ancestor-or-self::mods:mods[1]"/>
        <xsl:choose>
            <xsl:when test="$modsRoot/descendant::mods:recordInfo/mods:recordIdentifier">
                <xsl:value-of select="$modsRoot/descendant::mods:recordInfo/mods:recordIdentifier[1]/text()"/>
            </xsl:when>
            <xsl:when test="$modsRoot/descendant::mods:identifier">
                <xsl:value-of select="$modsRoot/descendant::mods:identifier[1]/text()"/>
            </xsl:when>
            <xsl:otherwise>
                <xsl:value-of select="generate-id($modsRoot)"/>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:function>
    
    <!-- Mint subject URI  -->
    <xsl:function name="local:rdfAbout">
        <xsl:param name="node"/>
        <xsl:param name="type"/>
        <xsl:variable name="recordID" select="local:recordURI($node)"/>
        <xsl:variable name="URI">
            <xsl:choose>
                <xsl:when test="$node/@valueURI"><xsl:value-of select="$node/@valueURI"/></xsl:when>
                <xsl:when test="$type"><xsl:value-of select="concat($baseuri, $recordID, '/', $type)"/></xsl:when>
            </xsl:choose>    
        </xsl:variable>
        <xsl:if test="$URI != ''">
            <xsl:attribute name="rdf:about"><xsl:value-of select="$URI"/></xsl:attribute>
        </xsl:if>
    </xsl:function>
    
    <!-- Mint object URI  -->
    <xsl:function name="local:rdfResource">
        <xsl:param name="node"/>
        <xsl:param name="type"/>
        <xsl:variable name="recordID" select="local:recordURI($node)"/>
        <xsl:attribute name="rdf:resource">
            <xsl:choose>
                <xsl:when test="$type"><xsl:value-of select="concat($baseuri, $recordID, '/', $type)"/></xsl:when>
                <xsl:otherwise>
                    <xsl:value-of select="concat($baseuri, $recordID)"/>
                </xsl:otherwise>
            </xsl:choose>
        </xsl:attribute>
    </xsl:function>
    
    <!-- Chop specified punctuation from end of string -->
    <xsl:function name="local:chopPunctuation">
        <xsl:param name="string"/>
        <xsl:param name="punctuation"/>
        <xsl:if test="ends-with(normalize-space($string),$punctuation)">
            <xsl:value-of select="replace($string,concat('[',$punctuation,']+$'),'')"/>
        </xsl:if>
    </xsl:function>
    
    <!-- ** END HELPER FUNCTIONS ** -->

    <!-- ** Global Variable **  -->
    <xsl:variable name="vCurrentVersion">v1.3</xsl:variable>
    
    <!-- namespace URIs -->
    <xsl:variable name="xs">http://www.w3.org/2001/XMLSchema#</xsl:variable>
    <!-- id.loc.gov vocabulary stems -->
    <xsl:variable name="descriptionConventions">http://id.loc.gov/vocabulary/descriptionConventions/</xsl:variable>
    <xsl:variable name="languages">http://id.loc.gov/vocabulary/languages/</xsl:variable>
    <xsl:variable name="relators">http://id.loc.gov/vocabulary/relators/</xsl:variable>
    
    <!-- dataTypes -->
    <xsl:variable name="dataTypeAnyURI">http://www.w3.org/2001/XMLSchema#anyURI</xsl:variable>
    <xsl:variable name="dataTypeDate">http://www.w3.org/2001/XMLSchema</xsl:variable>
    <!-- genre relators codes -->
    <xsl:variable name="realtorsDoc" select="document('https://id.loc.gov/vocabulary/relators.rdf')"/>
    
    <!-- Root template -->
    <xsl:template match="/">
        <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
            xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"
            xmlns:bf="http://id.loc.gov/ontologies/bibframe/"
            xmlns:bflc="http://id.loc.gov/ontologies/bflc/"
            xmlns:madsrdf="http://www.loc.gov/mads/rdf/v1#">
            <xsl:apply-templates/>
        </rdf:RDF>
    </xsl:template>

    <!-- mods collection -->
    <xsl:template match="mods:modsCollection">
        <xsl:apply-templates/>
    </xsl:template>

    <!-- mods record -->
    <xsl:template match="mods:mods">
            <bf:Work>
                <xsl:sequence select="local:rdfAbout(.,'#Work')"/>
                <xsl:call-template name="adminMetadata"/>
                <!-- Work label -->
                <xsl:choose>
                    <xsl:when test="mods:titleInfo[@type='uniform']">
                        <xsl:apply-templates select="mods:titleInfo[@type='uniform']" mode="rdfsLabel"/>
                    </xsl:when>
                    <xsl:when test="mods:titleInfo[@usage='primary']">
                        <xsl:apply-templates select="mods:titleInfo[@usage='primary']" mode="rdfsLabel"/>
                    </xsl:when>
                    <xsl:otherwise>
                        <xsl:apply-templates select="mods:titleInfo[1]" mode="rdfsLabel"/>
                    </xsl:otherwise>
                </xsl:choose>
                <!-- Call all MODS elements for Work -->
                <xsl:apply-templates mode="Work"/>
                <bf:hasInstance>
                    <xsl:sequence select="local:rdfResource(.,'#Instance')"/>
                </bf:hasInstance>
            </bf:Work>
            <!-- Build Instance  -->
            <bf:Instance>
                <xsl:sequence select="local:rdfAbout(.,'#Instance')"/>
                <bf:instanceOf>
                    <xsl:sequence select="local:rdfResource(.,'#Work')"/>
                </bf:instanceOf>
                <!-- Instance Label -->
                <xsl:choose>
                    <xsl:when test="mods:titleInfo[@type='uniform']">
                        <xsl:apply-templates select="mods:titleInfo[@type='uniform']" mode="rdfsLabel"/>
                    </xsl:when>
                    <xsl:when test="mods:titleInfo[@usage='primary']">
                        <xsl:apply-templates select="mods:titleInfo[@usage='primary']" mode="rdfsLabel"/>
                    </xsl:when>
                    <xsl:otherwise>
                        <xsl:apply-templates select="mods:titleInfo[1]" mode="rdfsLabel"/>
                    </xsl:otherwise>
                </xsl:choose>
                <xsl:apply-templates mode="Instance"/>
            </bf:Instance>
            <!-- Other works -->
        <!-- 1.2 -->
            <xsl:apply-templates select="mods:relatedItem[@type='reviewOf']" mode="Work"/>
    </xsl:template>
    
    <!-- ** Title templates ** -->
    <xsl:template match="mods:titleInfo" mode="rdfsLabel">
        <!-- _:inst a bf:Instance ; rdfs:label ""concatenated titleInfo value"" ; bf:title [ a bf:Title ; rdfs:label ""concatenated titleInfo value"" ] .  
             _:w a bf:Work ;  rdfs:label ""concatenated titleInfo value"" ; bf:title [ a bf:Title ; rdfs:label ""concatenated titleInfo value"" ] .  Retain order and supply ISBD punctuation. 
        -->
        <xsl:call-template name="rdfsLabel"/>
    </xsl:template>
    
    <!-- 1.2 -->
    <xsl:template match="mods:titleInfo" mode="Work">
        <!-- Used to construct name-title string for lookups when uniform title valueURI not present, or to select which Agent to use in description of new Work. -->
        <xsl:choose>
            <xsl:when test="@type = 'alternative'">
                <xsl:if test="@displayLabel = 'key' or @otherType = 'keyTitle'">
                    <!-- titleInfo@type="alternative"@displayLabel="key"	_:w a bf:Work ; bf:title [a bf:Title , bf:KeyTitle ; bf:mainTitle “title value” ] ."
                         titleInfo@type="alternative"@otherType="keyTitle"  _:w bf:Work ; bf:title [a bf:Title , bf:KeyTitle ;bf:mainTitle “title value” ] ."
                    -->
                    <!-- 1.2 -->
                    <bf:title>
                        <bf:Title>
                            <xsl:if test="@valueURI"><xsl:sequence select="local:rdfAbout(.,())"/></xsl:if>
                            <xsl:call-template name="rdfsLabel"/>
                            <xsl:apply-templates/>
                        </bf:Title>
                        <bf:KeyTitle>
                            <xsl:if test="@valueURI"><xsl:sequence select="local:rdfAbout(.,())"/></xsl:if>
                            <xsl:call-template name="rdfsLabel"/>
                            <xsl:apply-templates/>
                        </bf:KeyTitle>
                    </bf:title>
                </xsl:if>
            </xsl:when>
            <!-- Suppress abbreviated, alternative, translated in Work or mods:title/@transliteration, express in Instance-->
            <xsl:when test="@usage='primary' and not(../mods:titleInfo[not(@type) or @type='uniform'])">
                <bf:title>
                    <bf:Title>
                        <xsl:if test="@valueURI"><xsl:sequence select="local:rdfAbout(.,())"/></xsl:if>
                        <xsl:call-template name="rdfsLabel"/>
                        <xsl:apply-templates/>
                    </bf:Title>
                </bf:title>
            </xsl:when>
            <xsl:when test="@type = 'abbreviated' or @type = 'alternative' or @type = 'translated' or @transliteration or mods:title[@transliteration]"/>
            <xsl:otherwise>
                <!-- not(@type) or @type='uniform' or any other varient -->
                <!-- titleInfo _:w a bf:Work ; rdfs:label "concatenated titleInfo value" ; bf:title [ a bf:Title ;  rdfs:label "concatenated titleInfo value" ; bflc:titleSortKey "(nonSort removed) title value" ; bf:mainTitle “title value”] .  
                -->
                <bf:title>
                    <bf:Title>
                        <xsl:if test="@valueURI"><xsl:sequence select="local:rdfAbout(.,())"/></xsl:if>
                        <xsl:call-template name="rdfsLabel"/>
                        <xsl:apply-templates/>
                    </bf:Title>
                </bf:title>
            </xsl:otherwise>    
        </xsl:choose>
    </xsl:template>
    <xsl:template match="mods:titleInfo" mode="Instance">
        <!-- _:inst a bf:Instance ; bf:title [ a bf:Title , bf: VariantTitle ; mainTitle “title value” ; bf:variantType “displayLabel value“ ] . -->
       <xsl:choose>
           <xsl:when test="@type = 'abbreviated'">
                <!-- titleInfo@type="abbreviated -  "_:inst a bf:Instance ; bf:title [a bf:Title , bf:AbbreviatedTitle ; bf:mainTitle “title value” ] ."-->
                <bf:title>
                    <bf:AbbreviatedTitle>
                        <xsl:call-template name="rdfsLabel"/>
                        <xsl:apply-templates/>
                    </bf:AbbreviatedTitle>
                </bf:title>
           </xsl:when>
           <xsl:when test="@type = 'alternative' or @type = 'translated' or @transliteration or mods:title[@transliteration]">
                <!-- titleInfo@type="alternative - _:inst a bf:Instance ; bf:title [ a bf:Title , bf:VariantTitle ; bf:mainTitle 'title value'  ] -->
                    <bf:title>
                        <bf:VariantTitle>
                            <xsl:call-template name="rdfsLabel"/>
                            <xsl:apply-templates/>
                            <xsl:if test="@displayLabel and @displayLabel != 'key'">
                                <bf:variantType><xsl:value-of select="@displayLabel"/></bf:variantType>
                            </xsl:if>
                            <xsl:choose>
                                <xsl:when test="@type = 'translated'">
                                    <!-- titleInfo@type="translated" - _:inst a bf:Instance ; bf:title [ a bf:Title , bf:VariantTitle ; bf:mainTitle 'title value' ; bf:variantType 'translated' ] -->
                                    <bf:variantType>translated</bf:variantType>
                                </xsl:when>
                                <xsl:when test="@transliteration or mods:title[@transliteration]">
                                    <!-- titleInfo@type="translated" - _:inst a bf:Instance ; bf:title [ a bf:Title , bf:VariantTitle ; bf:mainTitle 'title value' ; bf:variantType 'translated' ]-->
                                    <bf:variantType>transliteration</bf:variantType>
                                </xsl:when>
                            </xsl:choose>
                        </bf:VariantTitle>
                    </bf:title>                   
           </xsl:when>
           <xsl:when test="not(@type)">
                <bf:title>
                    <bf:Title>
                        <xsl:call-template name="rdfsLabel"/>
                        <xsl:apply-templates/>
                    </bf:Title>
                    <!-- 1.2 -->
                    <xsl:if test="@displayLabel">
                        <bf:VariantTitle>
                            <xsl:call-template name="rdfsLabel"/>
                            <xsl:apply-templates/>
                            <bf:variantType><xsl:value-of select="@displayLabel"/></bf:variantType>
                        </bf:VariantTitle>    
                    </xsl:if>               
                </bf:title>
            </xsl:when> 
       </xsl:choose>
    </xsl:template>
    <xsl:template match="mods:title">
        <bf:mainTitle>
            <xsl:sequence select="local:buildLangAttribute(.)"/>            
            <xsl:if test="../mods:nonSort">
                <xsl:value-of select="../mods:nonSort"/><xsl:if test="not(ends-with(../mods:nonSort,' '))"><xsl:text> </xsl:text></xsl:if>    
            </xsl:if>
            <xsl:value-of select="."/>
        </bf:mainTitle>
    </xsl:template>
    <xsl:template match="mods:subTitle">
        <!-- titleInfo/subTitle   _bf:title [ a bf:Title ; subTitle "value" ] .-->
        <bf:subTitle>
            <xsl:sequence select="local:buildLangAttribute(.)"/>
            <xsl:value-of select="."/>
        </bf:subTitle>
    </xsl:template>
    <xsl:template match="mods:partNumber">
        <!-- titleInfo/partNumber bf:title [ a bf:Title ; partNumber "value" ] .-->
        <bf:partNumber>
            <xsl:sequence select="local:buildLangAttribute(.)"/>
            <xsl:value-of select="."/>
        </bf:partNumber>
    </xsl:template>
    <xsl:template match="mods:partName">
        <!-- titleInfo/partName  bf:title [ a bf:Title ; partName "value" ] . -->
        <bf:partName>
            <xsl:sequence select="local:buildLangAttribute(.)"/>
            <xsl:value-of select="."/>
        </bf:partName>
    </xsl:template>
    <xsl:template match="mods:nonSort">
        <!-- titleInfo/nonSort  ## bf:title [ a bf:Title ; bflc:titleSortKey "(nonSort removed) title value" ] .-->
        <bflc:titleSortKey><xsl:value-of select="string-join(parent::mods:titleInfo/child::*[not(self::mods:nonSort)],' ')"/></bflc:titleSortKey>
    </xsl:template>

    <!-- ** Name templates ** -->
    <xsl:template match="mods:name" mode="Work">
        <xsl:variable name="roleClass">
            <xsl:choose>
                <xsl:when test="descendant::mods:roleTerm[@type='code']">
                    <xsl:variable name="roleCode" select="concat('http://id.loc.gov/vocabulary/relators/',descendant::mods:roleTerm[@type='code'][1])"/>
                    <xsl:choose>
                        <xsl:when test="$realtorsDoc/descendant::madsrdf:Authority[@rdf:about = $roleCode]">
                            <xsl:variable name="relatorURI" select="replace($realtorsDoc/descendant::madsrdf:Authority[@rdf:about = $roleCode]/@rdf:about,'http:','https:')"/>
                            <xsl:variable name="doc" select="document(xs:anyURI(concat($relatorURI,'.rdf')))"/>
                            <xsl:choose>
                                <xsl:when test="$doc/descendant::madsrdf:isMemberOfMADSCollection[@rdf:resource = 'http://id.loc.gov/vocabulary/relators/collection_BIBFRAMEWork']">Work</xsl:when>
                                <xsl:when test="$doc/descendant::madsrdf:isMemberOfMADSCollection[@rdf:resource = 'http://id.loc.gov/vocabulary/relators/collection_RDAItem']">Instance</xsl:when>
                                <xsl:otherwise>Work</xsl:otherwise>
                            </xsl:choose>
                        </xsl:when>
                        <xsl:otherwise>Work</xsl:otherwise>
                    </xsl:choose>
                </xsl:when>
                <xsl:otherwise>Work</xsl:otherwise>
            </xsl:choose>            
        </xsl:variable>
        <xsl:choose>
            <xsl:when test="$roleClass = 'Instance'"/>
            <xsl:otherwise><xsl:call-template name="name"/></xsl:otherwise>
        </xsl:choose>
    </xsl:template>
    <xsl:template match="mods:name" mode="Instance">
        <xsl:variable name="roleClass">
            <xsl:choose>
                <xsl:when test="descendant::mods:roleTerm[@type='code']">
                    <xsl:variable name="roleCode" select="concat('http://id.loc.gov/vocabulary/relators/',descendant::mods:roleTerm[@type='code'][1])"/>
                    <xsl:choose>
                        <xsl:when test="$realtorsDoc/descendant::madsrdf:Authority[@rdf:about = $roleCode]">
                            <xsl:variable name="relatorURI" select="replace($realtorsDoc/descendant::madsrdf:Authority[@rdf:about = $roleCode]/@rdf:about,'http:','https:')"/>
                            <xsl:variable name="doc" select="document(xs:anyURI(concat($relatorURI,'.rdf')))"/>
                            <xsl:choose>
                                <xsl:when test="$doc/descendant::madsrdf:isMemberOfMADSCollection[@rdf:resource = 'http://id.loc.gov/vocabulary/relators/collection_BIBFRAMEWork']">Work</xsl:when>
                                <xsl:when test="$doc/descendant::madsrdf:isMemberOfMADSCollection[@rdf:resource = 'http://id.loc.gov/vocabulary/relators/collection_RDAItem']">Instance</xsl:when>
                                <xsl:otherwise>Work</xsl:otherwise>
                            </xsl:choose>
                        </xsl:when>
                        <xsl:otherwise>Work</xsl:otherwise>
                    </xsl:choose>
                </xsl:when>
                <xsl:otherwise>Work</xsl:otherwise>
            </xsl:choose>            
        </xsl:variable>
        <xsl:choose>
            <xsl:when test="$roleClass = 'Instance'"><xsl:call-template name="name"/></xsl:when>
            <xsl:otherwise/>
        </xsl:choose>
    </xsl:template>
    <!-- Named template for tei:name  to be used by Instance and Work -->
    <xsl:template name="name">
        <bf:contribution>
            <bf:Contribution>
                <xsl:if test="@usage = 'primary'">
                    <rdf:type rdf:resource="http://id.loc.gov/ontologies/bflc/PrimaryContribution"/>
                </xsl:if>
                <!-- name/namePart - ## bf:contribution [a bf:Contribution ; bf:agent [a bf:Agent ; rdfs:label "value"]. Concatenate nameParts: Retain order-->
                <xsl:variable name="label">
                    <xsl:for-each select="mods:namePart">
                        <xsl:value-of select="."/>
                        <xsl:choose>
                            <xsl:when test="position() = last()"/>
                            <xsl:when test="matches(.,'^.*[\.:,]$') or matches(.,'^.*[\.:,]\s+$')"><xsl:text> </xsl:text></xsl:when>
                            <xsl:otherwise>
                                <xsl:choose>
                                    <xsl:when test="following-sibling::mods:namePart[@type='date']"><xsl:text>, </xsl:text></xsl:when>
                                    <xsl:otherwise><xsl:text> </xsl:text></xsl:otherwise>
                                </xsl:choose>
                            </xsl:otherwise>
                        </xsl:choose>
                    </xsl:for-each>
                </xsl:variable>
                <xsl:variable name="searchString">
                    <xsl:choose>
                        <xsl:when test="ends-with($label,'.') or ends-with($label,',')">
                            <xsl:value-of select="substring($label,1, (string-length($label)-1))"/>
                        </xsl:when>
                        <xsl:otherwise>
                            <xsl:value-of select="normalize-space($label)"/>
                        </xsl:otherwise>
                    </xsl:choose>
                </xsl:variable>
                <bf:agent>
                    <bf:Agent>
                        <!-- name@valueURI -  bf:contribution [a bf:Contribution ; bf:agent <URI>]  -->
                        <xsl:variable name="authorityURI" select="local:authorityLookUp('http://id.loc.gov/authorities/names/label/',$searchString,'')"/>
                        <xsl:choose>
                            <xsl:when test="$authorityURI != ''">
                                <xsl:attribute name="rdf:about" select="$authorityURI"/>
                            </xsl:when>
                            <xsl:otherwise><xsl:sequence select="local:rdfAbout(., concat('#Agent-', count(preceding::*) + 1))"/></xsl:otherwise>
                        </xsl:choose>
                        <xsl:if test="@type">
                            <rdf:type>
                                <!-- name@type="conference" - bf:contribution [a bf:Contribution ; bf:agent [a bf:Meeting]  -->
                                <!-- name@type="corporate" - bf:contribution [a bf:Contribution ; bf:agent [a bf:Organization] .  -->
                                <!-- name@type="family" -  bf:contribution [a bf:Contribution ; bf:agent [a bf:Family] .  -->
                                <!-- name@type="personal" -bf:contribution [a bf:Contribution ; bf:agent [a bf:Person]  -->
                                <xsl:attribute name="rdf:resource">
                                    <xsl:choose>
                                        <xsl:when test="@type = 'conference'">http://id.loc.gov/ontologies/bibframe/Meeting</xsl:when>
                                        <xsl:when test="@type = 'corporate'">http://id.loc.gov/ontologies/bibframe/Organization</xsl:when>
                                        <xsl:when test="@type = 'family'">http://id.loc.gov/ontologies/bibframe/Family</xsl:when>
                                        <xsl:when test="@type = 'personal'">http://id.loc.gov/ontologies/bibframe/Person</xsl:when>
                                    </xsl:choose>
                                </xsl:attribute>
                            </rdf:type>
                        </xsl:if>
                        <xsl:call-template name="rdfsLabel">
                            <xsl:with-param name="label" select="$label"/>
                        </xsl:call-template> 
                        <!-- @authority - bf:contribution [a bf:Contribution ; bf:agent [a bf:Agent ; bf:source [a bf:Source ; bf:code "value"] ] ] . -->
                        <!-- name@authorityURI -  bf:contribution [a bf:Contribution ; bf:agent [a bf:Agent ; bf:source <URI>] . -->
                        <xsl:call-template name="bfSource"/>
                        <!-- mods:nameIdentifier -->
                        <xsl:apply-templates select="mods:nameIdentifier"/>
                        <!-- Name description -->
                        <xsl:apply-templates select="mods:description"/>
                    </bf:Agent>
                </bf:agent>
                <!-- Name role -->
                <xsl:apply-templates select="mods:role"/>
            </bf:Contribution>
        </bf:contribution>
    </xsl:template>

    <!-- mods:name/mods:nameIdentifier -->
    <xsl:template match="mods:nameIdentifier">
        <bf:identifiedBy>
            <bf:Identifier>
                <!-- name/nameIdentifier  - bf:contribution [ a bf:Contribution ; bf:agent [ a bf:Agent ; bf:identifiedBy [ a bf:Identifier ; rdf:value "value of nameIdentifier" ] ] ] -->
                <xsl:if test=". != ''">
                    <rdf:value>
                        <xsl:sequence select="local:buildLangAttribute(.)"/>
                        <xsl:value-of select="."/>
                    </rdf:value>
                </xsl:if>
                <!-- name/nameIdentifier@invalid="yes"  bf:contribution [ a bf:Contribution ; bf:agent [ a bf:Agent ; bf:identifiedBy [ a bf:Identifier ; bf:status [ a bf:Status ; rdfs:label "invalid" ] ] ] ]-->
                <xsl:if test="@invalid = 'yes'">
                    <bf:status>
                        <bf:Status>
                            <rdfs:label>invalid</rdfs:label>
                        </bf:Status>
                    </bf:status>
                </xsl:if>
                <!-- name/nameIdentifier@type - [ a bf:Contribution ; bf:agent [ a bf:Agent ; bf:identifiedBy [ a bf:Identifier ; bf:source [ a bf:Source ; bf:code "value" ] ] ] ]-->
                <xsl:if test="@type or @typeURI">
                    <bf:source>
                        <bf:Source>
                            <xsl:if test="@typeURI">
                                <xsl:attribute name="rdf:about" select="@typeURI"/>
                            </xsl:if>
                            <xsl:if test="@type">
                                <bf:code>
                                    <xsl:value-of select="@type"/>
                                </bf:code>                                
                            </xsl:if>
                        </bf:Source>
                    </bf:source>
                </xsl:if>
            </bf:Identifier>
        </bf:identifiedBy>
    </xsl:template>
    <!-- mods:name/mods:role -->
    <xsl:template match="mods:role">
        <bf:role>
            <bf:Role>
                <xsl:choose>
                    <xsl:when test="mods:roleTerm[@valueURI]">
                        <!-- name/role/roleTerm@valueURI - bf:contributor [a bf:Contribution ; bf:role <URI> ] -->
                        <xsl:attribute name="rdf:about" select="mods:roleTerm/@valueURI"/>
                    </xsl:when>
                    <xsl:when test="mods:roleTerm[@type = 'code']">
                        <xsl:variable name="relatorCode" select="concat($relators,mods:roleTerm[@type = 'code'])"/>
                        <xsl:if test="$realtorsDoc/descendant::madsrdf:Authority[@rdf:about = $relatorCode]">
                            <xsl:attribute name="rdf:about" select="$relatorCode"/>    
                        </xsl:if>
                    </xsl:when>
                </xsl:choose>
                <xsl:apply-templates/>
            </bf:Role>
        </bf:role>
    </xsl:template>
    <xsl:template match="mods:roleTerm">
        <!-- name/role/roleTerm@lang  - These are ISO 639-2 three character codes, some of which have two-character code equivalents to go into xml:lang. Conversion needed if retained. Conversion available on http://id.loc.gov/vocabulary/iso639-2.html-->
        <!-- name/role/roleTerm@xml:lang  - Add xml:lang to appropriate property -->
        <xsl:choose>
            <xsl:when test="@type = 'text'">
                <!-- name/role/roleTerm@type="text" - bf:contributor [a bf:Contribution ; bf:role [a bf:Role ; rdfs:label "value"] . -->
                <xsl:call-template name="rdfsLabel"/>  
                <xsl:call-template name="bfSource"/>
            </xsl:when>
            <xsl:when test="@type = 'code'">
                <xsl:variable name="relatorCode" select="concat($relators,.)"/>
                <!-- name/role/roleTerm@type="code" - bf:contributor [a bf:Contribution ; bf:role [a bf:Role ; bf:code [rdfs:value "value"] ]-->
                    <xsl:choose>
                        <xsl:when test="$realtorsDoc/descendant::madsrdf:Authority[@rdf:about = $relatorCode]"/>
                        <xsl:otherwise>
                            <bf:code>
                                <xsl:value-of select="."/>
                            </bf:code>
                        </xsl:otherwise>
                    </xsl:choose>
                <xsl:call-template name="bfSource"/>
            </xsl:when>
        </xsl:choose>
    </xsl:template>
    <!-- Name description -->
    <xsl:template match="mods:description">
        <!-- name/description - bf:contribution [a bf:Contribution ; bf:agent [a bf:Agent ; bf:note [a bf:Note ; bf:noteType "description" ; rdfs:value " " ]]] -->
        <!-- name/description@lang, name/description@lang:xml -->
        <bf:note>
            <bf:Note>
                <bf:noteType>description</bf:noteType>
                <rdfs:value>
                    <xsl:sequence select="local:buildLangAttribute(.)"/>
                    <xsl:value-of select="."/>
                </rdfs:value>
            </bf:Note>
        </bf:note>
    </xsl:template>

    <!-- **  typeOfResource ** -->
    <xsl:template match="mods:typeOfResource" mode="Work">
        <!-- typeOfResource [container] - [container element] -->
        <!--typeOfResource@xml:lang -->
        <xsl:choose>
            <xsl:when test="@valueURI">
                <!-- typeOfResource@valueURI -	_w a <URI> -->
                <rdf:type rdf:resource="{@valueURI}">
                    <xsl:sequence select="local:buildLangAttribute(.)"/>
                    <xsl:if test="@authority or @authorityURI">
                        <xsl:call-template name="bfSource"/>
                    </xsl:if>
                </rdf:type>
            </xsl:when>
            <xsl:when test=". = 'three dimensional object'">
                <!-- typeOfResource="three dimensional object" _:w a bf:Object . -->
                <rdf:type rdf:resource="http://id.loc.gov/ontologies/bibframe/Object">
                    <xsl:sequence select="local:buildLangAttribute(.)"/>
                </rdf:type>
            </xsl:when>
            <xsl:when test=". = 'text'">
                <!-- typeOfResource="text" - _:w a bf:Text . -->
                <rdf:type rdf:resource="http://id.loc.gov/ontologies/bibframe/Text">
                    <xsl:sequence select="local:buildLangAttribute(.)"/>
                </rdf:type>
            </xsl:when>
            <xsl:when test=". = 'still image'">
                <!-- typeOfResource="still image" - _:w a bf:StillImage . -->
                <rdf:type rdf:resource="http://id.loc.gov/ontologies/bibframe/StillImage">
                    <xsl:sequence select="local:buildLangAttribute(.)"/>
                </rdf:type>
            </xsl:when>
            <xsl:when test=". = ('sound recording - nonmusical','sound recording-nonmusical')">
                <!-- typeOfResource="sound recording - nonmusical" -  _:w a bf:Audio ; rdf:type <http://id.loc.gov/vocabulary/resourceTypes/aun>	
                    Subclassed resourceType from id.loc.gov SKOS/MADS controlled vocabulary.
                -->
                <rdf:type rdf:resource="http://id.loc.gov/ontologies/bibframe/Audio">
                    <xsl:sequence select="local:buildLangAttribute(.)"/>
                </rdf:type>
                <rdf:type rdf:resource="http://id.loc.gov/vocabulary/resourceTypes/aun"/>
            </xsl:when>
            <xsl:when test=". = ('sound recording - musical','sound recording-musical')">
                <!-- typeOfResource="sound recording - musical" - _:w a bf:Audio ; 
                        rdf:type <http://id.loc.gov/vocabulary/resourceTypes/aum	
                        Subclassed resourceType from id.loc.gov SKOS/MADS controlled vocabulary. -->
                <rdf:type rdf:resource="http://id.loc.gov/ontologies/bibframe/Audio">
                    <xsl:sequence select="local:buildLangAttribute(.)"/>
                </rdf:type>
                <rdf:type rdf:resource="http://id.loc.gov/vocabulary/resourceTypes/aum"/>
            </xsl:when>
            <xsl:when test=". = 'sound recording'">
                <!-- typeOfResource="sound recording" - _:w a bf:Audio . -->
                <rdf:type rdf:resource="http://id.loc.gov/ontologies/bibframe/Audio">
                    <xsl:sequence select="local:buildLangAttribute(.)"/>
                </rdf:type>
            </xsl:when>
            <xsl:when test=". = 'software, multimedia'">
                <!-- typeOfResource="software, multimedia" - _:w a bf:Multimedia . -->
                <rdf:type rdf:resource="http://id.loc.gov/ontologies/bibframe/Multimedia">
                    <xsl:sequence select="local:buildLangAttribute(.)"/>
                </rdf:type>
            </xsl:when>
            <xsl:when test=". = 'notated music'">
                <!-- typeOfResource="notated music" - 
                    _:w a bf:NotatedMusic . -->
                <rdf:type rdf:resource="http://id.loc.gov/ontologies/bibframe/NotatedMusic">
                    <xsl:sequence select="local:buildLangAttribute(.)"/>
                </rdf:type>
            </xsl:when>
            <xsl:when test=". = 'mixed material'">
                <!-- typeOfResource="mixed material" - _:w a bf:MixedMaterial . -->
                <rdf:type rdf:resource="http://id.loc.gov/ontologies/bibframe/MixedMaterial">
                    <xsl:sequence select="local:buildLangAttribute(.)"/>
                </rdf:type>
            </xsl:when>
            <xsl:when test=". = 'cartographic'">
                <!-- typeOfResource="cartographic" - _:w a bf:Cartography . -->
                <rdf:type rdf:resource="http://id.loc.gov/ontologies/bibframe/Cartography">
                    <xsl:sequence select="local:buildLangAttribute(.)"/>
                </rdf:type>
            </xsl:when>
            <xsl:when test=". = 'moving image'">
                <!-- typeOfResource="moving image" - _:w a bf:MovingImage . -->
                <rdf:type rdf:resource="http://id.loc.gov/ontologies/bibframe/MovingImage">
                    <xsl:sequence select="local:buildLangAttribute(.)"/>
                </rdf:type>
            </xsl:when>
            <xsl:otherwise>
                <!-- typeOfResource@authority - _w a <URI> ;  bf:source [a bf:Source ; bf:code "value" ] . -->
                <!-- typeOfResource@authorityURI - _w a <URI> ; bf:source <URI> -->
                <rdf:type>
                    <xsl:sequence select="local:buildLangAttribute(.)"/>
                    <xsl:choose>
                        <xsl:when test="starts-with(.,'http')">
                            <xsl:attribute name="rdf:resource" select="."/>
                        </xsl:when>
                        <xsl:otherwise>
                            <xsl:call-template name="rdfsLabel"/>
                        </xsl:otherwise>
                    </xsl:choose>
                    <xsl:call-template name="bfSource"/>
                </rdf:type>
            </xsl:otherwise>
        </xsl:choose>        
    </xsl:template>
    <xsl:template match="mods:typeOfResource" mode="Instance">
        <xsl:choose>
            <xsl:when test="@collection = 'yes'">
                <!-- typeOfResource@collection="yes"  _:inst a bf:Collection .	-->
                <rdf:type rdf:resource="http://id.loc.gov/ontologies/bibframe/Collection">
                    <xsl:sequence select="local:buildLangAttribute(.)"/>
                </rdf:type>
            </xsl:when>
            <xsl:when test="@manuscript">
                <!-- typeOfResource@manuscript - _:inst a bf:Manuscript . -->
                <rdf:type rdf:resource="http://id.loc.gov/ontologies/bibframe/Manuscript">
                    <xsl:sequence select="local:buildLangAttribute(.)"/>
                </rdf:type>
            </xsl:when>
        </xsl:choose>
    </xsl:template>

    <!-- ** genre ** -->
    <xsl:template match="mods:genre" mode="Work">
        <xsl:choose>
            <xsl:when test="@authority = 'rdacontent'">
                <!--  genre@authority="rdacontent"  _:w a bf:Work ; bf:content [a bf:Content ; rdfs:label "value"] . -->
                <bf:content>
                    <bf:Content>
                        <!-- Lookup URI from https://id.loc.gov/vocabulary/contentTypes.rdf-->
                        <xsl:variable name="URI" select="local:authorityLookUp('https://id.loc.gov/vocabulary/contentTypes.rdf',.,())"/>
                        <xsl:if test="$URI"><xsl:attribute name="rdf:about" select="$URI"/></xsl:if>
                        <xsl:call-template name="rdfsLabel"/> 
                        <xsl:call-template name="bfSource">
                            <xsl:with-param name="URI">http://id.loc.gov/vocabulary/genreFormSchemes/rdacontent</xsl:with-param>
                        </xsl:call-template>
                    </bf:Content>
                </bf:content>
            </xsl:when>
            <xsl:otherwise>
                <!-- genre _:w a bf:Work ; bf:genreForm [a bf:GenreForm ; rdfs:label "value']. Use bf:Work -->
                <bf:genreForm>
                    <bf:GenreForm>
                        <xsl:variable name="propertyURI">
                            <xsl:choose>
                                <xsl:when test="@valueURI">
                                    <xsl:value-of select="string(@valueURI)"/>
                                </xsl:when>
                                <xsl:when test="@authorityURI">
                                    <xsl:value-of select="local:authorityLookUp(string(@authorityURI),.,())"/>
                                </xsl:when>
                            </xsl:choose>
                        </xsl:variable>
                        <xsl:if test="$propertyURI != ''">
                            <xsl:attribute name="rdf:about" select="$propertyURI"/>    
                        </xsl:if>        
                        <xsl:call-template name="rdfsLabel"/>  
                        <xsl:if test="$propertyURI = ''">
                            <!-- genre@authority ## bf:genreForm [a bf:GenreForm ; rdfs:label ; bf:source [bf:code "value']] . -->
                            <!-- genre@authorityURI _:w a bf:Work ; bf:genreForm [a bf:GenreForm ; rdfs:label ; bf:source <URI>]. -->
                            <xsl:call-template name="bfSource"/>
                        </xsl:if>
                    </bf:GenreForm>
                </bf:genreForm>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>

    <!-- ** originInfo  ** -->
    <xsl:template match="mods:originInfo" mode="Work">
        <!-- originInfo/dateCreated	_:w a bf:Work ; bf:originDate "value" -->
        <!-- originInfo/dateCaptured   _:w a bf:Work ; bf:capture [a bf:Capture ; bf:date "value"] . -->
        <xsl:apply-templates select="mods:dateCreated"/>
        <xsl:apply-templates select="mods:dateCaptured"/>
    </xsl:template>
    <xsl:template match="mods:originInfo" mode="Instance">
        <!-- 1.2 -->
        <xsl:variable name="provisionActivityStmt">
            <xsl:value-of select="mods:place/mods:placeTerm[not(@type='code')][1]"/>
            <xsl:if test="mods:place[mods:placeTerm[not(@type='code')]] and mods:publisher"><xsl:text>, </xsl:text></xsl:if>
            <xsl:value-of select="mods:publisher"/>
            <xsl:if test="mods:publisher and mods:dateIssued"><xsl:text>; </xsl:text></xsl:if>
            <xsl:if test="mods:dateIssued">
                <xsl:choose>
                    <xsl:when test="mods:dateIssued[@point='start']">
                        <xsl:value-of select="mods:dateIssued[@point='start']"/>
                        <xsl:if test="mods:dateIssued[@point='end']">/<xsl:value-of select="mods:dateIssued[@point='end']"/></xsl:if>
                    </xsl:when>
                    <xsl:otherwise>
                        <xsl:value-of select="mods:dateIssued[1]"/>
                    </xsl:otherwise>
                </xsl:choose>
            </xsl:if>
        </xsl:variable>
        <bf:provisionActivityStatement>
            <xsl:value-of select="$provisionActivityStmt"/>
        </bf:provisionActivityStatement>    
        <!-- originInfo@eventType - ## ; bf:provisionActivity [a bf:ProvisionActivity ] . -->        
        <bf:provisionActivity>
            <bf:ProvisionActivity>
                <xsl:choose>
                    <xsl:when test="@eventType = 'distribution'">
                        <!-- originInfo@eventType="distribution"	## bf:provisionActivity [a bf:Distribution] . -->
                        <rdf:type rdf:resource="http://id.loc.gov/ontologies/bibframe/Distribution"/>
                    </xsl:when>
                    <xsl:when test="@eventType = 'manufacture'">
                        <!-- originInfo@eventType="manufacture"	## bf:provisionActivity [a bf:Manufacture] . -->
                        <rdf:type rdf:resource="http://id.loc.gov/ontologies/bibframe/Manufacture"/>
                    </xsl:when>
                    <xsl:when test="@eventType = 'distribution'">
                        <!-- originInfo@eventType="distribution"	## bf:provisionActivity [a bf:Production] . -->
                        <rdf:type rdf:resource="http://id.loc.gov/ontologies/bibframe/Production"/>
                    </xsl:when>
                    <xsl:when test="@eventType = 'publication'">
                        <!-- originInfo@eventType="publication"	## bf:provisionActivity [a bf:Publication] . -->
                        <rdf:type rdf:resource="http://id.loc.gov/ontologies/bibframe/Publication"/>
                    </xsl:when>
                    <xsl:when test="@eventType = 'production'">
                        <rdf:type rdf:resource="http://id.loc.gov/ontologies/bibframe/Production"/>
                    </xsl:when>              
                </xsl:choose>
                <xsl:if test="mods:dateIssued">
                    <bf:publication><bf:Publication><xsl:apply-templates select="mods:dateIssued"/></bf:Publication></bf:publication>
                </xsl:if>
<!--                <xsl:apply-templates select="mods:dateModified"/>-->
                <xsl:apply-templates select="mods:place"/>
                <xsl:apply-templates select="mods:publisher"/>
            </bf:ProvisionActivity>
        </bf:provisionActivity>  
        <xsl:if test="mods:dateOther">
            <bf:provisionActivity>
                <bf:ProvisionActivity>
                    <!-- originInfo/dateOther	"_:inst a bf:Instance ; bf:provisionActivity [a bf:ProvisionActivity ; bf:date ""value"" ] . - Create a new provision activity" -->
                    <xsl:apply-templates select="mods:dateOther"/>
                </bf:ProvisionActivity>
            </bf:provisionActivity>
        </xsl:if>
        <xsl:apply-templates select="mods:copyrightDate"/>
        <xsl:apply-templates select="mods:frequency"/>
        <xsl:apply-templates select="mods:edition"/>
        <xsl:apply-templates select="mods:issuance"/>
    </xsl:template>
    
    <!-- ** mods:place ** -->
    <xsl:template match="mods:place">
        <!-- originInfo/place [container element] -->
        <!-- originInfo/place/placeTerm	
            _:inst a bf:Instance ; bf:provisionActivity [a bf:ProvisionActivity [or subclass] ; bf:place [a bf:Place] . -->
        <bf:place>
            <xsl:apply-templates/>
        </bf:place>
    </xsl:template>

    <xsl:template match="mods:placeTerm">
        <!-- originInfo/place/placeTerm@lang, originInfo/place/placeTerm@xml:lang, originInfo/place/placeTerm@script -->
        <!-- originInfo/place/placeTerm@valueURI	
            ## bf:place <URI> . -->
        <bf:Place>
            <xsl:choose>
                <xsl:when test="@valueURI">
                    <xsl:attribute name="rdf:about" select="@valueURI"/>
                </xsl:when>
                <xsl:otherwise>
                    <xsl:if test="@type='code'">
                        <xsl:variable name="URI" select="local:authorityLookUp('https://id.loc.gov/vocabulary/countries.rdf',(),.)"/>
                        <xsl:if test="$URI != ''">
                            <xsl:attribute name="rdf:about" select="$URI"/>
                        </xsl:if>
                    </xsl:if>
                </xsl:otherwise>
            </xsl:choose>
            <!-- 1.2  -->
            <xsl:if test="@type != 'code' or not(@type)">
                <xsl:call-template name="rdfsLabel"/>                
            </xsl:if>
            <xsl:if test="@type = 'code'">
                <!-- originInfo/place/placeTerm@type="code" - # bf:place [a bf:Place ; bf:code "value" ]. -->
                <bf:code>
                    <xsl:value-of select="."/>
                </bf:code>
            </xsl:if>
            <!-- 1.2 -->
            <xsl:if test="not(@authority)">
                <xsl:call-template name="bfSource"/>                
            </xsl:if>
        </bf:Place>
    </xsl:template>
    
    <!-- ** publisher **  -->
    <xsl:template match="mods:publisher">
        <!-- originInfo/publisher - bf:agent [a bf:Agent ; rdfs:label "value'] . -->
        <bf:agent>
            <bf:Agent>
                <xsl:call-template name="rdfsLabel"/>
            </bf:Agent>
        </bf:agent>
    </xsl:template>
    
    <!-- ** frequency **  -->
    <xsl:template match="mods:frequency">
        <!-- originInfo/frequency	_:Inst a bf:Instance ; bf:frequency <URI> .
            If frequency@authority="marcfrequency", map term to URI. use URIs from http://id.loc.gov/vocabulary/frequencies.html  -->
        <!--  originInfo/frequency@authority - ## bf:frequency [bf:source ; bf:code "value" ].  -->
        <!-- originInfo/frequency@authorityURI - ## bf:frequency [bf:source <URI> ].  -->
        <!-- originInfo/frequency@valueURI - ## bf:frequency <URI> . -->
        <!-- originInfo/frequency@lang, originInfo/frequency@xml:lang, originInfo/frequency@script -->
        <bf:frequency>
            <bf:Frequency>
                <xsl:choose>
                    <xsl:when test="@authority='marcfrequency'">
                        <xsl:variable name="uri" select="local:authorityLookUp('https://id.loc.gov/vocabulary/frequencies.rdf',text(),())"/>                    
                        <xsl:attribute name="rdf:about" select="$uri"/>
                    </xsl:when>
                    <xsl:otherwise>
                        <xsl:sequence select="local:rdfAbout(.,())"/>
                    </xsl:otherwise>
                </xsl:choose>
                <xsl:if test="not(@valueURI) and not(@authority='marcfrequency')">
                    <xsl:call-template name="rdfsLabel"/>
                    <xsl:call-template name="bfSource"/>
                </xsl:if>    
            </bf:Frequency>
        </bf:frequency>
    </xsl:template>
    
    <!-- ** edition **  -->
    <xsl:template match="mods:edition">
        <!-- originInfo/edition	
            _:Inst a bf:Instance ; bf:editionStatement "value" . -->
        <bf:editionStatement>
            <xsl:sequence select="local:buildLangAttribute(.)"/>
            <xsl:value-of select="."/>
        </bf:editionStatement>
    </xsl:template>

    <!-- ** issuance **  -->
    <xsl:template match="mods:issuance">
        <!-- originInfo/issuance _:Inst a bf:Instance ;  bf:issuance < >.  Use URIs from if.loc.gov where possible. -->
        <bf:issuance>
            <bf:Issuance>
                <xsl:choose>
                    <xsl:when test=". = 'monographic'">
                        <!-- originInfo/issuance="monographic" - ## bf:issuance <http://id.loc.gov/vocabulary/issuance/mono>
                            bf:Monograph is defined as single unit Monograph is not a BIBFRAME class. -->
                        <xsl:attribute name="rdf:about" select="'http://id.loc.gov/vocabulary/issuance/mono'"/>
                    </xsl:when>
                    <xsl:when test=". = 'single unit'">
                        <!-- originInfo/issuance="single unit" - ## bf:issuance  <http://id.loc.gov/vocabulary/issuance/mono> . -->
                        <xsl:attribute name="rdf:about" select="'http://id.loc.gov/vocabulary/issuance/mono'"/>
                    </xsl:when>
                    <xsl:when test=". = 'multipart monograph'">
                        <!-- originInfo/issuance="multipart monograph" - ## bf:issuance  <http://id.loc.gov/vocabulary/issuance/mulm> . -->
                        <xsl:attribute name="rdf:about" select="'http://id.loc.gov/vocabulary/issuance/mulm'"/>
                    </xsl:when>
                    <xsl:when test=". = 'continuing'">
                        <!-- originInfo/issuance="continuing" - ## bf:issuance [a bf:Issuance ; rdfs:Label "continuing" ] .	
                             No MARC equivalent for simply "continuing" - only integrating or serial
                             If known whether continuing resource is serial or integrating, could apply that as well. -->
                        <rdfs:label>continuing</rdfs:label>
                    </xsl:when>
                    <xsl:when test=". = 'serial'">
                        <!-- originInfo/issuance="serial" - ## bf:issuance <http://id.loc.gov/vocabulary/issuance/serl> . -->
                        <xsl:attribute name="rdf:about" select="'http://id.loc.gov/vocabulary/issuance/serl'"/>
                    </xsl:when>
                    <xsl:when test=". = 'integrating resource'">
                        <!-- originInfo/issuance="integrating resource" - ## bf:issuance <http://id.loc.gov/vocabulary/issuance/intg> . -->
                        <xsl:attribute name="rdf:about" select="'http://id.loc.gov/vocabulary/issuance/intg'"/>
                    </xsl:when>
                </xsl:choose>
            </bf:Issuance>
        </bf:issuance>
    </xsl:template>

    <!-- ** mods:language ** -->
    <xsl:template match="mods:language" mode="Work">
        <bf:language>
            <bf:Language>
                <!--  language/languageTerm - _:w a bf:Work ; bf:language <URI>  
                    Convert to URI from appropriate vocabulary ISO 639-2 or ISO 639-1 (if two characters) -->
                <!-- language/languageTerm@type="code" - ## bf:language <URI> .	
                        Convert to URI from appropriate vocabulary ISO 639-2 or ISO 639-1 (if two characters) -->
                <xsl:choose>
                    <xsl:when test="mods:languageTerm[@valueURI]">
                        <xsl:attribute name="rdf:about" select="mods:languageTerm/@valueURI"/>
                    </xsl:when>
                    <xsl:when test="mods:languageTerm[@type='code']">
                        <xsl:variable name="lang">
                            <xsl:value-of select="concat($languages,local:langConversion(local:langConversion(mods:languageTerm[@type='code'])))"/>    
                        </xsl:variable>
                        <xsl:attribute name="rdf:about" select="$lang"/>
                    </xsl:when>
                    <xsl:when test="mods:languageTerm[not(@type)]">
                        <xsl:variable name="lang">
                            <xsl:value-of select="concat($languages,local:langConversion(local:langConversion(mods:languageTerm[not(@type)][1])))"/>    
                        </xsl:variable>
                        <xsl:attribute name="rdf:about" select="$lang"/>
                    </xsl:when>
                </xsl:choose>
                <!-- language@objectPart	_:w a bf:Work ; bf:language [a bf:Language ; bf:part "value" ] . --> 
                <xsl:if test="@objectPart">
                    <bf:part><xsl:value-of select="@objectPart"/></bf:part>                    
                </xsl:if>
                <xsl:apply-templates select="mods:languageTerm"/>
            </bf:Language>
        </bf:language>
    </xsl:template>
    
    <xsl:template match="mods:language" mode="Instance">
        <!-- 
            language/scriptTerm	_:Inst ; bf:Instance ; bf:note [ a bf:Note ; bf:noteType "script" ; rdfs:label "value" ] .
            language/scriptTerm@type="text"	## bf:note [ a bf:Note ; bf:noteType "script" ; rdfs:label "value" ] .
            language/scriptTerm@type="code"	## bf:note [ a bf:Note ; bf:noteType "script" ; bf:code "value" ] .
            language/scriptTerm@authority	## bf:note [a bf:Note ; bf:source [a bf:Source ; bf:code "value" ] .
            language/scriptTerm@authorityURI	## bf:note [a bf:Note ; bf:source [a bf:Source ; bf:code "value" ] .
            language/scriptTerm@valueURI	## bf:note <URI> .
        -->
        <xsl:apply-templates select="mods:scriptTerm" mode="Instance"/>
    </xsl:template>
    
    <xsl:template match="mods:languageTerm">
        <!-- language/languageTerm@type="text" - ## bf:language [a bf:Language ; rdfs:label "value" ]. -->
        <!-- WS-18 add not(@type) to catch languageTerms with no type attribute -->
        <xsl:if test="@type='text' or not(@type)">
            <rdfs:label><xsl:value-of select="."/></rdfs:label>
        </xsl:if>
        <!-- language/languageTerm@authority - ## bf:language [a bf:Language ; bf:source [a bf:source ; bf:code "value" ]].-->
        <!-- language/languageTerm@authorityURI - ## bf:language [a bf:Language ; bf:source <URI> ]. -->
        <xsl:if test="@authority != 'iso639-2b'">
            <xsl:call-template name="bfSource"/>            
        </xsl:if>
    </xsl:template>
    
    <xsl:template match="mods:scriptTerm" mode="Instance">
        <!-- language/scriptTerm - _:Inst a bf:Instance ; bf:notation [ a bf:Script ; rdfs:label "value" ] .-->
        <!-- language/scriptTerm@type="text" - _:Inst a bf:Instance ; bf:notation [ a bf:Script ; rdfs:label "value" ] .-->
        <!-- language/scriptTerm@type="code" - _:Inst a bf:Instance ; bf:notation [ a bf:Script ; bf:code "value" ] . -->
        <!-- language/scriptTerm@authority	## bf:source [ a bf:Source; bf:code "value" ] . -->
        <!-- language/scriptTerm@authorityURI	## bf:source <URI> . -->
        <!-- language/scriptTerm@valueURI	## bf:notation <URI> . -->
        <!-- language/scriptTerm@lang language/scriptTerm@xml:lang language/scriptTerm@script-->
        <!-- WS-19 Update to match mapping mods v3.7   -->
        <bf:note>
            <xsl:choose>
                <xsl:when test="@valueURI != ''">
                    <xsl:attribute name="rdf:about" select="@valueURI"/>
                </xsl:when>
                <xsl:otherwise>
                    <bf:Note>
                        <bf:noteType>script</bf:noteType>
                        <xsl:choose>
                            <xsl:when test="@type='code'">
                                <bf:code><xsl:value-of select="."/></bf:code>
                            </xsl:when>
                            <xsl:otherwise>
                                <xsl:call-template name="rdfsLabel"/>
                            </xsl:otherwise>
                        </xsl:choose>
                        <xsl:call-template name="bfSource"/>
                    </bf:Note>
                </xsl:otherwise>
            </xsl:choose>
        </bf:note>
    </xsl:template>
    
    <!-- ** physicalDescription ** -->
    <xsl:template match="mods:physicalDescription" mode="Work">
        <xsl:apply-templates mode="Work"/>
    </xsl:template>
    <xsl:template match="mods:physicalDescription" mode="Instance">
        <xsl:apply-templates mode="Instance"/>
    </xsl:template>
    
    <!-- ** physicalDescription/form ** -->
    <xsl:template match="mods:form"  mode="Instance">
        <!-- physicalDescription/form - _:Inst a bf:Instance ;  bf:carrier [a bf:Carrier ; rdfs:label "value" ] .		
             If authority is rdamedia map to bf:media, otherwise map to bf:carrier -->
        <xsl:choose>
            <xsl:when test="@authority='rdamedia'">
                <!-- physicalDescription/form@authority="rdamedia" - ## bf:media [a bf:Media ; bf:source <http://id.loc.gov/vocabulary/mediaTypes> ] . -->
                <bf:media>
                    <bf:Media>
                        <xsl:choose>
                            <xsl:when test="@authority='rdamedia'">
                                <!-- physicalDescription/form@authority='rdacarrier' -  ## bf:carrier [a bf:Carrier ; bf:source <http://id.loc.gov/vocabulary/carriers> ] . -->
                                <xsl:variable name="authorityURI" select="local:authorityLookUp('https://id.loc.gov/vocabulary/mediaTypes.rdf',.,())"/>
                                <xsl:choose>
                                    <xsl:when test="$authorityURI != ''">
                                        <xsl:attribute name="rdf:about" select="$authorityURI"/>
                                    </xsl:when>
                                    <xsl:otherwise>
                                        <xsl:sequence select="local:rdfAbout(.,())"/>
                                    </xsl:otherwise>
                                </xsl:choose>
                            </xsl:when>
                            <xsl:otherwise>
                                <xsl:sequence select="local:rdfAbout(.,())"/>
                            </xsl:otherwise>
                        </xsl:choose>
                        <xsl:call-template name="rdfsLabel"/>
                        <xsl:call-template name="bfSource">
                            <xsl:with-param name="URI">http://id.loc.gov/vocabulary/mediaTypes</xsl:with-param>
                        </xsl:call-template>
                    </bf:Media>
                </bf:media>
            </xsl:when>
            <xsl:otherwise>
                <!-- physicalDescription/form@type='carrier' ## bf:carrier [a bf:Carrier ; rdfs:label "value" ] . -->
                <bf:carrier>
                    <bf:Carrier>
                        <xsl:choose>
                            <xsl:when test="@authority='rdacarrier'">
                                <!-- physicalDescription/form@authority='rdacarrier' -  ## bf:carrier [a bf:Carrier ; bf:source <http://id.loc.gov/vocabulary/carriers> ] . -->
                                <xsl:variable name="authorityURI" select="local:authorityLookUp('https://id.loc.gov/vocabulary/carriers.rdf',.,())"/>
                                <xsl:choose>
                                    <xsl:when test="$authorityURI != ''">
                                        <xsl:attribute name="rdf:about" select="$authorityURI"/>
                                    </xsl:when>
                                    <xsl:otherwise>
                                        <xsl:sequence select="local:rdfAbout(.,())"/>
                                    </xsl:otherwise>
                                </xsl:choose>
                            </xsl:when>
                            <xsl:otherwise>
                                <xsl:sequence select="local:rdfAbout(.,())"/>
                            </xsl:otherwise>
                        </xsl:choose>
                        <xsl:call-template name="rdfsLabel"/>
                        <!-- physicalDescription/form@authorityURI - ## bf:carrier [a bf:Carrier ; bf:source [a bf:Source ; bf:code "value" ] . -->
                        <!-- physicalDescription/form@valueURI - ## bf:carrier <URI> . -->
                        <xsl:call-template name="bfSource"/>
                    </bf:Carrier>
                </bf:carrier>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>
    <!-- ** physicalDescription/reformattingQuality ** -->
    <xsl:template match="mods:reformattingQuality"  mode="Instance">
        <!-- physicalDescription/reformattingQuality _:Item a bf:Item ; bf:note [ a bf:Note ; bf:noteType "reformattingQuality" ; rdfs:label "value" ]		-->
        <!-- physicalDescription/reformattingQuality="access" - ## bf:note [ a bf:Note ; bf:noteType "reformattingQuality" ; rdfs:label "access" ] -->
        <!-- physicalDescription/reformattingQuality="preservation" - ## bf:note [ a bf:Note ; bf:noteType "reformattingQuality" ; rdfs:label "preservation" ] . -->
        <!-- physicalDescription/reformattingQuality="replacement" - ## bf:note [ a bf:Note ; bf:noteType "reformattingQuality" ; rdfs:label "replacement" ] . -->
        <bf:hasItem>
            <bf:Item>
                <xsl:sequence select="local:rdfAbout(., concat('#Instance-', count(preceding::*) + 1))"></xsl:sequence>
                <bf:note>
                    <bf:Note>
                        <bf:noteType>reformattingQuality</bf:noteType>
                        <xsl:call-template name="rdfsLabel"/>
                    </bf:Note>
                </bf:note>
            </bf:Item>
        </bf:hasItem>
    </xsl:template>
                    
    <xsl:template match="mods:digitalOrigin" mode="Instance">
        <xsl:call-template name="buildNote">
            <xsl:with-param name="noteType">digitalOrigin</xsl:with-param>
        </xsl:call-template>
        <!-- physicalDescription/digitalOrigin _:inst a bf:Instance ; bf:note [ a bf:Note ; bf:noteType "digitalOrigin" ; rdfs:label "value" ]  -->
        <!-- physicalDescription/digitalOrigin="born digital" ## bf:note [ a bf:Note ; bf:noteType "digitalOrigin" ; rdfs:label "born digital" ] . -->
        <!-- physicalDescription/digitalOrigin="reformatted digital" ## bf:note [ a bf:Note ; bf:noteType "digitalOrigin" ; rdfs:label "reformatted digital" ] . -->
        <!-- physicalDescription/digitalOrigin="digitized microfilm" ## bf:note [ a bf:Note ; bf:noteType "digitalOrigin" ; rdfs:label "digitized microfilm" ] . -->
        <!-- physicalDescription/digitalOrigin="digitized other analog" ## bf:note [ a bf:Note ; bf:noteType "digitalOrigin" ; rdfs:label "digitized other analog" ] . -->
    </xsl:template>
    <xsl:template match="mods:extent" mode="Instance">
        <!-- physicalDescription/extent _:inst a bf:Instance ; bf:extent [a bf:Extent ; rdfs:label "value" ] . -->
        <!-- physicalDescription/extent@lang - physicalDescription/extent@xml:lang - physicalDescription/extent@script  -->
        <!-- physicalDescription/extent@unit _:inst a bf:Instance ; bf:extent [a bf:Extent ; bf:unit [a bf:Unit ; rdfs:label "value" ] ] .  -->
        <bf:extent>
            <bf:Extent>
                <xsl:call-template name="rdfsLabel"/>
                <xsl:if test="@unit">
                    <bf:unit>
                        <bf:Unit>
                            <rdfs:label><xsl:value-of select="@unit"/></rdfs:label>
                        </bf:Unit>
                    </bf:unit>
                </xsl:if>
            </bf:Extent>
        </bf:extent>
    </xsl:template>
    <xsl:template match="mods:internetMediaType"  mode="Instance">
        <!--physicalDescription/internetMediaType _:inst a bf:Instance ; bf:digitalCharacteristic [a bf:EncodingFormat ; rdfs:label "value" ] . -->
        <bf:digitalCharacteristic>
            <bf:EncodingFormat>
                <rdfs:label><xsl:value-of select="."/></rdfs:label>
            </bf:EncodingFormat>
        </bf:digitalCharacteristic>
    </xsl:template>
    
    <!-- ** abstract ** -->
    <xsl:template match="mods:abstract" mode="Work">
        <xsl:choose>
            <xsl:when test="@type='review'">
                <!-- abstract@type="review" - _:w a bf:Work ; bf:review [ a bf:Review ; rdfs:label "value" ] . -->
                <!-- abstract@type="review" ## - rdfs:label "content of  @xlink:href", Add  ^^xs:anyURI after URI -->
                <bf:review>
                    <bf:Review>       
                        <xsl:call-template name="rdfsLabel"/>
                    </bf:Review>
                </bf:review>
            </xsl:when>
            <xsl:otherwise>
                <!-- abstract [value only] _:w a bf:Work ; bf:summary [a bf:Summary ; rdfs:label "value" ] . -->
                <bf:summary>
                    <bf:Summary>
                        <!-- ## - rdfs:label "content of  @xlink:href", Add  ^^xs:anyURI after URI -->
                        <xsl:call-template name="rdfsLabel"/>
                    </bf:Summary>
                </bf:summary>                
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>
    
    <!-- ** note ** -->
    <xsl:template match="mods:note" mode="Work">
        <xsl:choose>
            <xsl:when test="@type = 'organization'">
                <!-- physicalDescription/note@type="organization" - _:w a bf:Work ; bf:arrangement [a bf:Arrangement ; rdfs:label "value" ] . -->
                <bf:arrangement>
                    <bf:Arrangement>
                        <xsl:call-template name="rdfsLabel"/>
                    </bf:Arrangement>
                </bf:arrangement>
            </xsl:when>
            <xsl:when test="@type = 'acquisition'">
                <bf:hasItem >
                    <bf:Item>
                        <xsl:sequence select="local:rdfAbout(., concat('#Item-', count(preceding::*) + 1))"></xsl:sequence>
                        <bf:itemOf>
                            <xsl:sequence select="local:rdfResource(., '#Work')"/>
                        </bf:itemOf>
                        <!-- note@type="acquisition" _:It a bf:Item ; bf:immediateAcquisition [a bf:ImmediateAcquisition ; rdfs:label "value" ] . -->                       
                        <bf:immediateAcquisition>
                            <bf:ImmediateAcquisition>
                                <xsl:call-template name="rdfsLabel"/>                          
                            </bf:ImmediateAcquisition>
                        </bf:immediateAcquisition>
                    </bf:Item>
                </bf:hasItem>
            </xsl:when>
            <!-- WS-21 Add note/@type='exhibitions'   -->
            <xsl:when test="@type = 'exhibitions'">
                <bf:hasItem >
                    <bf:Item>
                        <xsl:sequence select="local:rdfAbout(., concat('#Item-', count(preceding::*) + 1))"></xsl:sequence>
                        <bf:itemOf>
                            <xsl:sequence select="local:rdfResource(., '#Work')"/>
                        </bf:itemOf>                       
                        <xsl:call-template name="buildNote">
                            <xsl:with-param name="noteType">exhibition</xsl:with-param>
                        </xsl:call-template>
                    </bf:Item>
                </bf:hasItem>
            </xsl:when>
            <xsl:when test="@type = 'ownership'">
                <!-- note@type="ownership" _:it a bf:Item ; bf:custodialHistory "value" . -->
                <bf:hasItem>
                    <bf:Item>
                        <xsl:sequence select="local:rdfAbout(., concat('#Item-', count(preceding::*) + 1))"></xsl:sequence>
                        <bf:itemOf>
                            <xsl:sequence select="local:rdfResource(., '#Work')"/>
                        </bf:itemOf>
                        <bf:custodialHistory><xsl:value-of select="."/></bf:custodialHistory>
                    </bf:Item>
                </bf:hasItem>
            </xsl:when>
            <xsl:when test="@type = 'preferred citation'">
                <!-- note@type="preferred citation" _:Inst a bf:Instance ; bf:preferredCitation "value" . -->
                <bf:preferredCitation><xsl:value-of select="."/></bf:preferredCitation>
            </xsl:when>
            <xsl:when test="@type = 'restriction'">
                <!-- note@type="restriction"
                    _:Inst a bf:Instance ; bf:usageAndAccessPolicy [ a bf:UsageAndAccessPolicy ; rdfs:label "value" ] . -->
                <bf:usageAndAccessPolicy>
                    <bf:UsageAndAccessPolicy>
                        <xsl:call-template name="rdfsLabel"/>
                    </bf:UsageAndAccessPolicy>
                </bf:usageAndAccessPolicy>
            </xsl:when>
            <xsl:when test="@type = 'statement of responsibility'">
                <!-- note@type="statement of responsibility" _:Inst a bf:Instance ; bf:responsibilityStatement "value" .  -->
                <bf:responsibilityStatement><xsl:value-of select="."/></bf:responsibilityStatement>
            </xsl:when>
            <xsl:when test="@type = 'creation/production credits'">
                <!-- note@type="creation/production credits" _:Ins a bf:Instance ; bf:credits "value" -->
                <bf:credits><xsl:value-of select="."/></bf:credits>
            </xsl:when>
            <xsl:when test="@type = 'thesis'">
                <!-- note@type="thesis" _:w a bf:Work ; bf:dissertation [a bf:Dissertation ; rdfs:label "value" ] . -->
                <bf:dissertation>
                    <bf:Dissertation>
                        <xsl:call-template name="rdfsLabel"/>
                    </bf:Dissertation>
                </bf:dissertation>
            </xsl:when>
            <xsl:when test="@type = 'venue'">
                <!-- note@type="venue" _:w a bf:Work ; bf:capture [a bf:Capture ; rdfs:label "value" ] .  -->
                <bf:capture>
                    <bf:Capture>
                        <xsl:call-template name="rdfsLabel"/>
                    </bf:Capture>
                </bf:capture>
            </xsl:when>
            <xsl:when test="@type='accrual policy'">
                <!-- note@type="accrual policy" _:It a bf:Item ; bf:note [ a bf:Note ; bf:noteType "accrual policy" ; rdfs:label "value" ] .-->
                <bf:hasItem >
                    <bf:Item>
                        <xsl:sequence select="local:rdfAbout(., concat('#Item-', count(preceding::*) + 1))"></xsl:sequence>
                        <bf:itemOf>
                            <xsl:sequence select="local:rdfResource(., '#Work')"/>
                        </bf:itemOf>
                        <xsl:call-template name="buildNote">
                            <xsl:with-param name="noteType">accrual policy</xsl:with-param>
                        </xsl:call-template>
                    </bf:Item>
                </bf:hasItem>
            </xsl:when>
            <xsl:when test="@type = 'accruel method'">
                <!-- note@type="accruel method" _:It a bf:Item bf:note [ a bf:Note ; bf:noteType "accrual method" ; rdfs:label "value" ] . -->
                <bf:hasItem >
                    <bf:Item>
                        <xsl:sequence select="local:rdfAbout(., concat('#Item-', count(preceding::*) + 1))"></xsl:sequence>
                        <bf:itemOf>
                            <xsl:sequence select="local:rdfResource(., '#Work')"/>
                        </bf:itemOf>
                        <xsl:call-template name="buildNote">
                            <xsl:with-param name="noteType">accrual method</xsl:with-param>
                        </xsl:call-template>  
                    </bf:Item>
                </bf:hasItem>
            </xsl:when>
            <xsl:when test="@type = 'action'">
                <!-- note@type="action" _:it a bf:Item ; bf:note [a bf:Note ; bf:noteType "action" ; rdfs:label "value" ] .-->
                <bf:hasItem>
                    <bf:Item>
                        <xsl:sequence select="local:rdfAbout(., concat('#Item-', count(preceding::*) + 1))"></xsl:sequence>
                        <bf:itemOf>
                            <xsl:sequence select="local:rdfResource(., '#Work')"/>
                        </bf:itemOf>
                        <xsl:call-template name="buildNote">
                            <xsl:with-param name="noteType">action</xsl:with-param>
                        </xsl:call-template>  
                    </bf:Item>
                </bf:hasItem>
            </xsl:when>
            <xsl:when test="@type = 'biographical/historical'">
                <!-- note@type="biographical/historical" _:It a bf:Item ; bf:note [ a bf:Note ; bf:noteType "biographical or historical" ; rdfs:label "value" ] . -->
                <bf:hasItem >
                    <bf:Item>
                        <xsl:sequence select="local:rdfAbout(., concat('#Item-', count(preceding::*) + 1))"></xsl:sequence>
                        <bf:itemOf>
                            <xsl:sequence select="local:rdfResource(., '#Work')"/>
                        </bf:itemOf>
                        <xsl:call-template name="buildNote">
                            <xsl:with-param name="noteType">biographical or historical</xsl:with-param>
                        </xsl:call-template>  
                    </bf:Item>
                </bf:hasItem>
            </xsl:when>
            <xsl:when test="@type = 'conservation history'">
                <!-- note@type="conservation history"	_:It a bf:Item ; bf:note [ a bf:Note ; bf:noteType "conservation history" ; rdfs:label "value" ] . -->
                <bf:hasItem >
                    <bf:Item>
                        <xsl:sequence select="local:rdfAbout(., concat('#Item-', count(preceding::*) + 1))"></xsl:sequence>
                        <bf:itemOf>
                            <xsl:sequence select="local:rdfResource(., '#Work')"/>
                        </bf:itemOf>
                        <xsl:call-template name="buildNote">
                            <xsl:with-param name="noteType">conservation history</xsl:with-param>
                        </xsl:call-template>
                    </bf:Item>
                </bf:hasItem>
            </xsl:when>
            <xsl:when test="@type='content'">
                <!--note@type="content" _:Ins a bf:Instance ; bf:note [ a bf:Note ; bf:noteType "content" ; rdfs:label "value" ] . -->
                <bf:hasItem >
                    <bf:Item>
                        <xsl:sequence select="local:rdfAbout(., concat('#Item-', count(preceding::*) + 1))"></xsl:sequence>
                        <bf:itemOf>
                            <xsl:sequence select="local:rdfResource(., '#Work')"/>
                        </bf:itemOf>
                        <xsl:call-template name="buildNote">
                            <xsl:with-param name="noteType">content</xsl:with-param>
                        </xsl:call-template>
                    </bf:Item>
                </bf:hasItem>
            </xsl:when>
            <xsl:when test="@type = 'handwritten'">
                <!-- note@type="handwritten" _:It a bf:Item ; bf:note [a bf:Note ; bf:noteType "handwritten" ; rdfs:label "value" ] . -->
                <bf:hasItem >
                    <bf:Item>
                        <xsl:sequence select="local:rdfAbout(., concat('#Item-', count(preceding::*) + 1))"></xsl:sequence>
                        <bf:itemOf>
                            <xsl:sequence select="local:rdfResource(., '#Work')"/>
                        </bf:itemOf>
                        <xsl:call-template name="buildNote">
                            <xsl:with-param name="noteType">handwritten</xsl:with-param>
                        </xsl:call-template>
                    </bf:Item>
                </bf:hasItem>
            </xsl:when>
            <xsl:when test="@type = 'original location'">
                <!-- note@type="original location" _:it a bf:Item1 ; bf:originalVersion [a bf:Item2 ; bf:note [ a bf:Note ; bf:noteType "original location" ; rdfs:label "value" ] ] .  -->
                <bf:hasItem >
                    <bf:Item>
                        <xsl:sequence select="local:rdfAbout(., concat('#Item-', count(preceding::*) + 1))"></xsl:sequence>
                        <bf:itemOf>
                            <xsl:sequence select="local:rdfResource(., '#Work')"/>
                        </bf:itemOf>
                        <bf:originalVersion>
                        <xsl:call-template name="buildNote">
                            <xsl:with-param name="noteType">original location</xsl:with-param>
                        </xsl:call-template>
                        </bf:originalVersion>
                    </bf:Item>
                </bf:hasItem>
            </xsl:when>
            <xsl:when test="@type = 'citation/reference'">
                <!-- note@type="citation/reference" _:w a bf:Work ; bf:note [ a bf:Note ; bf:noteType "citation or reference" ; rdfs:label "value" ] . -->
                <xsl:call-template name="buildNote">
                    <xsl:with-param name="noteType">citation or reference</xsl:with-param>
                </xsl:call-template>
            </xsl:when>
            <xsl:when test="@type = 'creation/production credits'">
                <!-- note@type="creation/production credits"
                _:w a bf:Work ; bf:credits "value"
                    Could be Work or Instance (MARC mapping of 508 uses Work). -->
                <bf:credits><xsl:value-of select="."/></bf:credits>
            </xsl:when>
            <xsl:when test="@type = 'date'">
                <!-- note@type="date" _:w a bf:Work ; bf:capture [ a bf:Capture ; rdfs:label "value" ] . -->
                <bf:capture>
                    <bf:Capture>
                        <xsl:call-template name="rdfsLabel"/>
                    </bf:Capture>
                </bf:capture>
            </xsl:when>
            <xsl:when test="@type = 'language'">
                <!-- note@type="language" _w: a bf:Work ; bf:note [ a bf:Note ; bf:noteType "language" ; rdfs:label "value" ] .-->
                <xsl:call-template name="buildNote">
                    <xsl:with-param name="noteType">language</xsl:with-param>
                </xsl:call-template>
            </xsl:when>
            <xsl:when test="@type = 'performers'">
                <!-- note@type="performers" _:Inst a bf:Instance ; bf:credits "value" .-->
                <bf:credits><xsl:value-of select="."/></bf:credits>
            </xsl:when>
            <xsl:when test="@type = 'subject completeness'">
                <!-- note@type="subject completeness" _:w a bf:Work ; bf:note [ a bf:Note ; bf:noteType "subject completeness" ; rdfs:label "value" ] .-->
                <xsl:call-template name="buildNote">
                    <xsl:with-param name="noteType">subject completeness</xsl:with-param>
                </xsl:call-template>  
            </xsl:when>
            <xsl:when test="@type = 'thesis'">
                <!-- note@type="thesis"
                    _:w a bf:Work ; bf:dissertation [a bf:Dissertation ; rdfs:label "value" ] .-->
                <bf:dissertation>
                    <bf:Dissertation>
                        <xsl:call-template name="rdfsLabel"/>
                    </bf:Dissertation>
                </bf:dissertation>
            </xsl:when>
            <xsl:when test="@type = 'venue'">
                <!-- note@type="venue"
                    _:w a bf:Work ; bf:capture [a bf:Capture ; rdfs:label "Value" ] .  -->
                <bf:capture>
                    <bf:Capture>
                        <xsl:call-template name="rdfsLabel"/>
                    </bf:Capture>
                </bf:capture>
            </xsl:when>
            <xsl:when test="@type = 'exhibitions'">
                <!-- note@type="exhibitions" _:It a bf:Item ; bf:note [ a bf:Note ; bf:noteType "exhibition" ; rdfs:label "value" ] . -->
                <bf:hasItem>
                    <bf:Item>
                        <xsl:sequence select="local:rdfAbout(., concat('#Item-', count(preceding::*) + 1))"></xsl:sequence>
                        <bf:itemOf>
                            <xsl:sequence select="local:rdfResource(., '#Work')"/>
                        </bf:itemOf>
                        <xsl:call-template name="buildNote">
                            <xsl:with-param name="noteType">exhibition</xsl:with-param>
                        </xsl:call-template>
                    </bf:Item>
                </bf:hasItem>
            </xsl:when>
        </xsl:choose>
    </xsl:template>
    <xsl:template match="mods:note">
        <xsl:call-template name="buildNote"/>
    </xsl:template> 
    <xsl:template match="mods:note" mode="Instance">
        <xsl:choose>
            <xsl:when test="parent::mods:physicalDescription">
               <!-- physicalDescription/note	_:inst a bf:Instance ; bf:note [a bf:Note ; rdfs:label] .
                    physicalDescription/note@type="technique"	_:inst a bf:Instance ; bf:productionMethod [a bf:ProductionMethod  ; rdfs:label "value" ] .
                -->
                <xsl:choose>
                    <xsl:when test="@type='condition'">
                        <!-- physicalDescription/note@type="condition"	_:it a bf:Item ; bf:note [ a bf:Note ; bf:noteType "condition" ]. -->
                        <xsl:call-template name="buildNote">
                            <xsl:with-param name="noteType">condition</xsl:with-param>
                        </xsl:call-template>
                    </xsl:when>
                    <!-- WS-20 Add note/@type='date/sequential designation'   -->
                    <xsl:when test="@type='date/sequential designation'">
                        <!-- physicalDescription/note@type="marks"	_:it a bf:Item ; bf:note [ a bf:Note ; bf:noteType "marks" ]. -->
                        <xsl:call-template name="buildNote">
                            <xsl:with-param name="noteType">date or sequential designation</xsl:with-param>
                        </xsl:call-template>
                    </xsl:when>
                    <xsl:when test="@type='marks'">
                        <!-- physicalDescription/note@type="marks"	_:it a bf:Item ; bf:note [ a bf:Note ; bf:noteType "marks" ]. -->
                        <xsl:call-template name="buildNote">
                            <xsl:with-param name="noteType">marks</xsl:with-param>
                        </xsl:call-template>
                    </xsl:when>
                    <xsl:when test="@type='medium'">
                        <!-- physicalDescription/note@type="medium"	_:inst a bf:Instance ; bf:note [ a bf:Note ; bf:noteType "medium" ] . -->
                        <xsl:call-template name="buildNote">
                            <xsl:with-param name="noteType">medium</xsl:with-param>
                        </xsl:call-template>
                    </xsl:when>
                    <xsl:when test="@type='organization'"/>
                    <xsl:when test="@type='physical description'">
                        <!-- physicalDescription/note@type="physical description"	_:inst a bf:Instance ; bf:note [ a bf:Note ; bf:noteType "physical Description" ].-->
                        <xsl:call-template name="buildNote">
                            <xsl:with-param name="noteType">physical description</xsl:with-param>
                        </xsl:call-template>
                    </xsl:when>
                    <xsl:when test="@type='physical details'">
                        <!-- physicalDescription/note@type="physical details"	_:inst a bf:Instance ; bf:note [ a bf:Note ; bf:noteType "physical details" ]. -->
                        <xsl:call-template name="buildNote">
                            <xsl:with-param name="noteType">physical details</xsl:with-param>
                        </xsl:call-template>
                    </xsl:when>
                    <xsl:when test="@type='presentation'">
                        <!-- physicalDescription/note@type="presentation"	_:inst a bf:Instance ; bf:note [ a bf:Note ; bf:noteType "presentation" ]. -->
                        <xsl:call-template name="buildNote">
                            <xsl:with-param name="noteType">presentation</xsl:with-param>
                        </xsl:call-template>
                    </xsl:when>
                    <xsl:when test="@type='script'">
                        <!-- physicalDescription/note@type="script"	_:inst a bf:Instance ; bf:note [ a bf:Note ; bf:noteType "script" ] . -->
                        <xsl:call-template name="buildNote">
                            <xsl:with-param name="noteType">script</xsl:with-param>
                        </xsl:call-template>
                    </xsl:when>
                    <!-- WS-23 Add  note@type="statement of responsibility"   -->
                    <xsl:when test="@type='statement of responsibility'">
                        <bf:responsibilityStatement><xsl:value-of select="."/></bf:responsibilityStatement>
                    </xsl:when>
                    <xsl:when test="@type='support'">
                        <!-- physicalDescription/note@type="support"	_:inst a bf:Instance ;  bf: mount [a bf:Mount ; rdfs:label " " ] -->
                        <bf:mount>
                            <bf:Mount>
                                <xsl:call-template name="rdfsLabel"/>
                            </bf:Mount>
                        </bf:mount>
                    </xsl:when>
                    <xsl:when test="@type='technique'">
                        <!-- physicalDescription/note@type="technique"	_:inst a bf:Instance ; bf:productionMethod [a bf:ProductionMethod  ; rdfs:label "value" ] . -->
                        <bf:productionMethod>
                            <bf:ProductionMethod>
                                <xsl:call-template name="rdfsLabel"/>
                            </bf:ProductionMethod>
                        </bf:productionMethod>
                    </xsl:when>
                    <xsl:otherwise>
                        <xsl:call-template name="buildNote"/>
                    </xsl:otherwise>
                </xsl:choose>
            </xsl:when>
            <xsl:when test="@type='admin'">
                <!-- note@type="admin" _:Inst1 a bf:Instance ; bf:note [ a bf:Note ; bf:noteType "admin" ; rdfs:label "value" ] . -->
                <xsl:call-template name="buildNote">
                    <xsl:with-param name="noteType">admin</xsl:with-param>
                </xsl:call-template>
            </xsl:when>
            <xsl:when test="@type = 'additional physical form'">
                <!-- note@type="additional physical form"	_:Inst1 a bf:Instance ; bf:note [ a bf:Note ; bf:noteType "additional physical form" ; rdfs:label "value" ] . -->
                <xsl:call-template name="buildNote">
                    <xsl:with-param name="noteType">additional physical form</xsl:with-param>    
                </xsl:call-template> 
            </xsl:when>
            <xsl:when test="@type = 'version identification'">
                <!-- note@type="version identification" _:Inst a bf:Instance ; bf:note [ a bf:Note ; bf:noteType "version identification" ; rdfs:label "value" ] .-->        
                <xsl:call-template name="buildNote">
                    <xsl:with-param name="noteType">version identification</xsl:with-param>
                </xsl:call-template> 
            </xsl:when>
            <xsl:when test="@type = 'original version'">
                <!-- note@type="original version" _:Inst a bf:Instance ; bf:note [a bf:Note ; bf:noteType "originalVersion" ; rdfs:label "value" ] . -->
                <xsl:call-template name="buildNote">
                    <xsl:with-param name="noteType">originalVersion</xsl:with-param>    
                </xsl:call-template> 
            </xsl:when>
            <xsl:when test="@type = 'bibliographic history'">
                <!-- note@type="bibliographic history" _:Inst a bf:Instance ; bf:note [ a bf:Note ; bf:noteType "bibliographic history" ; rdfs:label "value" ] .  -->
                <xsl:call-template name="buildNote">
                    <xsl:with-param name="noteType">bibliographic history</xsl:with-param>    
                </xsl:call-template>
            </xsl:when>
            <xsl:when test="@type = 'bibliography'">
                <!-- note@type="bibliography" _:Inst a bf:Instance ; bf:supplementaryContent [ a bf:SupplementaryContent ; rdfs:label "value" ] .  -->
                <bf:supplementaryContent>
                    <bf:SupplementaryContent>
                        <xsl:call-template name="rdfsLabel"/>
                    </bf:SupplementaryContent>    
                </bf:supplementaryContent>
            </xsl:when>
            <xsl:when test="@type = 'content'">
                <!-- note@type="content" _:Ins a bf:Instance ; bf:note [ a bf:Note ; bf:noteType "content" ; rdfs:label "value" ] . -->
                <xsl:call-template name="buildNote">
                    <xsl:with-param name="noteType">content</xsl:with-param>    
                </xsl:call-template>
            </xsl:when>
            <xsl:when test="@type = 'date/sequential designation'">
                <!-- note@type="date/sequential designation" _:Inst a bf:Instance ; bf:note [a bf:Note ; bf:noteType "date or sequential designation" ; rdfs:label "value" ] .-->
                <xsl:call-template name="buildNote">
                    <xsl:with-param name="noteType">date or sequential designation</xsl:with-param>     
                </xsl:call-template>
            </xsl:when>
            <xsl:when test="@type = 'numbering'">
                <!-- note@type="numbering" _:Inst a bf:Instance ; bf:note [a bf:Note ; bf:noteType "numbering" ; rdfs:label "value" ] . -->
                <xsl:call-template name="buildNote">
                    <xsl:with-param name="noteType">numbering</xsl:with-param>    
                </xsl:call-template>
            </xsl:when>
            <xsl:when test="@type = 'funding'">
                <!-- note@type="funding" _:Inst a bf:Instance ; bf:note [a bf:Note ; bf:noteType "funding" ; rdfs:label "value" ] . -->
                <xsl:call-template name="buildNote">
                    <xsl:with-param name="noteType">funding</xsl:with-param>    
                </xsl:call-template>
            </xsl:when>
            <xsl:when test="@type = 'preferred citation'">
                <!-- note@type="preferred citation" _:Inst a bf:Instance ; bf:preferredCitation "value" . -->        
                <bf:preferredCitation><xsl:value-of select="."/></bf:preferredCitation>
            </xsl:when>
            <xsl:when test="@type = 'publications'">
                <!-- note@type="publications" _:Inst a bf:Instance ; bf:note [ a bf:Note ; bf:noteType "publications" ; rdfs:label "value" ] . -->
                <xsl:call-template name="buildNote">
                    <xsl:with-param name="noteType">publications</xsl:with-param>
                </xsl:call-template>
            </xsl:when>
            <xsl:when test="@type = 'reproduction'">
                <!-- note@type="reproduction" _:Inst a bf:Instance ; bf:note [ a bf:Note ; bf:noteType "reproduction" ; rdfs:label "value" ] .-->
                <xsl:call-template name="buildNote">
                    <xsl:with-param name="noteType">reproduction</xsl:with-param>    
                </xsl:call-template>
            </xsl:when>
            <xsl:when test="@type = 'restriction'">
                <!-- note@type="restriction" _:Inst a bf:Instance ; bf:usageAndAccessPolicy [ a bf:UsageAndAccessPolicy ; rdfs:label "value" ] . -->
                <bf:usageAndAccessPolicy>
                    <bf:UsageAndAccessPolicy>
                        <xsl:call-template name="rdfsLabel"/>
                    </bf:UsageAndAccessPolicy>    
                </bf:usageAndAccessPolicy>
            </xsl:when>
            <xsl:when test="@type = 'source characteristics'">
                <!-- note@type="source characteristics" _Inst1 a bf:Instance ; bf:dataSource [ a bf:Work ; bf:hasInstance [ a bf:Instance ; bf:note [ a bf:Note ; rdfs:label "value of source characterisics" ] ] ] .  -->
                <bf:dataSource>
                    <bf:Work>
                        <xsl:sequence select="local:rdfAbout(.,'#dataSource')"/>
                        <bf:hasInstance>
                            <xsl:call-template name="buildNote">
                                <xsl:with-param name="noteType">source characteristics</xsl:with-param>
                            </xsl:call-template>
                        </bf:hasInstance>
                    </bf:Work>
                </bf:dataSource>
            </xsl:when>
            <xsl:when test="@type = 'source dimensions'">
                <!-- note@type="source dimensions" _Inst1 a bf:Instance ; bf:dataSource [ a bf:Work ; bf:hasInstance [ a bf:Instance ; bf:dimensions "value of source dimensions" ] ] .-->
                <bf:dataSource>
                    <bf:Work>
                        <xsl:sequence select="local:rdfAbout(.,'#dataSource')"/>
                        <bf:hasInstance>
                            <bf:dimensions><xsl:value-of select="."/></bf:dimensions>
                        </bf:hasInstance>
                    </bf:Work>
                </bf:dataSource>
            </xsl:when>
            <xsl:when test="@type = 'source identifier'">
                <!-- note@type="source identifier" _Inst1 a bf:Instance ; bf:dataSource [ a bf:Work ; bf:hasInstance [ a bf:Instance ; bf:identifiedBy [ a bf:Identifier ; rdf:value "value from source identifier ] ] ] . -->
                <bf:dataSource>
                    <bf:Work>
                        <xsl:sequence select="local:rdfAbout(.,'#dataSource')"/>
                        <bf:hasInstance>
                            <bf:identifiedBy>
                                <bf:Identifier><xsl:value-of select="."/></bf:Identifier>
                            </bf:identifiedBy>
                        </bf:hasInstance>
                    </bf:Work>
                </bf:dataSource>     
            </xsl:when>
            <xsl:when test="@type = 'source note'">
                <!-- note@type="source note" _Inst1 a bf:Instance ; bf:dataSource [ a bf:Work ; bf:hasInstance [ a bf:Instance ; bf:note [ a bf:Note ; rdfs:label "value of source note" ] ] ] . -->
                <xsl:call-template name="buildNote">
                    <xsl:with-param name="noteType">source note</xsl:with-param>
                </xsl:call-template>  
            </xsl:when>
            <xsl:when test="@type = 'statement of responsibility'">
                <!-- note@type="statement of responsibility" _:Inst a bf:Instance ; bf:responsibilityStatement "value" .  -->
                <bf:responsibilityStatement>
                    <xsl:sequence select="local:buildLangAttribute(.)"/>
                    <xsl:value-of select="."/>    
                </bf:responsibilityStatement>
            </xsl:when>
            <xsl:when test="@type = 'system details'">
                <!-- note@type="system details " _:Inst a bf:Instance ; bf:systemRequirement [a bf:SystemRequirement ; rdfs:label "value" ] . -->
                <bf:systemRequirement>
                    <bf:SystemRequirement>
                        <xsl:call-template name="rdfsLabel"/>
                    </bf:SystemRequirement>
                </bf:systemRequirement>
            </xsl:when>
            <xsl:otherwise>
                <xsl:call-template name="buildNote">
                    <xsl:with-param name="noteType"><xsl:value-of select="@type"/></xsl:with-param>
                </xsl:call-template>
                <!-- note _:Inst a bf:Instance ; bf:note [ a bf:Note ; rdfs:label "value" ] -->
                <!--<bf:hasInstance>
                    <bf:Instance>
                        <xsl:sequence select="local:rdfAbout(., concat('#Instance-', count(preceding::*) + 1))"></xsl:sequence>
                        <bf:instanceOf>
                            <xsl:sequence select="local:rdfResource(., '#Work')"/>    
                        </bf:instanceOf>
                        <bf:usageAndAccessPolicy>
                            <bf:UsageAndAccessPolicy>
                                <xsl:call-template name="rdfsLabel"/>
                            </bf:UsageAndAccessPolicy>
                        </bf:usageAndAccessPolicy>
                    </bf:Instance>
                </bf:hasInstance>-->
            </xsl:otherwise>            
        </xsl:choose>
    </xsl:template>
    
    <!-- ** mods:targetAudience** -->
    <xsl:template match="mods:targetAudience" mode="Work">
        <!-- targetAudience [element value only, no attributes] _:w a bf:Work ; bf:intendedAudience [a bf:IntendedAudiecnce ; rdfs:label "value"] . -->
        <bf:intendedAudience>
            <bf:IntendedAudience>
                <xsl:choose>
                    <xsl:when test="@valueURI"><xsl:attribute name="rdf:about" select="@valueURI"/></xsl:when>
                    <xsl:when test="@authorityURI">
                        <xsl:variable name="URI" select="local:authorityLookUp(string(@authorityURI),.,())"/>
                        <xsl:if test="$URI">
                            <xsl:attribute name="rdf:about" select="$URI"/>    
                        </xsl:if>
                    </xsl:when>
                    <xsl:when test="@authority = 'marctarget'">
                        <xsl:variable name="URI" select="local:authorityLookUp('https://id.loc.gov/vocabulary/maudience.rdf',.,())"/>
                        <xsl:if test="$URI">
                            <xsl:attribute name="rdf:about" select="$URI"/>    
                        </xsl:if>
                    </xsl:when>
                    <xsl:otherwise>
                        <xsl:sequence select="local:rdfAbout(.,())"/>
                    </xsl:otherwise>
                </xsl:choose>
                <xsl:call-template name="rdfsLabel"/>
                <xsl:call-template name="bfSource"/>
            </bf:IntendedAudience>
        </bf:intendedAudience>
    </xsl:template>
    
    <!-- ** table of contents **  -->
    <xsl:template match="mods:tableOfContents" mode="Work">
        <!-- tableOfContents :w1 a bf:Work ; :w1 a bf:Work ; bf:tableOfContents [a bf:TableOfContent] . -->
        <!-- tableOfContents@type="Contents" - ## bf:tableOfContents [a bf:TableOfContents ; rdfs:label "value] -->
        <!-- tableOfContents@type="Incomplete contents" ## bf:tableOfContents [ a bf:TableOfContents ; rdfs:label "value" ; bf:note [ a bf:Note ; rdfs:label "incomplete" ] ] . -->
        <!-- tableOfContents@type="Partial contents" - ## bf:tableOfContents [ a bf:TableOfContents ; rdfs:label "value" ; bf:note [ a bf:Note ; rdfs:label "partial" ] ] . -->
        <!-- tableOfContents@xlink -  ## - rdfs:label "content of  @XLINK", Add  ^^xs:anyURI after URI  -->
        <bf:tableOfContents>
            <bf:TableOfContent>
                <xsl:call-template name="rdfsLabel"/>
                <xsl:choose>
                    <xsl:when test="@type = 'Incomplete contents'">
                        <bf:note>
                            <bf:Note>
                                <rdfs:label>incomplete</rdfs:label>
                            </bf:Note>
                        </bf:note>
                    </xsl:when>
                    <xsl:when test="@type = 'Partial contents'">
                        <bf:note>
                            <bf:Note>
                                <rdfs:label>partial</rdfs:label>
                            </bf:Note>
                        </bf:note>
                    </xsl:when>
                </xsl:choose>
            </bf:TableOfContent>
        </bf:tableOfContents>
    </xsl:template>
    
    <!-- ** subject **  -->
    <xsl:template match="mods:subject" mode="Work">
        <xsl:variable name="label"><xsl:value-of select="string-join(descendant-or-self::text(),'--')"/></xsl:variable>
        <xsl:variable name="lookupLabel"><xsl:value-of select="string-join(descendant-or-self::*[not(self::mods:genre)]/text(),'--')"/></xsl:variable>
        <xsl:variable name="subjectElement">
            <xsl:choose>
                <xsl:when test="count(distinct-values(child::*/name(.))) gt 1">bf:Topic</xsl:when>
                <xsl:when test="local-name(child::*[1]) = 'topic'">bf:Topic</xsl:when>
                <xsl:when test="local-name(child::*[1]) = 'geographic'">bf:Place</xsl:when>
                <xsl:when test="local-name(child::*[1]) = 'hierarchicalGeographic'">bf:Place</xsl:when>
                <xsl:when test="local-name(child::*[1]) = 'temporal'">bf:Temporal</xsl:when>
                <xsl:when test="local-name(child::*[1]) = 'titleInfo'">bf:Work</xsl:when>
                <xsl:when test="local-name(child::*[1]) = 'name'">bf:Agent</xsl:when>
                <xsl:otherwise>bf:Topic</xsl:otherwise>
            </xsl:choose>
        </xsl:variable>
        <xsl:choose>
            <xsl:when test="mods:cartographics">
                <xsl:apply-templates select="mods:cartographics" mode="Work"/>
            </xsl:when>
            <xsl:when test="mods:geographicCode">
                <xsl:apply-templates select="mods:geographicCode" mode="Work"/>
            </xsl:when>
            <xsl:otherwise>
                <bf:subject>
                    <!-- If there are multiple subelements under <subject> 
                        add rdf:type with class according to first subelement and also add 
                        <rdf:type rdf:resource="http://www.loc.gov/mads/rdf/v1#ComplexSubject" />    
                    -->
                    <xsl:element name="{$subjectElement}">
                        <!-- Lookup here for authority URI  -->
                        <xsl:variable name="subjectURI" select="local:authorityLookUp('https://id.loc.gov/authorities/subject/label/',$lookupLabel,'')"/>
                        <xsl:variable name="authorityRecord">
                            <xsl:if test="$subjectURI != ''">
                                <xsl:variable name="runRequest" use-when="function-available('http:send-request')">
                                    <xsl:variable name="request" as="element(http:request)">
                                        <http:request href='{concat(replace($subjectURI,"http:","https:"),".rdf")}' method='get'/>
                                    </xsl:variable>
                                    <xsl:variable name="result" select="http:send-request($request)"/>
                                    <xsl:if test="$result[1][@status='200']">
                                        <xsl:choose>
                                            <xsl:when test="$result[2]/descendant::madsrdf:componentList">
                                                <xsl:copy-of select="$result[2]/descendant::madsrdf:componentList"/>        
                                            </xsl:when>
                                            <xsl:when test="$result[2]/descendant::madsrdf:elementList">
                                                <xsl:copy-of select="$result[2]/descendant::madsrdf:elementList"/>
                                            </xsl:when>
                                        </xsl:choose>
                                    </xsl:if>
                                </xsl:variable>
                                <xsl:if test="$runRequest != ''" use-when="function-available('http:send-request')">
                                    <xsl:sequence select="$runRequest"/>
                                </xsl:if>
                            </xsl:if>
                        </xsl:variable>
                        <xsl:choose>
                            <xsl:when test="$subjectURI != ''"><xsl:attribute name="rdf:about" select="$subjectURI"/></xsl:when>
                            <xsl:otherwise><xsl:sequence select="local:rdfAbout(.,concat('#Subject-', count(preceding::*) + 1))"/></xsl:otherwise>
                        </xsl:choose>
                        <!-- Subject type -->
                        <xsl:choose>
                            <xsl:when test="mods:hierarchicalGeographic">
                                <rdf:type rdf:resource="http://www.loc.gov/mads/rdf/v1#HierarchicalGeographic"/>
                            </xsl:when>
                            <xsl:when test="$subjectElement = 'bf:Work'">
                                <rdf:type rdf:resource="http://www.loc.gov/mads/rdf/v1#NameTitle"/>
                            </xsl:when>
                            <xsl:when test="$subjectElement = 'bf:Agent'">
                                <rdf:type rdf:resource="http://www.loc.gov/mads/rdf/v1#PersonalName"/>
                            </xsl:when>
                            <xsl:when test="count(distinct-values(child::*/name(.))) gt 1">
                                <rdf:type rdf:resource="http://www.loc.gov/mads/rdf/v1#ComplexSubject"/>
                            </xsl:when>
                        </xsl:choose>
                        <xsl:call-template name="rdfsLabel">
                            <xsl:with-param name="label" select="$label"/>
                        </xsl:call-template>
                        <xsl:call-template name="bfSource"/>                            
                        <madsrdf:authoritativeLabel><xsl:value-of select="$label"/></madsrdf:authoritativeLabel>
                        <madsrdf:isMemberOfMADSScheme rdf:resource="http://id.loc.gov/authorities/subjects"/>
                        <xsl:choose>
                            <xsl:when test="$subjectURI != '' and $authorityRecord != ''">
                                <xsl:sequence select="$authorityRecord"/>
                            </xsl:when>
                            <xsl:when test="$subjectElement = 'bf:Work'">
                                <xsl:apply-templates select="child::*" mode="Work"/> 
                            </xsl:when>
                            <xsl:when test="mods:hierarchicalGeographic">  
                                <madsrdf:componentList rdf:parseType="Collection">
                                    <madsrdf:HierarchicalGeographic>
                                    <xsl:apply-templates select="." mode="subject"/>
                                    </madsrdf:HierarchicalGeographic>
                                </madsrdf:componentList>
                            </xsl:when>
                            <xsl:otherwise>
                                <madsrdf:componentList rdf:parseType="Collection">
                                    <xsl:for-each select="child::*">
                                        <xsl:variable name="madsElement">
                                            <xsl:variable name="elementName" select="local-name(.)"/>
                                            <xsl:choose>
                                                <xsl:when test="$elementName = 'genre'">GenreForm</xsl:when>
                                                <xsl:otherwise>
                                                    <xsl:value-of select="concat(upper-case(substring($elementName,1,1)),substring($elementName,2))"/>
                                                </xsl:otherwise>
                                            </xsl:choose>
                                        </xsl:variable>
                                        <xsl:element name="madsrdf:{$madsElement}" xmlns:madsrdf="http://www.loc.gov/mads/rdf/v1#">
                                            <madsrdf:authoritativeLabel><xsl:value-of select="string-join(descendant-or-self::text(),' ')"/></madsrdf:authoritativeLabel>
                                            <madsrdf:elementList>
                                                <xsl:element name="{concat('madsrdf:',$madsElement,'Element')}">
                                                    <madsrdf:elementValue><xsl:value-of select="string-join(descendant-or-self::text(),' ')"/></madsrdf:elementValue>                                                    
                                                </xsl:element>
                                            </madsrdf:elementList>
                                        </xsl:element>
                                    </xsl:for-each>
                                </madsrdf:componentList>
                            </xsl:otherwise>
                        </xsl:choose>
                    </xsl:element>
                </bf:subject>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>    
    <xsl:template match="mods:continent" mode="subject">
        <!-- subject/hierarchicalGeographic/continent	
                ## bf:subject [a madsrdf:Continent ; rdfs:label "value" ] .		
                Use MODSRDF for hierarchicalGeographic and its subelements under bf:place		
                MODSRDF => MADSRDF? -->
        <madsrdf:Continent>
            <xsl:call-template name="rdfsLabel"/>
        </madsrdf:Continent>
    </xsl:template>
    <xsl:template match="mods:country" mode="subject">
        <!-- subject/hierarchicalGeographic/country	
            ## bf:subject [a madsrdf:Country ; rdfs:label "value" ] .		
            Use MODSRDF for hierarchicalGeographic and its subelements under bf:place  -->
        <madsrdf:Country>
            <xsl:call-template name="rdfsLabel"/>
        </madsrdf:Country>
    </xsl:template>
    <xsl:template match="mods:province" mode="subject">
        <!-- subject/hierarchicalGeographic/province	
            ## bf:subject [a madsrdf:Province ; rdfs:label "value" ] .		
            Use MODSRDF for hierarchicalGeographic and its subelements under bf:place -->
        <madsrdf:Province>
            <xsl:call-template name="rdfsLabel"/>
        </madsrdf:Province>
    </xsl:template>
    <xsl:template match="mods:region" mode="subject">
        <!-- subject/hierarchicalGeographic/region	
            ## bf:subject [ a madsrdf:Region ; rdfs:label "value" ] .		
            Use MODSRDF for hierarchicalGeographic and its subelements under bf:place -->
        <!--subject/hierarchicalGeographic/region@regionType	no mapping	no mapping for this attribute	
        subject/hierarchicalGeographic/region@authority-->
        <madsrdf:Region>
            <xsl:call-template name="rdfsLabel"/>
        </madsrdf:Region>
    </xsl:template>
    <xsl:template match="mods:state" mode="subject"> 
        <!-- subject/hierarchicalGeographic/state	
            ## bf:subject [ a madsrdf:State ; rdfs:label "value" ] .		
            Use MODSRDF for hierarchicalGeographic and its subelements under bf:place -->
        <madsrdf:State>
            <xsl:call-template name="rdfsLabel"/>
        </madsrdf:State>
    </xsl:template>
    <xsl:template match="mods:territory" mode="subject">
        <!-- subject/hierarchicalGeographic/territory	
            ## bf:subject [ a madsrdf:Territory ; rdfs:label "value" ] .		
            Use MODSRDF for hierarchicalGeographic and its subelements under bf:place -->
        <madsrdf:Territory>
            <xsl:call-template name="rdfsLabel"/>
        </madsrdf:Territory>
    </xsl:template>
    <xsl:template match="mods:county" mode="subject">
        <!-- subject/hierarchicalGeographic/county	
            ## bf:subject [ a madsrdf:County ; rdfs:label "value" ] .		
            Use MODSRDF for hierarchicalGeographic and its subelements under bf:place -->
        <madsrdf:County>
            <xsl:call-template name="rdfsLabel"/>
        </madsrdf:County>
    </xsl:template>
    <xsl:template match="mods:city" mode="subject">
        <!-- subject/hierarchicalGeographic/city	
            ## bf:subject [ a madsrdf:City ; rdfs:label "value" ] .		
            Use MODSRDF for hierarchicalGeographic and its subelements under bf:place -->
        <madsrdf:City>
            <xsl:call-template name="rdfsLabel"/>
        </madsrdf:City>
    </xsl:template>
    <xsl:template match="mods:citySection" mode="subject">
        <!-- subject/hierarchicalGeographic/citySection	
            ## bf:subject [ a madsrdf:CitySection ; rdfs:label "value" ] .		
            Use MODSRDF for hierarchicalGeographic and its subelements under bf:place -->
        <madsrdf:CitySection>
            <xsl:call-template name="rdfsLabel"/>
        </madsrdf:CitySection>
    </xsl:template>
    <xsl:template match="mods:island" mode="subject">
        <!-- subject/hierarchicalGeographic/island	
            ## bf:subject [ a madsrdf:Island ; rdfs:label "value" ] .		
            Use MODSRDF for hierarchicalGeographic and its subelements under bf:place -->
        <madsrdf:Island>
            <xsl:call-template name="rdfsLabel"/>
        </madsrdf:Island>
    </xsl:template>
    <xsl:template match="mods:area" mode="subject">
        <!-- subject/hierarchicalGeographic/area	
            ## bf:subject [ a madsrdf:Area ; rdfs:label "value" ] .		
            Use MODSRDF for hierarchicalGeographic and its subelements under bf:place -->
        <madsrdf:Area>
            <xsl:call-template name="rdfsLabel"/>
        </madsrdf:Area>
    </xsl:template>
    <xsl:template match="mods:extraterrestrialArea" mode="subject">
        <!-- subject/hierarchicalGeographic/extraterrestrialArea	
            ## bf:subject [ a madsrdf:ExtraterrestrialArea ; rdfs:label "value" ] .		
            Use MODSRDF for hierarchicalGeographic and its subelements under bf:place -->
        <madsrdf:ExtraterrestrialArea>
            <xsl:call-template name="rdfsLabel"/>
        </madsrdf:ExtraterrestrialArea>
    </xsl:template>
    <xsl:template match="mods:cartographics" mode="Work">
        <bf:cartographicAttributes>
            <bf:Cartographic>
                <xsl:apply-templates/>
            </bf:Cartographic>
        </bf:cartographicAttributes>
    </xsl:template>
    <xsl:template match="mods:coordinates">
        <!-- subject/cartographics/coordinates ## bf:cartographicAttributes [a bf:Cartographic ; bf:coordinates "value" ] . -->
        <!-- subject/cartographics/coordinates@lang, subject/cartographics/coordinates@xml:lang, subject/cartographics/coordinates@script -->
        <bf:coordinates><xsl:sequence select="local:buildLangAttribute(.)"/><xsl:value-of select="."/></bf:coordinates>
        <xsl:call-template name="bfSource"/>
    </xsl:template>    
    <xsl:template match="mods:scale">
        <!-- subject/cartographics/scale - ## bf:scale [a bf:Scale ; rdfs:label "value" ] . -->
        <bf:scale>
            <bf:Scale>
                <xsl:call-template name="rdfsLabel"/>
                <xsl:call-template name="bfSource"/>
            </bf:Scale>
        </bf:scale>
    </xsl:template>
    <xsl:template match="mods:projection">
        <!-- subject/cartographics/projection ## bf:projection [a bf:Projection ; rdfs:label "value" ] . -->
        <bf:projection>
            <bf:Projection>
                <xsl:call-template name="rdfsLabel"/>
                <xsl:call-template name="bfSource"/>
            </bf:Projection>    
        </bf:projection>
    </xsl:template>   
    <xsl:template match="mods:geographicCode" mode="Work">
         <xsl:if test="not(preceding-sibling::*)">
            <bf:geographicCoverage>
                <xsl:variable name="code">
                    <xsl:value-of select="local:chopPunctuation(.,'-')"/>
                </xsl:variable>
                <!-- 1.2-->
                <xsl:choose>
                    <xsl:when test="@valueURI"><xsl:sequence select="local:rdfAbout(.,())"/></xsl:when>
                    <xsl:otherwise>
                        <xsl:attribute name="rdf:about"><xsl:value-of select="concat('http://id.loc.gov/vocabulary/geographicAreas/',.)"/></xsl:attribute>
                    </xsl:otherwise>
                </xsl:choose>
<!--                    <xsl:call-template name="rdfsLabel"/>-->
                    <!-- subject/geographicCode	
                            ## bf:geographicCoverage <http://id.loc.gov/vocabulary/geographicAreas/xxx>
                            subject/geographicCode@authority	
                                ## bf:source [a bf:Source ; bf:code "value" ] .
                            subject/geographicCode@authority="marcgac"	
                                ## bf:source <http://id.loc.gov/vocabulary/geographicAreas>
                            subject/geographicCode@authority="marccountry"	
                                ## bf:source <http://id.loc.gov/vocabulary/countries>
                            subject/geographicCode@authority="iso3166"	
                                ## bf:source [a bf:Source ; bf:code "iso3166" ].
                            subject/geographicCode@authorityURI	
                                ## bf:source <URI>
                        -->
                    <xsl:call-template name="bfSource">
                        <xsl:with-param name="URI">
                            <xsl:choose>
                                <xsl:when test="@authority='marcgac'">http://id.loc.gov/vocabulary/geographicAreas</xsl:when>
                                <xsl:when test="@authority='marccountry'">http://id.loc.gov/vocabulary/countries</xsl:when>
                                <xsl:when test="@authorityURI"><xsl:value-of select="@authorityURI"/></xsl:when>
                            </xsl:choose>
                        </xsl:with-param>
                    </xsl:call-template>    
                
            </bf:geographicCoverage>
        </xsl:if>
    </xsl:template>
    <xsl:template match="mods:occupation" mode="subject">
        <madsrdf:Occupation>
            <xsl:call-template name="rdfsLabel"/>
            <xsl:call-template name="bfSource"/>
        </madsrdf:Occupation>
    </xsl:template>
    
    <!-- ** classification ** -->
    <xsl:template match="mods:classification" mode="Work">
        <!-- classification -  _:w a bf:Work ; bf:classification [a bf:Classification ; rdfs:label "value" ] . -->
        <bf:classification>
            <xsl:variable name="elementName">
                <xsl:choose>
                    <xsl:when test="@authority='ddc' or @authorityURI = 'http://id.loc.gov/ontologies/bibframe/ClassificationDdc'">bf:ClassificationDdc</xsl:when>
                    <xsl:when test="@authority='lcc' or @authorityURI = 'http://id.loc.gov/ontologies/bibframe/ClassificationLcc'">bf:ClassificationLcc</xsl:when>
                    <xsl:when test="@authority='nlm' or @authorityURI = 'http://id.loc.gov/ontologies/bibframe/ClassificationNlm'">bf:ClassificationNlm</xsl:when>
                    <xsl:when test="@authority='udc' or @authorityURI = 'http://id.loc.gov/ontologies/bibframe/ClassificationUdc'">bf:ClassificationUdc</xsl:when>
                    <xsl:otherwise>bf:Classification</xsl:otherwise>
                </xsl:choose>
            </xsl:variable>
            <xsl:element name="{$elementName}">
                <xsl:sequence select="local:rdfAbout(.,())"/>
                <xsl:call-template name="rdfsLabel"/>
                <xsl:if test="@edition">
                    <!-- classification@edition	## bf:classification [a bf:ClassificationXxx ; bf:edition "value" -->
                    <bf:edition>
                        <xsl:value-of select="@edition"/>
                    </bf:edition>
                </xsl:if>
                <xsl:if test="@generator">
                    <bf:note>
                        <bf:Note>
                            <rdfs:label><xsl:value-of select="concat('generator : ',@generator)"/></rdfs:label>
                        </bf:Note>
                    </bf:note>
                </xsl:if>
                <xsl:if test="$elementName = 'bf:Classification' and @authorityURI != ''">
                    <xsl:call-template name="bfSource"/>
                </xsl:if>
            </xsl:element>
        </bf:classification>
    </xsl:template>
    
    <!-- ** relatedItem ** -->
    <xsl:template match="mods:relatedItem" mode="Work">
        <!-- relatedItem _:w1 [a bf:Work ; bf:relatedTo : _:w2] . generate new work using the current mapping  -->
        <xsl:variable name="className">
            <xsl:choose>
                <!-- relatedItem@type="constituent"	_:w1 [a bf:Work ; bf:hasPart : _:w2] .-->
                <xsl:when test="@type='constituent'">bf:hasPart</xsl:when>
                <xsl:when test="@type='host'">
                    <xsl:choose>
                        <!-- _:w1 a bf:Work ; bf:partOf _:w2 . If relatedItem@displayLabel = "Finding aid": _:w1 a bf:Work ; bf:findingAid _:w2 . -->
                        <xsl:when test="@displayLable = 'Finding aid'">bf:findingAid</xsl:when>
                        <!-- relatedItem@type="host"_:w1 [a bf:Work ; bf:partOf : _:w2] . -->
                        <xsl:otherwise>bf:partOf</xsl:otherwise>
                    </xsl:choose>
                </xsl:when>
                <!-- relatedItem@type="isReferencedBy"	_:w1 [a bf:Work ; bf:referencedBy : _:w2] . .		-->
                <xsl:when test="@type='isReferencedBy'">bf:referencedBy</xsl:when>
                <!-- relatedItem@type="preceding" _:w1 [a bf:Work ; bf:precededBy : _:w2] .  -->
                <xsl:when test="@type='preceding'">bf:precededBy</xsl:when>
                <!-- relatedItem@type="references" _:w1 [a bf:Work ; bf:references : _:w2] .-->
                <xsl:when test="@type='references'">bf:references</xsl:when>
                <!-- relatedItem@type="reviewOf" _:w2 a bf:Work ; bf:review [ a bf:Review , bf:Work ; rdf:value _:w1 ; rdfs:label "value" ] .-->
                <xsl:when test="@type='reviewOf'">bf:review</xsl:when>
                <!-- relatedItem@type="series" _:w1 [a bf:Work ; bf:hasSeries : _:w2] . -->
                <xsl:when test="@type='series'">bf:hasSeries</xsl:when>
                <!-- relatedItem@type="succeeding" _:w1 [a bf:Work ; bf:succeededBy : _:w2] .  -->
                <xsl:when test="@type='succeeding'">bf:succeededBy</xsl:when>
                <xsl:otherwise>bf:relatedTo</xsl:otherwise>
            </xsl:choose>            
        </xsl:variable>
        <xsl:choose>
            <!-- 1.2 -->
            <xsl:when test="$className = 'bf:review'">
                <bf:Work>
                    <xsl:choose>
                        <xsl:when test="@otherTypeURI">
                            <xsl:attribute name="rdf:about" select="@otherTypeURI"/>
                        </xsl:when>
                        <xsl:when test="@xlink:href"><xsl:attribute name="rdf:about" select="@xlink:href"/></xsl:when>
                        <xsl:otherwise>
                            <xsl:sequence select="local:rdfAbout(.,concat('#WorkReview-', count(preceding::*) + 1))"/>                        
                        </xsl:otherwise>
                    </xsl:choose>
                    <bf:review>
                        <bf:Review>
                            <xsl:sequence select="local:rdfAbout(.,concat('#Review-',count(preceding::*) + 1))"/>
                            <bf:Work>
                                <!-- 1.2 -->
                                <rdf:value><xsl:value-of select="concat($baseuri, local:recordURI(.), '#Work')"/></rdf:value>
                                <xsl:apply-templates select="mods:titleInfo" mode="rdfsLabel"/>
                            </bf:Work>
                        </bf:Review>
                    </bf:review>
                </bf:Work>
            </xsl:when>
            <xsl:otherwise>
                <xsl:element name="{$className}">
                    <xsl:choose>
                        <xsl:when test="$className = 'bf:review'"/>
                        <xsl:otherwise>
                            <bf:Work>
                                <xsl:choose>
                                    <xsl:when test="@otherTypeURI">
                                        <!-- relatedItem@otherTypeURI _:w1 [a bf:Work <otherTypeURI>  : work 2 ] .-->
                                        <xsl:attribute name="rdf:about" select="@otherTypeURI"/>
                                    </xsl:when>
                                    <xsl:when test="@xlink:href"><xsl:attribute name="rdf:about" select="@xlink:href"/></xsl:when>
                                    <xsl:otherwise>
                                        <xsl:sequence select="local:rdfAbout(.,concat('#Work-', count(preceding::*) + 1))"/>                        
                                    </xsl:otherwise>
                                </xsl:choose>
                                <!-- 1.2 -->
                                <xsl:choose>
                                    <xsl:when test="mods:titleInfo[@type='uniform']">
                                        <xsl:apply-templates select="mods:titleInfo[@type='uniform']" mode="rdfsLabel"/>
                                    </xsl:when>
                                    <xsl:when test="mods:titleInfo[@usage='primary']">
                                        <xsl:apply-templates select="mods:titleInfo[@usage='primary']" mode="rdfsLabel"/>
                                    </xsl:when>
                                    <xsl:otherwise>
                                        <xsl:apply-templates select="mods:titleInfo[1]" mode="rdfsLabel"/>
                                    </xsl:otherwise>
                                </xsl:choose>
                                <xsl:apply-templates mode="Work"/>
                                <xsl:apply-templates select="descendant-or-self::mods:identifier" mode="Instance"/>
                            </bf:Work>
                        </xsl:otherwise>
                    </xsl:choose>
                </xsl:element>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>
    <xsl:template match="mods:relatedItem" mode="Instance">
        <xsl:variable name="className">
            <xsl:choose>
                <!-- relatedItem@type="original" _:inst1 [a bf:Instance ; bf:originalVersionOf : _:inst2 ] . -->
                <xsl:when test="@type='original'">bf:originalVersionOf</xsl:when>
                <!-- relatedItem@type="otherFormat" _:inst1 [a bf:Instance ; bf:otherPhysicalFormat : _:inst2 ] .  -->
                <xsl:when test="@type='otherFormat'">bf:otherPhysicalFormat</xsl:when>
                <!-- otherVersion -->
            </xsl:choose>            
        </xsl:variable>
        <xsl:if test="$className != ''">
            <xsl:element name="{$className}">
                <bf:Instance>
                    <xsl:choose>
                        <xsl:when test="@otherTypeURI">
                            <!-- relatedItem@otherTypeURI	_:w1 [a bf:Work <otherTypeURI>  : work 2 ] .-->
                            <xsl:attribute name="rdf:about" select="@otherTypeURI"/>
                        </xsl:when>
                        <xsl:otherwise>
                            <xsl:sequence select="local:rdfAbout(.,concat('#Work-', count(preceding::*) + 1))"/>                        
                        </xsl:otherwise>
                    </xsl:choose>
                    <xsl:apply-templates mode="Work"/>
                    <xsl:apply-templates select="descendant-or-self::mods:identifier" mode="Instance"/>
                </bf:Instance>
            </xsl:element>            
        </xsl:if>
    </xsl:template>
    
    <!-- ** identifier ** -->
    <xsl:template match="mods:identifier" mode="Work">
        <xsl:if test="@type='issn-l'">
            <bf:identifiedBy>
                <xsl:variable name="elementName">
                    <xsl:choose>
                        <!-- identifier @ type"issn-l" _:w a bf:Work ; bf:identifiedBy [ a bf:IssnL ; rdf:value "value" ] . -->
                        <xsl:when test="@type='issn-l'">bf:IssnL</xsl:when>
                    </xsl:choose>
                </xsl:variable>
                <!-- identifier@displayLabel - ## bf:identifiedBy [ a bf:Identifier ; rdf:value "identifier value" ; bf:note [ a bf:Note ; rdfs:label "displayLabel value" ] ] . -->
                <!-- identifier@typeURI	_:Inst a bf:Instance ; bf:identifiedBy [a bf:Identifier ; bf:source <URI> ] . -->
                <xsl:element name="{$elementName}">
                    <rdf:value><xsl:value-of select="."/></rdf:value>
                    <xsl:if test="@invalid='yes'">
                        <!-- identifier @ invalid="yes"  ## bf:identifiedBy [a bf:Identifier ; bf:status [rdfs:value "invalid"]] . identifier @ invalid="yes" then Property value=invalid	 -->
                        <bf:status>
                            <bf:Status>
                                <rdfs:value>invalid</rdfs:value>                                    
                            </bf:Status>
                        </bf:status>
                    </xsl:if>
                    <xsl:if test="@displayLabel">
                        <bf:note>
                            <bf:Note>
                                <rdfs:label><xsl:value-of select="@displayLabel"/></rdfs:label>
                            </bf:Note>
                        </bf:note>
                    </xsl:if>
                    <xsl:if test="$elementName = 'bf:Identifier' and @type!= '' or @typeURI!=''">
                        <bf:source>
                            <bf:Source>
                                <xsl:if test="@typeURI">
                                    <xsl:attribute name="rdf:about" select="@typeURI"/>
                                </xsl:if>
                                <xsl:if test="@type">
                                    <bf:code><xsl:value-of select="@type"/></bf:code>                                
                                </xsl:if>
                            </bf:Source>
                        </bf:source>                    
                    </xsl:if>
                </xsl:element>
            </bf:identifiedBy> 
        </xsl:if>
    </xsl:template>
    <xsl:template match="mods:identifier" mode="Instance">
        <!-- identifier	 _:Inst a bf:Instance ; bf:identifiedBy [a bf:Identifier ; rdf:value "value" ]. -->
        <xsl:if test="@type!='issn-l' or not(@type)">
            <bf:identifiedBy>
                <xsl:variable name="elementName">
                    <xsl:choose>
                        <!-- identifier @ type="ansi" ## bf:identifiedBy [ a bf:Ansi ; rdf:value "value" ] .-->
                        <xsl:when test="@type='ansi'">bf:Ansi</xsl:when>
                        <!--  identifier @ type="doi" ## bf:identifiedBy [ a bf:Doi ; rdf:value "value" ] .	-->
                        <xsl:when test="@type='doi'">bf:Doi</xsl:when>
                        <!--identifier @ type="ean" ## bf:identifiedBy [ a bf:Ean ; rdf:value "value" ] .-->
                        <xsl:when test="@type='ean'">bf:Ean</xsl:when>
                        <!-- identifier @ type="hdl" ## bf:identifiedBy [ a bf:Hdl ; rdf:value "value" ] . -->
                        <xsl:when test="@type='hdl'">bf:Hdl</xsl:when>
                        <!-- identifier @ type="isan" ## bf:identifiedBy [ a bf:Isan ; rdf:value "value" ] . -->
                        <xsl:when test="@type='isan'">bf:Isan</xsl:when>
                        <!-- identifier @ type="isbn" ## bf:identifiedBy [ a bf:Isbn ; rdf:value "value" ] . -->
                        <xsl:when test="@type='isbn'">bf:Isbn</xsl:when>
                        <!-- identifier @ type="ismn" ## bf:identifiedBy [ a bf:Ismn ; rdf:value "value" ] . -->
                        <xsl:when test="@type='ismn'">bf:Ismn</xsl:when>
                        <!-- identifier @ type="iso" ## bf:identifiedBy [ a bf:Iso ; rdf:value "value" ] . -->
                        <xsl:when test="@type='iso'">bf:Iso</xsl:when>
                        <!-- identifier @ type="isrc" ## bf:identifiedBy [ a bf:Isrc ; rdf:value "value" ] . -->
                        <xsl:when test="@type='isrc'">bf:Isrc</xsl:when>
                        <!-- identifier @ type="issn" ## bf:identifiedBy [ a bf:Issn ; rdf:value "value" ] . -->
                        <xsl:when test="@type='issn'">bf:Issn</xsl:when>
                        <!-- identifier @ type="issue number" _:Inst a bf:Instance ; bf:identifiedBy [ a bf:IssueNumber ; rdf:value "value" ] .-->
                        <xsl:when test="@type='issue number'">bf:IssueNumber</xsl:when>
                        <!-- identifier @ type="istc" ## bf:identifiedBy [ a bf:Istc ; rdf:value "value" ] .  -->
                        <xsl:when test="@type='istc'">bf:Istc</xsl:when>
                        <!-- identifier @ type="iswc" ## bf:identifiedBy [ a bf:Iswc ; rdf:value "value" ] . -->
                        <xsl:when test="@type='iswc'">bf:Iswc</xsl:when>
                        <!-- identifier @ type="lccn" - ## bf:identifiedBy [ a bf:Lccn ; rdf:value "value" ] . -->
                        <xsl:when test="@type='lccn'">bf:Lccn</xsl:when>
                        <!--identifier @ type="local" ## bf:identifiedBy [ a bf:Local ; rdf:value "value" ] . -->
                        <xsl:when test="@type='local'">bf:Local</xsl:when>
                        <!-- identifier @ type="matrix number" ## bf:identifiedBy [ a bf:Matrixnumber ; rdf:value "value" ]. (LC identifier source code list uses matrix-number) -->
                        <xsl:when test="@type='matrix number'">bf:Matrixnumber</xsl:when>                
                        <!-- identifier @ type="music plate" ## bf:identifiedBy [ a bf:MusicPlate ; rdf:value "value" ] .(LC identifier source code list uses music-plate) -->
                        <xsl:when test="@type='music plate'">bf:MusicPlate</xsl:when>
                        <!-- identifier @ type="music publisher" ## bf:identifiedBy [ a bf:MusicPublisherNumber ; rdf:value "value" ] .
                        (LC identifier source code list uses music-publisher)  -->
                        <xsl:when test="@type='music publisher'">bf:MusicPublisherNumber</xsl:when>                
                        <!-- identifier @ type="sici" ## bf:identifiedBy [ a bf:Sici ; rdf:value "value" ] . -->
                        <xsl:when test="@type='sici'">bf:Sici</xsl:when>
                        <!-- identifier @ type="stocknumber" ## bf:identifiedBy [ a bf:StockNumber ; rdf:value "value" ]. (LC identifier source code list uses stock-number) -->
                        <xsl:when test="@type='stocknumber'">bf:StockNumber</xsl:when>                
                        <!-- identifier @ type="strn" ## bf:identifiedBy [ a bf:Strn ; rdf:value "value" ] . -->
                        <xsl:when test="@type='strn'">bf:Strn</xsl:when>
                        <!-- identifier @ type="upc" ## bf:identifiedBy [ a bf:Upc ; rdf:value "value" ] . -->
                        <xsl:when test="@type='upc'">bf:Upc</xsl:when>                
                        <!-- identifier @ type="uri" ## bf:identifiedBy [ a identifier:uri ; rdf:value 'value" ] .-->
                        <xsl:when test="@type='uri'">identifier:uri</xsl:when>
                        <!-- identifier @ type="urn" ## bf:identifiedBy [ a bf:Urn ; rdf:value "value" ] . -->
                        <xsl:when test="@type='urn'">bf:Urn</xsl:when>
                        <!-- identifier @type="coden" - ## bf:identifiedBy [ a bf:Coden ; rdf:value "value" ] .		Use with bf:Instance -->
                        <xsl:when test="@type='coden'">bf:Coden</xsl:when>
                        <!-- identifier @type="videorecording" ## bf:identifiedBy [ a bf:VideorecordingNumber ; rdf:value "value" ] .
                        (LC identifier source code list uses videorecording-identifier) -->
                        <xsl:when test="@type='videorecording'">bf:VideorecordingNumber</xsl:when>
                        <xsl:otherwise>bf:Identifier</xsl:otherwise>
                    </xsl:choose>
                </xsl:variable>
                <!-- identifier@displayLabel - ## bf:identifiedBy [ a bf:Identifier ; rdf:value "identifier value" ; bf:note [ a bf:Note ; rdfs:label "displayLabel value" ] ] . -->
                <!-- identifier@typeURI	_:Inst a bf:Instance ; bf:identifiedBy [a bf:Identifier ; bf:source <URI> ] . -->
                <xsl:element name="{$elementName}">
                    <rdf:value><xsl:value-of select="."/></rdf:value>
                    <xsl:if test="@invalid='yes'">
                        <!-- identifier @ invalid="yes"  ## bf:identifiedBy [a bf:Identifier ; bf:status [rdfs:value "invalid"]] . identifier @ invalid="yes" then Property value=invalid	 -->
                        <bf:status>
                            <bf:Status>
                                <rdfs:value>invalid</rdfs:value>                                    
                            </bf:Status>
                        </bf:status>
                    </xsl:if>
                    <xsl:if test="@displayLabel">
                        <bf:note>
                            <bf:Note>
                                <rdfs:label><xsl:value-of select="@displayLabel"/></rdfs:label>
                            </bf:Note>
                        </bf:note>
                    </xsl:if>
                    <xsl:if test="$elementName = 'bf:Identifier' and @type!= '' or @typeURI!=''">
                        <bf:source>
                            <bf:Source>
                                <xsl:if test="@typeURI">
                                    <xsl:attribute name="rdf:about" select="@typeURI"/>
                                </xsl:if>
                                <xsl:if test="@type">
                                    <bf:code><xsl:value-of select="@type"/></bf:code>                                
                                </xsl:if>
                            </bf:Source>
                        </bf:source>                    
                    </xsl:if>
                </xsl:element>
            </bf:identifiedBy> 
        </xsl:if> 
    </xsl:template>
    
    <!-- ** location ** -->
    <xsl:template match="mods:location" mode="Instance">
        <bf:hasItem>
            <bf:Item>
                <xsl:sequence select="local:rdfAbout(., concat('#location-', count(preceding::*) + 1))"></xsl:sequence>
                <bf:itemOf>
                    <xsl:sequence select="local:rdfResource(., '#Instance')"/>
                </bf:itemOf>
                <xsl:apply-templates mode="Instance"/>
            </bf:Item>
        </bf:hasItem>
    </xsl:template>
    <xsl:template match="mods:physicalLocation" mode="Instance">
        <!-- location/physicalLocation	_:I a bf:Item ; bf:heldBy [a bf:Organization ; rdfs:label "value" ] . -->    
        <!-- location/physicalLocation@type="repository" -  _:item a bf:Item ; bf:heldBy [ a bf:Organization ; rdfs:label "value" ] . -->
        <!-- location/physicalLocation@type="current" -  _:item a bf:Item ; bf:heldBy [ a bf:Organization ; rdfs:label "value" ] . -->
        <bf:heldBy>
            <bf:Organization>
                <!-- location/physicalLocation@valueURI	## bf:heldBy <URI> -->
                <xsl:sequence select="local:rdfAbout(.,())"/>
                <xsl:call-template name="rdfsLabel"/>
                <!-- location/physicalLocation@type="creation" ## bf:place [a bf:Place ; rdfs:label "value" ; bf:note [a bf:Note ; rdfs:label "creation location" ] ] . -->
                <!-- location/physicalLocation@type="discovery" ## bf:place [a bf:Place ; rdfs:label "value" ; bf:note [a bf:Note ; rdfs:label "discovery location" ] ] .-->
                <xsl:if test="@type = 'creation' or @type='discovery'">
                <bf:place>
                    <bf:Place>
                        <xsl:call-template name="rdfsLabel"/>
                        <bf:note>
                            <bf:Note>                                
                                <rdfs:label>
                                    <xsl:choose>
                                        <xsl:when test="@type = 'creation'">creation location</xsl:when>
                                        <xsl:when test="@type = 'discovery'">discovery location</xsl:when>
                                    </xsl:choose>
                                </rdfs:label>
                            </bf:Note>    
                        </bf:note>                            
                    </bf:Place>
                </bf:place>
                </xsl:if>
                <!-- location/physicalLocation@authority	bf:heldBy [a bf:Organization ; bf:source [a bf:Source ; rdf:value "value" ] ] . -->
                <!-- location/physicalLocation@authorityURI	## bf:heldBy [ a bf:Organization ; bf:source <URI> ] . -->
                <xsl:call-template name="bfSource">
                    <xsl:with-param name="valueFlag">true</xsl:with-param>
                </xsl:call-template>
            </bf:Organization>    
        </bf:heldBy>
    </xsl:template>
    <xsl:template match="mods:shelfLocator" mode="Instance">
        <!-- location/shelfLocator ## bf:shelfMark [a bf:ShelfMark ; rdfs:label "value" ] . -->
        <bf:shelfMark>
            <bf:ShelfMark>
                <xsl:call-template name="rdfsLabel"/>
            </bf:ShelfMark>
        </bf:shelfMark>
    </xsl:template>
    <xsl:template match="mods:url" mode="Instance">
        <bf:electronicLocator>
            <rdf:Resource>
                <!--location/url -  ## bf:electronicLocator [ a rdf:Resource  ; rdfs:label "value" ^^xsd:anyURI ] .-->
                <!-- location/url@displayLabel ## bf:electronicLocator [ a rdf:Resource ; rdf:value "URL" ; rdfs:label "value" ] . -->
                <xsl:choose>
                    <xsl:when test="@displayLabel">
                        <rdf:value rdf:datatype="http://www.w3.org/2001/XMLSchema#anyURI"><xsl:value-of select="."/></rdf:value>
                        <rdfs:label><xsl:value-of select="@displayLabel"/></rdfs:label>
                    </xsl:when>
                    <xsl:otherwise>
                        <xsl:call-template name="rdfsLabel">
                            <xsl:with-param name="dataType" select="'http://www.w3.org/2001/XMLSchema#anyURI'"></xsl:with-param>
                        </xsl:call-template> 
                    </xsl:otherwise>
                </xsl:choose>
                <xsl:if test="@dateLastAccessed">
                    <!-- location/url@dateLastAccessed ## bf:electronicLocator 
                        [ a rdf:Resource  ; rdfs:label "value" ^^xsd:anyURI ; 
                        bf:note [a bf:Note ; bf:noteType "date last accessed" ; 
                        rdfs:label "value"^^xsd:date ] ] . -->
                    <bf:note>
                        <bf:Note>
                            <bf:noteType>date last accessed</bf:noteType>
                            <rdfs:label rdf:datatype="http://www.w3.org/2001/XMLSchema#date"><xsl:value-of select="@dateLastAccessed"/></rdfs:label>
                        </bf:Note>
                    </bf:note>
                </xsl:if>
                <xsl:if test="@note">
                    <!-- location/url@note ## bf:electronicLocator [ a rdf:Resource ; bflc:locator <URI> ; bf:note [a bf:Note ; rdfs:label "value" ] .		There is no electronicLocator class, so a blank node must be used. The BFLC extension provides a property for the URI. -->
                    <bf:note>
                        <bf:Note>
                            <rdfs:label><xsl:value-of select="@note"/></rdfs:label>
                        </bf:Note>    
                    </bf:note>
                </xsl:if>
                <xsl:if test="@access">
                    <!-- location/url@access="preview" ## bf:electronicLocator [ a rdf:Resource ; bflc:locator <URI> ; bf:note [a bf:Note ; rdfs:label "value" ] ; bf:noteType "electronic access" ; rdfs:label "preview" ] . -->
                    <!-- location/url@access="raw object"	## bf:electronicLocator [ a rdf:Resource ; bflc:locator <URI> ; bf:note [a bf:Note ; rdfs:label "value" ] ; bf:noteType "electronic access" ; rdfs:label "raw object" ] . -->
                    <!-- location/url@access="object in context"	## bf:electronicLocator [ a rdf:Resource ; bflc:locator <URI> ; bf:note [a bf:Note rdfs:label "value" ; bf:noteType "electronic access" ; rdfs:label "object in context" ] . -->
                    <bf:note>
                        <bf:Note>
                            <bf:noteType>electronic access</bf:noteType>
                            <rdfs:label><xsl:value-of select="@access"/></rdfs:label>                                        
                        </bf:Note>    
                    </bf:note>
                </xsl:if>
                <xsl:if test="@usage">
                    <!-- location/url@usage	## bf:electronicLocator [ a rdf:Resource ; bflc:locator <URI> ; bf:note [a bf:Note rdfs:label "value" ; bf:noteType "URL usage" ] . -->
                    <!-- location/url@usage="primary display"	## bf:electronicLocator  [ a rdf:Resource ; bflc:locator <URI> ; bf:note [a bf:Note rdfs:label "value" ; bf:noteType "URL usage" ;rdfs:label "primary display" ] . -->
                    <!-- location/url@usage="primary"	## bf:electronicLocator  [ a rdf:Resource ; bflc:locator <URI> ; bf:note [a bf:Note rdfs:label "value" ; bf:noteType "URL usage" ; rdfs:label "primary" ] . -->
                    <bf:note>
                        <bf:Note>
                            <bf:noteType>URL usage</bf:noteType>
                            <rdfs:label><xsl:value-of select="@usage"/></rdfs:label>
                        </bf:Note>   
                    </bf:note>
                </xsl:if>
            </rdf:Resource>
        </bf:electronicLocator>         
    </xsl:template>
    <xsl:template match="mods:holdingSimple" mode="Instance">
        <!-- location/holdingSimple/copyInformation/form@authority	## bf:carrier [a bf:Carrier ; bf:source [a bf:Source ; rdf:value "value" ] . -->
        <!-- location/holdingSimple/copyInformation/form@authorityURI	## bf:carrier [a bf:Carrier ; bf:source <> ] . -->
        <!-- location/holdingSimple/copyInformation/form@valueURI	## bf:carrier < > . -->
        <xsl:apply-templates mode="Instance"/>
    </xsl:template> 
    <xsl:template match="mods:copyInformation" mode="Instance">
        <xsl:apply-templates mode="Instance"/>
    </xsl:template>
    <xsl:template match="mods:sublocation" mode="Instance">
        <!-- _:I a bf:Item ; bf:subLocation [ a bf:Sublocation ; rdfs:label 'value'] -->
        <bf:subLocation>
            <bf:Sublocation>
                <xsl:call-template name="rdfsLabel"/>
            </bf:Sublocation>
        </bf:subLocation>
    </xsl:template>
    <xsl:template match="mods:electronicLocator" mode="Instance">
        <!-- location/holdingSimple/copyInformation/electronicLocator	_:I a bf:Item ; bf:electronicLocator <URI> . -->
        <bf:electronicLocator>
            <rdf:Resource>
                <xsl:call-template name="rdfsLabel">
                    <xsl:with-param name="dataType" select="$dataTypeAnyURI"></xsl:with-param>
                </xsl:call-template>                
            </rdf:Resource>
        </bf:electronicLocator>
    </xsl:template>
    <xsl:template match="mods:enumerationAndChronology" mode="Instance">
        <!-- enumerationAndChronology	_:I a bf:Item ; bf:enumerationAndChronology [a bf:EnumerationAndChronology ; rdfs:label "value" ] . -->
        <bf:enumerationAndChronology>
            <bf:EnumerationAndChronology>
                <xsl:call-template name="rdfsLabel"/>
            </bf:EnumerationAndChronology>
        </bf:enumerationAndChronology>
    </xsl:template>
    <xsl:template match="mods:itemIdentifier" mode="Instance">
        <!-- itemIdentifier _:I a bf:Item ; bf:identifiedBy [a bf:Identifier ; rdf:value "value" ] .-->
        <bf:identifiedBy>
            <bf:Identifier>
                <rdf:value><xsl:value-of select="."/></rdf:value>
            </bf:Identifier>
        </bf:identifiedBy>
    </xsl:template>
    
    <!-- ** accessCondition ** -->
    <!-- 1.2  -->
    <xsl:template match="mods:accessCondition" mode="Instance">
        <!-- accessCondition [element value only, no attributes]  _:I a bf:Item ; bf:usageAndAccessPolicy [a bf:UsageAndAccessPolicy ; rdfs:label "value" ] . -->
        <!-- accessCondition@type"resriction on access" - ## bf:usageAndAccessPolicy [a bf:AccessPolicy ; rdfs:label "value" ] . -->
        <!-- accessCondition@type"use and reproduction" - ## bf:usageAndAccessPolicy [a bf:UsePolicy ; rdfs:label "value" ] . -->
        <!-- accessCondition@xlink - ## - rdfs:label content of @XLINK, Add ^^xs:anyURI after URI -->
        <bf:hasItem>
            <bf:Item>
                <xsl:sequence select="local:rdfAbout(., concat('#accessCondition-', count(preceding::*) + 1))"></xsl:sequence>
                <xsl:if test="@xlink:href">
                    <rdfs:label rdf:datatype="{$dataTypeAnyURI}"><xsl:value-of select="@xlink:href"/></rdfs:label>
                </xsl:if>
                <bf:itemOf>
                    <xsl:sequence select="local:rdfResource(., '#Instance')"/>
                </bf:itemOf> 
                    <bf:usageAndAccessPolicy>
                        <xsl:choose>
                            <xsl:when test="@type='resriction on access'">
                                <bf:AccessPolicy>
                                    <xsl:call-template name="rdfsLabel"/>
                                </bf:AccessPolicy>
                            </xsl:when>
                            <xsl:when test="@type='use and reproduction'">
                                <bf:UsePolicy>
                                    <xsl:call-template name="rdfsLabel"/>
                                </bf:UsePolicy>
                            </xsl:when>
                            <xsl:otherwise>
                                <bf:UsageAndAccessPolicy>
                                    <rdf:value><xsl:value-of select="."/></rdf:value>
                                </bf:UsageAndAccessPolicy>
                            </xsl:otherwise>
                        </xsl:choose>
                    </bf:usageAndAccessPolicy>
            </bf:Item>
        </bf:hasItem>
    </xsl:template>
    
    <!-- ** part ** -->
    <xsl:template match="mods:part" mode="Work">
        <!-- part [container element] _:w1 [a bf:Work ; bf:hasPart _:w2] . "generate new work, with each subelement using the current mapping. 
            Work 2 is the work contained within the <part> topelement, 
            work 1 should be constructed from the remaining MODS elements in the record.  -->
        <!-- part@lang part@script  part@xml:lang -->
        <xsl:choose>
            <xsl:when test="count(descendant::mods:detail) gt 1">
                <xsl:apply-templates select="mods:detail" mode="Work"/>
                <xsl:if test="child::*[not(self::mods:detail)]">
                    <bf:hasPart>
                        <bf:Work>
                            <xsl:sequence select="local:rdfAbout(.,concat('#PartWork-',count(preceding::*) + 1))"/>
                            <xsl:apply-templates select="child::*[not(self::mods:detail)]" mode="part"/>
                            <xsl:if test="@type">
                                <!--part@type _:w2 [a bf:Work ; bf:genreForm [a bf:GenreForm ; rdfs:label "value" ] ] . -->
                                <bf:genreForm>
                                    <bf:GenreForm>
                                        <rdfs:label><xsl:value-of select="@type"/></rdfs:label>
                                    </bf:GenreForm>
                                </bf:genreForm>
                            </xsl:if>
                        </bf:Work>                                
                    </bf:hasPart>
                </xsl:if>
            </xsl:when>
            <xsl:otherwise>
                <bf:hasPart>
                    <bf:Work>
                        <xsl:sequence select="local:rdfAbout(.,concat('#PartWork-',count(preceding::*) + 1))"/>
                        <xsl:apply-templates mode="part"/>
                        <xsl:if test="@type">
                            <!--part@type _:w2 [a bf:Work ; bf:genreForm [a bf:GenreForm ; rdfs:label "value" ] ] . -->
                            <bf:genreForm>
                                <bf:GenreForm>
                                    <rdfs:label><xsl:value-of select="@type"/></rdfs:label>
                                </bf:GenreForm>
                            </bf:genreForm>
                        </xsl:if>
                    </bf:Work>
                </bf:hasPart>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>
    <xsl:template match="mods:detail" mode="part">
        <xsl:apply-templates mode="part"/>
    </xsl:template>
    <xsl:template match="mods:detail" mode="Work">
        <!-- part/detail -->
        <!-- part/detail/number	## _: w2; bf:title ; bf:partNumber "value" -->
        <!-- part/detail/caption	## _w2 ; bf:title ; bf:partName "value" -->
        <!-- part/detail/title	## _:w2 ; bf:title [a bf:Title ; rdfs:label "value" ] . -->
        <xsl:if test="child::*">
            <bf:hasPart>
                <bf:Work>
                    <xsl:sequence select="local:rdfAbout(.,concat('#PartWork-',count(preceding::*) + 1))"/>
                    <xsl:apply-templates mode="part"/>
                    <xsl:if test="@type">
                        <!-- part/detail@type _:w2 [a bf:Work ; bf:genreForm [a bf:GenreForm ; rdfs:label "value" ] ] . -->
                        <bf:genreForm>
                            <bf:GenreForm>
                                <rdfs:label><xsl:value-of select="@type"/></rdfs:label>  
                            </bf:GenreForm>
                        </bf:genreForm>
                    </xsl:if>
                </bf:Work>
            </bf:hasPart>
        </xsl:if>
    </xsl:template>
    <xsl:template match="mods:title" mode="part">
        <bf:title>
            <bf:Title>
                <xsl:call-template name="rdfsLabel">
                    <xsl:with-param name="label" select="string-join((.,../mods:caption,../mods:number), ' ')"></xsl:with-param>
                </xsl:call-template>
                <bf:mainTitle><xsl:value-of select="."/></bf:mainTitle>
                <xsl:if test="../mods:caption">
                    <bf:partName><xsl:value-of select="../mods:caption"/></bf:partName>
                </xsl:if>
                <xsl:if test="../mods:number">
                    <bf:partNumber><xsl:value-of select="../mods:number"/></bf:partNumber>
                </xsl:if>
            </bf:Title>
        </bf:title>
    </xsl:template>
    <xsl:template match="mods:number" mode="part"/>
    <xsl:template match="mods:caption" mode="part"/>
    <xsl:template match="mods:date" mode="all">
        <!-- part/date ## _:w2 ; bf:date "value" ^^xsd:date -->
        <xsl:call-template name="bfDates"/>
    </xsl:template>
    <xsl:template match="mods:text" mode="part">
        <!-- part/text	## _:w2 bf:note [a bf:Note ; noteType "partText" ; rdfs:label "value" ] . -->
        <xsl:call-template name="buildNote">
            <xsl:with-param name="noteType">partText</xsl:with-param>
        </xsl:call-template>
    </xsl:template>
    <xsl:template match="mods:extent" mode="part">
        <!-- part/extent	## _:w2 ; bf:hasInstance [a bf:Instance ; bf:extent [a bf:Extent ; rdfs:label "value" ] . -->
        <bf:hasInstance>
            <bf:Instance>
                <xsl:sequence select="local:rdfAbout(.,concat('#PartInstance-',count(preceding::*) + 1))"/>
                <bf:extent>
                    <bf:Extent>
                        <xsl:call-template name="rdfsLabel">
                            <xsl:with-param name="separator">, </xsl:with-param>
                        </xsl:call-template>
                    </bf:Extent>
                </bf:extent>
            </bf:Instance>
        </bf:hasInstance>
    </xsl:template>
    
    <!-- ** recordInfo ** -->
    <xsl:template match="mods:recordInfo" mode="adminmetadata">
        <!-- recordInfo [container element]  _:W ; a bf:Work ;  bf:adminMetadata .-->
        <!-- recordInfo@lang recordInfo@script recordInfo@xml:lang --> 
        <xsl:apply-templates mode="adminmetadata"/>
    </xsl:template>
    <xsl:template match="mods:recordContentSource" mode="adminmetadata">
        <!-- recordInfo/recordContentSource  _:W ; a bf:Work ;  bf:adminMetadata [a bf:AdminMetadata ; bf:assigner [ a bf:Agent ; rdfs:label "value" ] ]
                    if intention is to convert codes to URIs for those that are up at: https://id.loc.gov/vocabulary/organizations.html -->
        <!-- recordInfo/recordContentSource@authority - ## bf:assigner [ a bf:Agent ; bf:source [ a bf:Source ; bf:code "value" ] ] . -->
        <!-- recordInfo/recordContentSource@authorityURI - ## bf:assigner [ a bf:Agent ; bf:source <URI> ] . -->
        <!-- recordInfo/recordContentSource@valueURI - ## bf:assigner <URI> . -->
        <bf:assigner>
            <bf:Agent>
                <xsl:if test="@valueURI"><xsl:sequence select="local:rdfAbout(.,())"/></xsl:if>
                <xsl:call-template name="rdfsLabel"/>        
                <xsl:call-template name="bfSource"/>
            </bf:Agent>
        </bf:assigner>
    </xsl:template>   
    <xsl:template match="mods:recodInfoNote" mode="adminmetadata">
        <!-- recordInfo/recodInfoNote _:W ; a bf:Work ;  bf:adminMetadata [a bf:AdminMetadata ; bf:note [a bf:Note ; bf:noteType "recordInfoNote" ; rdfs:label "value" ] ] . -->
        <!-- recordInfo/recodInfoNote@type ## bf:adminMetadata [a bf:AdminMetadata ; bf:note [a bf:Note ; bf:noteType "value" ; rdfs:label "value" ] ] . -->
        <!-- recordInfo/recodInfoNote@xlink - ## - rdfs:label content of @XLINK, Add ^^xs:anyURI after URI -->
        <!-- recordInfo/recodInfoNote@lang - recordInfo/recodInfoNote@xml:lang - recordInfo/recodInfoNote@script -->
        <!-- recordInfo/recodInfoNote@typeURI	## bf:adminMetadata [a bf:AdminMetadata ; bf:note [a bf:Note ; bf:source <URI> ] .
            noteType is a datatype property and cannot carry a URI -->
        <bf:note>
            <bf:Note>
                <bf:noteType>
                    <xsl:choose>
                        <xsl:when test="@type"><xsl:value-of select="@type"/></xsl:when>
                        <xsl:otherwise>recordInfoNote</xsl:otherwise>
                    </xsl:choose>
                </bf:noteType>
                <xsl:call-template name="rdfsLabel"/>
                <xsl:call-template name="bfSource">
                    <xsl:with-param name="valueFlag" select="'true'"></xsl:with-param>
                </xsl:call-template>
            </bf:Note>
        </bf:note>
    </xsl:template>
    <xsl:template match="mods:recordCreationDate | mods:recordChangeDate" mode="adminmetadata">
        <!-- recordInfo/recordCreationDate - _:W ; a bf:Work ; bf:adminMetadata [ a bf:AdminMetadata ; bf:creationDate "value" ^^xsd:date ] . -->
        <!-- recordInfo/recordCreationDate@point -->
        <!-- recordInfo/recordCreationDate@lang recordInfo/recordCreationDate@xml:lang recordInfo/recordCreationDate@script-->
        <!-- recordInfo/recordCreationDate@encoding ## ## bf:creationDate "value" ^^[encoding value]   -->
        
        <!-- recordInfo/recordChangeDate _:W ; a bf:Work ; bf:adminMetadata [ a bf:AdminMetadata ; bf:changeDate "value" ^^xsd:date ] insert / between start and end date + ^^edtf:EDTF -->
        <!-- recordInfo/recordChangeDate@encoding	## bf:changeDate "value" ^^edtf:edtf ] .		Code as edtf -->
        <!-- recordInfo/recordChangeDate@point	see note	see note	insert / between start and end date + ^^edtf:EDTF -->
        <!-- recordInfo/recordChangeDate@lang - recordInfo/recordChangeDate@xml:lang - recordInfo/recordChangeDate@script -->
        <xsl:call-template name="bfDates"/>
    </xsl:template>
    <xsl:template match="mods:recordIdentifier" mode="adminmetadata">
        <!-- recordInfo/recordIdentifier	
                _:W ; a bf:Work ; bf:adminMetadata [ a bf:AdminMetadata ; bf:identifiedBy [a bf:Local ; rdf:value "value" ] . -->
        <!-- recordInfo/recordIdentifier@source	
                ## bf:identifiedBy [ a bf:Local ; bf:source  [a bf:Source ; rdf:value "value" ] ] . -->
        <bf:identifiedBy>
            <bf:Local>
                <rdf:value><xsl:value-of select="."/></rdf:value>
                <xsl:call-template name="bfSource">
                    <xsl:with-param name="valueFlag">true</xsl:with-param>
                </xsl:call-template>
            </bf:Local>
        </bf:identifiedBy>
    </xsl:template>    
    <xsl:template match="mods:recordOrigin" mode="adminmetadata">
        <!-- recordInfo/recordOrigin - _:W ; a bf:Work ; bf:adminMetadata [ a bf:AdminMetadata ; bf:generationProcess [ a bf:GenerationProcess ; rdfs:label "value"] .--> 
        <bf:generationProcess>
            <bf:GenerationProcess>
                <xsl:call-template name="rdfsLabel"/>
            </bf:GenerationProcess>
        </bf:generationProcess>
    </xsl:template>   
    <xsl:template match="mods:languageOfCataloging" mode="adminmetadata">
        <!-- recordInfo/languageOfCataloging/languageTerm	_:W ; a bf:Work ; bf:adminMetadata [ a bf:AdminMetadata ; bf:descriptionLanguage <URI> ] . -->
        <!-- recordInfo/languageOfCataloging/languageTerm@type="text"	## bf:descriptionLanguage [a bf:Language ; rdfs:label "value" ] . -->
        <!-- recordInfo/languageOfCataloging/languageTerm@type="code"	## bf:descriptionLanguage <URI> . -->
        <!-- recordInfo/languageOfCataloging/languageTerm@authority	## bf:descriptionLanguage [a bf:Language ; bf:source [a bf:Source ; bf:code "value" ]].  -->
        <!-- recordInfo/languageOfCataloging/languageTerm@authority="iso639-2b"	## bf:descriptionLanguage [a bf:Language ; bf:source [a bf:Source ; bf:code "iso639-2b" ]]. -->
        <!-- recordInfo/languageOfCataloging/languageTerm@authority="rfc3066"	## bf:descriptionLanguage [a bf:Language ; bf:source [a bf:Source ; bf:code "rfc3066" ]]. -->
        <!-- recordInfo/languageOfCataloging/languageTerm@authority="iso639-3"	## bf:descriptionLanguage [a bf:Language ; bf:source [a bf:Source ; bf:code "iso639-3" ]]. -->
        <!-- recordInfo/languageOfCataloging/languageTerm@authority="rfc4646"	## bf:descriptionLanguage [a bf:Language ; bf:source [a bf:Source ; bf:code "rfc4646" ]]. -->
        <!-- recordInfo/languageOfCataloging/languageTerm@authorityURI	## bf:descriptionLanguage [a bf:Language ; bf:source <URI> ] . -->
        <!-- recordInfo/languageOfCataloging/languageTerm@valueURI	## bf:descriptionLanguage <URI> . -->
        <bf:descriptionLanguage>
            <bf:Language>
                <xsl:choose>
                    <xsl:when test="mods:languageTerm[@valueURI]">
                        <xsl:attribute name="rdf:about" select="mods:languageTerm/@valueURI"/>
                    </xsl:when>
                    <xsl:when test="mods:languageTerm[@type='code']">
                        <xsl:variable name="lang">
                            <xsl:value-of select="concat($languages,local:langConversion(local:langConversion(mods:languageTerm[@type='code'])))"/>    
                        </xsl:variable>
                        <xsl:attribute name="rdf:about" select="$lang"/>
                    </xsl:when>
                    <xsl:otherwise>
                        <xsl:variable name="lang">
                            <xsl:value-of select="local:langConversion(local:langConversion(mods:languageTerm[not(@type='text')]))"/>
                        </xsl:variable>
                        <xsl:choose>
                            <xsl:when test="$lang != ''">
                                <xsl:attribute name="rdf:about" select="concat($languages,$lang)"/>
                            </xsl:when>
                            <xsl:otherwise>
                                <rdfs:label><xsl:value-of select="mods:languageTerm[@type='text']"/></rdfs:label>
                            </xsl:otherwise>
                        </xsl:choose>
                    </xsl:otherwise>
                </xsl:choose>
                <xsl:for-each select="mods:languageTerm">
                    <xsl:call-template name="bfSource"/>
                </xsl:for-each>
            </bf:Language>
        </bf:descriptionLanguage>
    </xsl:template>  
    <xsl:template match="mods:descriptionStandard" mode="adminmetadata">
        <!--
            recordInfo/descriptionStandard _:W ; a bf:Work ; bf:adminMetadata [ a bf:AdminMetadata ; bf:descriptionConvention [a bf:DescriptionConvention ; bf:code "value" ] .			
            recordInfo/descriptionStandard@authority ## bf:descriptionConvention [a bf:DescriptionConvention ; bf:source [a bf:Source ; bf:code "value" ] ] .			
            recordInfo/descriptionStandard@authorityURI ## bf:descriptionConvention [a bf:DescriptionConvention ; bf:source <URI>  ] ] .			
            recordInfo/descriptionStandard@valueURI	## bf:descriptionConventions <URI> ] .			
            ## bf:descriptionConvention <uri> .		
        -->
        <bf:descriptionConvention>
            <bf:DescriptionConvention>
                <xsl:choose>
                    <xsl:when test="@valueURI">
                        <xsl:attribute name="rdf:about" select="@valueURI"/>
                    </xsl:when>
                    <xsl:otherwise>
                        <xsl:attribute name="rdf:about" select="concat($descriptionConventions,.)"/>
                        <bf:code>
                            <xsl:sequence select="local:buildLangAttribute(.)"/>
                            <xsl:value-of select="."/>
                        </bf:code>
                        <xsl:call-template name="bfSource"/>
                    </xsl:otherwise>
                </xsl:choose>
            </bf:DescriptionConvention>
        </bf:descriptionConvention>
    </xsl:template>
    
    <!-- Date templates -->
    <xsl:template match="mods:dateIssued | mods:dateIssued | mods:dateOther | mods:copyrightDate | mods:dateCreated | mods:dateValid | mods:dateModified">
        <xsl:call-template name="bfDates"/>
    </xsl:template>
    
    <xsl:template match="mods:dateCaptured">
        <bf:capture>
            <bf:Capture>
                <xsl:apply-templates select="mods:originInfo/mods:dateCaptured"/>
            </bf:Capture>    
        </bf:capture>
    </xsl:template>
    
    
    <!-- ** Helper templates ** -->
     
    <!-- Named template to output bf:note used by multiple mods elements in Instances, Items and Works -->
    <xsl:template name="buildNote">
        <xsl:param name="noteType"/>
        <bf:note>
            <bf:Note>
<!--                <xsl:sequence select="local:rdfAbout(.,())"></xsl:sequence>                        -->
                <xsl:choose>
                    <xsl:when test="$noteType != ''">
                        <bf:noteType><xsl:value-of select="$noteType"/></bf:noteType>
                    </xsl:when>
                    <xsl:when test="@type = 'language'"/>
                    <xsl:when test="not(@type) and parent::mods:copyInformation"><bf:noteType>copyNote</bf:noteType></xsl:when>
                    <xsl:otherwise>
                        <xsl:if test="@type">
                            <bf:noteType>
                                <xsl:choose>
                                    <!-- note@type="biographical/historical"  bf:noteType "biographical or historical" -->
                                    <xsl:when test="@type = 'biographical/historical'">biographical or historical</xsl:when>
                                    <!-- note@type="original version" bf:noteType "originalVersion" -->
                                    <xsl:when test="@type = 'original version'">originalVersion</xsl:when>
                                    <!--  note@type="exhibitions" bf:noteType "exhibition"  -->
                                    <xsl:when test="@type = 'exhibitions'">exhibition</xsl:when>
                                    <!-- note@type="date/sequential designation" bf:noteType "date or sequential designation"  -->
                                    <xsl:when test="@type = 'date/sequential designation'">date or sequential designation</xsl:when>
                                    <!-- note@type="citation/reference" citation or reference" -->
                                    <xsl:when test="@type = 'citation/reference'">citation or reference</xsl:when>
                                    <xsl:otherwise><xsl:value-of select="@type"/></xsl:otherwise>
                                </xsl:choose>
                            </bf:noteType>                                
                        </xsl:if>
                    </xsl:otherwise>
                </xsl:choose>
                <xsl:choose>
                    <xsl:when test="self::*/@type='code'">
                        <bf:code><xsl:value-of select="."/></bf:code>
                    </xsl:when>
                    <xsl:otherwise>
                        <xsl:call-template name="rdfsLabel"/>
                    </xsl:otherwise>
                </xsl:choose>
                <xsl:if test="@xlink:href">
                    <rdfs:label rdf:datatype="{$dataTypeAnyURI}"><xsl:value-of select="@xlink:href"/></rdfs:label>
                </xsl:if>
                <xsl:choose>
                    <xsl:when test="@typeURI">
                        <bf:source><bf:Source rdf:about="{string(@typeURI)}"/></bf:source>
                    </xsl:when>
                    <xsl:otherwise><xsl:call-template name="bfSource"/></xsl:otherwise>
                </xsl:choose>
                
            </bf:Note>
        </bf:note>
    </xsl:template>
    
    <!-- bf:adminMetadata template, add XSLT version and current date, calls all admin data -->
    <xsl:template name="adminMetadata">
        <bf:adminMetadata>
            <bf:AdminMetadata>
                <bf:generationProcess>
                    <bf:GenerationProcess>
                        <rdfs:label>MODS2BIBFRAME <xsl:value-of select="$vCurrentVersion"/></rdfs:label>
                        <bf:generationDate>
                            <xsl:attribute name="rdf:datatype"><xsl:value-of select="concat($xs,'dateTime')"/></xsl:attribute>
                            <xsl:value-of select="current-dateTime()"/>
                        </bf:generationDate>
                    </bf:GenerationProcess>
                </bf:generationProcess>
                <!-- 1.2 -->
                <xsl:apply-templates mode="adminmetadata"/>
            </bf:AdminMetadata>
        </bf:adminMetadata>
    </xsl:template>
    
    <!-- ** Named template to process originInfo dates.dateIssued, dateCreated, dateCaptured, copyrightDate, dateOther ** -->
    <xsl:template name="bfDates">
        <xsl:variable name="elementName">
            <xsl:choose>
                <xsl:when test="local-name(.) = 'dateCreated'">bf:originDate</xsl:when>
                <xsl:when test="local-name(.) = 'copyrightDate'">bf:copyrightDate</xsl:when>
                <xsl:when test="local-name(.) = 'recordChangeDate'">bf:changeDate</xsl:when>
                <xsl:when test="local-name(.) = 'recordCreationDate'">bf:creationDate</xsl:when>
                <xsl:otherwise>bf:date</xsl:otherwise>
            </xsl:choose>
        </xsl:variable>
        <xsl:variable name="datatype">
            <xsl:choose>
                <xsl:when test=". castable as xs:date">http://www.w3.org/2001/XMLSchema#date</xsl:when>
                <xsl:when test=". castable as xs:dateTime">http://www.w3.org/2001/XMLSchema#dateTime</xsl:when>
                <xsl:when test="@encoding = 'edtf'">http://id.loc.gov/datatypes/edtf</xsl:when>
                <xsl:when test="@encoding"><xsl:value-of select="@encoding"/></xsl:when>
            </xsl:choose>
        </xsl:variable>
        <xsl:choose>
            <xsl:when test="@point">
                <xsl:if test="@point='start'">
                    <!-- originInfo/$nodes@encoding - ## bf:date "value"^^<http://id.loc.gov/datatypes/edtf>		
                         code as edtf	Convert all encoded dates to EDTF encoding? 
                         ex: <bf:date rdf:datatype="http://id.loc.gov/datatypes/edtf">2004/..</bf:date>
                    -->
                    <!-- $nodes/@point - ## bf:date "value"^^<http://id.loc.gov/datatypes/edtf>		
                         insert / between start and end date + ^^edtf:EDTF -->
                    <!-- $nodes/@lang, $nodes/@xml:lang, $nodes/@script -->
                    <xsl:element name="{$elementName}">
                        <xsl:sequence select="local:buildLangAttribute(.)"/>
                        <xsl:attribute name="rdf:datatype">http://id.loc.gov/datatypes/edtf</xsl:attribute>
                        <xsl:value-of select="concat(., '/', following-sibling::*[@point = 'end'][1])"/>                        
                    </xsl:element>
                </xsl:if>
            </xsl:when>
            <xsl:otherwise>
                <xsl:element name="{$elementName}">
                    <xsl:sequence select="local:buildLangAttribute(.)"/>
                    <xsl:if test="$datatype != ''">
                        <xsl:attribute name="rdf:datatype"><xsl:value-of select="$datatype"/></xsl:attribute>
                    </xsl:if>
                    <xsl:value-of select="."/>
                </xsl:element>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>
    
    <!-- Named template for rdfs:labels -->
    <xsl:template name="rdfsLabel">
        <xsl:param name="label"/>
        <xsl:param name="dataType"/>
        <!-- separator may not need, just precomppute values in $label -->
        <xsl:param name="separator"/>
        <xsl:variable name="s1">
            <xsl:choose>
                <xsl:when test="$separator"><xsl:value-of select="$separator"/></xsl:when>
                <xsl:otherwise><xsl:text> </xsl:text></xsl:otherwise>
            </xsl:choose>
        </xsl:variable>
        <xsl:choose>
            <xsl:when test="@xlink:href">
                <rdfs:label rdf:datatype="http://www.w3.org/2001/XMLSchema#anyURI">
                    <xsl:value-of select="@xlink:href"/>
                </rdfs:label>
            </xsl:when>
            <xsl:otherwise>
                <xsl:if test="descendant-or-self::text() != '' or $label != ''">
                    <rdfs:label>
                        <xsl:sequence select="local:buildLangAttribute(.)"/>
                        <xsl:choose>
                            <xsl:when test="$dataType"><xsl:attribute name="rdf:datatype" select="$dataType"/></xsl:when>
                            <!-- 1.2 -->
                            <xsl:when test=". castable as xs:date"><xsl:attribute name="rdf:datatype">http://www.w3.org/2001/XMLSchema#date</xsl:attribute></xsl:when>
                            <xsl:when test=". castable as xs:dateTime"><xsl:attribute name="rdf:datatype">http://www.w3.org/2001/XMLSchema#dateTime</xsl:attribute></xsl:when>
                            <xsl:when test="@encoding = 'edtf'"><xsl:attribute name="rdf:datatype">http://id.loc.gov/datatypes/edtf</xsl:attribute></xsl:when>
                            <xsl:when test="@encoding"><xsl:attribute name="rdf:datatype"><xsl:value-of select="@encoding"/></xsl:attribute></xsl:when>
                        </xsl:choose>
                        <xsl:choose>
                            <xsl:when test="$label"><xsl:value-of select="normalize-space(($label))"/></xsl:when>
                            <xsl:when test="node()"><xsl:value-of select="normalize-space(string-join(node(), $s1))"/></xsl:when>
                            <xsl:otherwise><xsl:value-of select="normalize-space(string-join(descendant-or-self::text(), $s1))"/></xsl:otherwise>
                        </xsl:choose>
                    </rdfs:label>    
                </xsl:if>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>

    <!-- Named template for bf:source -->
    <xsl:template name="bfSource">
        <xsl:param name="URI"/>
        <xsl:param name="valueFlag"/>
        <xsl:param name="codeFlag"/>
        <xsl:if test="@authority or @authorityURI or @typeURI or @source">
            <!-- @authorityURI bf:source <URI> -->
            <xsl:variable name="authorityURI">
                <xsl:choose>
                    <xsl:when test="$URI">
                        <xsl:value-of select="$URI"/>
                    </xsl:when>
                    <xsl:when test="@authorityURI">
                        <xsl:value-of select="@authorityURI"/>    
                    </xsl:when>
                    <xsl:when test="@typeURI">
                        <xsl:value-of select="@typeURI"/>
                    </xsl:when>
                    <xsl:when test="starts-with(@source,'http')">
                        <xsl:value-of select="@source"/>
                    </xsl:when>
                </xsl:choose>
            </xsl:variable>
            <xsl:variable name="value">
                <xsl:choose>
                    <xsl:when test="@authority"><xsl:value-of select="@authority"/></xsl:when>
                    <xsl:when test="@source"><xsl:value-of select="@source"/></xsl:when>
                    <xsl:when test="@type='code'"><xsl:value-of select="."/></xsl:when>
                </xsl:choose>
            </xsl:variable>
            <!-- WS-2 suppress empty source -->
            <xsl:if test="$authorityURI != '' or (not(@valueURI) and $value != '')">
                <bf:source>
                    <bf:Source>
                        <xsl:if test="$authorityURI != ''">
                            <xsl:attribute name="rdf:about" select="$authorityURI"/>    
                        </xsl:if>
                        <xsl:if test="not(@valueURI) and $value != ''">
                            <xsl:choose>
                                <xsl:when test="@authority = ''"/>
                                <xsl:when test="@authority = 'marcfrequency'"/>
                                <xsl:when test="@authority = 'rdacontent'"/>
                                <xsl:when test="@authority = 'marccountry'"/>
                                <xsl:when test="$valueFlag = 'true'">
                                    <rdf:value><xsl:value-of select="$value"/></rdf:value>
                                </xsl:when>
                                <xsl:otherwise>
                                    <bf:code><xsl:value-of select="$value"/></bf:code>
                                </xsl:otherwise>
                            </xsl:choose>
                        </xsl:if>
                    </bf:Source>
                </bf:source>
            </xsl:if>
        </xsl:if>
    </xsl:template>
    
    
    <!-- Suppress all non specified elements -->
    <xsl:template match="*" mode="Instance Work adminmetadata"/>
    
    <!-- warn about other elements -->
    <xsl:template match="*">
        <xsl:message terminate="no">
            <xsl:text>WARNING: Unmatched element: </xsl:text><xsl:value-of select="name()"/>
        </xsl:message>
    </xsl:template>
</xsl:stylesheet>
<!-- Stylus Studio meta-information - (c) 2004-2005. Progress Software Corporation. All rights reserved.
<metaInformation>
<scenarios/><MapperMetaTag><MapperInfo srcSchemaPathIsRelative="yes" srcSchemaInterpretAsXML="no" destSchemaPath="" destSchemaRoot="" destSchemaPathIsRelative="yes" destSchemaInterpretAsXML="no"/><MapperBlockPosition></MapperBlockPosition><TemplateContext></TemplateContext></MapperMetaTag>
</metaInformation>
-->