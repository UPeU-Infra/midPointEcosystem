package pe.upeu.connector.keycloak;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.apache.http.HttpEntity;
import org.apache.http.NameValuePair;
import org.apache.http.client.config.RequestConfig;
import org.apache.http.client.entity.UrlEncodedFormEntity;
import org.apache.http.client.methods.CloseableHttpResponse;
import org.apache.http.client.methods.HttpDelete;
import org.apache.http.client.methods.HttpGet;
import org.apache.http.client.methods.HttpPost;
import org.apache.http.client.methods.HttpPut;
import org.apache.http.entity.ContentType;
import org.apache.http.entity.StringEntity;
import org.apache.http.impl.client.CloseableHttpClient;
import org.apache.http.impl.client.HttpClients;
import org.apache.http.message.BasicNameValuePair;
import org.apache.http.util.EntityUtils;

import org.identityconnectors.common.logging.Log;
import org.identityconnectors.framework.common.exceptions.AlreadyExistsException;
import org.identityconnectors.framework.common.exceptions.ConnectorIOException;
import org.identityconnectors.framework.common.exceptions.InvalidCredentialException;
import org.identityconnectors.framework.common.exceptions.UnknownUidException;

import java.io.Closeable;
import java.io.IOException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.AtomicReference;

/**
 * HTTP client wrapper for Keycloak Admin REST API.
 * Uses Apache HttpClient with auto-refreshing OAuth2 client_credentials token.
 * All Jackson and HttpClient classes are relocated (shaded) to avoid
 * classloader conflicts with MidPoint's own RESTEasy/Jackson.
 */
public class KeycloakHttpClient implements Closeable {

    private static final Log LOG = Log.getLog(KeycloakHttpClient.class);

    private final KeycloakConfiguration config;
    private final CloseableHttpClient httpClient;
    private final ObjectMapper mapper;

    // Token state (thread-safe)
    private final AtomicReference<String> accessToken = new AtomicReference<>();
    private final AtomicLong tokenExpiresAt = new AtomicLong(0);
    private static final long TOKEN_REFRESH_MARGIN_MS = 30_000L; // refresh 30s before expiry

