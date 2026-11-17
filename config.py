"""Configuración general del ETL: municipios, fuentes, rutas y conexiones."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE = Path(__file__).resolve().parent
load_dotenv(BASE / ".env")

# Carpetas de trabajo (zona de datos crudos y zona de datos limpios)
DIR_CRUDOS = BASE / "datos_crudos"
DIR_LIMPIOS = BASE / "datos_limpios"
DIR_SQL = BASE / "sql"

# Credenciales (se leen del archivo .env, nunca se escriben en el código)
TOKEN_INEGI = os.getenv("TOKEN_INEGI", "")
# El INEGI da un token para el Banco de Indicadores y otro para el DENUE
TOKEN_BISE = os.getenv("TOKEN_BISE", TOKEN_INEGI)
TOKEN_DENUE = os.getenv("TOKEN_DENUE", TOKEN_INEGI)
PG_URL = os.getenv(
    "PG_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/oaxacaanalisis"
)
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "oaxacaanalisis")

CLAVE_ENTIDAD = "20"  # Oaxaca
NOMBRE_ENTIDAD = "Oaxaca"

# Los 15 municipios de Valles Centrales que analiza el proyecto
MUNICIPIOS = {
    "067": "Oaxaca de Juárez",
    "385": "Santa Cruz Xoxocotlán",
    "565": "Villa de Zaachila",
    "390": "Santa Lucía del Camino",
    "399": "Santa María Atzompa",
    "375": "Santa Cruz Amilpas",
    "350": "San Sebastián Tutla",
    "107": "San Antonio de la Cal",
    "157": "San Jacinto Amilpas",
    "083": "San Agustín de las Juntas",
    "115": "San Bartolo Coyotepec",
    "409": "Santa María del Tule",
    "553": "Tlalixtac de Cabrera",
    "091": "San Andrés Huayápam",
    "293": "San Pablo Etla",
}

# URLs de las 4 APIs (las mismas que se documentaron en Postman/Bruno)
URL_CATALOGO = "https://gaia.inegi.org.mx/wscatgeo/v2/mgem/20"
URL_BISE = (
    "https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml/"
    "INDICATOR/{indicador}/es/{area}/false/BISE/2.0/{token}?type=json"
)
URL_DENUE = (
    "https://www.inegi.org.mx/app/api/denue/v1/consulta/Cuantificar/"
    "{actividad}/{area}/0/{token}"
)
URL_CENSO = "https://api.datosmexico.org/api/v1/censo2020/localidades/20/{mun}/0000"

# Indicadores del Banco de Indicadores que se consultan
INDICADORES_BISE = {"1002000001": ("Población total", "Demografía", "Personas")}

# Sectores SCIAN (2 dígitos) que se cuantifican en el DENUE
SECTORES_SCIAN = {
    "11": "Agricultura, cría y explotación de animales, aprovechamiento forestal, pesca y caza",
    "21": "Minería",
    "22": "Generación, transmisión y distribución de energía eléctrica, agua y gas",
    "23": "Construcción",
    "31": "Industrias manufactureras",
    "43": "Comercio al por mayor",
    "46": "Comercio al por menor",
    "48": "Transportes, correos y almacenamiento",
    "51": "Información en medios masivos",
    "52": "Servicios financieros y de seguros",
    "53": "Servicios inmobiliarios y de alquiler de bienes muebles e intangibles",
    "54": "Servicios profesionales, científicos y técnicos",
    "55": "Corporativos",
    "56": "Servicios de apoyo a los negocios y manejo de residuos",
    "61": "Servicios educativos",
    "62": "Servicios de salud y de asistencia social",
    "71": "Servicios de esparcimiento culturales y deportivos",
    "72": "Servicios de alojamiento temporal y de preparación de alimentos y bebidas",
    "81": "Otros servicios excepto actividades gubernamentales",
    "93": "Actividades legislativas, gubernamentales, de impartición de justicia",
}

# Campos del Censo 2020 que se conservan: código -> (nombre, categoría, unidad)
INDICADORES_CENSO = {
    "pobtot": ("Población total", "Demografía", "Personas"),
    "pobfem": ("Población femenina", "Demografía", "Personas"),
    "pobmas": ("Población masculina", "Demografía", "Personas"),
    "pob0_14": ("Población de 0 a 14 años", "Demografía", "Personas"),
    "pob15_64": ("Población de 15 a 64 años", "Demografía", "Personas"),
    "pob65_mas": ("Población de 65 años y más", "Demografía", "Personas"),
    "graproes": ("Grado promedio de escolaridad", "Educación", "Años"),
    "p15ym_an": ("Población de 15 años y más analfabeta", "Educación", "Personas"),
    "p15a17a": ("Población de 15 a 17 años que asiste a la escuela", "Educación", "Personas"),
    "pea": ("Población económicamente activa", "Empleo", "Personas"),
    "pocupada": ("Población ocupada", "Empleo", "Personas"),
    "pdesocup": ("Población desocupada", "Empleo", "Personas"),
    "pder_ss": ("Población afiliada a servicios de salud", "Salud", "Personas"),
    "psinder": ("Población sin afiliación a servicios de salud", "Salud", "Personas"),
    "pder_imss": ("Población afiliada al IMSS", "Salud", "Personas"),
    "tvivparhab": ("Viviendas particulares habitadas", "Vivienda y servicios", "Viviendas"),
    "vph_c_elec": ("Viviendas con electricidad", "Vivienda y servicios", "Viviendas"),
    "vph_aguadv": ("Viviendas con agua entubada", "Vivienda y servicios", "Viviendas"),
    "vph_drenaj": ("Viviendas con drenaje", "Vivienda y servicios", "Viviendas"),
    "vph_inter": ("Viviendas con internet", "Tecnología", "Viviendas"),
    "vph_pc": ("Viviendas con computadora", "Tecnología", "Viviendas"),
    "vph_cel": ("Viviendas con teléfono celular", "Tecnología", "Viviendas"),
}

# Indicadores calculados en la transformación: código -> (nombre, categoría, numerador, denominador, factor)
INDICADORES_CALCULADOS = {
    "pct_desocupacion": ("Tasa de desocupación", "Empleo", "pdesocup", "pea", 100),
    "pct_sin_salud": ("Porcentaje de población sin afiliación a salud", "Salud", "psinder", "pobtot", 100),
    "pct_viv_electricidad": ("Porcentaje de viviendas con electricidad", "Vivienda y servicios", "vph_c_elec", "tvivparhab", 100),
    "pct_viv_agua": ("Porcentaje de viviendas con agua entubada", "Vivienda y servicios", "vph_aguadv", "tvivparhab", 100),
    "pct_viv_drenaje": ("Porcentaje de viviendas con drenaje", "Vivienda y servicios", "vph_drenaj", "tvivparhab", 100),
    "pct_viv_internet": ("Porcentaje de viviendas con internet", "Tecnología", "vph_inter", "tvivparhab", 100),
    "pct_viv_computadora": ("Porcentaje de viviendas con computadora", "Tecnología", "vph_pc", "tvivparhab", 100),
    "indice_masculinidad": ("Índice de masculinidad (hombres por cada 100 mujeres)", "Demografía", "pobmas", "pobfem", 100),
}

# Valores que las fuentes usan para "dato no disponible"
VALORES_NULOS = {"", "*", "N/D", "ND", "n/d", "NA", "-", "null", "None"}

ACTIVIDAD_NO_APLICA = ("00", "No aplica (indicador no económico)")
