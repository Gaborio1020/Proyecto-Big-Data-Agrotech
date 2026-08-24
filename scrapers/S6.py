import requests
from bs4 import BeautifulSoup
import time


def ejecutar_extraccion():

    NOMBRE_INTEGRANTE = "Mathieus Villavicencio"
    COMUNA = "Coquimbo"

    datos_finales = []
    fecha_actual = time.strftime("%Y-%m-%d %H:%M:%S")

    anios = ["2025", "2024"]

    # Nombres de mes en minúsculas para coincidir con el esquema unificado
    meses_nombre = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]

    # Nombres con mayúscula inicial tal como aparecen en el HTML de Meteochile
    meses_html = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]

    meses_num = {
        "Enero": "01", "Febrero": "02", "Marzo": "03", "Abril": "04",
        "Mayo": "05", "Junio": "06", "Julio": "07", "Agosto": "08",
        "Septiembre": "09", "Octubre": "10", "Noviembre": "11", "Diciembre": "12"
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    def scrapear_tabla(url, tipo_dato, anio):
        """
        Extrae datos de una tabla HTML de Meteochile.

        Estructura real de la tabla:
          - thead > tr[0]: "Día" + colspan "Meses"         (th)
          - thead > tr[1]: "Enero", "Febrero", ..., "Diciembre"  (th)
          - tbody > tr[N]: día (td) + valor por mes (td)

        El error anterior ocurría porque find_all('tr') mezclaba thead y tbody,
        y find_all('td') en filas de <th> devolvía lista vacía desplazando
        todos los índices. Ahora se lee thead/tbody por separado y se
        construye el mapa de columnas dinámicamente desde los headers reales.
        """
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            table = soup.find('table')
            if not table:
                print(f"⚠️  No se encontró tabla en {url}")
                return

            # --- LEER HEADERS DINÁMICAMENTE ---
            # Buscar la fila de headers que contiene los nombres de mes
            # Puede estar en <thead> o como primeras <tr> del <table>
            thead = table.find('thead')
            if thead:
                header_rows = thead.find_all('tr')
            else:
                # Sin thead: los headers son las primeras filas con <th>
                header_rows = [tr for tr in table.find_all('tr')
                               if tr.find('th')]

            # La fila de meses es la que contiene "Enero" (o similar)
            col_map = {}  # mes_nombre_html → índice de columna (0-based desde "Día")
            for hr in header_rows:
                celdas = hr.find_all(['th', 'td'])
                textos = [c.get_text(strip=True) for c in celdas]
                if any(t in meses_html for t in textos):
                    for idx, texto in enumerate(textos):
                        if texto in meses_html:
                            col_map[texto] = idx
                    break  # encontramos la fila correcta

            if not col_map:
                # Fallback: asumir orden estándar si no se pudo leer header
                print(f"⚠️  No se pudo leer cabecera de meses en {url}, usando orden por defecto")
                col_map = {mes: i + 1 for i, mes in enumerate(meses_html)}

            # --- LEER FILAS DE DATOS ---
            tbody = table.find('tbody')
            if tbody:
                filas_datos = tbody.find_all('tr')
            else:
                # Sin tbody: saltamos las filas de header ya procesadas
                n_header_rows = len(header_rows)
                filas_datos = table.find_all('tr')[n_header_rows:]

            for fila in filas_datos:
                columnas = fila.find_all('td')

                if not columnas:
                    continue

                # Primera columna es el día
                try:
                    dia = int(columnas[0].get_text(strip=True))
                except ValueError:
                    continue

                # Iterar sobre cada mes según el mapa de columnas
                for mes_html, col_idx in col_map.items():
                    if col_idx >= len(columnas):
                        continue

                    valor_text = columnas[col_idx].get_text(strip=True)

                    if not valor_text or valor_text in (".", "-", ""):
                        continue

                    try:
                        valor_float = float(valor_text.replace(",", "."))
                    except ValueError:
                        continue

                    mes_num_str = meses_num[mes_html]
                    # Nombre de mes en minúsculas para esquema unificado
                    mes_minusc = meses_nombre[meses_html.index(mes_html)]
                    fecha_completa = f"{anio}-{mes_num_str}-{str(dia).zfill(2)}"

                    registro = {
                        "integrante": NOMBRE_INTEGRANTE,
                        "fecha": fecha_completa,
                        "mes": mes_minusc,
                        "año": int(anio),
                        "comuna": COMUNA,
                        "fecha_captura": fecha_actual
                    }

                    if tipo_dato == "uv":
                        registro["radiacion_uv"] = valor_float
                    elif tipo_dato == "humedad":
                        registro["humedad"] = valor_float

                    datos_finales.append(registro)

        except requests.RequestException as e:
            print(f"❌ Error de conexión en {url}: {e}")
        except Exception as e:
            import traceback
            print(f"❌ Error al parsear {url}: {e}")
            traceback.print_exc()

    # --- EJECUTAR PARA TODOS LOS AÑOS Y TIPOS ---
    try:
        for anio in anios:
            scrapear_tabla(
                f"https://climatologia.meteochile.gob.cl/application/anual/indiceUvbMaximoAnual/290004/{anio}",
                "uv",
                anio
            )
            scrapear_tabla(
                f"https://climatologia.meteochile.gob.cl/application/anual/humedadAnual/290004/{anio}",
                "humedad",
                anio
            )

        print(f"✅ OK: {len(datos_finales)} registros")

    except Exception as e:
        print(f"❌ Error general: {e}")

    return datos_finales