    public KeycloakHttpClient(KeycloakConfiguration config) {
        this.config = config;

        RequestConfig requestConfig = RequestConfig.custom()
            .setConnectTimeout(config.getConnectionTimeoutMs())
            .setSocketTimeout(config.getReadTimeoutMs())
            .setConnectionRequestTimeout(config.getConnectionTimeoutMs())
            .build();

        this.httpClient = HttpClients.custom()
            .setDefaultRequestConfig(requestConfig)
            .build();

        this.mapper = new ObjectMapper();
        // Critical: ignore unknown fields so future Keycloak versions adding
        // new fields (like "deprecated" in FeatureRepresentation) don't break us
        this.mapper.configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);
    }

    // -------------------------------------------------------------------------
    // Token management
    // -------------------------------------------------------------------------

    private synchronized String getToken() {
        long now = System.currentTimeMillis();
        if (accessToken.get() != null && now < tokenExpiresAt.get()) {
            return accessToken.get();
        }
        return refreshToken();
    }

    private String refreshToken() {
        String url = config.getServerUrl() + "/realms/" + encode(config.getRealm())
            + "/protocol/openid-connect/token";
        LOG.info("Refreshing Keycloak token from {0}", url);

        HttpPost post = new HttpPost(url);
        List<NameValuePair> params = new ArrayList<>();
        params.add(new BasicNameValuePair("grant_type", "client_credentials"));
        params.add(new BasicNameValuePair("client_id", config.getClientId()));
        params.add(new BasicNameValuePair("client_secret", config.getClearClientSecret()));

        try {
            post.setEntity(new UrlEncodedFormEntity(params, StandardCharsets.UTF_8));
            try (CloseableHttpResponse resp = httpClient.execute(post)) {
                int status = resp.getStatusLine().getStatusCode();
                String body = EntityUtils.toString(resp.getEntity(), StandardCharsets.UTF_8);
                if (status == 401 || status == 403) {
                    throw new InvalidCredentialException("Keycloak token endpoint returned " + status
                        + ": " + body);
                }
                if (status != 200) {
                    throw new ConnectorIOException("Token endpoint returned HTTP " + status + ": " + body);
                }
                Map<String, Object> json = mapper.readValue(body, new TypeReference<Map<String, Object>>() {});
                String token = (String) json.get("access_token");
                int expiresIn = json.containsKey("expires_in")
                    ? ((Number) json.get("expires_in")).intValue() : 300;
                accessToken.set(token);
                tokenExpiresAt.set(System.currentTimeMillis() + (expiresIn * 1000L) - TOKEN_REFRESH_MARGIN_MS);
                LOG.ok("Keycloak token obtained, expires_in={0}s", expiresIn);
                return token;
            }
        } catch (IOException e) {
            throw new ConnectorIOException("Failed to obtain Keycloak token: " + e.getMessage(), e);
        }
    }

    /** Force a fresh token (used in test()). */
    public void invalidateToken() {
        accessToken.set(null);
        tokenExpiresAt.set(0);
    }

    // -------------------------------------------------------------------------
    // Low-level HTTP helpers
    // -------------------------------------------------------------------------

    private String adminBase() {
        return config.getServerUrl() + "/admin/realms/" + encode(config.getRealm());
    }

    /** GET → parsed Map or List. Returns null on 404. */
    public <T> T get(String path, TypeReference<T> type) {
        HttpGet req = new HttpGet(adminBase() + path);
        req.setHeader("Authorization", "Bearer " + getToken());
        req.setHeader("Accept", "application/json");
        try (CloseableHttpResponse resp = httpClient.execute(req)) {
            int status = resp.getStatusLine().getStatusCode();
            HttpEntity entity = resp.getEntity();
            String body = entity != null ? EntityUtils.toString(entity, StandardCharsets.UTF_8) : "";
            if (status == 404) return null;
            if (status == 401) {
                // Token may have expired on server side; retry once
                invalidateToken();
                return getWithFreshToken(path, type);
            }
            if (status < 200 || status >= 300) {
                throw new ConnectorIOException("GET " + path + " returned HTTP " + status + ": " + body);
            }
            return mapper.readValue(body, type);
        } catch (IOException e) {
            throw new ConnectorIOException("GET " + path + " failed: " + e.getMessage(), e);
        }
    }

    private <T> T getWithFreshToken(String path, TypeReference<T> type) {
        HttpGet req = new HttpGet(adminBase() + path);
        req.setHeader("Authorization", "Bearer " + getToken());
        req.setHeader("Accept", "application/json");
        try (CloseableHttpResponse resp = httpClient.execute(req)) {
            int status = resp.getStatusLine().getStatusCode();
            HttpEntity entity = resp.getEntity();
            String body = entity != null ? EntityUtils.toString(entity, StandardCharsets.UTF_8) : "";
            if (status == 404) return null;
            if (status < 200 || status >= 300) {
                throw new ConnectorIOException("GET " + path + " returned HTTP " + status + ": " + body);
            }
            return mapper.readValue(body, type);
        } catch (IOException e) {
            throw new ConnectorIOException("GET " + path + " failed: " + e.getMessage(), e);
        }
    }

    /** POST JSON → Location header (for creates) or response body. */
    public String post(String path, Object body) {
        HttpPost req = new HttpPost(adminBase() + path);
        req.setHeader("Authorization", "Bearer " + getToken());
        req.setHeader("Content-Type", "application/json");
        req.setHeader("Accept", "application/json");
        try {
            req.setEntity(new StringEntity(mapper.writeValueAsString(body), ContentType.APPLICATION_JSON));
            try (CloseableHttpResponse resp = httpClient.execute(req)) {
                int status = resp.getStatusLine().getStatusCode();
                HttpEntity entity = resp.getEntity();
                String respBody = entity != null ? EntityUtils.toString(entity, StandardCharsets.UTF_8) : "";
                if (status == 401) {
                    invalidateToken();
                    return postWithFreshToken(path, body);
                }
                if (status == 409) {
                    throw new AlreadyExistsException(
                        "POST " + path + " 409 Conflict: " + respBody);
                }
                if (status < 200 || status >= 300) {
                    throw new ConnectorIOException("POST " + path + " returned HTTP " + status + ": " + respBody);
                }
                // For 201 Created, Keycloak returns Location header with the new ID
                org.apache.http.Header location = resp.getFirstHeader("Location");
                if (location != null) {
                    String loc = location.getValue();
                    return loc.substring(loc.lastIndexOf('/') + 1);
                }
                return respBody;
            }
        } catch (IOException e) {
            throw new ConnectorIOException("POST " + path + " failed: " + e.getMessage(), e);
        }
    }

    private String postWithFreshToken(String path, Object body) {
        HttpPost req = new HttpPost(adminBase() + path);
        req.setHeader("Authorization", "Bearer " + getToken());
        req.setHeader("Content-Type", "application/json");
        req.setHeader("Accept", "application/json");
        try {
            req.setEntity(new StringEntity(mapper.writeValueAsString(body), ContentType.APPLICATION_JSON));
            try (CloseableHttpResponse resp = httpClient.execute(req)) {
                int status = resp.getStatusLine().getStatusCode();
                HttpEntity entity = resp.getEntity();
                String respBody = entity != null ? EntityUtils.toString(entity, StandardCharsets.UTF_8) : "";
                if (status == 409) {
                    throw new AlreadyExistsException(
                        "POST " + path + " 409 Conflict: " + respBody);
                }
                if (status < 200 || status >= 300) {
                    throw new ConnectorIOException("POST " + path + " returned HTTP " + status + ": " + respBody);
                }
                org.apache.http.Header location = resp.getFirstHeader("Location");
                if (location != null) {
                    String loc = location.getValue();
                    return loc.substring(loc.lastIndexOf('/') + 1);
                }
                return respBody;
            }
        } catch (IOException e) {
            throw new ConnectorIOException("POST " + path + " failed: " + e.getMessage(), e);
        }
    }

    /** PUT JSON → no body expected (204). */
    public void put(String path, Object body) {
        HttpPut req = new HttpPut(adminBase() + path);
        req.setHeader("Authorization", "Bearer " + getToken());
        req.setHeader("Content-Type", "application/json");
        try {
            req.setEntity(new StringEntity(mapper.writeValueAsString(body), ContentType.APPLICATION_JSON));
            try (CloseableHttpResponse resp = httpClient.execute(req)) {
                int status = resp.getStatusLine().getStatusCode();
                if (status == 401) {
                    invalidateToken();
                    put(path, body);
                    return;
                }
                if (status == 404) {
                    throw new UnknownUidException(
                        "PUT " + path + " returned 404 — UID not found");
                }
                if (status < 200 || status >= 300) {
                    HttpEntity entity = resp.getEntity();
                    String respBody = entity != null ? EntityUtils.toString(entity, StandardCharsets.UTF_8) : "";
                    throw new ConnectorIOException("PUT " + path + " returned HTTP " + status + ": " + respBody);
                }
                EntityUtils.consume(resp.getEntity());
            }
        } catch (IOException e) {
            throw new ConnectorIOException("PUT " + path + " failed: " + e.getMessage(), e);
        }
    }

    /** DELETE — throws UnknownUidException on 404. */
    public void delete(String path) {
        HttpDelete req = new HttpDelete(adminBase() + path);
        req.setHeader("Authorization", "Bearer " + getToken());
        try (CloseableHttpResponse resp = httpClient.execute(req)) {
            int status = resp.getStatusLine().getStatusCode();
            if (status == 401) {
                invalidateToken();
                delete(path);
                return;
            }
            if (status == 404) {
                throw new org.identityconnectors.framework.common.exceptions.UnknownUidException(
                    "DELETE " + path + " returned 404 — UID not found");
            }
            if (status < 200 || status >= 300) {
                HttpEntity entity = resp.getEntity();
                String respBody = entity != null ? EntityUtils.toString(entity, StandardCharsets.UTF_8) : "";
                throw new ConnectorIOException("DELETE " + path + " returned HTTP " + status + ": " + respBody);
            }
            EntityUtils.consume(resp.getEntity());
        } catch (IOException e) {
            throw new ConnectorIOException("DELETE " + path + " failed: " + e.getMessage(), e);
        }
    }

    // -------------------------------------------------------------------------
    // Keycloak Admin API — high-level methods
    // -------------------------------------------------------------------------

    /** Test connectivity: get realm info. */
    public Map<String, Object> getRealmInfo() {
        invalidateToken(); // force fresh token on test
        return get("", new TypeReference<Map<String, Object>>() {});
    }

    /** List users with pagination. Returns empty list if none. */
    public List<Map<String, Object>> listUsers(int first, int max) {
        String path = "/users?first=" + first + "&max=" + max + "&briefRepresentation=false";
        List<Map<String, Object>> result = get(path, new TypeReference<List<Map<String, Object>>>() {});
        return result != null ? result : Collections.emptyList();
    }

    /** Count total users. */
    public int countUsers() {
        Integer count = get("/users/count", new TypeReference<Integer>() {});
        return count != null ? count : 0;
    }

    /** Get single user by Keycloak UUID. Returns null if not found. */
    public Map<String, Object> getUserById(String id) {
        return get("/users/" + encode(id), new TypeReference<Map<String, Object>>() {});
    }

    /** Search user by username (exact match). Returns null if not found. */
    public Map<String, Object> getUserByUsername(String username) {
        String path = "/users?username=" + encode(username) + "&exact=true";
        List<Map<String, Object>> list = get(path, new TypeReference<List<Map<String, Object>>>() {});
        if (list == null || list.isEmpty()) return null;
        return list.get(0);
    }

    /** Create user. Returns new Keycloak UUID. */
    public String createUser(Map<String, Object> userRep) {
        return post("/users", userRep);
    }

    /** Update user. */
    public void updateUser(String id, Map<String, Object> userRep) {
        put("/users/" + encode(id), userRep);
    }

    /** Delete user. */
    public void deleteUser(String id) {
        delete("/users/" + encode(id));
    }

    /** Reset password for user. */
    public void resetPassword(String id, String newPassword, boolean temporary) {
        ObjectNode cred = mapper.createObjectNode();
        cred.put("type", "password");
        cred.put("value", newPassword);
        cred.put("temporary", temporary);
        put("/users/" + encode(id) + "/reset-password", cred);
    }

    // -------------------------------------------------------------------------
    // Utilities
    // -------------------------------------------------------------------------

    private static String encode(String s) {
        try {
            return URLEncoder.encode(s, "UTF-8");
        } catch (Exception e) {
            return s;
        }
    }

    @Override
    public void close() {
        try {
            httpClient.close();
        } catch (IOException e) {
            LOG.warn("Error closing HttpClient: {0}", e.getMessage());
        }
    }
}
