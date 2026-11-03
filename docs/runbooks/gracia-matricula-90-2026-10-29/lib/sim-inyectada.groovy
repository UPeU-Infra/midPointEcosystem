// SIMULACION SIN PERSISTENCIA con configuracion INYECTADA EN MEMORIA (gracia-matricula-90).
// No escribe nada: el template y el resource e22 se leen del repo, se les aplican los PATCH en memoria y se
// entregan al clockwork (LensContext.explicitFocusTemplateOid + focusTemplate; resourceCache.rememberResource).
// La tarea corre en modo SIMULATED_* => DeltaExecution aplica los deltas solo sobre objectCurrent en memoria
// (codigo 4.10.2 executor/DeltaExecution l.482/644/826) y ClockworkAuditHelper no audita (l.89).
// Variables que inyecta sim.py: TPL_XML (lista de PATCH del template), RES_XML (lista de PATCH de e22),
// SCHEMA_XML (PATCH del schema, solo se valida que parsea), DEV (true = configuracion de desarrollo),
// RECONCILE, ROWS = [[oid, F, EFF, add217], ...] (F/EFF/add217 vacios = sin inyeccion de datos), NAMES = [F, EFF].
import com.evolveum.midpoint.model.impl.expr.SpringApplicationContextHolder as H
import com.evolveum.midpoint.model.impl.lens.ContextFactory
import com.evolveum.midpoint.model.impl.lens.Clockwork
import com.evolveum.midpoint.model.api.ModelExecuteOptions
import com.evolveum.midpoint.provisioning.api.ProvisioningService
import com.evolveum.midpoint.repo.api.RepositoryService
import com.evolveum.midpoint.schema.DeltaConvertor
import com.evolveum.midpoint.schema.TaskExecutionMode
import com.evolveum.midpoint.schema.result.OperationResult
import com.evolveum.midpoint.task.api.TaskManager
import com.evolveum.midpoint.prism.path.ItemPath
import com.evolveum.midpoint.xml.ns._public.common.api_types_3.ObjectModificationType
import com.evolveum.midpoint.xml.ns._public.common.common_3.*
import javax.xml.namespace.QName

def pc = midpoint.prismContext
def NS = 'urn:sciback:midpoint:person'
def TPL = '855caaca-68c4-4f7f-8ff8-b4e35dd7d390'
def E22 = '6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e22'
def repo = H.getBean('cacheRepositoryService', RepositoryService.class)
def prov = H.getBean(ProvisioningService.class)
def cf = H.getBean(ContextFactory.class)
def cw = H.getBean(Clockwork.class)
def sb = new StringBuilder()
def res0 = new OperationResult('g90-sim')
def task = H.getBean(TaskManager.class).createTaskInstance('g90-sim')
task.setOwner(midpoint.getPrincipal()?.getFocus()?.asPrismObject())
task.setChannel('http://midpoint.evolveum.com/xml/ns/public/common/channels-3#recompute')
task.setExecutionMode(DEV ? TaskExecutionMode.SIMULATED_DEVELOPMENT : TaskExecutionMode.SIMULATED_PRODUCTION)
sb << 'MODE=' << task.getExecutionMode() << ' persistent=' << task.getExecutionMode().isFullyPersistent() << '\n'
if (task.getExecutionMode().isFullyPersistent()) { return 'ABORT: modo persistente' }

def applyPatches = { obj, List xmls ->
  xmls.each { x ->
    def px = pc.parserFor(x); px = x.trim().startsWith('{') ? px.json() : px.xml()
    def omt = px.parseRealValue(ObjectModificationType.class)
    def mods = DeltaConvertor.toModifications(omt.getItemDelta(), obj.getDefinition())
    mods.each { it.applyTo(obj) }
  }
}
// 0) el PATCH del schema (nombres reales) parsea y se aplica sobre una COPIA en memoria
if (SCHEMA_XML) {
  try {
    def sch = repo.getObject(SchemaType.class, 'e800335c-9ca1-4a2d-b4ca-e06f6db42693', null, res0)
    def before = pc.xmlSerializer().serialize(sch)
    applyPatches(sch, [SCHEMA_XML])
    def after = pc.xmlSerializer().serialize(sch)
    sb << 'SCHEMA-PATCH: xsd:element antes=' << (before =~ /xsd:element /).size() << ' despues=' << (after =~ /xsd:element /).size()
    sb << ' studentEnrollmentLastEnd=' << after.contains('name="studentEnrollmentLastEnd"') << ' studentEnrollmentEffectiveEnd=' << after.contains('name="studentEnrollmentEffectiveEnd"') << '\n'
  } catch (Throwable t) { sb << 'SCHEMA-PATCH ERROR ' << t << '\n' }
}
// 1) template y resource en memoria
def tpl = repo.getObject(ObjectTemplateType.class, TPL, null, res0)
applyPatches(tpl, TPL_XML)
def e22 = prov.getObject(ResourceType.class, E22, null, task, res0)
applyPatches(e22, RES_XML)
e22.setUserData('com.evolveum.midpoint.schema.processor.ResourceSchema.completeSchema', null)
sb << 'TPL mappings=' << tpl.asObjectable().getMapping().size() << ' items=' << tpl.asObjectable().getItem().size() << ' | E22 patches=' << RES_XML.size() << '\n'
// verificacion: el inbound nuevo esta en el esquema refinado
try {
  def cs = com.evolveum.midpoint.schema.processor.ResourceSchemaFactory.getCompleteSchema(e22)
  def ot = cs.getObjectTypeDefinitions().find { it.getKind().toString() == 'ACCOUNT' }
  def ad = ot.findSimpleAttributeDefinition(new QName('http://midpoint.evolveum.com/xml/ns/public/resource/instance-3', 'SCHOOL_NAME'))
  sb << 'E22 SCHOOL_NAME inbounds=' << ad.getInboundMappingBeans().collect { it.getName() + ':' + it.getLifecycleState() } << '\n'
} catch (Throwable t) { sb << 'E22 schema check err ' << t << '\n' }

