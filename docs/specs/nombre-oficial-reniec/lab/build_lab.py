#!/usr/bin/env python3
"""Genera los objetos SOLO-LABORATORIO de E1 (nombre-oficial-reniec) a partir de los XML de PROD del repo.

- Recursos simulados con conector CSV que COPIAN LITERALMENTE los <attribute> de nombre de
  trabajadores.xml / estudiantes.xml / reniec-cache.xml (y la correlación de reniec-cache), con el
  MISMO OID que en PROD, para que la librería upeuNombreOficial (hasLinkedAccount por OID) funcione igual.
- Plantilla de laboratorio: includeRef a UserTemplate-Nombre-Oficial + copia del Bloque B (fullName)
  y del Bloque J (identityDocuments) de UserTemplate-Person-Base (versión del archivo indicado).
- Arquetipo de laboratorio que apunta a esa plantilla (solo lo llevan los usuarios de prueba).

NUNCA desplegar estos objetos en PROD: allí existen los recursos Oracle reales con esos OID.
Uso: build_lab.py <repo> <person-base.xml a usar para B y J> <dir-salida>
"""
import re, sys, pathlib
repo, pb_path, out = map(pathlib.Path, sys.argv[1:4])
out.mkdir(parents=True, exist_ok=True)

def attr_blocks(xml, refs):
    res = []
    for m in re.finditer(r'(\n[ \t]*<attribute>\s*<ref>(ri:[A-Z_]+)</ref>.*?</attribute>)', xml, re.S):
        if m.group(2) in refs:
            res.append(m.group(1))
    found = {re.search(r'<ref>(ri:[A-Z_]+)</ref>', b).group(1) for b in res}
    assert found == set(refs), (refs, found)
    return ''.join(res)

CSV_NS = 'http://midpoint.evolveum.com/xml/ns/public/connector/icf-1/bundle/com.evolveum.polygon.connector-csv/com.evolveum.polygon.connector.csv.CsvConnector'

def resource(oid, name, csv, uid, attrs, correlation, sync):
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<!-- SOLO LABORATORIO — generado por build_lab.py. NO desplegar en PROD (mismo OID que el recurso Oracle real). -->
<resource xmlns="http://midpoint.evolveum.com/xml/ns/public/common/common-3"
    xmlns:c="http://midpoint.evolveum.com/xml/ns/public/common/common-3"
    xmlns:q="http://prism.evolveum.com/xml/ns/public/query-3"
    xmlns:ri="http://midpoint.evolveum.com/xml/ns/public/resource/instance-3"
    xmlns:upeu="urn:upeu:midpoint:local"
    xmlns:sb="urn:sciback:midpoint:person"
    oid="{oid}">
    <name>{name}</name>
    <description>SOLO LABORATORIO. Simula con un CSV el recurso Oracle de PROD del mismo OID; los mappings de nombre son copia literal del XML de PROD.</description>
    <lifecycleState>active</lifecycleState>
    <connectorRef type="c:ConnectorType">
        <filter><q:text>connectorType = "com.evolveum.polygon.connector.csv.CsvConnector"</q:text></filter>
    </connectorRef>
    <connectorConfiguration xmlns:icfc="http://midpoint.evolveum.com/xml/ns/public/connector/icf-1/connector-schema-3">
        <icfc:configurationProperties xmlns:cfg="{CSV_NS}">
            <cfg:filePath>/opt/midpoint/var/e1-lab/{csv}</cfg:filePath>
            <cfg:tmpFolder>/opt/midpoint/var/e1-lab</cfg:tmpFolder>
            <cfg:encoding>utf-8</cfg:encoding>
            <cfg:fieldDelimiter>,</cfg:fieldDelimiter>
            <cfg:quote>"</cfg:quote>
            <cfg:headerExists>true</cfg:headerExists>
            <cfg:trim>true</cfg:trim>
            <cfg:uniqueAttribute>{uid}</cfg:uniqueAttribute>
            <cfg:nameAttribute>{uid}</cfg:nameAttribute>
            <cfg:readOnly>true</cfg:readOnly>
        </icfc:configurationProperties>
    </connectorConfiguration>
    <schemaHandling>
        <objectType>
            <kind>account</kind>
            <intent>default</intent>
            <default>true</default>
            <delineation><objectClass>ri:AccountObjectClass</objectClass></delineation>
            <focus><type>UserType</type></focus>
{attrs}
{correlation}
{sync}
        </objectType>
    </schemaHandling>
    <capabilities>
        <configured xmlns:cap="http://midpoint.evolveum.com/xml/ns/public/resource/capabilities-3">
            <cap:create><cap:enabled>false</cap:enabled></cap:create>
            <cap:update><cap:enabled>false</cap:enabled></cap:update>
            <cap:delete><cap:enabled>false</cap:enabled></cap:delete>
        </configured>
    </capabilities>
    <projection><assignmentPolicyEnforcement>relative</assignmentPolicyEnforcement></projection>
