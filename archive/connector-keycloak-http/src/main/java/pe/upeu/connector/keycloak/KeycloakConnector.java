package pe.upeu.connector.keycloak;

import com.fasterxml.jackson.core.type.TypeReference;

import org.identityconnectors.common.logging.Log;
import org.identityconnectors.common.security.GuardedString;
import org.identityconnectors.framework.common.exceptions.ConnectorException;
import org.identityconnectors.framework.common.exceptions.ConnectorIOException;
import org.identityconnectors.framework.common.exceptions.UnknownUidException;
import org.identityconnectors.framework.common.objects.*;
import org.identityconnectors.framework.common.objects.SearchResult;
import org.identityconnectors.framework.spi.SearchResultsHandler;
import org.identityconnectors.framework.common.objects.filter.AbstractFilterTranslator;
import org.identityconnectors.framework.common.objects.filter.EqualsFilter;
import org.identityconnectors.framework.common.objects.filter.FilterTranslator;
import org.identityconnectors.framework.spi.Configuration;
import org.identityconnectors.framework.spi.ConnectorClass;
import org.identityconnectors.framework.spi.PoolableConnector;
import org.identityconnectors.framework.spi.operations.*;

import java.util.*;

/**
 * ConnId connector for Keycloak Admin REST API.
 *
 * Uses Apache HttpClient (shaded) — no RESTEasy, no keycloak-admin-client.
 * Supports __ACCOUNT__ object class only.
 *
 * Attributes supported:
 *   __NAME__              = username
 *   __UID__               = Keycloak internal UUID
 *   __ENABLE__            = enabled (boolean)
 *   __PASSWORD__          = password (write-only)
 *   firstName, lastName, email
 *   Custom (stored in attributes map):
 *     primaryAffiliation, faculty, academicProgram, campus,
 *     academicPhase, institutionalIdCard, orcid, scopedAffiliation,
 *     employeeNumber, taxId, universityIdCard
 */
