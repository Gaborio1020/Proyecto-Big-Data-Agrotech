import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
import os

MESES_MAP = {
    "01": "enero", "02": "febrero", "03": "marzo",
    "04": "abril", "05": "mayo", "06": "junio",
    "07": "julio", "08": "agosto", "09": "septiembre",
    "10": "octubre", "11": "noviembre", "12": "diciembre"
}

# Abreviaturas en español que usa el sitio ENAP en el HTML
MESES_ABREV = {
    "ene": "01", "feb": "02", "mar": "03", "abr": "04",
    "may": "05", "jun": "06", "jul": "07", "ago": "08",
    "sep": "09", "oct": "10", "nov": "11", "dic": "12"
}

AÑOS_VALIDOS = {2024, 2025}


def cargar_datos_historicos():
    """
    Carga datos históricos USD/CLP desde el CSV.
    Solo incluye registros de 2024 y 2025.
    Retorna registros con esquema unificado: producto, precio, variacion.
    """
    NOMBRE_INTEGRANTE = "Maximiliano Berrios"
    csv_path = os.path.join(os.path.dirname(__file__), "data", "Datos históricos USD_CLP.csv")

    datos_historicos = []

    if not os.path.exists(csv_path):
        print(f"✗ Archivo no encontrado: {csv_path}")
        return datos_historicos

    try:
        df = pd.read_csv(csv_path, encoding='utf-8')
        print(f"Columnas detectadas: {list(df.columns)}")

        for _, row in df.iterrows():
            # --- PROCESAR FECHA (formato DD.MM.YYYY del CSV) ---
            fecha_raw = str(row['Fecha']).strip()
            partes = fecha_raw.split('.')
            if len(partes) == 3:
                dia, mes_num, año_str = partes
                try:
                    año = int(año_str)
                except ValueError:
                    print(f"⚠ Año no numérico omitido: {fecha_raw}")
                    continue
            else:
                print(f"⚠ Fecha con formato inesperado omitida: {fecha_raw}")
                continue

            # --- FILTRO AÑO ---
            if año not in AÑOS_VALIDOS:
                continue

            mes_num = mes_num.zfill(2)
            fecha_formateada = f"{año}-{mes_num}-{dia}"
            mes_nombre = MESES_MAP.get(mes_num, mes_num)

            # --- PRECIO (campo unificado) ---
            precio_str = str(row['Último']).replace('.', '').replace(',', '.')
            try:
                precio = float(precio_str)
            except ValueError:
                precio = 0.0

            # --- VARIACIÓN (desde variacion_pct del CSV, campo unificado) ---
            variacion_str = str(row['% var.']).replace('%', '').replace(',', '.').strip()
            try:
                variacion = float(variacion_str) if variacion_str else 0.0
            except ValueError:
                variacion = 0.0

            datos_historicos.append({
                "integrante": NOMBRE_INTEGRANTE,
                "producto": "usd_clp",
                "precio": precio,
                "fecha": fecha_formateada,
                "mes": mes_nombre,
                "año": año,
                "variacion": variacion,
                "p_apertura": row['Apertura'],
                "maximo": row['Máximo'],
                "minimo": row['Mínimo'],
                "fecha_captura": time.strftime("%Y-%m-%d %H:%M:%S")
            })

        print(f"✓ Datos históricos USD/CLP cargados: {len(datos_historicos)} filas (solo 2024-2025)")

    except Exception as e:
        print(f"✗ Error cargando datos históricos: {e}")
        import traceback
        traceback.print_exc()

    return datos_historicos


