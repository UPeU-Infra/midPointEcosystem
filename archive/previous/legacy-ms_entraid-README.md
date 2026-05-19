# Instalar MSGraphConnetor el Servidor de MidPoint

1. **Acceder al Contenedor de Docker**:
Primero, abre una terminal y accede a tu contenedor **`midpoint_server`**.
    
    ```bash
    docker exec -it midpoint_server /bin/bash
    ```
    

1. **Descargar el Conector**:
Descarga el conector de Azure AD desde el repositorio de GitHub de Evolveum.
    
    ```bash
    cd /opt/midpoint/var/icf-connectors
    ```
    
    Bajar de aqui:
    
    [Microsoft Entra (Former Azure) Connector - Evolveum Docs](https://docs.evolveum.com/connectors/connectors/com.evolveum.polygon.connector.msgraphapi.MSGraphConnector/)
    
    Otra opción de descarga:
    
    [Maven Repository: com.evolveum.polygon » connector-msgraph » 1.2.0.0](https://mvnrepository.com/artifact/com.evolveum.polygon/connector-msgraph/1.2.0.0)
    
    ```bash
    wget https://nexus.evolveum.com/nexus/repository/public/com/evolveum/polygon/connector-msgraph/1.2.0.0/connector-msgraph-1.2.0.0.jar
    ```
    
    Salimos del contenedor:
    
    ```bash
    exit
    ```
    
2. **Reiniciar MidPoint**:
Después de añadir el conector, es recomendable reiniciar el contenedor de MidPoint para que cargue el nuevo conector.
    
    ```bash
    docker restart midpoint_server
    ```
    

Ver si se instaló correctamente:

- Inicia sesión en la interfaz de administración de MidPoint.
- Ve a la sección Resources > New resource.
- Haz clic en From Scratch.
    
    ![Captura de pantalla 2024-05-21 a la(s) 4.48.21 p. m..png](Instalar%20MSGraphConnetor%20el%20Servidor%20de%20MidPoint%2086e72caf8f524e3f989a1dcf983fb885/Captura_de_pantalla_2024-05-21_a_la(s)_4.48.21_p._m..png)
    
- Si sale el Resource MSGraphConnetor, todo se instaló correctamente.
    
    ![Captura de pantalla 2024-05-21 a la(s) 5.28.50 p. m..png](Instalar%20MSGraphConnetor%20el%20Servidor%20de%20MidPoint%2086e72caf8f524e3f989a1dcf983fb885/Captura_de_pantalla_2024-05-21_a_la(s)_5.28.50_p._m..png)
