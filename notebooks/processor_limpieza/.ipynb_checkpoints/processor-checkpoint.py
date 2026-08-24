import os
from pymongo import MongoClient
from dotenv import load_dotenv
import pandas as pd
import numpy as np

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("DB_NAME")]
raw = db[os.getenv("RAW_COLLECTION")]
processed = db[os.getenv("PROCESSED_COLLECTION")]

docs = list(raw.find({}))
RAW_COLL = os.getenv("RAW_COLLECTION")
print(f"Se encontraron {len(docs)} documentos en {RAW_COLL}")

if not docs:
    print("⚠️ No hay datos para procesar.")
    exit(0)

df = pd.DataFrame(docs)

# ═══════════════════════════════════════════════════════════════════════════════
# BLOQUE 1: NORMALIZACIÓN DE SCHEMA (compatibilidad schema antiguo → nuevo)
# ═══════════════════════════════════════════════════════════════════════════════

# 1a. precio_petroleo (schema antiguo) → precio + producto="petroleo"
#     En el schema nuevo esto ya viene como precio con producto="petroleo".
#     Para registros antiguos que aún traigan precio_petroleo separado, consolidar.
if "precio_petroleo" in df.columns:
    mask_pp = df["precio_petroleo"].notna() & df["precio"].isna()
    df.loc[mask_pp, "precio"] = df.loc[mask_pp, "precio_petroleo"]
    df.loc[mask_pp & df["producto"].isna(), "producto"] = "petroleo"
    df = df.drop(columns=["precio_petroleo"])

# 1b. apertura (schema antiguo) → p_apertura (schema nuevo)
#     Unificar en una sola columna p_apertura.
if "apertura" in df.columns:
    if "p_apertura" not in df.columns:
        df["p_apertura"] = df["apertura"]
    else:
        # Si coexisten, priorizar p_apertura; rellenar huecos con apertura
        df["p_apertura"] = df["p_apertura"].combine_first(df["apertura"])
    df = df.drop(columns=["apertura"])

# 1c. precio_usd_clp (schema antiguo) → precio + producto="usd_clp"
#     En el schema nuevo esto ya viene como precio con producto="usd_clp".
if "precio_usd_clp" in df.columns:
    mask_usd = df["precio_usd_clp"].notna() & df["precio"].isna()
    df.loc[mask_usd, "precio"] = df.loc[mask_usd, "precio_usd_clp"]
    df.loc[mask_usd & df["producto"].isna(), "producto"] = "usd_clp"
    df = df.drop(columns=["precio_usd_clp"])

# 1d. variacion_pct (schema antiguo) → descartado; se calcula desde precio
if "variacion_pct" in df.columns:
    df = df.drop(columns=["variacion_pct"])

# 1e. maximo / minimo / p_apertura: en schema nuevo vienen como strings con comas
#     (ej. "913,90"). Normalizar a float.
for col_num_str in ["maximo", "minimo", "p_apertura"]:
    if col_num_str in df.columns:
        df[col_num_str] = (
            df[col_num_str]
            .astype(str)
            .str.replace(",", ".", regex=False)
            .replace({"None": None, "nan": None, "null": None, "": None})
        )
        df[col_num_str] = pd.to_numeric(df[col_num_str], errors="coerce")

# ═══════════════════════════════════════════════════════════════════════════════
# BLOQUE 2: LIMPIEZA Y SANEAMIENTO DE DATOS
# ═══════════════════════════════════════════════════════════════════════════════

# 2a. Año: corregir valores corruptos (ej. "17" interpretado como año '17 → 2017)
if "año" in df.columns:
    df["año"] = pd.to_numeric(df["año"], errors="coerce")
    mask_año_corto = df["año"].notna() & (df["año"] < 100)
    df.loc[mask_año_corto, "año"] = df.loc[mask_año_corto, "año"] + 2000
    print(f"  ⚠️  {mask_año_corto.sum()} registros con año abreviado corregidos (ej. 17 → 2017).")

# 2b. Precio: normalizar a float
df["precio_normalizado"] = df["precio"].apply(
    lambda x: round(float(x), 0) if x is not None and not (isinstance(x, float) and np.isnan(x)) else None
)

# 2c. Fecha: clave de enlace uniforme YYYY-MM-DD (tolerante a formatos mixtos)
df["fecha_enlace"] = pd.to_datetime(df["fecha"], errors="coerce", dayfirst=True).dt.strftime("%Y-%m-%d")

# 2d. Comuna: limpiar espacios
if "comuna" in df.columns:
    df["comuna"] = df["comuna"].astype(str).str.strip().replace("None", None).replace("nan", None)

# 2e. Fechas internas: estandarizar formatos
for col_fecha in ["fecha", "fecha_captura"]:
    if col_fecha in df.columns:
        df[col_fecha] = pd.to_datetime(df[col_fecha], errors="coerce", dayfirst=True)
        fmt = "%Y-%m-%d" if col_fecha == "fecha" else "%Y-%m-%d %H:%M:%S"
        df[col_fecha] = df[col_fecha].dt.strftime(fmt)

# ═══════════════════════════════════════════════════════════════════════════════
# BLOQUE 3: FEATURES TEMPORALES
# ═══════════════════════════════════════════════════════════════════════════════

df["mes_num"] = pd.to_datetime(df["fecha_enlace"], errors="coerce").dt.month
df["dia_año"] = pd.to_datetime(df["fecha_enlace"], errors="coerce").dt.dayofyear
df["semana_año"] = pd.to_datetime(df["fecha_enlace"], errors="coerce").dt.isocalendar().week

