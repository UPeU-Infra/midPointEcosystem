# Conector Koha 1.7.1 — 28-oct-2026

Repunta el `connectorRef` del recurso Koha consolidado (`e10a539a`) de la 1.7.0 (`8c090235`) a la
1.7.1 (`51e26e79`). Qué corrige: ver el changelog `v1.7.1` de `UPeU-Infra/connector-koha`.

- `patch-connectorRef-171.xml` — aplicado el 28-oct; test connection `success`; canario de un
  usuario: las bajas de `STUDY_LEVEL`/`STUDYCYCLE` se aplican y una segunda pasada no cambia nada.
- `rollback-connectorRef-170.xml` — vuelta atrás (PATCH, nunca PUT). Los JAR no se borran.
