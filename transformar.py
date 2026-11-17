"""FASE 2 - TRANSFORMACIÓN.

Lee los datos crudos, aplica las reglas de limpieza y normalización (R1 a R10)
y escribe los datos limpios en datos_limpios/ con la forma del modelo estrella.
Cada regla anota cuántos registros afectó en reporte_limpieza.csv.
"""
import json
import re
import unicodedata

import numpy as np
import pandas as pd

import config as cfg

REPORTE = []      # bitácora de reglas de limpieza
VALIDACIONES = []  # inconsistencias detectadas (se reportan, no se borran)


def anotar(regla, descripcion, afectados):
    REPORTE.append({"regla": regla, "descripcion": descripcion, "registros_afectados": int(afectados)})


def leer_crudo(nombre):
    ruta = cfg.DIR_CRUDOS / f"{nombre}.json"
    if not ruta.exists():
        return None
    return json.loads(ruta.read_text(encoding="utf-8"))["respuesta"]


def primero(d, *claves):
    """Devuelve el primer campo que exista en el diccionario (las APIs cambian nombres)."""
    for c in claves:
        if isinstance(d, dict) and c in d and d[c] is not None:
            return d[c]
    return None


def lista_registros(datos):
    """Saca la lista de registros sin importar si viene envuelta en 'datos', 'data', etc."""
    if isinstance(datos, list):
        return datos
    if isinstance(datos, dict):
        for k in ("datos", "data", "results", "resultados", "Series"):
            if k in datos:
                v = datos[k]
                return v if isinstance(v, list) else [v]
        return [datos]
    return []


# ---------- Reglas de limpieza reutilizables ----------

def limpiar_texto(s):
    """R3: quita espacios sobrantes y normaliza Unicode (conserva acentos)."""
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return None
    s = unicodedata.normalize("NFC", str(s))
    return re.sub(r"\s+", " ", s).strip()


def a_numero(serie):
    """R4: convierte a número; '*', 'N/D', vacío, etc. pasan a nulo."""
    s = serie.astype("object").map(lambda v: None if str(v).strip() in cfg.VALORES_NULOS else v)
    s = s.map(lambda v: str(v).replace(",", "") if isinstance(v, str) else v)
    return pd.to_numeric(s, errors="coerce")


def clave_mun(v):
    """R2: clave municipal a 3 dígitos con ceros a la izquierda."""
    return None if v is None else str(v).strip().split(".")[0].zfill(3)[-3:]


# ---------- Transformación por fuente ----------

def transformar_catalogo():
    crudo = leer_crudo("api1_catalogo_municipios")
    filas = []
    for r in lista_registros(crudo):
        cvegeo = primero(r, "cvegeo", "cve_geo", "CVEGEO")
        mun = clave_mun(primero(r, "cve_mun", "cve_agem", "CVE_MUN") or (str(cvegeo)[-3:] if cvegeo else None))
        filas.append({
            "clave_municipio": mun,
            "nombre": primero(r, "nomgeo", "nom_agem", "nom_mun", "NOMGEO"),
            "clave_cabecera": primero(r, "cve_cab", "CVE_CAB"),
            "pob_total_cat": primero(r, "pob_total", "pob", "POB_TOTAL"),
            "pob_fem_cat": primero(r, "pob_femenina", "pob_fem"),
            "pob_mas_cat": primero(r, "pob_masculina", "pob_mas"),
            "viviendas_cat": primero(r, "total_viviendas_habitadas", "viv"),
        })
    df = pd.DataFrame(filas)
    total = len(df)
    if df.empty:
        print("   (sin catálogo crudo: se usan los nombres de config.py)")
        df = pd.DataFrame({"clave_municipio": list(cfg.MUNICIPIOS), "nombre": list(cfg.MUNICIPIOS.values())})
    df = df[df["clave_municipio"].isin(cfg.MUNICIPIOS)].copy()
    anotar("R1", "Catálogo: se conservan solo los 15 municipios de Valles Centrales", total - len(df))
    antes = df["nombre"].copy()
    df["nombre"] = df["nombre"].map(limpiar_texto)
    anotar("R3", "Catálogo: nombres con espacios sobrantes o Unicode no normalizado", (antes != df["nombre"]).sum())
    df["clave_geo"] = cfg.CLAVE_ENTIDAD + df["clave_municipio"]
    return df