@ConnectorClass(
    displayNameKey = "connector.keycloak.http.display",
    configurationClass = KeycloakConfiguration.class
)
public class KeycloakConnector implements
        PoolableConnector,
        TestOp,
        SchemaOp,
        SearchOp<String>,
        CreateOp,
        UpdateDeltaOp,
        DeleteOp {

    private static final Log LOG = Log.getLog(KeycloakConnector.class);

    // Custom attribute names
    public static final String ATTR_FIRST_NAME       = "firstName";
    public static final String ATTR_LAST_NAME        = "lastName";
    public static final String ATTR_EMAIL            = "email";
    public static final String ATTR_PRIMARY_AFF      = "primaryAffiliation";
    public static final String ATTR_FACULTY          = "faculty";
    public static final String ATTR_PROGRAM          = "academicProgram";
    public static final String ATTR_CAMPUS           = "campus";
    public static final String ATTR_PHASE            = "academicPhase";
    public static final String ATTR_ID_CARD          = "institutionalIdCard";
    public static final String ATTR_ORCID            = "orcid";
    public static final String ATTR_SCOPED_AFF       = "scopedAffiliation";
    public static final String ATTR_EMPLOYEE_NUMBER  = "employeeNumber";
    public static final String ATTR_TAX_ID           = "taxId";
    public static final String ATTR_UNIV_ID_CARD     = "universityIdCard";

    // All custom attributes go into Keycloak "attributes" map
    private static final Set<String> CUSTOM_ATTRS = new HashSet<>(Arrays.asList(
        ATTR_PRIMARY_AFF, ATTR_FACULTY, ATTR_PROGRAM, ATTR_CAMPUS,
        ATTR_PHASE, ATTR_ID_CARD, ATTR_ORCID, ATTR_SCOPED_AFF,
        ATTR_EMPLOYEE_NUMBER, ATTR_TAX_ID, ATTR_UNIV_ID_CARD
    ));

    private KeycloakConfiguration config;
    private KeycloakHttpClient client;

    // -------------------------------------------------------------------------
    // Lifecycle
    // -------------------------------------------------------------------------

    @Override
    public void init(Configuration configuration) {
        this.config = (KeycloakConfiguration) configuration;
        this.config.validate();
        this.client = new KeycloakHttpClient(this.config);
        LOG.ok("KeycloakConnector initialized for {0}/realms/{1}",
            config.getServerUrl(), config.getRealm());
    }

    @Override
    public void dispose() {
        if (client != null) {
            client.close();
            client = null;
        }
    }

    @Override
    public void checkAlive() {
        // Called by the pool to verify the connector is still usable.
        // A lightweight check: just verify the token is obtainable.
        try {
            client.getRealmInfo();
        } catch (Exception e) {
            throw new ConnectorIOException("checkAlive failed: " + e.getMessage(), e);
        }
    }

    @Override
    public Configuration getConfiguration() {
        return config;
    }

    // -------------------------------------------------------------------------
    // TestOp
    // -------------------------------------------------------------------------

    @Override
    public void test() {
        LOG.info("Testing Keycloak connection to {0}/realms/{1}",
            config.getServerUrl(), config.getRealm());
        Map<String, Object> realm = client.getRealmInfo();
        if (realm == null) {
            throw new ConnectorException("Realm '" + config.getRealm()
                + "' not found at " + config.getServerUrl());
        }
        int userCount = client.countUsers();
        LOG.ok("Keycloak test OK — realm={0}, users={1}", config.getRealm(), userCount);
    }

    // -------------------------------------------------------------------------
    // SchemaOp
    // -------------------------------------------------------------------------

    @Override
    public Schema schema() {
        SchemaBuilder sb = new SchemaBuilder(KeycloakConnector.class);
        ObjectClassInfoBuilder ocb = new ObjectClassInfoBuilder();
        ocb.setType(ObjectClass.ACCOUNT_NAME);

        // __UID__ — Keycloak UUID, not creatable/updatable
        AttributeInfoBuilder uidAib = new AttributeInfoBuilder(Uid.NAME, String.class);
        uidAib.setCreateable(false);
        uidAib.setUpdateable(false);
        uidAib.setReadable(true);
        uidAib.setNativeName("id");
        ocb.addAttributeInfo(uidAib.build());

        // __NAME__ = username
        AttributeInfoBuilder nameAib = new AttributeInfoBuilder(Name.NAME, String.class);
        nameAib.setRequired(true);
        nameAib.setNativeName("username");
        ocb.addAttributeInfo(nameAib.build());

        // __ENABLE__
        ocb.addAttributeInfo(OperationalAttributeInfos.ENABLE);

        // __PASSWORD__
        ocb.addAttributeInfo(OperationalAttributeInfos.PASSWORD);

        // Standard user fields
        ocb.addAttributeInfo(AttributeInfoBuilder.build(ATTR_FIRST_NAME, String.class));
        ocb.addAttributeInfo(AttributeInfoBuilder.build(ATTR_LAST_NAME, String.class));
        ocb.addAttributeInfo(AttributeInfoBuilder.build(ATTR_EMAIL, String.class));

        // Custom attributes (stored in Keycloak user "attributes" map)
        for (String attr : CUSTOM_ATTRS) {
            ocb.addAttributeInfo(AttributeInfoBuilder.build(attr, String.class));
        }

        // Paginación
        sb.defineOperationOption(OperationOptionInfoBuilder.buildPageSize(), SearchOp.class);
        sb.defineOperationOption(OperationOptionInfoBuilder.buildPagedResultsOffset(), SearchOp.class);

        sb.defineObjectClass(ocb.build());
        return sb.build();
    }

    // -------------------------------------------------------------------------
    // SearchOp
    // -------------------------------------------------------------------------

    @Override
    public FilterTranslator<String> createFilterTranslator(ObjectClass oclass, OperationOptions options) {
        return new AbstractFilterTranslator<String>() {
            @Override
            protected String createEqualsExpression(EqualsFilter filter, boolean not) {
                if (not) return null; // can't negate in Keycloak query
                String name = filter.getAttribute().getName();
                Object val  = AttributeUtil.getSingleValue(filter.getAttribute());
                if (val == null) return null;
                // Translate ConnId attribute name to Keycloak query param
                if (Name.NAME.equals(name) || "username".equals(name)) {
                    return "username:" + val.toString();
                }
                if (ATTR_EMAIL.equals(name)) {
                    return "email:" + val.toString();
                }
                // For other attrs: fall through to client-side filtering
                return null;
            }
        };
    }

    @Override
    public void executeQuery(ObjectClass oclass, String query,
            ResultsHandler handler, OperationOptions options) {

        if (!ObjectClass.ACCOUNT.equals(oclass)) {
            throw new ConnectorException("Unsupported object class: " + oclass);
        }

        if (query != null && query.startsWith("username:")) {
            // Single user lookup by username
            String username = query.substring("username:".length());
            Map<String, Object> user = client.getUserByUsername(username);
            if (user != null) {
                handler.handle(toConnectorObject(user));
            }
            return;
        }

        // Paginated full scan
        int pageSize = options != null && options.getPageSize() != null
            ? options.getPageSize() : 100;
        int offset = options != null && options.getPagedResultsOffset() != null
            ? options.getPagedResultsOffset() - 1 : 0; // ConnId is 1-based
        if (offset < 0) offset = 0;

        if (query != null && query.startsWith("email:")) {
            // Email search via Keycloak query
            String email = query.substring("email:".length());
            List<Map<String, Object>> users = client.get(
                "/users?email=" + email + "&exact=true&briefRepresentation=false",
                new TypeReference<List<Map<String, Object>>>() {});
            if (users != null) {
                for (Map<String, Object> u : users) {
                    if (!handler.handle(toConnectorObject(u))) return;
                }
            }
            return;
        }

        // No filter — paginated list
        List<Map<String, Object>> users = client.listUsers(offset, pageSize);
        for (Map<String, Object> u : users) {
            if (!handler.handle(toConnectorObject(u))) return;
        }

        // Report SearchResult for paging
        if (handler instanceof SearchResultsHandler) {
            int total = client.countUsers();
            int remaining = Math.max(0, total - offset - users.size());
            ((SearchResultsHandler) handler).handleResult(
                new SearchResult(null, remaining, remaining == 0));
        }
    }

    // -------------------------------------------------------------------------
    // CreateOp
    // -------------------------------------------------------------------------

    @Override
    public Uid create(ObjectClass oclass, Set<Attribute> attrs, OperationOptions options) {
        if (!ObjectClass.ACCOUNT.equals(oclass)) {
            throw new ConnectorException("Unsupported object class: " + oclass);
        }

        Map<String, Object> userRep = buildUserRepresentation(attrs, true);
        LOG.info("Creating Keycloak user: {0}", userRep.get("username"));

        // Handle password separately
        GuardedString password = AttributeUtil.getPasswordValue(attrs);
        if (password != null) {
            // Password will be set after create via reset-password endpoint
        }

        String newId = client.createUser(userRep);
        LOG.ok("Created Keycloak user id={0}", newId);

        // Set password if provided
        if (password != null) {
            final StringBuilder sb = new StringBuilder();
            password.access(chars -> sb.append(new String(chars)));
            client.resetPassword(newId, sb.toString(), false);
        }

        return new Uid(newId);
    }

    // -------------------------------------------------------------------------
    // UpdateDeltaOp
    // -------------------------------------------------------------------------

    @Override
    public Set<AttributeDelta> updateDelta(ObjectClass oclass, Uid uid,
            Set<AttributeDelta> modifications, OperationOptions options) {

        if (!ObjectClass.ACCOUNT.equals(oclass)) {
            throw new ConnectorException("Unsupported object class: " + oclass);
        }

        String id = uid.getUidValue();

        // Fetch current state to do a merge (Keycloak PUT replaces the whole object)
        Map<String, Object> current = client.getUserById(id);
        if (current == null) {
            throw new UnknownUidException("User not found in Keycloak: " + id);
        }

        // Apply deltas to current representation
        for (AttributeDelta delta : modifications) {
            String name = delta.getName();

            if (OperationalAttributes.PASSWORD_NAME.equals(name)) {
                // Handle password change
                List<Object> vals = delta.getValuesToReplace();
                if (vals != null && !vals.isEmpty()) {
                    Object val = vals.get(0);
                    String clearPwd = null;
                    if (val instanceof GuardedString) {
                        StringBuilder sb = new StringBuilder();
                        ((GuardedString) val).access(chars -> sb.append(new String(chars)));
                        clearPwd = sb.toString();
                    } else if (val instanceof String) {
                        clearPwd = (String) val;
                    }
                    if (clearPwd != null) {
                        client.resetPassword(id, clearPwd, false);
                    }
                }
                continue;
            }

            if (OperationalAttributes.ENABLE_NAME.equals(name)) {
                List<Object> vals = delta.getValuesToReplace();
                if (vals != null && !vals.isEmpty()) {
                    current.put("enabled", vals.get(0));
                }
                continue;
            }

            List<Object> replace = delta.getValuesToReplace();
            Object newVal = (replace != null && !replace.isEmpty()) ? replace.get(0) : null;

            if (ATTR_FIRST_NAME.equals(name)) {
                current.put("firstName", newVal);
            } else if (ATTR_LAST_NAME.equals(name)) {
                current.put("lastName", newVal);
            } else if (ATTR_EMAIL.equals(name)) {
                current.put("email", newVal);
            } else if (Name.NAME.equals(name)) {
                current.put("username", newVal);
            } else if (CUSTOM_ATTRS.contains(name)) {
                @SuppressWarnings("unchecked")
                Map<String, Object> kcAttrs = (Map<String, Object>)
                    current.computeIfAbsent("attributes", k -> new HashMap<>());
                if (newVal != null) {
                    kcAttrs.put(name, Collections.singletonList(newVal.toString()));
                } else {
                    kcAttrs.remove(name);
                }
            }
        }

        client.updateUser(id, current);
        LOG.ok("Updated Keycloak user id={0}", id);
        return Collections.emptySet();
    }

    // -------------------------------------------------------------------------
    // DeleteOp
    // -------------------------------------------------------------------------

    @Override
    public void delete(ObjectClass oclass, Uid uid, OperationOptions options) {
        if (!ObjectClass.ACCOUNT.equals(oclass)) {
            throw new ConnectorException("Unsupported object class: " + oclass);
        }
        client.deleteUser(uid.getUidValue());
        LOG.ok("Deleted Keycloak user id={0}", uid.getUidValue());
    }

    // -------------------------------------------------------------------------
    // Internal helpers
    // -------------------------------------------------------------------------

    /** Convert a Set<Attribute> from ConnId to a Keycloak user representation map. */
    @SuppressWarnings("unchecked")
    private Map<String, Object> buildUserRepresentation(Set<Attribute> attrs, boolean forCreate) {
        Map<String, Object> rep = new HashMap<>();
        Map<String, Object> kcAttrs = new HashMap<>();

        for (Attribute attr : attrs) {
            String name = attr.getName();
            Object val  = AttributeUtil.getSingleValue(attr);

            if (Name.NAME.equals(name)) {
                rep.put("username", val);
            } else if (ATTR_FIRST_NAME.equals(name)) {
                rep.put("firstName", val);
            } else if (ATTR_LAST_NAME.equals(name)) {
                rep.put("lastName", val);
            } else if (ATTR_EMAIL.equals(name)) {
                rep.put("email", val);
                rep.put("emailVerified", true);
            } else if (OperationalAttributes.ENABLE_NAME.equals(name)) {
                rep.put("enabled", val != null ? val : true);
            } else if (OperationalAttributes.PASSWORD_NAME.equals(name)) {
                // handled separately
            } else if (CUSTOM_ATTRS.contains(name)) {
                if (val != null) {
                    // Keycloak stores custom attrs as List<String>
                    kcAttrs.put(name, Collections.singletonList(val.toString()));
                }
            }
        }

        if (!kcAttrs.isEmpty()) {
            rep.put("attributes", kcAttrs);
        }

        if (forCreate) {
            // Defaults for new accounts
            rep.putIfAbsent("enabled", true);
        }

        return rep;
    }

    /** Convert a Keycloak user map to a ConnId ConnectorObject. */
    @SuppressWarnings("unchecked")
    private ConnectorObject toConnectorObject(Map<String, Object> user) {
        ConnectorObjectBuilder builder = new ConnectorObjectBuilder();
        builder.setObjectClass(ObjectClass.ACCOUNT);

        String id       = (String) user.get("id");
        String username = (String) user.get("username");
        builder.setUid(id);
        builder.setName(username != null ? username : id);

        // Standard fields
        addStringAttr(builder, ATTR_FIRST_NAME, user.get("firstName"));
        addStringAttr(builder, ATTR_LAST_NAME,  user.get("lastName"));
        addStringAttr(builder, ATTR_EMAIL,       user.get("email"));

        // Enabled
        Object enabled = user.get("enabled");
        builder.addAttribute(AttributeBuilder.buildEnabled(
            enabled != null ? Boolean.parseBoolean(enabled.toString()) : true));

        // Custom attributes (Keycloak stores them as List<String>)
        Object rawAttrs = user.get("attributes");
        if (rawAttrs instanceof Map) {
            Map<String, Object> kcAttrs = (Map<String, Object>) rawAttrs;
            for (String customAttr : CUSTOM_ATTRS) {
                Object attrVal = kcAttrs.get(customAttr);
                if (attrVal instanceof List) {
                    List<?> list = (List<?>) attrVal;
                    if (!list.isEmpty()) {
                        builder.addAttribute(customAttr, list.get(0).toString());
                    }
                } else if (attrVal instanceof String) {
                    builder.addAttribute(customAttr, attrVal.toString());
                }
            }
        }

        return builder.build();
    }

    private void addStringAttr(ConnectorObjectBuilder builder, String name, Object value) {
        if (value != null) {
            builder.addAttribute(name, value.toString());
        }
    }
}