def ext = { o, n -> def p = o?.findProperty(ItemPath.create(UserType.F_EXTENSION, new QName(NS, n))); p?.getRealValue()?.toString() ?: '' }
def ITEMS = ['liveAffiliationStudent', 'liveAffiliationWorker', 'liveAffiliationAlum', 'terminationDateStudent', NAMES[0], NAMES[1]]
def snap = { o -> def u = o?.asObjectable(); [u?.getLifecycleState() ?: '', u?.getActivation()?.getAdministrativeStatus()?.toString() ?: '', u?.getActivation()?.getEffectiveStatus()?.toString() ?: ''] + ITEMS.collect { ext(o, it) } }
sb << 'COLS name|lc|adm|eff|217|216|215|218|F|EFF  (REAL -> NUEVO)\n'
ROWS.each { row ->
  def oid = row[0]
  def r = new OperationResult('g90-sim-user')
  try {
    def real = repo.getObject(UserType.class, oid, null, r)
    def user = real.clone()
    def inj = []
    if (row[1]) { user.findOrCreateProperty(ItemPath.create(UserType.F_EXTENSION, new QName(NS, NAMES[0]))).setRealValue(row[1]); inj << 'F' }
    if (row[2]) { user.findOrCreateProperty(ItemPath.create(UserType.F_EXTENSION, new QName(NS, NAMES[1]))).setRealValue(row[2]); inj << 'EFF' }
    if (row[3] == '1') { user.findOrCreateProperty(ItemPath.create(UserType.F_EXTENSION, new QName(NS, 'liveAffiliationStudent'))).setRealValue('student'); inj << '217' }
    def opts = ModelExecuteOptions.create()
    if (RECONCILE) opts = opts.reconcile()
    def ctx = cf.createRecomputeContext(user, opts, task, r)
    def fc = ctx.getFocusContext()
    fc.setFresh(true)
    ctx.setExplicitFocusTemplateOid(TPL)
    fc.setFocusTemplate(tpl.asObjectable())
    fc.setExpandedFocusTemplate(tpl.asObjectable())
    ctx.rememberResource(e22.asObjectable())
    cw.run(ctx, task, r)
    r.computeStatusIfUnknown()
    def nw = fc.getObjectNew()
    def a = snap(real), b = snap(nw)
    def ch = []
    a.eachWithIndex { v, i -> if (v != b[i]) ch << (['lc', 'adm', 'eff', '217', '216', '215', '218', 'F', 'EFF'][i] + ':' + v + '>' + b[i]) }
    def trig = (nw.asObjectable().getTrigger() - real.asObjectable().getTrigger()).collect { it.getTimestamp()?.toString()?.take(10) }
    def trOld = real.asObjectable().getTrigger().size(), trNew = nw.asObjectable().getTrigger().size()
    def fpaths = []
    fc.getExecutedDeltas().each { d -> d.getObjectDelta()?.getModifications()?.each { m -> fpaths << m.getPath().toString().replaceAll(/\{[^}]*\}/, '') } }
    def projs = []
    ctx.getProjectionContexts().each { p ->
      def rn = p.getResource()?.getName()?.getOrig() ?: p.getKey()?.getResourceOid()
      def mods = []
      p.getExecutedDeltas().each { d ->
        def od = d.getObjectDelta()
        if (od == null) return
        if (od.isAdd()) mods << 'ADD' else if (od.isDelete()) mods << 'DELETE' else od.getModifications().each { m -> mods << m.getPath().lastName()?.getLocalPart() + (m.getValuesToReplace() ? '=' + m.getValuesToReplace()*.getRealValue() : '') + (m.getValuesToAdd() ? '+' + m.getValuesToAdd()*.getRealValue() : '') + (m.getValuesToDelete() ? '-' + m.getValuesToDelete()*.getRealValue() : '') }
      }
      if (mods) projs << (rn + '{' + mods.unique().join(',').take(300) + '}')
    }
    sb << 'U ' << real.getName() << ' inj=' << inj << ' st=' << r.getStatus() << ' | ' << a.join('|') << ' -> ' << b.join('|') << '\n'
    sb << '   CAMBIOS=' << ch << ' TRIG+=' << trig << ' (' << trOld << '->' << trNew << ') FOCUS_PATHS=' << fpaths.unique() << '\n'
    sb << '   PROJ=' << projs << '\n'
    if (r.getStatus()?.toString() in ['FATAL_ERROR', 'PARTIAL_ERROR']) {
      def walk; walk = { x, ind -> if (x.getStatus()?.toString() in ['FATAL_ERROR', 'PARTIAL_ERROR']) sb << ind << x.getOperation() << ' ' << x.getStatus() << ' ' << (x.getMessage() ?: '').take(300) << '\n'; x.getSubresults().each { walk(it, ind + '  ') } }
      walk(r, '   ! ')
    }
  } catch (Throwable t) {
    sb << 'U ' << oid << ' EXCEPTION ' << t.getClass().getName() << ': ' << (t.getMessage() ?: '').take(500) << '\n'
  }
}
return sb.toString()