def ejecutar_extraccion():
    """
    Scraper ENAP (Diésel) + datos históricos USD/CLP.
    Ambas fuentes usan esquema unificado: producto, precio, variacion.

    Formato de fecha del HTML de ENAP: DD-MES-AA
    donde MES es abreviatura en español (ene, feb, mar, abr, may, jun,
    jul, ago, sep, oct, nov, dic) y AA es año de 2 dígitos (ej. 24, 25).
    """
    NOMBRE_INTEGRANTE = "Maximiliano Berrios"
    URL = "https://www.enap.cl/tabla-de-precios-de-paridad-historico"

    datos_finales = []

    # --- REQUEST ---
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(URL, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    filas = soup.select("table tbody tr")
    print(f"Filas encontradas en ENAP: {len(filas)}")

    # Invertir para procesar cronológicamente (variación correcta)
    filas = list(filas)[::-1]

    precio_anterior = None

    for fila in filas:
        try:
            columnas = fila.find_all("td")

            if len(columnas) < 5:
                continue

            fecha_raw = columnas[0].get_text(strip=True)
            diesel_raw = columnas[4].get_text(strip=True)

            if diesel_raw == "":
                continue

            # --- LIMPIAR PRECIO ---
            valor = diesel_raw.replace(".", "").replace(",", "").strip()
            precio = float(valor) if valor.isdigit() else 0.0

            # --- PROCESAR FECHA (formato ENAP: DD-MES-AA, ej. 04-ene-24) ---
            partes = fecha_raw.split("-")
            if len(partes) != 3:
                print(f"⚠ Fecha con formato inesperado omitida: {fecha_raw}")
                precio_anterior = None
                continue

            dia, mes_abrev, año_str = partes
            mes_abrev = mes_abrev.lower().strip()

            # Resolver mes: puede venir como abreviatura (ene) o número (01)
            if mes_abrev in MESES_ABREV:
                mes_num = MESES_ABREV[mes_abrev]
            elif mes_abrev.isdigit():
                mes_num = mes_abrev.zfill(2)
            else:
                print(f"⚠ Mes no reconocido omitido: {fecha_raw}")
                precio_anterior = None
                continue

            # Resolver año: puede venir de 2 dígitos (24) o 4 dígitos (2024)
            if not año_str.isdigit():
                print(f"⚠ Año no numérico omitido: {fecha_raw}")
                precio_anterior = None
                continue

            año = int(año_str)
            if año < 100:
                año = 2000 + año

            mes_nombre = MESES_MAP.get(mes_num, mes_num)
            fecha_formateada = f"{año}-{mes_num}-{dia.zfill(2)}"

            # --- VARIACIÓN ---
            variacion = (precio - precio_anterior) if precio_anterior is not None else 0.0
            precio_anterior = precio

            # --- GUARDAR (esquema unificado) ---
            datos_finales.append({
                "integrante": NOMBRE_INTEGRANTE,
                "producto": "petroleo",
                "precio": precio,
                "fecha": fecha_formateada,
                "mes": mes_nombre,
                "año": año,
                "variacion": variacion,
                "iva": precio * 0.19,
                "fecha_captura": time.strftime("%Y-%m-%d %H:%M:%S")
            })

        except Exception as e:
            print(f"Error en fila: {e}")
            continue

    print(f"✓ Datos ENAP (diésel) cargados: {len(datos_finales)} registros")

    # --- AGREGAR DATOS HISTÓRICOS USD/CLP ---
    datos_historicos = cargar_datos_historicos()
    datos_finales.extend(datos_historicos)

    print(f"Total de datos combinados: {len(datos_finales)}")

    return datos_finales


if __name__ == "__main__":
    print("=" * 60)
    print("EJECUTANDO SCRAPER - MAXIMILIANO BERRIOS")
    print("=" * 60)

    datos = ejecutar_extraccion()

    datos_petroleo = [d for d in datos if d.get("producto") == "petroleo"]
    datos_usd = [d for d in datos if d.get("producto") == "usd_clp"]

    print("\n" + "=" * 60)
    print("RESUMEN FINAL")
    print("=" * 60)
    print(f"DATOS ENAP (DIÉSEL / petroleo): {len(datos_petroleo)} registros")
    print(f"DATOS USD/CLP HISTÓRICOS:        {len(datos_usd)} registros")
    print(f"TOTAL DE REGISTROS:              {len(datos)}")
    print("=" * 60)

    print("\n" + "=" * 60)
    print("VISTA PREVIA: PRIMERAS 5 FILAS ENAP (petroleo)")
    print("=" * 60)
    df_petroleo = pd.DataFrame(datos_petroleo)
    print(df_petroleo.head())

    print("\n" + "=" * 60)
    print("VISTA PREVIA: PRIMERAS 5 FILAS USD/CLP")
    print("=" * 60)
    df_usd = pd.DataFrame(datos_usd)
    print(df_usd.head())