def transformar_censo():
    filas = []
    for mun in cfg.MUNICIPIOS:
        crudo = leer_crudo(f"api4_censo_{mun}")
        if crudo is None:
            continue
        reg = lista_registros(crudo)
        reg = reg[0] if reg else {}
        fila = {k.lower(): v for k, v in reg.items() if not isinstance(v, (dict, list))}
        fila["clave_municipio"] = clave_mun(fila.get("mun", mun))
        filas.append(fila)
    df = pd.DataFrame(filas)
    if df.empty:
        return df

    n = len(df)
    df = df.drop_duplicates(subset="clave_municipio")
    anotar("R5", "Censo: registros duplicados del mismo municipio", n - len(df))

    columnas = [c for c in cfg.INDICADORES_CENSO if c in df.columns]
    nulos_antes = df[columnas].isna().sum().sum()
    for c in columnas:
        df[c] = a_numero(df[c])
    anotar("R4", "Censo: valores '*', 'N/D' o vacíos convertidos a NULL",
           df[columnas].isna().sum().sum() - nulos_antes)

    negativos = (df[columnas] < 0).sum().sum()
    df[columnas] = df[columnas].mask(df[columnas] < 0)
    anotar("R6", "Censo: valores negativos (imposibles) convertidos a NULL", negativos)

    # Validaciones de consistencia (se registran, no se corrigen)
    for _, r in df.iterrows():
        geo = cfg.CLAVE_ENTIDAD + r["clave_municipio"]
        if {"pobfem", "pobmas", "pobtot"} <= set(df.columns) and pd.notna(r["pobtot"]):
            if abs((r["pobfem"] or 0) + (r["pobmas"] or 0) - r["pobtot"]) > 0:
                VALIDACIONES.append({"clave_geo": geo, "regla": "pobfem + pobmas = pobtot",
                                     "detalle": f"{r['pobfem']} + {r['pobmas']} vs {r['pobtot']}"})
        if {"pocupada", "pdesocup", "pea"} <= set(df.columns) and pd.notna(r["pea"]):
            if abs((r["pocupada"] or 0) + (r["pdesocup"] or 0) - r["pea"]) > 0:
                VALIDACIONES.append({"clave_geo": geo, "regla": "pocupada + pdesocup = pea",
                                     "detalle": f"{r['pocupada']} + {r['pdesocup']} vs {r['pea']}"})
    anotar("R6", "Censo: inconsistencias aritméticas detectadas (ver validaciones.csv)", len(VALIDACIONES))

    # R8: indicadores calculados
    calculados = 0
    for cod, (_, _, num, den, factor) in cfg.INDICADORES_CALCULADOS.items():
        if num in df.columns and den in df.columns:
            df[cod] = (df[num] / df[den].replace(0, np.nan) * factor).round(2)
            calculados += df[cod].notna().sum()
    anotar("R8", "Censo: indicadores porcentuales calculados", calculados)

    df["clave_geo"] = cfg.CLAVE_ENTIDAD + df["clave_municipio"]
    return df[["clave_geo", "clave_municipio"] + columnas +
              [c for c in cfg.INDICADORES_CALCULADOS if c in df.columns]]


