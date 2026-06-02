-- Sets de "membresia viva" en Oracle LAMB (SOLO LECTURA).
-- Mismas fuentes autoritativas que los resources MidPoint estudiantes.xml / trabajadores.xml.
-- Conexion: thick mode (Instant Client) — la version de Oracle no soporta python-oracledb thin.

-- (A) ESTUDIANTES VIVOS — matricula vigente semestres 279/267. Devuelve CODIGO + NUM_DOCUMENTO.
SELECT DISTINCT pna.CODIGO, pn.NUM_DOCUMENTO
FROM MOISES.PERSONA p
JOIN MOISES.PERSONA_NATURAL pn        ON pn.ID_PERSONA = p.ID_PERSONA
JOIN MOISES.PERSONA_NATURAL_ALUMNO pna ON pna.ID_PERSONA = p.ID_PERSONA
JOIN DAVID.ACAD_ALUMNO_CONTRATO aac    ON aac.ID_PERSONA = p.ID_PERSONA
JOIN DAVID.ACAD_SEMESTRE_PROGRAMA asp  ON asp.ID_SEMESTRE_PROGRAMA = aac.ID_SEMESTRE_PROGRAMA
                                      AND asp.ID_SEMESTRE IN (279, 267)
JOIN DAVID.ACAD_ALUMNO_CONTRATO_CURSO aacc ON aacc.ID_ALUMNO_CONTRATO = aac.ID_ALUMNO_CONTRATO
JOIN DAVID.ACAD_CURSO_ALUMNO aca       ON aca.ID_CURSO_ALUMNO = aacc.ID_CURSO_ALUMNO
                                      AND aca.ESTADO = '1';

-- (B) TRABAJADORES VIVOS — contrato 7124 activo y vigente. Devuelve COD_APS + NUM_DOCUMENTO.
SELECT DISTINCT e.COD_APS, pn.NUM_DOCUMENTO
FROM ELISEO.VW_APS_EMPLEADO e
JOIN MOISES.PERSONA_NATURAL pn ON pn.ID_PERSONA = e.ID_PERSONA
WHERE e.ID_ENTIDAD = 7124
  AND e.ESTADO = 'A'
  AND (e.FEC_TERMINO IS NULL OR e.FEC_TERMINO >= SYSDATE)
  AND e.COD_APS IS NOT NULL AND TRIM(e.COD_APS) IS NOT NULL
  AND NOT REGEXP_LIKE(TRIM(e.COD_APS), '^0+$');
</content>
