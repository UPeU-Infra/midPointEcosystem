package pe.upeu.connector.keycloak;

import org.identityconnectors.common.security.GuardedString;
import org.identityconnectors.framework.spi.AbstractConfiguration;
import org.identityconnectors.framework.spi.ConfigurationProperty;

public class KeycloakConfiguration extends AbstractConfiguration {

    private String serverUrl = "http://localhost:8080";
    private String realm = "master";
    private String clientId = "admin-cli";
    private GuardedString clientSecret;
    private int connectionTimeoutMs = 10000;
    private int readTimeoutMs = 30000;

    @ConfigurationProperty(
        displayMessageKey = "config.serverUrl.display",
        helpMessageKey = "config.serverUrl.help",
        required = true,
        order = 1
    )
    public String getServerUrl() { return serverUrl; }
    public void setServerUrl(String serverUrl) { this.serverUrl = serverUrl; }

    @ConfigurationProperty(
        displayMessageKey = "config.realm.display",
        helpMessageKey = "config.realm.help",
        required = true,
        order = 2
    )
    public String getRealm() { return realm; }
    public void setRealm(String realm) { this.realm = realm; }

    @ConfigurationProperty(
        displayMessageKey = "config.clientId.display",
        helpMessageKey = "config.clientId.help",
        required = true,
        order = 3
    )
    public String getClientId() { return clientId; }
    public void setClientId(String clientId) { this.clientId = clientId; }

    @ConfigurationProperty(
        displayMessageKey = "config.clientSecret.display",
        helpMessageKey = "config.clientSecret.help",
        required = true,
        confidential = true,
        order = 4
    )
    public GuardedString getClientSecret() { return clientSecret; }
    public void setClientSecret(GuardedString clientSecret) { this.clientSecret = clientSecret; }

    @ConfigurationProperty(
        displayMessageKey = "config.connectionTimeoutMs.display",
        helpMessageKey = "config.connectionTimeoutMs.help",
        order = 5
    )
    public int getConnectionTimeoutMs() { return connectionTimeoutMs; }
    public void setConnectionTimeoutMs(int connectionTimeoutMs) { this.connectionTimeoutMs = connectionTimeoutMs; }

    @ConfigurationProperty(
        displayMessageKey = "config.readTimeoutMs.display",
        helpMessageKey = "config.readTimeoutMs.help",
        order = 6
    )
    public int getReadTimeoutMs() { return readTimeoutMs; }
    public void setReadTimeoutMs(int readTimeoutMs) { this.readTimeoutMs = readTimeoutMs; }

    @Override
    public void validate() {
        if (serverUrl == null || serverUrl.trim().isEmpty()) {
            throw new IllegalArgumentException("serverUrl must not be empty");
        }
        if (realm == null || realm.trim().isEmpty()) {
            throw new IllegalArgumentException("realm must not be empty");
        }
        if (clientId == null || clientId.trim().isEmpty()) {
            throw new IllegalArgumentException("clientId must not be empty");
        }
        if (clientSecret == null) {
            throw new IllegalArgumentException("clientSecret must not be null");
        }
    }

    /** Extract cleartext from GuardedString — only used inside the connector classloader. */
    public String getClearClientSecret() {
        final StringBuilder sb = new StringBuilder();
        clientSecret.access(chars -> sb.append(new String(chars)));
        return sb.toString();
    }
}
