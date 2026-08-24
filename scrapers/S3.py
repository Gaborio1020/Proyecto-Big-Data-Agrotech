import pandas as pd
import requests
import time
import re
import os
import warnings
from bs4 import BeautifulSoup
warnings.filterwarnings('ignore')

def ejecutar_extraccion():
    NOMBRE_INTEGRANTE = "Lissette Mathieu"
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = os.path.join(BASE_DIR, "data")

    ARCHIVOS_EXCEL = [
        "precio-consumidor_semanal_2024_uva_palta.xlsx",
        "precio-consumidor_semanal_2025_uva_palta.xlsx"
    ]
    MESES_NUM = {
        1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio",
        7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
    }

    FERTILIZANTE = "Superfosfato triple"
    URL = "https://www.indexmundi.com/es/precios-de-mercado/?mercancia=superfosfato-triple&meses=240&moneda=clp"

    MESES_ES = {
        "ene": ("enero", 1), "feb": ("febrero", 2), "mar": ("marzo", 3),
        "abr": ("abril", 4), "may": ("mayo", 5), "jun": ("junio", 6),
        "jul": ("julio", 7), "ago": ("agosto", 8), "sep": ("septiembre", 9),
        "oct": ("octubre", 10), "nov": ("noviembre", 11), "dic": ("diciembre", 12)
    }

    datos_finales = []

    # ==================== PARTE 1: ODEPA (EXCEL) ====================
    for nombre_archivo in ARCHIVOS_EXCEL:
        ruta_completa = os.path.join(BASE_DIR, nombre_archivo)
        print(f"📂 Buscando: {ruta_completa}")
        try:
            df = pd.read_excel(ruta_completa, skiprows=4)
            columnas = ['Fecha inicio', 'Producto', 'Sector', 'Variedad', 'Calidad', 'Tipo punto monitoreo', 'Precio promedio']
            df_step = df[columnas].dropna(subset=['Fecha inicio', 'Precio promedio']).copy()
            df_step['Fecha inicio'] = pd.to_datetime(df_step['Fecha inicio'], dayfirst=True)

            for _, fila in df_step.iterrows():
                valor = fila["Precio promedio"]

                if isinstance(valor, (int, float)):
                    precio_limpio = int(valor)
                else:
                    texto = str(valor).strip()
                    texto = texto.replace(".", "").replace(",", ".")
                    texto = re.sub(r'[^\d.]', '', texto)
                    precio_limpio = int(float(texto)) if texto else None

                if precio_limpio is not None:
                    fecha = fila["Fecha inicio"]
                    datos_finales.append({
                        "integrante": NOMBRE_INTEGRANTE,
                        "producto": fila["Producto"],
                        "comuna": fila["Sector"],
                        "variedad": fila["Variedad"],
                        "calidad": fila["Calidad"],
                        "lugar_monitoreo": fila["Tipo punto monitoreo"],
                        "fecha": fecha.strftime("%Y-%m-%d"),
                        "mes": MESES_NUM[fecha.month],
                        "año": fecha.year,
                        "precio": precio_limpio,
                        "fecha_captura": time.strftime('%Y-%m-%d %H:%M:%S')
                    })

            print(f"✅ ODEPA: {nombre_archivo} procesado.")

            odepa_recientes = [d for d in datos_finales if "producto" in d][-3:]
            print("   📋 Muestra ODEPA (últimos 3 registros):")
            for r in odepa_recientes:
                print(f"      {r['fecha']} | {r['producto']} | {r['variedad']} | ${r['precio']:,} CLP | {r['lugar_monitoreo']}")

        except Exception as e:
            print(f"❌ Error en {nombre_archivo}: {e}")

    # ==================== PARTE 2: INDEXMUNDI (WEB) ====================
    try:
        response = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(response.text, "html.parser")

        tabla = soup.find("table", recursive=True)
        filas = tabla.find_all("tr")

        indexmundi_temp = []

        for fila in filas:
            celdas = fila.find_all("td")
            if len(celdas) >= 3:
                mes_raw = celdas[0].text.strip()
                precio_raw = celdas[1].text.strip()
                v_raw = celdas[2].get_text(strip=True).replace('%', '')

                match = re.match(r"(\w+)\.\s+(\d{4})", mes_raw)
                if not match:
                    continue

                abrev, anio = match.group(1), int(match.group(2))
                if abrev not in MESES_ES:
                    continue

                nombre_mes, _ = MESES_ES[abrev]
                precio = int(float(precio_raw.replace(".", "").replace(",", ".")))
                variacion = str(v_raw.replace(',', '.')) if v_raw else None

                registro = {
                    "integrante": NOMBRE_INTEGRANTE,
                    "fertilizante": FERTILIZANTE,
                    "precio": precio,
                    "mes": nombre_mes,
                    "año": anio,
                    "variacion": variacion,
                    "fecha_captura": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                datos_finales.append(registro)
                indexmundi_temp.append(registro)

        print(f"✅ IndexMundi: {FERTILIZANTE} scrapeado.")

        if indexmundi_temp:
            print("   📋 Muestra IndexMundi (primeros 3):")
            for r in indexmundi_temp[:3]:
                print(f"      {r['mes']} {r['año']} | ${r['precio']:,} CLP")
            print("   📋 Muestra IndexMundi (últimos 3):")
            for r in indexmundi_temp[-3:]:
                print(f"      {r['mes']} {r['año']} | ${r['precio']:,} CLP")

    except Exception as e:
        print(f"❌ Error IndexMundi: {e}")

    # ==================== RESUMEN FINAL ====================
    print(f"\n📊 Total registros extraídos: {len(datos_finales)}")
    precios = [d["precio"] for d in datos_finales if "precio" in d]
    if precios:
        print(f"   Precio mínimo:  ${min(precios):,} CLP")
        print(f"   Precio máximo:  ${max(precios):,} CLP")
        print(f"   Precio promedio: ${int(sum(precios)/len(precios)):,} CLP")

    return datos_finales

# ==================== EJECUTAR ====================
datos = ejecutar_extraccion()