</resource>
'''

SYNC = '''            <synchronization>
                <reaction><situation>linked</situation><actions><synchronize/></actions></reaction>
                <reaction><situation>unlinked</situation><actions><link/></actions></reaction>
                <reaction><situation>unmatched</situation><actions/></reaction>
                <reaction><situation>deleted</situation><actions><unlink/></actions></reaction>
            </synchronization>'''

LAMB_CORR_ATTR = '''
            <attribute>
                <ref>ri:NUM_DOCUMENTO</ref>
                <inbound>
                    <name>lab-num-documento-to-lambDocNum-correlation</name>
                    <strength>strong</strength>
                    <expression><script><code>def d = (input ?: '').toString().trim(); (d ==~ /\\d{7,8}/) ? d.padLeft(8, '0') : null</code></script></expression>
                    <target><path>extension/upeu:lambDocNum</path></target>
                    <evaluationPhases><include>beforeCorrelation</include><exclude>clockwork</exclude></evaluationPhases>
                </inbound>
            </attribute>'''
LAMB_CORR = '''            <correlation><correlators><items><name>correlate-by-lambDocNum</name>
                <item><ref>extension/upeu:lambDocNum</ref></item></items></correlators></correlation>'''

lamb = repo / 'upeu/resources/oracle-lamb'
trab = (lamb / 'trabajadores.xml').read_text(encoding='utf-8')
estu = (lamb / 'estudiantes.xml').read_text(encoding='utf-8')
ren = (lamb / 'reniec-cache.xml').read_text(encoding='utf-8')

(out / 'lab-sim-trabajadores.xml').write_text(resource(
    '6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e21', 'LAB-SIM Oracle LAMB Trabajadores (CSV)', 'trabajadores.csv', 'NUM_DOCUMENTO',
    LAMB_CORR_ATTR + attr_blocks(trab, ['ri:NOMBRE', 'ri:PATERNO']), LAMB_CORR, SYNC), encoding='utf-8')
(out / 'lab-sim-estudiantes.xml').write_text(resource(
    '6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e22', 'LAB-SIM Oracle LAMB Estudiantes (CSV)', 'estudiantes.csv', 'NUM_DOCUMENTO',
    LAMB_CORR_ATTR + attr_blocks(estu, ['ri:NOMBRE', 'ri:PATERNO']), LAMB_CORR, SYNC), encoding='utf-8')
ren_corr = re.search(r'(\n[ \t]*<correlation>.*?</correlation>)', ren, re.S).group(1)
(out / 'lab-sim-reniec-cache.xml').write_text(resource(
    'c4d5e6f7-a8b9-0123-cdef-123456789abc', 'LAB-SIM Oracle LAMB RENIEC Cache (CSV)', 'reniec-cache.csv', 'NRO_DOCUMENTO',
    attr_blocks(ren, ['ri:NRO_DOCUMENTO', 'ri:CONTENT', 'ri:FECHA_REGISTRO']), ren_corr, SYNC), encoding='utf-8')

pb = pb_path.read_text(encoding='utf-8')
def item_with_mapping(name):
    for m in re.finditer(r'\n[ \t]*<item>.*?</item>', pb, re.S):
        if f'<name>{name}</name>' in m.group(0):
            return m.group(0)
    raise SystemExit('no encontrado ' + name)
B = item_with_mapping('B-fullname-from-given-family')
J = item_with_mapping('J-build-identityDocuments-from-lambDocType-lambDocNum')
(out / 'lab-template-e1.xml').write_text(f'''<?xml version="1.0" encoding="UTF-8"?>
<!-- SOLO LABORATORIO — generado por build_lab.py desde {pb_path.name}. Incluye UserTemplate-Nombre-Oficial
     (el mismo objeto que irá a PROD) + copia de los Bloques B (fullName) y J (identityDocuments). -->
<objectTemplate xmlns="http://midpoint.evolveum.com/xml/ns/public/common/common-3"
    xmlns:c="http://midpoint.evolveum.com/xml/ns/public/common/common-3"
    xmlns:sciback="urn:sciback:midpoint:person"
    xmlns:upeu="urn:upeu:midpoint:local"
    oid="6c2349f8-b015-48a7-8302-b7ff65a950a3">
    <name>LAB-UserTemplate-E1-Nombre-Oficial</name>
    <lifecycleState>active</lifecycleState>
    <includeRef oid="0943af72-231e-4aef-a0fd-7cbad1357fe7" type="c:ObjectTemplateType"/>
{B}
{J}
</objectTemplate>
''', encoding='utf-8')
(out / 'lab-archetype-e1.xml').write_text('''<?xml version="1.0" encoding="UTF-8"?>
<!-- SOLO LABORATORIO — arquetipo que aplica LAB-UserTemplate-E1-Nombre-Oficial a los usuarios de prueba. -->
<archetype xmlns="http://midpoint.evolveum.com/xml/ns/public/common/common-3"
    xmlns:c="http://midpoint.evolveum.com/xml/ns/public/common/common-3"
    oid="a793776e-98a7-4b83-91d2-bee06aa25321">
    <name>LAB-E1-Persona-Prueba</name>
    <archetypePolicy>
        <objectTemplateRef oid="6c2349f8-b015-48a7-8302-b7ff65a950a3" type="c:ObjectTemplateType"/>
    </archetypePolicy>
</archetype>
''', encoding='utf-8')
print('ok', sorted(p.name for p in out.iterdir()))
