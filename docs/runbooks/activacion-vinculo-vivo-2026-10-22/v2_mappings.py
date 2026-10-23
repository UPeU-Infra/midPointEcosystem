"""Genera los mappings v2 (rango explicito) para template y PATCH. Una sola fuente de texto."""
E = {'worker': '6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e21', 'student': '6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e22',
     'alum': '6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e23'}
ITEM = {'worker': 'liveAffiliationWorker', 'student': 'liveAffiliationStudent', 'alum': 'liveAffiliationAlum'}
RN = {'student': ('R1', 'estudiantes'), 'alum': ('R2', 'egresados'), 'worker': ('R3', 'trabajadores')}
CANARIO = ['202014210', '202622500', '201610032', '201122601', '202514113', '202622704', '201811473', '45302782']

def groovy_list(names):
    return '[' + ', '.join("'%s'" % n for n in names) + ']'

def scope_line(names):
    return ("def CANARIO = %s  // vacio = todos; con nombres = SOLO esos usuarios (encendido acotado)\n"
            "if (!CANARIO.isEmpty() &amp;&amp; !(basic.stringify(focus?.name) in CANARIO)) return false\n") % groovy_list(names)

def r_mapping(k, names, lifecycle, mid=None, ns_prefix='c:'):
    tag, res = RN[k]
    p = ns_prefix
    idattr = ' id="%d"' % mid if mid else ''
    code = ("\n// RANGO (no condition): retirable el valor actual si NO hay cuenta viva de su IIA en el contexto.\n"
            "if (input == null || basic.stringify(input).trim() == '') return false\n"
            + scope_line(names) +
            "try { def gone = !midpoint.hasLinkedAccount('%s'); if (gone) log.warn('%sv2: retira {} de {} (sin cuenta viva de su IIA)', input, focus?.name); return gone } catch (Exception e) { log.warn('%sv2: hasLinkedAccount fallo en {}: {} -> no se retira', focus?.name, e.message); return false }\n"
            % (E[k], tag, tag))
    return ('<%smapping%s>\n'
            '    <%sname>%sv2-rango-retirar-%s-sin-cuenta-%s-viva</%sname>\n'
            '    <%slifecycleState>%s</%slifecycleState>\n'
            '    <%sstrength>strong</%sstrength>\n'
            '    <%sexpression><%sscript><%scode>null</%scode></%sscript></%sexpression>\n'
            '    <%starget>\n'
            '        <%spath>extension/sciback:%s</%spath>\n'
            '        <%sset>\n'
            '            <%scondition>\n'
            '                <%sscript>\n'
            '                    <%scode>%s                    </%scode>\n'
            '                </%sscript>\n'
            '            </%scondition>\n'
            '        </%sset>\n'
            '    </%starget>\n'
            '</%smapping>') % (p, idattr, p, tag, ITEM[k], res, p, p, lifecycle, p, p, p, p, p, p, p, p, p, p, p, ITEM[k], p,
                                 p, p, p, p, code, p, p, p, p, p, p)

def act_mapping(names, lifecycle, mid=None, ns_prefix='c:'):
    p = ns_prefix
    idattr = ' id="%d"' % mid if mid else ''
    code = ("\n// RANGO (no condition): retirable el DISABLED actual si hay un vinculo VIVO (item + cuenta de su IIA).\n"
            "if (input == null || !basic.stringify(input).trim().equalsIgnoreCase('disabled')) return false\n"
            + scope_line(names) +
            "def NS = 'urn:sciback:midpoint:person'\n"
            "def live = { String item, String res -&gt; def v = basic.getExtensionPropertyValue(focus, NS, item); v != null &amp;&amp; basic.stringify(v).trim() != '' &amp;&amp; midpoint.hasLinkedAccount(res) }\n"
            "try { def ok = live('liveAffiliationWorker', '%s') || live('liveAffiliationStudent', '%s') || live('liveAffiliationAlum', '%s'); if (ok) log.warn('ACTv2: limpia DISABLED de {} (vinculo vivo)', focus?.name); return ok } catch (Exception e) { log.warn('ACTv2: fallo en {}: {} -> no se limpia', focus?.name, e.message); return false }\n"
            % (E['worker'], E['student'], E['alum']))
    return ('<%smapping%s>\n'
            '    <%sname>ACTv2-rango-limpiar-disabled-si-vinculo-vivo</%sname>\n'
            '    <%slifecycleState>%s</%slifecycleState>\n'
            '    <%sstrength>strong</%sstrength>\n'
            '    <%sexpression><%sscript><%scode>null</%scode></%sscript></%sexpression>\n'
            '    <%starget>\n'
            '        <%spath>activation/administrativeStatus</%spath>\n'
            '        <%sset>\n'
            '            <%scondition>\n'
            '                <%sscript>\n'
            '                    <%scode>%s                    </%scode>\n'
            '                </%sscript>\n'
            '            </%scondition>\n'
            '        </%sset>\n'
            '    </%starget>\n'
            '</%smapping>') % (p, idattr, p, p, p, lifecycle, p, p, p, p, p, p, p, p, p, p, p, p, p, p, p, p, code, p, p, p, p, p, p)
