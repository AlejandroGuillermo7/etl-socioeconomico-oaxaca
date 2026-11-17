"""FASE 1 - EXTRACCIÓN.

Consulta las 4 APIs y guarda cada respuesta tal como llega (datos crudos)
en la carpeta datos_crudos/. Aquí no se modifica ningún valor.
"""
import json
import time
from datetime import datetime

import requests

import config as cfg

SESION = requests.Session()
SESION.headers.update({"User-Agent": "ETL-Oaxaca-ITO/1.0"})


def _get_json(url, intentos=3):
    """GET con reintentos. Devuelve el JSON o None si falla."""
    for i in range(1, intentos + 1):
        try:
            r = SESION.get(url, timeout=30)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as e:
            print(f"   intento {i}/{intentos} falló: {e}")
            time.sleep(2 * i)
    return None


def _ocultar_token(url):
    for t in (cfg.TOKEN_BISE, cfg.TOKEN_DENUE):
        if t:
            url = url.replace(t, "TOKEN")
    return url


def _guardar(nombre, datos, url):
    """Guarda la respuesta cruda junto con sus metadatos de extracción."""
    cfg.DIR_CRUDOS.mkdir(exist_ok=True)
    envoltura = {
        "_metadatos": {
            "url": _ocultar_token(url),
            "fecha_extraccion": datetime.now().isoformat(timespec="seconds"),
        },
        "respuesta": datos,
    }
    ruta = cfg.DIR_CRUDOS / f"{nombre}.json"
    ruta.write_text(json.dumps(envoltura, ensure_ascii=False, indent=2), encoding="utf-8")
    return ruta


def extraer_catalogo():
    print("API 1 · Catálogo Geoestadístico (INEGI)")
    datos = _get_json(cfg.URL_CATALOGO)
    if datos is not None:
        print("   guardado en", _guardar("api1_catalogo_municipios", datos, cfg.URL_CATALOGO).name)
    return datos is not None


def extraer_bise():
    print("API 2 · Banco de Indicadores (INEGI)")
    ok = True
    for indicador in cfg.INDICADORES_BISE:
        url = cfg.URL_BISE.format(indicador=indicador, area=cfg.CLAVE_ENTIDAD, token=cfg.TOKEN_BISE)
        datos = _get_json(url)
        if datos is None:
            ok = False
            continue
        print("   guardado en", _guardar(f"api2_bise_{indicador}", datos, url).name)
    return ok


def extraer_denue():
    print("API 3 · DENUE (INEGI): establecimientos por sector SCIAN")
    resultados, url_ej = [], ""
    for mun in cfg.MUNICIPIOS:
        area = cfg.CLAVE_ENTIDAD + mun
        for sector in cfg.SECTORES_SCIAN:
            url = cfg.URL_DENUE.format(actividad=sector, area=area, token=cfg.TOKEN_DENUE)
            url_ej = url
            datos = _get_json(url)
            resultados.append({"area": area, "sector": sector, "respuesta": datos})
            time.sleep(0.2)  # no saturar el servicio
        print(f"   {area} {cfg.MUNICIPIOS[mun]}: {len(cfg.SECTORES_SCIAN)} sectores consultados")
    _guardar("api3_denue_sectores", resultados, url_ej)
    return True


def extraer_censo():
    print("API 4 · Censo de Población y Vivienda 2020 (Datos México)")
    ok = True
    for mun, nombre in cfg.MUNICIPIOS.items():
        url = cfg.URL_CENSO.format(mun=mun)
        datos = _get_json(url)
        if datos is None:
            print(f"   {mun} {nombre}: SIN RESPUESTA")
            ok = False
            continue
        _guardar(f"api4_censo_{mun}", datos, url)
        print(f"   {mun} {nombre}: ok")
    return ok


def ejecutar():
    if not cfg.TOKEN_BISE:
        print("AVISO: falta TOKEN_BISE en el archivo .env (se omite la API 2)")
    if not cfg.TOKEN_DENUE:
        print("AVISO: falta TOKEN_DENUE en el archivo .env (se omite la API 3)")
    resumen = {
        "API 1 Catálogo": extraer_catalogo(),
        "API 2 BISE": extraer_bise() if cfg.TOKEN_BISE else False,
        "API 3 DENUE": extraer_denue() if cfg.TOKEN_DENUE else False,
        "API 4 Censo": extraer_censo(),
    }
    archivos = sorted(cfg.DIR_CRUDOS.glob("*.json"))
    print(f"\nExtracción terminada: {len(archivos)} archivos en {cfg.DIR_CRUDOS.name}/")
    for api, ok in resumen.items():
        print(f"   {api}: {'ok' if ok else 'con errores o sin token'}")
    return resumen


if __name__ == "__main__":
    ejecutar()
