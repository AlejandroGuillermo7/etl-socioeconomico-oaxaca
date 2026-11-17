"""FASE 3 - CARGA.

1. PostgreSQL (instancia AWS EC2) = data warehouse con el modelo estrella.
   Se cargan primero las dimensiones y después la tabla de hechos.
2. Vistas por tema = data marts (base del dashboard de la siguiente unidad).
3. MongoDB = un documento por municipio con sus datos limpios + los datos crudos.
"""
from datetime import datetime

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

import config as cfg


def leer(nombre):
    ruta = cfg.DIR_LIMPIOS / f"{nombre}.csv"
    df = pd.read_csv(ruta, dtype=str, encoding="utf-8-sig") if ruta.exists() else pd.DataFrame()
    return df.replace({np.nan: None})


def _insertar(con, tabla, df, columnas, conflicto):
    if df.empty:
        return 0
    sql = text(f"INSERT INTO {tabla} ({', '.join(columnas)}) VALUES ({', '.join(':' + c for c in columnas)}) "
               f"ON CONFLICT ({conflicto}) DO NOTHING")
    res = con.execute(sql, df[columnas].to_dict("records"))
    return res.rowcount


def cargar_postgres():
    print("Conectando a PostgreSQL:", cfg.PG_URL.split("@")[-1])
    motor = create_engine(cfg.PG_URL)
    with motor.begin() as con:
        con.execute(text((cfg.DIR_SQL / "01_modelo_estrella.sql").read_text(encoding="utf-8")))

        # 1) Dimensiones
        n = {
            "dim_geografia": _insertar(con, "dim_geografia", leer("dim_geografia"),
                                       ["clave_geo", "nivel", "clave_entidad", "clave_municipio", "nombre"], "clave_geo"),
            "dim_tiempo": _insertar(con, "dim_tiempo", leer("dim_tiempo"),
                                    ["anio", "periodo", "fecha_referencia", "tipo_referencia"], "anio, periodo, tipo_referencia"),
            "dim_indicador": _insertar(con, "dim_indicador", leer("dim_indicador"),
                                       ["codigo_origen", "nombre", "categoria", "unidad", "fuente_api"], "codigo_origen, fuente_api"),
            "dim_actividad": _insertar(con, "dim_actividad", leer("dim_actividad"),
                                       ["codigo_scian", "nivel_scian", "descripcion", "codigo_padre"], "codigo_scian"),
        }

        # 2) Búsqueda de claves sustitutas (surrogate keys) para la tabla de hechos
        fact = leer("fact_indicadores")
        if not fact.empty:
            geo = pd.read_sql(text("SELECT sk_geografia, clave_geo FROM dim_geografia"), con)
            ind = pd.read_sql(text("SELECT sk_indicador, codigo_origen, fuente_api FROM dim_indicador"), con)
            tie = pd.read_sql(text("SELECT sk_tiempo, anio::text AS anio, periodo, tipo_referencia FROM dim_tiempo"), con)
            act = pd.read_sql(text("SELECT sk_actividad, codigo_scian FROM dim_actividad"), con)
            f = (fact.merge(geo, on="clave_geo").merge(ind, on=["codigo_origen", "fuente_api"])
                     .merge(tie, on=["anio", "periodo", "tipo_referencia"]).merge(act, on="codigo_scian"))
            sin_clave = len(fact) - len(f)
            if sin_clave:
                print(f"   AVISO: {sin_clave} hechos sin clave de dimensión; no se cargan")
            filas = f[["sk_geografia", "sk_indicador", "sk_tiempo", "sk_actividad", "valor"]].to_dict("records")
            con.execute(text(
                "INSERT INTO fact_indicadores (sk_geografia, sk_indicador, sk_tiempo, sk_actividad, valor) "
                "VALUES (:sk_geografia, :sk_indicador, :sk_tiempo, :sk_actividad, :valor) "
                "ON CONFLICT (sk_geografia, sk_indicador, sk_tiempo, sk_actividad) "
                "DO UPDATE SET valor = EXCLUDED.valor, fecha_carga = CURRENT_TIMESTAMP"), filas)
            n["fact_indicadores"] = len(filas)

        # 3) Data marts
        con.execute(text((cfg.DIR_SQL / "02_data_marts.sql").read_text(encoding="utf-8")))

        print("Carga en PostgreSQL terminada (filas nuevas o actualizadas):")
        for t, c in n.items():
            print(f"   {t}: {c}")
        total = con.execute(text("SELECT COUNT(*) FROM fact_indicadores")).scalar()
        print(f"   total en fact_indicadores: {total}")
    return n


def cargar_mongo():
    from pymongo import MongoClient
    print("Conectando a MongoDB:", cfg.MONGO_URL.split("@")[-1])
    cliente = MongoClient(cfg.MONGO_URL, serverSelectionTimeoutMS=5000)
    db = cliente[cfg.MONGO_DB]

    geo = leer("dim_geografia")
    censo = leer("censo_limpio_por_municipio")
    fact = leer("fact_indicadores")
    nuevos = 0
    for _, g in geo[geo["nivel"] == "MUNICIPAL"].iterrows():
        doc = {"clave_geo": g["clave_geo"], "nombre": g["nombre"], "entidad": cfg.NOMBRE_ENTIDAD,
               "fecha_carga": datetime.now()}
        fila = censo[censo["clave_geo"] == g["clave_geo"]] if not censo.empty else censo
        if not fila.empty:
            reg = fila.iloc[0].to_dict()
            doc["censo2020"] = {k: float(reg[k]) for k in cfg.INDICADORES_CENSO if reg.get(k) is not None}
            doc["indicadores_calculados"] = {k: float(reg[k]) for k in cfg.INDICADORES_CALCULADOS if reg.get(k) is not None}
        est = fact[(fact["clave_geo"] == g["clave_geo"]) & (fact["codigo_origen"] == "establecimientos")] if not fact.empty else fact
        doc["establecimientos"] = [{"scian": r["codigo_scian"], "actividad": cfg.SECTORES_SCIAN.get(r["codigo_scian"]),
                                    "total": int(float(r["valor"]))} for _, r in est.iterrows()]
        r = db.municipios.update_one({"clave_geo": g["clave_geo"]}, {"$set": doc}, upsert=True)
        nuevos += 1 if r.upserted_id is not None else 0
    db.municipios.create_index("clave_geo", unique=True)

    # Respaldo de los datos crudos (enfoque ELT: se guardan tal cual llegaron)
    import json
    for ruta in sorted(cfg.DIR_CRUDOS.glob("*.json")):
        contenido = json.loads(ruta.read_text(encoding="utf-8"))
        db.datos_crudos.update_one({"archivo": ruta.stem}, {"$set": {"archivo": ruta.stem, **contenido}}, upsert=True)

    print("Carga en MongoDB terminada:")
    print(f"   municipios: {db.municipios.count_documents({})} documentos"
          f" ({nuevos} nuevos)")
    print(f"   datos_crudos: {db.datos_crudos.count_documents({})} documentos")


def ejecutar(con_mongo=True):
    cargar_postgres()
    if con_mongo:
        cargar_mongo()


if __name__ == "__main__":
    ejecutar()
