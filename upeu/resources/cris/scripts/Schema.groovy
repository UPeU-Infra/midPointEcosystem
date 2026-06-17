/*
 * Schema.groovy — define los object classes del resource DSpace-CRIS UPeU.
 *
 *   orgUnit  → OrgUnit  (focus=OrgType en MidPoint)
 *   person   → Person   (focus=UserType en MidPoint)
 *
 * Atributos = metadatos PerúCRIS que MidPoint emite por outbound.
 * __UID__ = uuid del item DSpace (asignado en el create); __NAME__ = identificador lógico
 * estable (legalName para OrgUnit, orcid|dni para Person) usado para upsert.
 */
import org.identityconnectors.framework.common.objects.AttributeInfoBuilder
import org.identityconnectors.framework.common.objects.ObjectClassInfoBuilder

def attr = { String n, boolean multi = false ->
    def b = new AttributeInfoBuilder(n, String.class)
    b.setMultiValued(multi); b.setCreateable(true); b.setUpdateable(true); b.setReadable(true)
    b.build()
}

// ---- OrgUnit ----
def ou = new ObjectClassInfoBuilder()
ou.setType('orgUnit')
ou.addAttributeInfo(attr('legalName'))                 // organization.legalName (= __NAME__)
ou.addAttributeInfo(attr('parentOrganizationUuid'))    // organization.parentOrganization (authority=uuid del padre)
ou.addAttributeInfo(attr('parentOrganizationName'))    // valor legible del padre
ou.addAttributeInfo(attr('tiposubunidad'))             // perucris.orgunit.tiposubunidad (URI vocab)
ou.addAttributeInfo(attr('esRaiz'))                    // 'true' solo para UPeU raíz
ou.addAttributeInfo(attr('ruc'))                       // solo raíz
builder.defineObjectClass(ou.build())

// ---- Person ----
def p = new ObjectClassInfoBuilder()
p.setType('person')
p.addAttributeInfo(attr('dcTitle'))                    // dc.title "Apellidos, Nombres" (= __NAME__ fallback)
p.addAttributeInfo(attr('givenName'))                  // person.givenName
p.addAttributeInfo(attr('familyName'))                 // person.familyName
p.addAttributeInfo(attr('email'))                      // person.email
p.addAttributeInfo(attr('orcid'))                      // person.identifier.orcid
p.addAttributeInfo(attr('dni'))                        // perucris.person.dni
p.addAttributeInfo(attr('affiliationOrgUnitUuid', true)) // uuids de OrgUnit afiliadas (place 0 = principal)
builder.defineObjectClass(p.build())