def transformar_bise():
    filas = []
    for indicador in cfg.INDICADORES_BISE:
        crudo = leer_crudo(f"api2_bise_{indicador}")
        for serie in lista_registros(crudo):
            for obs in serie.get("OBSERVATIONS", []) if isinstance(serie, dict) else []:
                filas.append({"codigo_origen": indicador, "periodo": obs.get("TIME_PERIOD"),
                              "valor": obs.get("OBS_VALUE")})
    df = pd.DataFrame(filas, columns=["codigo_origen", "periodo", "valor"])
    if df.empty:
        return df
    df["valor"] = a_numero(df["valor"])
    df["periodo"] = df["periodo"].map(limpiar_texto)
    df["anio"] = pd.to_numeric(df["periodo"].str[:4], errors="coerce")
    n = len(df)
    df = df.dropna(subset=["valor", "anio"]).drop_duplicates(subset=["codigo_origen", "periodo"])
    anotar("R5", "BISE: observaciones sin valor o duplicadas eliminadas", n - len(df))
    df["anio"] = df["anio"].astype(int)
    return df


def transformar_denue():
    crudo = leer_crudo("api3_denue_sectores") or []
    filas = []
    for item in crudo:
        total = 0
        for r in lista_registros(item.get("respuesta")):
            t = primero(r, "Total", "total", "TOTAL")
            total += int(float(t)) if t not in (None, "") else 0
        filas.append({"clave_geo": item["area"], "codigo_scian": item["sector"],
                      "valor": total if item.get("respuesta") is not None else np.nan})
    df = pd.DataFrame(filas, columns=["clave_geo", "codigo_scian", "valor"])
    if df.empty:
        return df
    n = len(df)
    df = df.dropna(subset=["valor"]).drop_duplicates(subset=["clave_geo", "codigo_scian"])
    anotar("R5", "DENUE: consultas sin respuesta o duplicadas eliminadas", n - len(df))
    return df


# ---------- Construcción del modelo estrella ----------

