-- Data marts: vistas por área temática sobre el data warehouse.
-- Son la base que usará el dashboard de la siguiente unidad.

-- Vista general desnormalizada (une la tabla de hechos con sus dimensiones)
CREATE OR REPLACE VIEW v_indicadores AS
SELECT g.clave_geo, g.nombre AS municipio, g.nivel,
       i.categoria, i.codigo_origen AS indicador, i.nombre AS nombre_indicador,
       i.unidad, i.fuente_api, t.anio, t.periodo,
       a.codigo_scian, a.descripcion AS actividad,
       f.valor, f.fecha_carga
FROM fact_indicadores f
JOIN dim_geografia g ON g.sk_geografia = f.sk_geografia
JOIN dim_indicador i ON i.sk_indicador = f.sk_indicador
JOIN dim_tiempo    t ON t.sk_tiempo    = f.sk_tiempo
JOIN dim_actividad a ON a.sk_actividad = f.sk_actividad;

CREATE OR REPLACE VIEW mart_demografia AS
SELECT * FROM v_indicadores WHERE categoria = 'Demografía' AND nivel = 'MUNICIPAL';

CREATE OR REPLACE VIEW mart_educacion AS
SELECT * FROM v_indicadores WHERE categoria = 'Educación';

CREATE OR REPLACE VIEW mart_empleo AS
SELECT * FROM v_indicadores WHERE categoria = 'Empleo';

CREATE OR REPLACE VIEW mart_salud AS
SELECT * FROM v_indicadores WHERE categoria = 'Salud';

CREATE OR REPLACE VIEW mart_vivienda AS
SELECT * FROM v_indicadores WHERE categoria = 'Vivienda y servicios';

CREATE OR REPLACE VIEW mart_tecnologia AS
SELECT * FROM v_indicadores WHERE categoria = 'Tecnología';

CREATE OR REPLACE VIEW mart_actividad_economica AS
SELECT clave_geo, municipio, codigo_scian, actividad, periodo, valor AS establecimientos
FROM v_indicadores WHERE categoria = 'Actividad económica';

-- Resumen por municipio (una fila por municipio), listo para comparar y hacer rankings
CREATE OR REPLACE VIEW mart_resumen_municipio AS
SELECT clave_geo, municipio,
       MAX(valor) FILTER (WHERE indicador = 'pobtot')              AS poblacion_total,
       MAX(valor) FILTER (WHERE indicador = 'graproes')            AS grado_promedio_escolaridad,
       MAX(valor) FILTER (WHERE indicador = 'pct_desocupacion')    AS tasa_desocupacion,
       MAX(valor) FILTER (WHERE indicador = 'pct_sin_salud')       AS pct_sin_salud,
       MAX(valor) FILTER (WHERE indicador = 'pct_viv_agua')        AS pct_viv_agua,
       MAX(valor) FILTER (WHERE indicador = 'pct_viv_drenaje')     AS pct_viv_drenaje,
       MAX(valor) FILTER (WHERE indicador = 'pct_viv_internet')    AS pct_viv_internet,
       MAX(valor) FILTER (WHERE indicador = 'pct_viv_computadora') AS pct_viv_computadora,
       SUM(valor) FILTER (WHERE indicador = 'establecimientos')    AS establecimientos
FROM v_indicadores
WHERE nivel = 'MUNICIPAL'
GROUP BY clave_geo, municipio;