estacionalidad_map = {12: 0, 1: 0, 2: 0, 3: 1, 4: 1, 5: 1, 6: 2, 7: 2, 8: 2, 9: 3, 10: 3, 11: 3}
df["estacionalidad_index"] = df["mes_num"].map(estacionalidad_map)

# ═══════════════════════════════════════════════════════════════════════════════
# BLOQUE 4: SEPARACIÓN POR ENTIDAD Y EXTRACCIÓN DE TASA DE CAMBIO
# ═══════════════════════════════════════════════════════════════════════════════

# Registros de productos (frutas, verduras, petróleo, etc. — incluyendo usd_clp)
df_productos = df[df["producto"].notna()].copy()

# Registros ambientales
df_ambiental = df[
    df["producto"].isna() &
    (df["temperatura"].notna() | df["humedad"].notna() | df["radiacion_uv"].notna())
].copy()

# Tasa de cambio USD/CLP: extraída directamente de registros con producto="usd_clp"
#   Schema nuevo: precio con producto="usd_clp" (precio de cierre del día)
#   Schema antiguo: precio_usd_clp (ya consolidado en precio arriba)
df_usd = df[df["producto"] == "usd_clp"][["fecha_enlace", "precio"]].copy()
df_usd = df_usd.rename(columns={"precio": "tasa_cambio"})
df_tasa_diaria = df_usd.groupby("fecha_enlace")["tasa_cambio"].mean().reset_index()

# Consolidar clima diario por fecha y comuna
df_clima_diario = df_ambiental.groupby(["fecha_enlace", "comuna"]).agg({
    "temperatura": "mean",
    "humedad": "mean",
    "precipitaciones": "mean",
    "radiacion_uv": "mean",
}).reset_index()

# ═══════════════════════════════════════════════════════════════════════════════
# BLOQUE 5: CONSTRUCCIÓN DEL DATAFRAME DE PRODUCTOS (excluye usd_clp como fila)
# ═══════════════════════════════════════════════════════════════════════════════

# Excluir usd_clp del conjunto de productos: es una variable macro, no un producto agrícola
df_productos_agro = df_productos[df_productos["producto"] != "usd_clp"].copy()

cols_ambientales = ["temperatura", "humedad", "precipitaciones", "radiacion_uv", "tasa_cambio"]
df_productos_agro = df_productos_agro.drop(columns=cols_ambientales, errors="ignore")

# Cruce horizontal: productos ← clima diario ← tasa de cambio
df_procesado = pd.merge(df_productos_agro, df_clima_diario, on=["fecha_enlace", "comuna"], how="left")
df_procesado = pd.merge(df_procesado, df_tasa_diaria, on="fecha_enlace", how="left")

# ═══════════════════════════════════════════════════════════════════════════════
# BLOQUE 6: IMPUTACIÓN INTELIGENTE
# ═══════════════════════════════════════════════════════════════════════════════

for col in cols_ambientales:
    if col in df_procesado.columns:
        comuna_means = df_procesado.groupby("comuna")[col].transform("mean")
        df_procesado[col] = df_procesado[col].fillna(comuna_means)
        global_mean = df_procesado[col].mean()
        if pd.isna(global_mean) or np.isnan(global_mean):
            global_mean = 0
        df_procesado[col] = df_procesado[col].fillna(global_mean)

# ═══════════════════════════════════════════════════════════════════════════════
# BLOQUE 7: CÁLCULO DE VARIACIÓN Y ENCODING CATEGÓRICO
# ═══════════════════════════════════════════════════════════════════════════════

df_procesado = df_procesado.sort_values(by=["producto", "comuna", "fecha_enlace"])
df_procesado["variacion"] = (
    df_procesado.groupby(["producto", "comuna"])["precio_normalizado"]
    .pct_change()
    .apply(lambda x: round(x * 100, 2) if pd.notnull(x) else None)
)

df_procesado["comuna_index"] = df_procesado["comuna"].astype("category").cat.codes
df_procesado["lugar_monitoreo_index"] = df_procesado["lugar_monitoreo"].astype("category").cat.codes
df_procesado["variedad_index"] = df_procesado["variedad"].astype("category").cat.codes

# ═══════════════════════════════════════════════════════════════════════════════
# BLOQUE 8: SELECCIÓN DE COLUMNAS FINALES Y ESCRITURA
# ═══════════════════════════════════════════════════════════════════════════════

columnas_permitidas = [
    "_id", "año", "calidad", "comuna", "estacion", "fecha",
    "fertilizante", "humedad", "integrante", "iva",
    "lugar_monitoreo", "maximo", "mes", "minimo", "p_apertura",
    "precipitaciones", "precio", "precio_normalizado", "producto",
    "radiacion_uv", "tasa_cambio", "temperatura", "variacion", "variedad",
    # Features temporales
    "mes_num", "dia_año", "semana_año", "estacionalidad_index",
    # Encodings categóricos
    "comuna_index", "lugar_monitoreo_index", "variedad_index",
]

df_final = df_procesado[[col for col in df_procesado.columns if col in columnas_permitidas]]

print(f"\n📋 Resumen del procesamiento:")
print(f"   Documentos crudos         : {len(docs):,}")
print(f"   Registros de productos    : {len(df_productos_agro):,}")
print(f"   Registros ambientales     : {len(df_ambiental):,}")
print(f"   Registros tasa USD/CLP    : {len(df_usd):,}")
print(f"   Documentos en df_final    : {len(df_final):,}")
print(f"   Columnas exportadas       : {list(df_final.columns)}")

processed.delete_many({})
processed.insert_many(df_final.to_dict("records"))

print(f"\n✅ Processor ejecutado correctamente. Se insertaron {len(df_final)} documentos en processed_data.")
#. 