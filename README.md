# ETL · Indicadores socioeconómicos de Valles Centrales (Oaxaca)

Proceso ETL en Python que toma los datos de las 4 APIs del proyecto, los limpia y los carga en el
data warehouse (PostgreSQL en AWS EC2) y en MongoDB.

```
APIs (INEGI, Datos México) ──► extraer.py ──► datos_crudos/*.json
                                   transformar.py ──► datos_limpios/*.csv
                                        cargar.py ──► PostgreSQL (modelo estrella + data marts) y MongoDB
```

## 1. Instalación (una sola vez)

```bash
python -m venv venv
venv\Scripts\activate            # Windows   (en Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
```

Copien `.env.ejemplo` como `.env` y pongan su token del INEGI, la IP de la instancia EC2 y la
contraseña de PostgreSQL. En el grupo de seguridad de EC2 debe estar abierto el puerto 5432 para su IP.

## 2. Ejecución

```bash
python main.py                  # todo el proceso
python extraer.py               # solo la fase de extracción
python transformar.py           # solo la transformación (usa datos_crudos/)
python cargar.py                # solo la carga (usa datos_limpios/)
python main.py --sin-extraer    # repetir transformación y carga sin volver a llamar a las APIs
python main.py --sin-mongo      # cargar solo en PostgreSQL
```

El proceso se puede repetir sin duplicar datos: las dimensiones usan `ON CONFLICT DO NOTHING` y los
hechos `ON CONFLICT DO UPDATE`.

## 3. Qué genera cada fase

| Fase | Salida | Para qué sirve en el documento / video |
| --- | --- | --- |
| Extracción | `datos_crudos/api1_…json` … `api4_censo_XXX.json` | Mostrar los **datos crudos** tal como llegan |
| Transformación | `datos_limpios/fact_indicadores.csv`, `dim_*.csv`, `censo_limpio_por_municipio.csv` | Mostrar los **datos limpios** |
| Transformación | `datos_limpios/reporte_limpieza.csv` | Cuántos registros afectó cada regla de limpieza |
| Transformación | `datos_limpios/validaciones.csv` | Inconsistencias encontradas en las fuentes |
| Carga | Tablas `dim_*` y `fact_indicadores` en PostgreSQL | **Data warehouse** |
| Carga | Vistas `mart_*` en PostgreSQL | **Data marts** (base del dashboard de la siguiente unidad) |
| Carga | Colecciones `municipios` y `datos_crudos` en MongoDB | Almacenamiento documental |

## 4. Consultas para comprobar la carga (psql o pgAdmin)

```sql
SELECT COUNT(*) FROM fact_indicadores;
SELECT * FROM mart_resumen_municipio ORDER BY poblacion_total DESC;
SELECT municipio, nombre_indicador, valor FROM mart_tecnologia WHERE indicador = 'pct_viv_internet' ORDER BY valor DESC;
```

## 5. Si una API cambia el nombre de un campo

Los datos crudos se guardan primero, así que se puede abrir el JSON, ver el nombre real del campo y
agregarlo en la función `primero(...)` correspondiente de `transformar.py`.