def ejecutar():
    REPORTE.clear(); VALIDACIONES.clear()
    cfg.DIR_LIMPIOS.mkdir(exist_ok=True)
    cat, censo, bise, denue = transformar_catalogo(), transformar_censo(), transformar_bise(), transformar_denue()
    fecha_denue = pd.Timestamp.today().normalize()

    # dim_geografia: estado + 15 municipios (el nombre oficial sale del catálogo, R3)
    dim_geo = pd.concat([
        pd.DataFrame([{"clave_geo": cfg.CLAVE_ENTIDAD, "nivel": "ESTATAL", "clave_entidad": cfg.CLAVE_ENTIDAD,
                       "clave_municipio": None, "nombre": cfg.NOMBRE_ENTIDAD}]),
        cat.assign(nivel="MUNICIPAL", clave_entidad=cfg.CLAVE_ENTIDAD)[
            ["clave_geo", "nivel", "clave_entidad", "clave_municipio", "nombre"]],
    ], ignore_index=True)

    # dim_tiempo (R9: periodos homologados)
    tiempos = [{"anio": 2020, "periodo": "2020", "fecha_referencia": "2020-03-15", "tipo_referencia": "Censo 2020"}]
    if not denue.empty:
        tiempos.append({"anio": fecha_denue.year, "periodo": fecha_denue.strftime("%Y-%m"),
                        "fecha_referencia": fecha_denue.date().isoformat(), "tipo_referencia": "Consulta DENUE"})
    for _, r in bise[["anio", "periodo"]].drop_duplicates().iterrows() if not bise.empty else []:
        tiempos.append({"anio": int(r["anio"]), "periodo": r["periodo"], "fecha_referencia": None,
                        "tipo_referencia": "Serie BISE"})
    dim_tiempo = pd.DataFrame(tiempos).drop_duplicates(subset=["anio", "periodo", "tipo_referencia"])

    # dim_indicador
    ind = [{"codigo_origen": k, "nombre": v[0], "categoria": v[1], "unidad": v[2], "fuente_api": "Censo 2020 (Datos México)"}
           for k, v in cfg.INDICADORES_CENSO.items()]
    ind += [{"codigo_origen": k, "nombre": v[0], "categoria": v[1], "unidad": "Porcentaje" if k.startswith("pct") else "Índice",
             "fuente_api": "Calculado (ETL)"} for k, v in cfg.INDICADORES_CALCULADOS.items()]
    ind += [{"codigo_origen": k, "nombre": v[0], "categoria": v[1], "unidad": v[2], "fuente_api": "BISE (INEGI)"}
            for k, v in cfg.INDICADORES_BISE.items()]
    ind += [{"codigo_origen": "establecimientos", "nombre": "Número de establecimientos", "categoria": "Actividad económica",
             "unidad": "Establecimientos", "fuente_api": "DENUE (INEGI)"}]
    dim_ind = pd.DataFrame(ind)

    # dim_actividad (R10: fila "No aplica" para hechos que no son económicos)
    dim_act = pd.DataFrame(
        [{"codigo_scian": cfg.ACTIVIDAD_NO_APLICA[0], "nivel_scian": "N/A", "descripcion": cfg.ACTIVIDAD_NO_APLICA[1], "codigo_padre": None}] +
        [{"codigo_scian": k, "nivel_scian": "Sector", "descripcion": v, "codigo_padre": None} for k, v in cfg.SECTORES_SCIAN.items()])

    # fact_indicadores (R7: de formato ancho a formato largo)
    hechos = []
    if not censo.empty:
        codigos = [c for c in censo.columns if c not in ("clave_geo", "clave_municipio")]
        largo = censo.melt(id_vars="clave_geo", value_vars=codigos, var_name="codigo_origen", value_name="valor")
        largo["fuente_api"] = np.where(largo["codigo_origen"].isin(cfg.INDICADORES_CALCULADOS),
                                       "Calculado (ETL)", "Censo 2020 (Datos México)")
        largo = largo.assign(anio=2020, periodo="2020", tipo_referencia="Censo 2020", codigo_scian=cfg.ACTIVIDAD_NO_APLICA[0])
        anotar("R7", "Censo: columnas convertidas a filas (formato largo) para la tabla de hechos", len(largo))
        hechos.append(largo)
    if not bise.empty:
        hechos.append(bise.assign(clave_geo=cfg.CLAVE_ENTIDAD, fuente_api="BISE (INEGI)", tipo_referencia="Serie BISE",
                                  codigo_scian=cfg.ACTIVIDAD_NO_APLICA[0])[
            ["clave_geo", "codigo_origen", "valor", "fuente_api", "anio", "periodo", "tipo_referencia", "codigo_scian"]])
    if not denue.empty:
        hechos.append(denue.assign(codigo_origen="establecimientos", fuente_api="DENUE (INEGI)", anio=fecha_denue.year,
                                   periodo=fecha_denue.strftime("%Y-%m"), tipo_referencia="Consulta DENUE"))
    fact = pd.concat(hechos, ignore_index=True) if hechos else pd.DataFrame()
    if not fact.empty:
        n = len(fact)
        fact = fact.dropna(subset=["valor"])
        anotar("R4", "Hechos: filas sin valor (NULL) que no se cargan", n - len(fact))
        clave = ["clave_geo", "codigo_origen", "fuente_api", "anio", "periodo", "tipo_referencia", "codigo_scian"]
        n = len(fact)
        fact = fact.drop_duplicates(subset=clave)
        anotar("R5", "Hechos: duplicados por (municipio, indicador, periodo, actividad)", n - len(fact))
        fact = fact[clave + ["valor"]]

    salidas = {"dim_geografia": dim_geo, "dim_tiempo": dim_tiempo, "dim_indicador": dim_ind,
               "dim_actividad": dim_act, "fact_indicadores": fact, "censo_limpio_por_municipio": censo,
               "reporte_limpieza": pd.DataFrame(REPORTE), "validaciones": pd.DataFrame(VALIDACIONES, columns=["clave_geo", "regla", "detalle"])}
    for nombre, df in salidas.items():
        df.to_csv(cfg.DIR_LIMPIOS / f"{nombre}.csv", index=False, encoding="utf-8-sig")

    print("Transformación terminada. Archivos en datos_limpios/:")
    for nombre, df in salidas.items():
        print(f"   {nombre}.csv: {len(df)} filas")
    print("\nReglas de limpieza aplicadas:")
    print(pd.DataFrame(REPORTE).to_string(index=False))
    return salidas


if __name__ == "__main__":
    ejecutar()
