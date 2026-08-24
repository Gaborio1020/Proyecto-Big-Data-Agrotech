import requests
import urllib3
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
from pymongo import MongoClient
import warnings
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore')

INTEGRANTE = "gabriel tenorio"

ESTACIONES = [
    {
        "region_id":       5,
        "comuna_id":       4102,
        "comuna_nombre":   "Coquimbo",
        "estacion_id":     327,
        "estacion_nombre": "Coquimbo"
    },
    {
        "region_id":       5,
        "comuna_id":       4101,
        "comuna_nombre":   "La Serena",
        "estacion_id":     323, 
        "estacion_nombre": "Cerro Grande"
    }
]

MESES = {
    "1": "enero", "2": "febrero", "3": "marzo", "4": "abril",
    "5": "mayo", "6": "junio", "7": "julio", "8": "agosto",
    "9": "septiembre", "10": "octubre", "11": "noviembre", "12": "diciembre"
}

TRIMESTRES = [
    ("01/01/2024 00:00", "31/03/2024 23:59", "2024-Q1"),
    ("01/04/2024 00:00", "30/06/2024 23:59", "2024-Q2"),
    ("01/07/2024 00:00", "30/09/2024 23:59", "2024-Q3"),
    ("01/10/2024 00:00", "31/12/2024 23:59", "2024-Q4"),
    ("01/01/2025 00:00", "31/03/2025 23:59", "2025-Q1"),
    ("01/04/2025 00:00", "30/06/2025 23:59", "2025-Q2"),
    ("01/07/2025 00:00", "30/09/2025 23:59", "2025-Q3"),
    ("01/10/2025 00:00", "31/12/2025 23:59", "2025-Q4"),
]


def extraer_datos_estacion(estacion_config):
    bloques = []

    for fecha_inicio, fecha_fin, periodo in TRIMESTRES:
        try:
            url = "https://www.agromet.cl/ext/aux/getDatosHistoricosEstacion_histo_estacion.php"
            headers = {
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "https://www.agromet.cl/datos-historicos",
                "User-Agent": "Mozilla/5.0 (compatible; ScraperAgrotech/1.0)"
            }
            payload = {
                "combo_reg_ia_id": str(estacion_config['region_id']),
                "combo_com_ia_id": str(estacion_config['comuna_id']),
                "combo_ema_ia_id": str(estacion_config['estacion_id']),
                "id_variable": "TEMP_MED",
                "fechaInicio": fecha_inicio,
                "fechaFin": fecha_fin
            }

            response = requests.post(url, headers=headers, data=payload, verify=False, timeout=30)
            response.raise_for_status()

            soup  = BeautifulSoup(response.text, 'html.parser')
            tabla = soup.find('table', class_='tabla_paginada')

            if not tabla:
                print(f"  ✗ Sin tabla: {periodo}")
                continue

            header_row = tabla.find('thead').find_all('tr')[1]
            columnas   = [th.get_text(strip=True) for th in header_row.find_all('th')]
            filas      = [[td.get_text(strip=True) for td in tr.find_all('td')]
                          for tr in tabla.find('tbody').find_all('tr')]

            df = pd.DataFrame(filas, columns=columnas)

            for col in ['Temp. promedio aire', 'Precipitación horaria']:
                df[col] = pd.to_numeric(
                    df[col].str.replace(',', '.').str.replace('--', ''),
                    errors='coerce'
                )

            df['comuna']   = estacion_config['comuna_nombre']
            df['estacion'] = estacion_config['estacion_nombre']
            bloques.append(df)

            time.sleep(1)

        except requests.exceptions.RequestException as e:
            print(f"  ✗ Error de conexión {periodo}: {e}")
            continue
        except Exception as e:
            print(f"  ✗ Error {periodo}: {e}")
            continue

    return pd.concat(bloques, ignore_index=True) if bloques else pd.DataFrame()


def ejecutar_extraccion():
    print("Scraper Agromet — Gabriel Tenorio")

    dataframes = []
    for estacion in ESTACIONES:
        print(f"  → {estacion['estacion_nombre']} ({estacion['comuna_nombre']})")
        df = extraer_datos_estacion(estacion)
        if not df.empty:
            dataframes.append(df)

    if not dataframes:
        print("  ✗ Sin datos")
        return []

    df = pd.concat(dataframes, ignore_index=True)

    if 'Fecha Hora' not in df.columns:
        print(f"  ✗ Columna 'Fecha Hora' no encontrada")
        return []

    dt              = pd.to_datetime(df['Fecha Hora'].str[:10], dayfirst=True, errors='coerce')
    df['fecha']     = dt.dt.strftime('%Y-%m-%d')
    df['año']       = dt.dt.year
    df['mes']       = dt.dt.month.astype(str).map(MESES)

    df_agrupado = (
        df
        .groupby(['comuna', 'estacion', 'año', 'mes', 'fecha'], sort=False, dropna=False)
        .agg(
            temperatura    = ('Temp. promedio aire',   'mean'),
            precipitaciones= ('Precipitación horaria', 'sum')
        )
        .reset_index()
    )

    fecha_captura = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    datos_finales = []

    for _, row in df_agrupado.iterrows():
        datos_finales.append({
            "integrante":      INTEGRANTE,
            "mes":             row['mes'],
            "año":             int(row['año']) if pd.notna(row['año']) else 0,  # Cambiar None por 0
            "fecha":           row['fecha'],
            "fecha_captura":   fecha_captura,
            "comuna":          row['comuna'],
            "estacion":        row['estacion'],
            "temperatura": float(row['temperatura']) if pd.notna(row['temperatura']) else 0.0,
            "precipitaciones": float(row['precipitaciones']) if pd.notna(row['precipitaciones']) else 0.0
        })

    print(f"  ✓ {len(datos_finales)} registros generados")
    return datos_finales


if __name__ == "__main__":
    datos = ejecutar_extraccion()

    if datos:
        try:
            client    = MongoClient('mongodb://database:27017/')
            db        = client['proyecto_bigdata']
            coleccion = db['agromet_gabriel']

            resultado = coleccion.insert_many(datos)

            print(f"✓ {len(resultado.inserted_ids)} documentos insertados")
            print(f"  Base de datos : proyecto_bigdata")
            print(f"  Colección     : agromet_gabriel")

            df_out = pd.DataFrame(datos)
            print(f"\n  Comunas    : {df_out['comuna'].unique().tolist()}")
            print(f"  Estaciones : {df_out['estacion'].unique().tolist()}")
            print(f"  Años       : {sorted(df_out['año'].dropna().astype(int).unique().tolist())}")
            print(f"\n{df_out.head(5).to_string(index=False)}")

            client.close()

        except Exception as e:
            print(f"✗ Error MongoDB: {e}")
            print("  Verifica que el contenedor de MongoDB esté corriendo")
