"""Ejecuta el proceso ETL completo: extracción -> transformación -> carga.

Uso:
    python main.py                 # proceso completo
    python main.py --sin-extraer   # reutiliza los datos crudos ya descargados
    python main.py --sin-mongo     # carga solo en PostgreSQL
"""
import argparse
import time

import cargar
import extraer
import transformar


def main():
    p = argparse.ArgumentParser(description="ETL indicadores socioeconómicos - Valles Centrales de Oaxaca")
    p.add_argument("--sin-extraer", action="store_true", help="no vuelve a consultar las APIs")
    p.add_argument("--sin-mongo", action="store_true", help="no carga en MongoDB")
    a = p.parse_args()

    inicio = time.time()
    if not a.sin_extraer:
        print("=" * 60, "\nFASE 1 · EXTRACCIÓN\n" + "=" * 60)
        extraer.ejecutar()
    print("\n" + "=" * 60, "\nFASE 2 · TRANSFORMACIÓN\n" + "=" * 60)
    transformar.ejecutar()
    print("\n" + "=" * 60, "\nFASE 3 · CARGA\n" + "=" * 60)
    cargar.ejecutar(con_mongo=not a.sin_mongo)
    print(f"\nETL completo en {time.time() - inicio:.1f} segundos")


if __name__ == "__main__":
    main()
