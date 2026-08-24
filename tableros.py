"""
Tableros AgroTech — Streamlit + ECharts
Ejecutar: streamlit run tableros.py

Dependencias: streamlit, streamlit-echarts, pymongo, python-dotenv, pandas, numpy, scikit-learn, statsmodels
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from pymongo import MongoClient
from sklearn.metrics import r2_score
from streamlit_echarts import JsCode, st_echarts

try:
    import statsmodels.api as sm
except ImportError:
    sm = None

# ── Entorno ──────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "db_g9agrotech")
PROCESSED_COLLECTION = os.getenv("PROCESSED_COLLECTION", "processed_data")

MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
    7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}
ANIO_REF_FIJO, MES_REF_FIJO = 2025, 3

PALETTE = ["#1B6CA8", "#5BB328", "#F49D22", "#7B4FA3", "#0096C8", "#E85D4C"]
COLOR_ESCALONADA = "#E07A4A"
COLOR_CONCENTRAR = "#3D8B40"
COLOR_FERIA = "#2E7D32"
COLOR_SUPER = "#EF6C00"
COLOR_PRECIO_DIA = "#00897B"
COLOR_REF_MENSUAL = "#000000"
COLOR_OPTIMO = "#2E7D32"
COLOR_PARCIAL = "#F9A825"
COLOR_NO_OPTIMO = "#C62828"
COLOR_TEXTO_GRAF = "#1B2838"
COLOR_EJE = "#555555"
COLOR_GRID = "#E8ECF0"

CANALES = ["Feria libre", "Supermercado"]
ECHARTS_THEME = ""

PESOS_IASC = {"retorno": 0.40, "estabilidad": 0.35, "viabilidad": 0.25}
VENTANA_PM_IASC = 3
SEMAFORO_IASC_COLOR = {"Verde": "#2E7D32", "Amarillo": "#F9A825", "Rojo": "#C62828", "—": "#9E9E9E"}

UMBRALES_COSECHA = {
    "Palta": {"temp_min": 15, "temp_max": 20, "hum_max": 30},
    "Limón": {"temp_min": 12, "temp_max": 28, "hum_max": 75},
    "Naranja": {"temp_min": 10, "temp_max": 30, "hum_max": 75},
    "Tomate": {"temp_min": 18, "temp_max": 28, "hum_max": 70},
    "Papa": {"temp_min": 10, "temp_max": 25, "hum_max": 80},
    "Uva": {"temp_min": 15, "temp_max": 30, "hum_max": 65},
}

LOGO_PATH = ROOT / "assets" / "agrotech_logo.png"

# Rejilla fija 2×3 (máximo 6 productos)
GRIDS_2X3 = [
    {"left": "5%", "top": "20%", "width": "28%", "height": "30%"},
    {"left": "36%", "top": "20%", "width": "28%", "height": "30%"},
    {"left": "67%", "top": "20%", "width": "28%", "height": "30%"},
    {"left": "5%", "bottom": "4%", "width": "28%", "height": "30%"},
    {"left": "36%", "bottom": "4%", "width": "28%", "height": "30%"},
    {"left": "67%", "bottom": "4%", "width": "28%", "height": "30%"},
]


def mes_referencia(df=None, productos=None, min_registros=1):
    return ANIO_REF_FIJO, MES_REF_FIJO, MESES_ES[MES_REF_FIJO]


def _clean_key(key: str) -> str:
    """Limpia una key de componente para evitar '__' (usado internamente por Streamlit)."""
    while "__" in key:
        key = key.replace("__", "_")
    if key.endswith("_"):
        key = key[:-1]
    return key


def _layout_grids(n: int) -> list[dict]:
    """Posiciones de panel según cantidad de productos (1 = centrado, sin ejes extra)."""
    n = max(1, min(n, 6))
    if n == 1:
        return [{"left": "12%", "top": "24%", "width": "76%", "height": "68%"}]
    if n == 2:
        return [
            {"left": "4%", "top": "24%", "width": "44%", "height": "68%"},
            {"left": "52%", "top": "24%", "width": "44%", "height": "68%"},
        ]
    if n == 3:
        return [
            {"left": "3%", "top": "24%", "width": "30%", "height": "68%"},
            {"left": "35%", "top": "24%", "width": "30%", "height": "68%"},
            {"left": "67%", "top": "24%", "width": "30%", "height": "68%"},
        ]
    if n == 4:
        return [
            {"left": "4%", "top": "24%", "width": "44%", "height": "34%"},
            {"left": "52%", "top": "24%", "width": "44%", "height": "34%"},
            {"left": "4%", "bottom": "4%", "width": "44%", "height": "34%"},
            {"left": "52%", "bottom": "4%", "width": "44%", "height": "34%"},
        ]
    if n == 5:
        return [
            {"left": "3%", "top": "24%", "width": "30%", "height": "34%"},
            {"left": "35%", "top": "24%", "width": "30%", "height": "34%"},
            {"left": "67%", "top": "24%", "width": "30%", "height": "34%"},
            {"left": "18%", "bottom": "4%", "width": "30%", "height": "34%"},
            {"left": "52%", "bottom": "4%", "width": "30%", "height": "34%"},
        ]
    return GRIDS_2X3


def altura_grafico_multiproducto(n: int) -> str:
    if n <= 1:
        return "520px"
    if n <= 3:
        return "580px"
    return "720px"


def titulo_periodo_filtros(
    productos: list[str] | None,
    anio: int | None,
    meses: list[int] | None,
) -> str:
    partes = []
    if productos:
        if len(productos) == 1:
            partes.append(productos[0])
        else:
            partes.append(f"{len(productos)} productos")
    if meses:
        if len(meses) == 1:
            partes.append(MESES_ES[meses[0]])
        else:
            partes.append(f"{len(meses)} meses")
    if anio is not None:
        partes.append(str(anio))
    return " · ".join(partes) if partes else "Datos completos"


def widget_filtros_periodo(
    anios_disponibles: list[int],
    key_prefix: str,
) -> tuple[int | None, int | None]:
    """Filtro de año y un solo mes (selectbox)."""
    c1, c2 = st.columns(2)
    with c1:
        anio_sel = st.selectbox(
            "Año",
            ["Todos"] + [str(a) for a in sorted(anios_disponibles)],
            key=f"{key_prefix}_anio",
        )
    with c2:
        mes_sel = st.selectbox(
            "Mes",
            ["Todos"] + [MESES_ES[m] for m in range(1, 13)],
            key=f"{key_prefix}_mes",
        )
    anio = None if anio_sel == "Todos" else int(anio_sel)
    mes = None if mes_sel == "Todos" else next(k for k, v in MESES_ES.items() if v == mes_sel)
    return anio, mes


def widget_filtros_kpi(
    productos: list[str],
    anios_disponibles: list[int],
    key_prefix: str,
    mes_single: bool = False,
) -> tuple[list[str] | None, int | None, list[int] | None]:
    c1, c2, c3 = st.columns(3)
    with c1:
        prods_sel = st.multiselect(
            "Producto",
            productos,
            key=f"{key_prefix}_prod",
            placeholder="Todos los productos",
        )
    with c2:
        anio_sel = st.selectbox(
            "Año",
            ["Todos"] + [str(a) for a in sorted(anios_disponibles)],
            key=f"{key_prefix}_anio",
        )
    with c3:
        if mes_single:
            mes_sel = st.selectbox(
                "Mes",
                ["Todos"] + [MESES_ES[m] for m in range(1, 13)],
                key=f"{key_prefix}_mes",
            )
            meses = None if mes_sel == "Todos" else [next(k for k, v in MESES_ES.items() if v == mes_sel)]
        else:
            meses_sel = st.multiselect(
                "Mes",
                [MESES_ES[m] for m in range(1, 13)],
                key=f"{key_prefix}_mes",
                placeholder="Todos los meses",
            )
            meses = None if not meses_sel else [k for k, v in MESES_ES.items() if v in meses_sel]
    productos_f = prods_sel if prods_sel else None
    anio = None if anio_sel == "Todos" else int(anio_sel)
    return productos_f, anio, meses


def widget_filtros_estrategico_2(df_canal_cal: pd.DataFrame, key_prefix: str):
    productos = sorted(df_canal_cal["producto"].dropna().unique())
    calidades = sorted(df_canal_cal["calidad"].dropna().unique())
    canales = sorted(df_canal_cal["lugar_monitoreo"].dropna().unique())
    c1, c2, c3 = st.columns(3)
    with c1:
        prods = st.multiselect("Producto", productos, key=f"{key_prefix}_prod", placeholder="Todos")
    with c2:
        cals = st.multiselect("Calidad", calidades, key=f"{key_prefix}_cal", placeholder="Todas")
    with c3:
        chans = st.multiselect("Canal de venta", canales, key=f"{key_prefix}_canal", placeholder="Todos")
    return prods, cals, chans


def filtrar_estrategico_2(
    df: pd.DataFrame,
    productos: list[str],
    calidades: list[str],
    canales: list[str],
) -> pd.DataFrame:
    out = df.copy()
    if productos:
        out = out[out["producto"].isin(productos)]
    if calidades:
        out = out[out["calidad"].isin(calidades)]
    if canales:
        out = out[out["lugar_monitoreo"].isin(canales)]
    return out


def aplicar_filtros_kpi(
    df: pd.DataFrame,
    productos: list[str] | None,
    anio: int | None,
    meses: list[int] | None,
    col_producto: str = "producto",
    col_anio: str = "anio",
    col_mes: str = "mes_num",
) -> pd.DataFrame:
    out = df.copy()
    if productos:
        out = out[out[col_producto].isin(productos)]
    if anio is not None and col_anio in out.columns:
        out = out[out[col_anio] == anio]
    if meses and col_mes in out.columns:
        out = out[out[col_mes].isin(meses)]
    return out


def productos_para_grafico(productos: list[str], filtro: list[str] | None) -> list[str]:
    if filtro:
        return [p for p in productos if p in filtro]
    return list(productos)


def etiquetas_periodo(df: pd.DataFrame, anio_filtro: int | None, meses_filtro: list[int] | None) -> list[str]:
    if df.empty:
        return []
    if anio_filtro is None and not meses_filtro:
        return [f"{r.mes_nombre} {int(r.anio)}" for r in df.itertuples()]
    if meses_filtro and len(meses_filtro) == 1 and anio_filtro is not None:
        return df["mes_nombre"].tolist()
    if "mes_nombre" in df.columns and "anio" in df.columns:
        return [f"{r.mes_nombre} {int(r.anio)}" for r in df.itertuples()]
    if "mes_nombre" in df.columns:
        return df["mes_nombre"].tolist()
    return []


def render_header():
    col_logo, col_title, col_btn = st.columns([1, 9, 2])
    with col_logo:
        # URL corregida con el '?' antes de los parámetros
        logo_url = "https://cdn.discordapp.com/attachments/1085307260160446517/1518713022699409419/AgroTech_Logo.jpeg?ex=6a3aeb38&is=6a3999b8&hm=70b261da417af4b393818ad57d8da78841821f3b59fab9c16ce0d07a82c746b2&"
        st.image(logo_url, width=72)
    with col_title:
        st.markdown("## AgroTech — Tableros de KPIs")
        st.caption(
            "Visualización interactiva con ECharts · Filtros por mes, año y producto en KPIs tácticos y operativos"
        )
    with col_btn:
        st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
        if st.button("Recargar datos", use_container_width=True, key="btn_recargar"):
            st.cache_data.clear()
            st.rerun()


def preparar_df_analisis(df_raw: pd.DataFrame, n_inicial: int | None = None):
    df = df_raw[df_raw["producto"].notna()].drop_duplicates()
    df = df[df["producto"].str.lower() != "petroleo"]

    for col in ["precio_petroleo", "precio_petroleo_contexto", "tasa_cambio"]:
        if col in df.columns:
            df = df.drop(columns=[col])

    for col in ["precio", "temperatura", "humedad", "precipitaciones", "radiacion_uv"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "fecha" not in df.columns:
        raise RuntimeError("processed_data no trae columna 'fecha'.")

    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    if df["fecha"].isna().any() and {"año", "dia_año"}.issubset(df.columns):
        mask_sin_fecha = df["fecha"].isna()
        df.loc[mask_sin_fecha, "fecha"] = (
            pd.to_datetime(df.loc[mask_sin_fecha, "año"].astype(int).astype(str) + "-01-01")
            + pd.to_timedelta(df.loc[mask_sin_fecha, "dia_año"].astype(float) - 1, unit="D")
        )
    df["mes_num"] = df["fecha"].dt.month
    df["semana"] = df["fecha"].dt.isocalendar().week.astype(int)
    df["anio"] = df["fecha"].dt.year
    df["mes_nombre"] = df["fecha"].dt.month.map(MESES_ES)

    df = df.dropna(subset=["precio", "producto", "fecha"])
    df["precio_log"] = np.log1p(df["precio"])

    productos_lista = sorted(df["producto"].unique().tolist())
    features_climaticas = [
        c for c in ["temperatura", "humedad", "precipitaciones", "radiacion_uv"] if c in df.columns
    ]
    n_final = len(df)
    if n_inicial is None:
        n_inicial = len(df_raw)
    n_descartados = n_inicial - n_final
    pct_descartados = (n_descartados / n_inicial) * 100 if n_inicial else 0.0

    return df, productos_lista, features_climaticas, n_final, n_descartados, pct_descartados


def calcular_outliers_iqr(serie: pd.Series) -> int:
    q1, q3 = serie.quantile(0.25), serie.quantile(0.75)
    iqr = q3 - q1
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    return int(((serie < lower) | (serie > upper)).sum())


def _normalizar_iasc(s: pd.Series, invertir: bool = False) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce")
    valid = s.dropna()
    if valid.empty:
        return pd.Series(np.nan, index=s.index)
    lo, hi = float(valid.min()), float(valid.max())
    if hi == lo:
        out = pd.Series(50.0, index=s.index)
    else:
        out = (s - lo) / (hi - lo) * 100
    return (100 - out) if invertir else out


def _r2_test_ols(df_p: pd.DataFrame, features_climaticas: list[str]) -> float:
    """R² out-of-sample (80/20 temporal) — misma rutina OLS que proyecto_final.ipynb."""
    if sm is None or not features_climaticas:
        return np.nan
    df_p = df_p.dropna(subset=["precio_log"] + features_climaticas).sort_values("fecha")
    if len(df_p) < 30:
        return np.nan
    split_idx = max(1, int(len(df_p) * 0.8))
    train, test = df_p.iloc[:split_idx], df_p.iloc[split_idx:]
    if test.empty:
        return np.nan
    x_train = sm.add_constant(train[features_climaticas].astype(float), has_constant="add")
    x_test = sm.add_constant(test[features_climaticas].astype(float), has_constant="add")
    ols = sm.OLS(train["precio_log"], x_train).fit()
    return float(r2_score(test["precio_log"], ols.predict(x_test)))


def _semaforo_iasc(v: float) -> str:
    if pd.isna(v):
        return "—"
    if v >= 70:
        return "Verde"
    if v >= 40:
        return "Amarillo"
    return "Rojo"


def _recomendacion_iasc(row: pd.Series, cv_mediana: float) -> str:
    partes = []
    if pd.notna(row["Retorno PM ($)"]):
        partes.append(f"precio PM ${row['Retorno PM ($)']:,.0f} en {row['Canal margen']}")
    if pd.notna(row["CV% promedio"]):
        vol = "baja" if row["CV% promedio"] <= cv_mediana else "alta"
        partes.append(f"volatilidad {vol} (CV {row['CV% promedio']:.1f}%)")
    if pd.notna(row["R² clima (test)"]):
        clima = "alineada" if row["R² clima (test)"] >= 0.05 else "limitada"
        partes.append(f"viabilidad climática {clima} (R²={row['R² clima (test)']:.2f})")
    if row["IASC"] >= 70:
        accion = "Priorizar siembra/comercialización"
    elif row["IASC"] >= 40:
        accion = "Monitorear y ajustar canal"
    else:
        accion = "Postergar o reducir exposición"
    detalle = ", ".join(partes) if partes else "datos insuficientes"
    return f"{row['Producto']}: {detalle} → {accion}"


def _df_hasta_periodo(
    df: pd.DataFrame, anio_ref: int | None, mes_ref: int | None
) -> pd.DataFrame:
    """Registros acotados al periodo seleccionado."""
    if anio_ref is not None and mes_ref is not None:
        return df[
            (df["anio"] < anio_ref) | ((df["anio"] == anio_ref) & (df["mes_num"] <= mes_ref))
        ]
    if anio_ref is not None:
        return df[df["anio"] == anio_ref]
    if mes_ref is not None:
        return df[df["mes_num"] == mes_ref]
    return df


def kpi_estrategico_1_iasc(
    df: pd.DataFrame,
    productos_lista: list[str],
    features_climaticas: list[str],
    anio_ref: int | None = None,
    mes_ref: int | None = None,
) -> pd.DataFrame:
    """IASC — misma lógica que notebooks/proyecto_final.ipynb, con corte opcional por año/mes."""
    if not features_climaticas:
        raise RuntimeError(
            "No hay features climáticas en processed_data "
            "(temperatura, humedad, precipitaciones, radiacion_uv). "
            "El componente de viabilidad del IASC no puede calcularse."
        )
    df_canal_base = df.copy()
    if anio_ref is not None and mes_ref is not None:
        df_canal_base = df[
            (df["anio"] < anio_ref) | ((df["anio"] == anio_ref) & (df["mes_num"] <= mes_ref))
        ]
    elif anio_ref is not None:
        df_canal_base = df[df["anio"] <= anio_ref]
    elif mes_ref is not None:
        df_canal_base = df[df["mes_num"] <= mes_ref]
    canal_mes = (
        df_canal_base[df_canal_base["lugar_monitoreo"].isin(CANALES)]
        .groupby(["producto", "anio", "mes_num", "lugar_monitoreo"])["precio"]
        .mean()
        .unstack("lugar_monitoreo")
        .reset_index()
    )
    for c in CANALES:
        if c not in canal_mes.columns:
            canal_mes[c] = np.nan
    canal_mes["canal_margen"] = np.where(
        canal_mes["Supermercado"].fillna(-np.inf) >= canal_mes["Feria libre"].fillna(-np.inf),
        "Supermercado",
        "Feria libre",
    )
    canal_mes["precio_canal"] = np.where(
        canal_mes["canal_margen"] == "Supermercado",
        canal_mes["Supermercado"],
        canal_mes["Feria libre"],
    )
    canal_mes = canal_mes.sort_values(["producto", "anio", "mes_num"])
    canal_mes["retorno_pm"] = canal_mes.groupby("producto")["precio_canal"].transform(
        lambda s: s.rolling(VENTANA_PM_IASC, min_periods=1).mean()
    )
    if anio_ref is not None and mes_ref is not None:
        ref_canal = canal_mes[(canal_mes["anio"] == anio_ref) & (canal_mes["mes_num"] == mes_ref)]
        ultimo_canal = ref_canal.set_index("producto")
    elif anio_ref is not None:
        ultimo_canal = canal_mes[canal_mes["anio"] == anio_ref].groupby("producto").tail(1).set_index("producto")
    elif mes_ref is not None:
        ref_canal = canal_mes[canal_mes["mes_num"] == mes_ref].groupby("producto").tail(1)
        ultimo_canal = ref_canal.set_index("producto")
    else:
        ultimo_canal = canal_mes.groupby("producto").tail(1).set_index("producto")

    df_cv = _df_hasta_periodo(df, anio_ref, mes_ref)

    stats_mes = (
        df_cv.groupby(["producto", "anio", "mes_num"])["precio"]
        .agg(n="count", std="std", media="mean")
        .reset_index()
    )
    stats_mes = stats_mes[stats_mes["n"] >= 5]
    stats_mes["cv_pct"] = (stats_mes["std"] / stats_mes["media"] * 100).replace([np.inf, -np.inf], np.nan)
    cv_prod = stats_mes.groupby("producto")["cv_pct"].mean()
    cv_mediana = float(cv_prod.median()) if not cv_prod.empty else np.nan

    r2_prod = {
        prod: _r2_test_ols(
            _df_hasta_periodo(df[df["producto"] == prod], anio_ref, mes_ref),
            features_climaticas,
        )
        for prod in productos_lista
    }

    filas = []
    for prod in productos_lista:
        u = ultimo_canal.loc[prod] if prod in ultimo_canal.index else None
        filas.append({
            "Producto": prod,
            "Retorno PM ($)": u["retorno_pm"] if u is not None else np.nan,
            "Canal margen": u["canal_margen"] if u is not None else "—",
            "CV% promedio": cv_prod.get(prod, np.nan),
            "R² clima (test)": r2_prod.get(prod, np.nan),
        })

    df_iasc = pd.DataFrame(filas)
    df_iasc["Score retorno"] = _normalizar_iasc(df_iasc.set_index("Producto")["Retorno PM ($)"]).values
    df_iasc["Score estabilidad"] = _normalizar_iasc(
        df_iasc.set_index("Producto")["CV% promedio"], invertir=True
    ).values
    r2_clip = df_iasc["R² clima (test)"].clip(lower=0)
    df_iasc["Score viabilidad"] = _normalizar_iasc(r2_clip).values
    df_iasc["IASC"] = (
        PESOS_IASC["retorno"] * df_iasc["Score retorno"].fillna(0)
        + PESOS_IASC["estabilidad"] * df_iasc["Score estabilidad"].fillna(0)
        + PESOS_IASC["viabilidad"] * df_iasc["Score viabilidad"].fillna(0)
    ).round(1)
    df_iasc["Semáforo"] = df_iasc["IASC"].map(_semaforo_iasc)
    df_iasc["Recomendación"] = df_iasc.apply(
        lambda r: _recomendacion_iasc(r, cv_mediana), axis=1
    )
    return df_iasc.sort_values("IASC", ascending=False).reset_index(drop=True)


def kpi_estrategico_2(df: pd.DataFrame):
    df_canal_cal = (
        df.groupby(["producto", "lugar_monitoreo", "calidad"])["precio"]
        .agg(precio_promedio="mean", n="count")
        .reset_index()
    )
    df_canal_cal = df_canal_cal[df_canal_cal["n"] >= 5]
    brechas = []
    for (prod, cal), sub in df_canal_cal.groupby(["producto", "calidad"]):
        canales = sub.set_index("lugar_monitoreo")["precio_promedio"]
        if {"Supermercado", "Feria libre"}.issubset(canales.index):
            brechas.append({
                "producto": prod, "calidad": cal,
                "precio_feria": canales["Feria libre"],
                "precio_super": canales["Supermercado"],
                "brecha_$": canales["Supermercado"] - canales["Feria libre"],
                "n_total": sub["n"].sum(),
            })
    tabla_est2 = pd.DataFrame(brechas).sort_values(["producto", "calidad"]) if brechas else df_canal_cal.copy()
    return df_canal_cal, tabla_est2


def kpi_tactico_1(df: pd.DataFrame, productos_lista: list[str]):
    df_amp = df.copy()
    df_amp["semana_inicio"] = df_amp["fecha"] - pd.to_timedelta(df_amp["fecha"].dt.dayofweek, unit="D")
    tabla_amp = (
        df_amp.groupby(["producto", "anio", "mes_num", "semana", "semana_inicio"])["precio"]
        .agg(precio_max="max", precio_min="min", n="count")
        .reset_index()
    )
    tabla_amp["amplitud"] = (tabla_amp["precio_max"] - tabla_amp["precio_min"]).round(0)
    tabla_amp = tabla_amp[tabla_amp["n"] >= 3].copy()
    mediana_amp = tabla_amp.groupby("producto")["amplitud"].transform("median")
    tabla_amp["recomendacion"] = np.where(
        tabla_amp["amplitud"] >= mediana_amp, "Venta escalonada", "Concentrar venta"
    )
    return tabla_amp


def kpi_tactico_2(df: pd.DataFrame, productos_lista: list[str]):
    min_n_mes = 5
    stats_mes = (
        df.groupby(["producto", "anio", "mes_num", "mes_nombre"])["precio"]
        .agg(n="count", precio_medio="mean", std="std")
        .reset_index()
    )
    stats_mes["cv_pct"] = (stats_mes["std"] / stats_mes["precio_medio"] * 100).round(1)
    canal_mes = (
        df[df["lugar_monitoreo"].isin(CANALES)]
        .groupby(["producto", "anio", "mes_num", "lugar_monitoreo"])["precio"].mean()
        .unstack("lugar_monitoreo").reset_index()
    )
    for c in CANALES:
        if c not in canal_mes.columns:
            canal_mes[c] = np.nan
    canal_mes["precio_feria"] = canal_mes["Feria libre"].round(0)
    canal_mes["precio_super"] = canal_mes["Supermercado"].round(0)
    canal_mes["brecha_canal"] = (canal_mes["Supermercado"] - canal_mes["Feria libre"]).round(0)
    canal_mes["brecha_pct"] = np.where(
        canal_mes["Feria libre"] > 0,
        (canal_mes["brecha_canal"] / canal_mes["Feria libre"] * 100).round(1),
        np.nan,
    )
    kpi_t2 = stats_mes.merge(
        canal_mes[["producto", "anio", "mes_num", "precio_feria", "precio_super", "brecha_canal", "brecha_pct"]],
        on=["producto", "anio", "mes_num"],
        how="left",
    )
    kpi_t2 = kpi_t2[kpi_t2["n"] >= min_n_mes].sort_values(["producto", "anio", "mes_num"])
    cv_med = kpi_t2["cv_pct"].median()
    brecha_med = kpi_t2["brecha_canal"].abs().median()

    def zona_decision(row):
        cv_alto = row["cv_pct"] >= cv_med
        brecha_alta = abs(row["brecha_canal"]) >= brecha_med if pd.notna(row["brecha_canal"]) else False
        if cv_alto and brecha_alta:
            return "Volátil + priorizar supermercado"
        if cv_alto:
            return "Volátil + venta flexible"
        if brecha_alta:
            return "Estable + priorizar supermercado"
        return "Estable + contrato viable"

    kpi_t2["zona_decision"] = kpi_t2.apply(zona_decision, axis=1)
    return kpi_t2


def kpi_operativo_1(df: pd.DataFrame, productos_lista: list[str]):
    ref_mes = df.groupby(["producto", "anio", "mes_num"])["precio"].mean().reset_index(name="precio_referencial")
    df_venta = df.merge(ref_mes, on=["producto", "anio", "mes_num"], how="left")
    df_diario = (
        df_venta.groupby(["producto", "fecha", "anio", "mes_num"])
        .agg(precio=("precio", "mean"), precio_referencial=("precio_referencial", "mean"))
        .reset_index()
    )
    df_diario["estado"] = np.where(
        df_diario["precio"] >= df_diario["precio_referencial"],
        "Sobre precio referencial",
        "Bajo precio referencial",
    )
    return df_diario


def evaluar_cosecha(row):
    u = UMBRALES_COSECHA.get(row["producto"], {"temp_min": 10, "temp_max": 30, "hum_max": 80})
    ok_t = u["temp_min"] <= row["temperatura"] <= u["temp_max"]
    ok_h = row["humedad"] <= u["hum_max"]
    if ok_t and ok_h:
        return "Óptimo"
    if ok_t or ok_h:
        return "Parcial"
    return "No óptimo"


def kpi_operativo_2(df: pd.DataFrame, productos_lista: list[str]):
    rows = []
    for _, r in df.dropna(subset=["temperatura", "humedad"]).iterrows():
        u = UMBRALES_COSECHA.get(r["producto"], {"temp_min": 10, "temp_max": 30, "hum_max": 80})
        rows.append({
            "producto": r["producto"],
            "calidad": r["calidad"] if pd.notna(r.get("calidad", np.nan)) else "—",
            "fecha": r["fecha"].date() if hasattr(r["fecha"], "date") else r["fecha"],
            "temperatura": round(r["temperatura"], 1),
            "humedad": round(r["humedad"], 1),
            "temp_optima": u["temp_min"] <= r["temperatura"] <= u["temp_max"],
            "hum_optima": r["humedad"] <= u["hum_max"],
            "estado_cosecha": evaluar_cosecha(r),
        })
    tablero_oper2 = pd.DataFrame(rows)
    tablero_oper2["fecha_dt"] = pd.to_datetime(tablero_oper2["fecha"])
    tablero_oper2["anio"] = tablero_oper2["fecha_dt"].dt.year
    tablero_oper2["mes_num"] = tablero_oper2["fecha_dt"].dt.month
    return tablero_oper2


# ── ECharts builders ─────────────────────────────────────────────────────────

def _style_axis(ax: dict) -> dict:
    ax.setdefault("axisLine", {"lineStyle": {"color": COLOR_GRID}})
    ax.setdefault("axisLabel", {}).setdefault("color", COLOR_EJE)
    ax.setdefault("nameTextStyle", {"color": COLOR_EJE})
    ax.setdefault("splitLine", {"lineStyle": {"color": COLOR_GRID, "type": "dashed", "opacity": 0.9}})
    return ax


def _apply_chart_theme(opt: dict) -> dict:
    opt["backgroundColor"] = "#ffffff"
    opt.setdefault("textStyle", {"color": COLOR_TEXTO_GRAF})
    title = opt.get("title")
    if isinstance(title, dict):
        title.setdefault("textStyle", {})["color"] = COLOR_TEXTO_GRAF
        title.setdefault("subtextStyle", {})["color"] = "#666666"
    for key in ("xAxis", "yAxis"):
        axes = opt.get(key, [])
        if isinstance(axes, dict):
            axes = [axes]
        opt[key] = [_style_axis(ax) for ax in axes]
    legend = opt.get("legend")
    if isinstance(legend, dict):
        legend.setdefault("textStyle", {})["color"] = COLOR_EJE
    return opt


def inject_app_light_theme():
    st.markdown(
        """
        <style>
        .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            background-color: #ffffff !important;
        }
        [data-testid="stSidebar"], [data-testid="collapsedControl"] {
            display: none !important;
        }
        iframe[src*="streamlit_echarts"] {
            background-color: #ffffff !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _base_chart(title: str, height: str = "520px") -> dict:
    return _apply_chart_theme({
        "title": {"text": title, "left": "center", "top": 0, "textStyle": {"fontSize": 13}},
        "tooltip": {"trigger": "item", "backgroundColor": "#fff", "borderColor": COLOR_GRID, "textStyle": {"color": COLOR_TEXTO_GRAF}},
        "grid": {"left": "8%", "right": "6%", "bottom": "12%", "top": "14%", "containLabel": True},
    })


def chart_estrategico_1_iasc(df_iasc: pd.DataFrame, subtitulo_periodo: str = "") -> dict:
    if df_iasc.empty:
        return _base_chart("KPI Estratégico 1 (IASC): sin datos disponibles")

    df_plot = df_iasc.sort_values("IASC", ascending=True)
    bar_data = [
        {
            "value": float(row["IASC"]),
            "itemStyle": {"color": SEMAFORO_IASC_COLOR.get(row["Semáforo"], "#9E9E9E")},
        }
        for _, row in df_plot.iterrows()
    ]

    titulo = (
        "KPI Estratégico 1: IASC — Índice de Atractivo de Siembra y Comercialización\n"
        "40% retorno canal · 35% estabilidad (CV%) · 25% viabilidad climática (R² OLS)"
    )
    if subtitulo_periodo:
        titulo += f"\n{subtitulo_periodo}"

    opt = _base_chart(titulo)
    opt["grid"] = {"left": "14%", "right": "10%", "bottom": "8%", "top": "18%", "containLabel": True}
    opt["tooltip"] = {"trigger": "axis", "axisPointer": {"type": "shadow"}}
    opt["xAxis"] = {"type": "value", "max": 100, "name": "IASC (1 – 100)"}
    opt["yAxis"] = {"type": "category", "data": df_plot["Producto"].tolist()}
    opt["series"] = [{
        "type": "bar",
        "data": bar_data,
        "label": {
            "show": True,
            "position": "right",
            "formatter": JsCode(
                "function(p){ return Number(p.value).toFixed(1); }"
            ).js_code,
        },
        "barMaxWidth": 28,
    }]
    return opt


def chart_estrategico_2(df_canal_cal: pd.DataFrame) -> dict:
    if df_canal_cal.empty:
        return _base_chart("KPI Estratégico 2: sin datos con los filtros seleccionados")

    productos = sorted(df_canal_cal["producto"].unique())
    combos = sorted(
        df_canal_cal[["calidad", "lugar_monitoreo"]].drop_duplicates().values.tolist(),
        key=lambda r: (str(r[0]), str(r[1])),
    )
    series = []
    for i, (cal, canal) in enumerate(combos):
        sub = df_canal_cal[(df_canal_cal["calidad"] == cal) & (df_canal_cal["lugar_monitoreo"] == canal)]
        by_prod = sub.set_index("producto")["precio_promedio"]
        series.append({
            "name": f"{cal} — {canal}",
            "type": "bar",
            "data": [round(by_prod[p], 0) if p in by_prod.index else None for p in productos],
            "itemStyle": {"color": PALETTE[i % len(PALETTE)], "borderColor": "#333", "borderWidth": 0.5},
            "barMaxWidth": 28,
        })
    opt = _base_chart("KPI Estratégico 2: Precio promedio por producto, calidad y canal")
    opt["tooltip"] = {"trigger": "axis", "axisPointer": {"type": "shadow"}}
    opt["legend"] = {"top": "bottom", "type": "scroll", "data": [s["name"] for s in series]}
    opt["xAxis"] = {"type": "category", "data": productos, "axisLabel": {"rotate": 20, "interval": 0}}
    opt["yAxis"] = {"type": "value", "name": "Precio promedio ($ CLP)"}
    opt["series"] = series
    return opt


def _parse_height_px(height: str) -> int:
    digits = "".join(ch for ch in height if ch.isdigit())
    return int(digits) if digits else 520


def _sanitize_echarts(obj):
    """Convierte numpy/pandas a tipos JSON nativos (evita fallos silenciosos)."""
    if isinstance(obj, JsCode):
        return obj
    if isinstance(obj, dict):
        return {k: _sanitize_echarts(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_echarts(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        val = float(obj)
        return None if np.isnan(val) else val
    if isinstance(obj, np.ndarray):
        return _sanitize_echarts(obj.tolist())
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    return obj


def render_echart(options: dict, height: str, key: str, events: dict | None = None):
    px = _parse_height_px(height)
    st.markdown(
        f"""
        <style>
        div[data-testid="stCustomComponentV1"]:has(iframe[src*="streamlit_echarts"]) iframe {{
            height: {px}px !important;
            min-height: {px}px !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    return st_echarts(
        options=_apply_chart_theme(_sanitize_echarts(options)),
        height=height,
        key=key,
        theme=ECHARTS_THEME,
        events=events or {},
    )


def _grid_axes(n: int):
    x_axes = [
        {"type": "category", "gridIndex": i, "axisLabel": {"fontSize": 9, "rotate": 35}}
        for i in range(n)
    ]
    y_axes = [
        {
            "type": "value",
            "gridIndex": i,
            "splitLine": {"lineStyle": {"type": "dashed", "opacity": 0.35}},
        }
        for i in range(n)
    ]
    return x_axes, y_axes


def _product_labels_graphic(productos: list[str], grids: list[dict]) -> list[dict]:
    graphics = []
    for idx, prod in enumerate(productos):
        g = grids[idx]
        left_pct = float(g["left"].replace("%", ""))
        width_pct = float(g["width"].replace("%", ""))
        center_left = f"{left_pct + width_pct / 2}%"
        if "top" in g:
            top_pct = max(float(g["top"].replace("%", "")) - 7, 2)
            top = f"{top_pct}%"
        else:
            bottom_pct = float(g["bottom"].replace("%", ""))
            height_pct = float(g["height"].replace("%", ""))
            top = f"{100 - bottom_pct - height_pct - 7}%"
        graphics.append({
            "type": "text",
            "left": center_left,
            "top": top,
            "style": {
                "text": prod,
                "fontSize": 14,
                "fontWeight": "bold",
                "fill": COLOR_TEXTO_GRAF,
                "textAlign": "center",
            },
        })
    return graphics


def _multi_grid_option(
    title: str,
    productos: list[str],
    x_axes: list,
    y_axes: list,
    series: list,
    subtext: str | None = None,
    legend: dict | None = None,
    tooltip: str = "axis",
) -> dict:
    n = max(len(productos), 1)
    grids = _layout_grids(n)
    opt = {
        "title": {
            "text": title,
            "subtext": subtext or "",
            "left": "center",
            "top": 0,
            "textStyle": {"fontSize": 13},
            "subtextStyle": {"fontSize": 11},
        },
        "tooltip": {"trigger": tooltip},
        "grid": grids,
        "xAxis": x_axes[:n],
        "yAxis": y_axes[:n],
        "series": series,
        "graphic": _product_labels_graphic(productos[:n], grids),
    }
    if legend:
        opt["legend"] = legend
    return _apply_chart_theme(opt)


def chart_tactico_1_grid(
    tabla_amp: pd.DataFrame,
    productos: list[str],
    titulo_periodo: str,
    anio_filtro: int | None,
    meses_filtro: list[int] | None,
) -> dict:
    n = max(len(productos), 1)
    x_axes, y_axes = _grid_axes(n)
    series = []
    for idx, prod in enumerate(productos):
        sub = tabla_amp[tabla_amp["producto"] == prod].sort_values("semana_inicio")
        y_axes[idx]["name"] = "Amplitud ($ CLP)"
        if sub.empty:
            x_axes[idx]["data"] = ["Sin datos"]
            continue
        if anio_filtro is not None and meses_filtro and len(meses_filtro) == 1:
            labels = sub["semana_inicio"].dt.strftime("%d-%m").tolist()
        else:
            labels = [
                f"{row.semana_inicio.strftime('%d-%m')} ({MESES_ES.get(int(row.mes_num), '')[:3]})"
                for row in sub.itertuples()
            ]
        x_axes[idx]["data"] = labels
        x_axes[idx]["name"] = "Semanas"
        x_axes[idx]["nameGap"] = 20
        bar_data = [
            {
                "value": float(row["amplitud"]),
                "itemStyle": {
                    "color": COLOR_ESCALONADA if row["recomendacion"] == "Venta escalonada" else COLOR_CONCENTRAR,
                    "borderColor": "#333",
                    "borderWidth": 0.3,
                },
            }
            for _, row in sub.iterrows()
        ]
        series.append({
            "type": "bar",
            "xAxisIndex": idx,
            "yAxisIndex": idx,
            "data": bar_data,
            "barMaxWidth": 22,
        })
    return _multi_grid_option(
        f"KPI Táctico 1: Amplitud semanal (máx − mín) — {titulo_periodo}",
        productos,
        x_axes,
        y_axes,
        series,
        subtext="Verde = concentrar venta | Coral = venta escalonada",
    )


def chart_tactico_2_cv_grid(
    kpi_t2: pd.DataFrame,
    productos: list[str],
    titulo_periodo: str,
    anio_filtro: int | None,
    meses_filtro: list[int] | None,
) -> dict:
    n = max(len(productos), 1)
    x_axes, y_axes = _grid_axes(n)
    series = []
    for idx, prod in enumerate(productos):
        sub = kpi_t2[kpi_t2["producto"] == prod].sort_values(["anio", "mes_num"])
        y_axes[idx]["name"] = "CV %"
        if sub.empty:
            x_axes[idx]["data"] = ["Sin datos"]
            continue
        x_axes[idx]["data"] = etiquetas_periodo(sub, anio_filtro, meses_filtro)
        series.append({
            "type": "bar",
            "xAxisIndex": idx,
            "yAxisIndex": idx,
            "data": sub["cv_pct"].tolist(),
            "itemStyle": {"color": PALETTE[0], "opacity": 0.9, "borderColor": "#ccc", "borderWidth": 0.3},
            "barMaxWidth": 20,
        })
    return _multi_grid_option(
        f"KPI Táctico 2 — Variabilidad mensual (CV%) — {titulo_periodo}",
        productos,
        x_axes,
        y_axes,
        series,
    )


def chart_tactico_2_brecha_grid(
    kpi_t2: pd.DataFrame,
    productos: list[str],
    titulo_periodo: str,
    anio_filtro: int | None,
    meses_filtro: list[int] | None,
) -> dict:
    n = max(len(productos), 1)
    x_axes, y_axes = _grid_axes(n)
    series = []
    for idx, prod in enumerate(productos):
        sub = kpi_t2[kpi_t2["producto"] == prod].dropna(subset=["precio_feria", "precio_super"]).sort_values(
            ["anio", "mes_num"]
        )
        y_axes[idx]["name"] = "Precio ($ CLP)"
        if sub.empty:
            x_axes[idx]["data"] = ["Sin datos"]
            continue
        x_axes[idx]["data"] = etiquetas_periodo(sub, anio_filtro, meses_filtro)
        series.extend([
            {
                "name": "Feria libre",
                "type": "line",
                "xAxisIndex": idx,
                "yAxisIndex": idx,
                "data": sub["precio_feria"].tolist(),
                "symbol": "circle",
                "symbolSize": 7,
                "lineStyle": {"color": COLOR_FERIA, "width": 2},
                "itemStyle": {"color": COLOR_FERIA},
            },
            {
                "name": "Supermercado",
                "type": "line",
                "xAxisIndex": idx,
                "yAxisIndex": idx,
                "data": sub["precio_super"].tolist(),
                "symbol": "rect",
                "symbolSize": 7,
                "lineStyle": {"color": COLOR_SUPER, "width": 2},
                "itemStyle": {"color": COLOR_SUPER},
            },
        ])
        brecha_pts = []
        for i, row in enumerate(sub.itertuples()):
            if pd.notna(row.brecha_canal):
                y_mid = (row.precio_feria + row.precio_super) / 2
                brecha_pts.append({
                    "value": [i, y_mid],
                    "label": {
                        "show": True,
                        "formatter": f"${row.brecha_canal:,.0f}\n({row.brecha_pct:.0f}%)",
                        "fontSize": 8,
                        "color": COLOR_REF_MENSUAL,
                        "position": "top",
                    },
                    "itemStyle": {"color": "transparent"},
                })
        if brecha_pts:
            series.append({
                "type": "scatter",
                "xAxisIndex": idx,
                "yAxisIndex": idx,
                "data": brecha_pts,
                "symbolSize": 1,
                "tooltip": {"show": False},
            })
    return _multi_grid_option(
        f"KPI Táctico 2 — Brecha mensual Feria vs. Supermercado — {titulo_periodo}",
        productos,
        x_axes,
        y_axes,
        series,
        subtext="Etiquetas = monto ($) y porcentaje de brecha",
        legend={"data": ["Feria libre", "Supermercado"], "top": 40},
    )


def chart_operativo_1_grid(
    df_diario: pd.DataFrame, productos: list[str], titulo_periodo: str
) -> dict:
    n = max(len(productos), 1)
    x_axes, y_axes = _grid_axes(n)
    series = []
    for idx, prod in enumerate(productos):
        sub = df_diario[df_diario["producto"] == prod].sort_values("fecha")
        y_axes[idx]["name"] = "Precio ($ CLP)"
        if sub.empty:
            x_axes[idx]["data"] = ["Sin datos"]
            continue
        x_axes[idx]["data"] = sub["fecha"].dt.strftime("%d-%m").tolist()
        x_axes[idx]["name"] = "Fecha"
        x_axes[idx]["nameGap"] = 20
        series.extend([
            {
                "name": "Precio día",
                "type": "line",
                "xAxisIndex": idx,
                "yAxisIndex": idx,
                "data": sub["precio"].round(0).tolist(),
                "symbol": "circle",
                "symbolSize": 6,
                "lineStyle": {"color": COLOR_PRECIO_DIA, "width": 2},
                "itemStyle": {"color": COLOR_PRECIO_DIA},
                "z": 2,
            },
            {
                "name": "Ref. mensual",
                "type": "line",
                "xAxisIndex": idx,
                "yAxisIndex": idx,
                "data": sub["precio_referencial"].round(0).tolist(),
                "step": "end",
                "lineStyle": {"color": COLOR_REF_MENSUAL, "type": "dashed", "width": 2},
                "itemStyle": {"color": COLOR_REF_MENSUAL},
                "showSymbol": False,
                "z": 1,
            },
        ])
        bajo_pts = [
            [i, round(row.precio, 0)]
            for i, row in enumerate(sub.itertuples())
            if row.estado == "Bajo precio referencial"
        ]
        if bajo_pts:
            series.append({
                "name": "Bajo ref.",
                "type": "scatter",
                "xAxisIndex": idx,
                "yAxisIndex": idx,
                "data": bajo_pts,
                "symbolSize": 10,
                "itemStyle": {"color": COLOR_NO_OPTIMO},
            })
    return _multi_grid_option(
        f"KPI Operativo 1: Precio diario vs. referencial — {titulo_periodo}",
        productos,
        x_axes,
        y_axes,
        series,
        subtext="Puntos rojos = bajo precio referencial (no conviene vender)",
        legend={"data": ["Precio día", "Ref. mensual", "Bajo ref."], "top": 40},
    )


def chart_operativo_2_grid(
    tablero_oper2: pd.DataFrame, productos: list[str], titulo_periodo: str
) -> dict:
    graf = tablero_oper2.copy()
    if "fecha_dt" not in graf.columns:
        graf["fecha_dt"] = pd.to_datetime(graf["fecha"])
    n = max(len(productos), 1)
    x_axes = [
        {
            "type": "value",
            "gridIndex": i,
            "name": "Temp (°C)",
            "splitLine": {"lineStyle": {"type": "dashed", "opacity": 0.35}},
        }
        for i in range(n)
    ]
    y_axes = [
        {
            "type": "value",
            "gridIndex": i,
            "name": "Humedad (%)",
            "splitLine": {"lineStyle": {"type": "dashed", "opacity": 0.35}},
        }
        for i in range(n)
    ]
    estado_color = {"Óptimo": COLOR_OPTIMO, "Parcial": COLOR_PARCIAL, "No óptimo": COLOR_NO_OPTIMO}
    series = []
    for idx, prod in enumerate(productos):
        sub = graf[graf["producto"] == prod]
        if sub.empty:
            continue
        u = UMBRALES_COSECHA.get(prod, {"temp_min": 10, "temp_max": 30, "hum_max": 80})
        scatter_data = [
            {
                "value": [row["temperatura"], row["humedad"]],
                "id": int(row["_punto_id"]),
                "itemStyle": {
                    "color": estado_color.get(row["estado_cosecha"], "#888"),
                    "borderColor": "#333",
                    "borderWidth": 0.5,
                },
            }
            for _, row in sub.iterrows()
        ]
        series.append({
            "type": "scatter",
            "xAxisIndex": idx,
            "yAxisIndex": idx,
            "data": scatter_data,
            "symbolSize": 10,
            "markLine": {
                "silent": True,
                "symbol": "none",
                "lineStyle": {"color": "#999", "type": "dotted"},
                "data": [
                    {"xAxis": u["temp_min"]},
                    {"xAxis": u["temp_max"]},
                    {"yAxis": u["hum_max"]},
                ],
            },
        })
    series.extend([
        {"name": "Óptimo", "type": "scatter", "xAxisIndex": 0, "yAxisIndex": 0, "data": [], "itemStyle": {"color": COLOR_OPTIMO}},
        {"name": "Parcial", "type": "scatter", "xAxisIndex": 0, "yAxisIndex": 0, "data": [], "itemStyle": {"color": COLOR_PARCIAL}},
        {"name": "No óptimo", "type": "scatter", "xAxisIndex": 0, "yAxisIndex": 0, "data": [], "itemStyle": {"color": COLOR_NO_OPTIMO}},
    ])
    return _multi_grid_option(
        f"KPI Operativo 2: Condiciones de cosecha — {titulo_periodo}",
        productos,
        x_axes,
        y_axes,
        series,
        legend={"data": ["Óptimo", "Parcial", "No óptimo"], "top": 40},
        tooltip="item",
    )


OPER2_CLICK_EVENT = {
    "click": "function(p){ return p.data && p.data.id != null ? p.data.id : null; }",
}


# ── Tableros formateados ─────────────────────────────────────────────────────

def formato_tablero_est1_resumen(df_iasc: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "Producto", "IASC", "Semáforo", "Retorno PM ($)", "Canal margen",
        "CV% promedio", "R² clima (test)", "Recomendación",
    ]
    t = df_iasc[cols].copy()
    t["Retorno PM ($)"] = t["Retorno PM ($)"].map(lambda x: f"${x:,.0f}" if pd.notna(x) else "—")
    t["CV% promedio"] = t["CV% promedio"].map(lambda x: f"{x:.1f}%" if pd.notna(x) else "—")
    t["R² clima (test)"] = t["R² clima (test)"].map(lambda x: f"{x:.3f}" if pd.notna(x) else "—")
    t["IASC"] = t["IASC"].map(lambda x: f"{x:.1f}" if pd.notna(x) else "—")
    return t


def formato_tablero_est1_detalle(row: pd.Series) -> pd.DataFrame:
    """Fila transuesta como en proyecto_final.ipynb (desglose por producto)."""
    cols = [
        "Producto", "IASC", "Semáforo", "Retorno PM ($)", "Canal margen",
        "CV% promedio", "R² clima (test)", "Recomendación",
    ]
    det = row[cols].to_frame()
    det.columns = ["Valor"]
    det.loc["Retorno PM ($)", "Valor"] = (
        f"${row['Retorno PM ($)']:,.0f}" if pd.notna(row["Retorno PM ($)"]) else "—"
    )
    det.loc["CV% promedio", "Valor"] = (
        f"{row['CV% promedio']:.1f}%" if pd.notna(row["CV% promedio"]) else "—"
    )
    det.loc["R² clima (test)", "Valor"] = (
        f"{row['R² clima (test)']:.6f}" if pd.notna(row["R² clima (test)"]) else "—"
    )
    det.loc["IASC", "Valor"] = f"{row['IASC']:.4f}" if pd.notna(row["IASC"]) else "—"
    return det


def formato_tablero_est2(tabla_est2: pd.DataFrame, brechas: bool) -> pd.DataFrame:
    t = tabla_est2.copy()
    if brechas:
        for col in ["precio_feria", "precio_super", "brecha_$"]:
            t[col] = t[col].map(lambda x: f"${x:,.0f}")
    else:
        t = t.round({"precio_promedio": 0})
    return t


def formato_tablero_tact1(tabla_amp: pd.DataFrame) -> pd.DataFrame:
    t = tabla_amp[["producto", "semana", "mes_num", "anio", "amplitud", "recomendacion"]].sort_values(["producto", "anio", "semana"]).copy()
    t["mes_nombre"] = t["mes_num"].map(MESES_ES)
    t = t.drop(columns=["mes_num"])
    t["amplitud"] = t["amplitud"].map(lambda x: f"${x:,.0f}")
    return t[["producto", "semana", "mes_nombre", "anio", "amplitud", "recomendacion"]]


def formato_tablero_tact2(kpi_t2: pd.DataFrame) -> pd.DataFrame:
    t = kpi_t2[
        ["producto", "anio", "mes_nombre", "n", "cv_pct", "precio_feria", "precio_super", "brecha_canal", "brecha_pct", "zona_decision"]
    ].copy()
    t["cv_pct"] = t["cv_pct"].map(lambda x: f"{x:.1f}%")
    t["precio_feria"] = t["precio_feria"].map(lambda x: f"${x:,.0f}" if pd.notna(x) else "—")
    t["precio_super"] = t["precio_super"].map(lambda x: f"${x:,.0f}" if pd.notna(x) else "—")
    t["brecha_canal"] = t["brecha_canal"].map(lambda x: f"${x:,.0f}" if pd.notna(x) else "—")
    t["brecha_pct"] = t["brecha_pct"].map(lambda x: f"{x:.1f}%" if pd.notna(x) else "—")
    return t


def formato_tablero_oper1(df_diario_graf: pd.DataFrame) -> pd.DataFrame:
    t = df_diario_graf[["producto", "fecha", "precio", "precio_referencial", "estado"]].copy()
    t["fecha"] = pd.to_datetime(t["fecha"]).dt.strftime("%Y-%m-%d")
    t["precio"] = t["precio"].round(0).map(lambda x: f"${x:,.0f}")
    t["precio_referencial"] = t["precio_referencial"].round(0).map(lambda x: f"${x:,.0f}")
    return t


def estilo_tablero_oper1(df_diario: pd.DataFrame):
    """Colores de la columna estado igual que proyecto_final.ipynb."""
    t = formato_tablero_oper1(df_diario)

    def _color_estado(val):
        if val == "Bajo precio referencial":
            return "color: red"
        if val == "Sobre precio referencial":
            return "color: green"
        return ""

    return t.style.applymap(_color_estado, subset=["estado"])


def formato_tablero_oper2(tablero_oper2_graf: pd.DataFrame) -> pd.DataFrame:
    t = tablero_oper2_graf.drop(columns=["fecha_dt", "anio", "mes_num", "_punto_id"], errors="ignore").copy()
    t = t.rename(columns={"temp_optima": "temperatura optima", "hum_optima": "humedad optima"})
    t = t[["producto", "calidad", "fecha", "temperatura", "humedad", "temperatura optima", "humedad optima", "estado_cosecha"]]
    t["temperatura"] = t["temperatura"].map(lambda v: f"{v:.1f}°C")
    t["humedad"] = t["humedad"].map(lambda h: f"{int(round(h))}%")
    t["temperatura optima"] = t["temperatura optima"].map({True: "Si", False: "No"})
    t["humedad optima"] = t["humedad optima"].map({True: "Si", False: "No"})
    return t


def estilo_tablero_oper2(tablero_oper2: pd.DataFrame):
    """Color solo en la columna estado_cosecha (sin fondo de fila)."""
    t = formato_tablero_oper2(tablero_oper2)

    def _color_estado_cosecha(val):
        if val == "Óptimo":
            return "color: green"
        if val == "Parcial":
            return "color: #DAA520"
        if val == "No óptimo":
            return "color: red"
        return ""

    return t.style.applymap(_color_estado_cosecha, subset=["estado_cosecha"])


# ── Carga de datos ───────────────────────────────────────────────────────────

@st.cache_data(show_spinner="Cargando datos desde MongoDB…")
def cargar_pipeline(_pipeline_version: str = "iasc-filtros-v1"):
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=15000)
    client.admin.command("ping")
    db = client[DB_NAME]
    df_raw = pd.DataFrame(list(db[PROCESSED_COLLECTION].find({})))
    if df_raw.empty:
        raise ValueError("La colección procesada está vacía.")
    n_inicial = len(df_raw)
    df, productos_lista, features_climaticas, n_final, n_descartados, pct_descartados = preparar_df_analisis(
        df_raw, n_inicial
    )
    if "calidad" not in df.columns:
        raise RuntimeError("Se requiere la columna 'calidad' para KPI Estratégico 2.")
    df_canal_cal, tabla_est2 = kpi_estrategico_2(df)
    brechas_ok = "brecha_$" in tabla_est2.columns
    tabla_amp = kpi_tactico_1(df, productos_lista)
    kpi_t2 = kpi_tactico_2(df, productos_lista)
    df_diario = kpi_operativo_1(df, productos_lista)
    tablero_oper2 = kpi_operativo_2(df, productos_lista)
    anios = sorted(
        {
            int(a)
            for a in pd.concat([
                tabla_amp["anio"],
                kpi_t2["anio"],
                df_diario["anio"],
                tablero_oper2["anio"],
            ]).dropna().unique()
        }
    )
    return {
        "meta": {
            "n_inicial": n_inicial, "n_final": n_final,
            "n_descartados": n_descartados, "pct_descartados": pct_descartados,
            "fecha_min": df["fecha"].min(), "fecha_max": df["fecha"].max(),
            "productos": productos_lista,
            "anios": anios,
            "features_climaticas": features_climaticas,
        },
        "df": df,
        "df_canal_cal": df_canal_cal,
        "tabla_est2": tabla_est2,
        "brechas_ok": brechas_ok,
        "tabla_amp": tabla_amp,
        "kpi_t2": kpi_t2,
        "df_diario": df_diario,
        "tablero_oper2": tablero_oper2,
    }


# ── App Streamlit ────────────────────────────────────────────────────────────

def _df_to_csv(df: pd.DataFrame) -> str:
    return df.to_csv(index=False).encode("utf-8")


def main():
    st.set_page_config(page_title="AgroTech Tableros", page_icon="🌾", layout="wide")
    inject_app_light_theme()
    render_header()

    try:
        data = cargar_pipeline()
    except Exception as exc:
        st.error(f"No se pudieron cargar los datos: {exc}")
        st.info("Verifica MONGO_URI en `.env` y que MongoDB tenga datos en `processed_data`.")
        return

    meta = data["meta"]
    productos = meta["productos"]
    st.markdown(
        f"**Registros:** {meta['n_final']:,} agrícolas puros "
        f"({meta['pct_descartados']:.1f}% descartados en limpieza) · "
        f"**Rango:** {meta['fecha_min'].date()} → {meta['fecha_max'].date()} · "
        f"**Productos:** {', '.join(productos)}"
    )

    seccion = st.radio(
        "Nivel KPI",
        ["Estratégico", "Táctico", "Operativo"],
        horizontal=True,
        key="seccion_kpi",
    )

    if seccion == "Estratégico":
        anios = meta["anios"]
        features_climaticas = meta["features_climaticas"]

        st.subheader("KPI Estratégico 1 — IASC (Índice de Atractivo de Siembra y Comercialización)")
        if sm is None:
            st.warning(
                "Falta `statsmodels`. Ejecuta `pip install statsmodels` y pulsa **Recargar datos** "
                "para que R² clima e IASC coincidan con proyecto_final.ipynb."
            )
        anio_est1, mes_est1 = widget_filtros_periodo(anios, "est1")
        titulo_est1 = titulo_periodo_filtros(None, anio_est1, [mes_est1] if mes_est1 else None)
        df_iasc = kpi_estrategico_1_iasc(
            data["df"], productos, features_climaticas, anio_est1, mes_est1
        )
        filtro_key = f"{anio_est1}_{mes_est1}"
        render_echart(
            chart_estrategico_1_iasc(df_iasc, titulo_est1),
            height="480px",
            key=_clean_key(f"est1_iasc_{filtro_key}"),
        )
        st.markdown(f"**Tablero estratégico 1 — IASC** ({titulo_est1})")
        st.dataframe(formato_tablero_est1_resumen(df_iasc), use_container_width=True, hide_index=True)
        st.download_button("📥 Exportar IASC CSV", _df_to_csv(df_iasc), "iasc_resumen.csv", "text/csv")

        st.markdown("**Desglose por producto** (selecciona en el menú):")
        productos_iasc = df_iasc["Producto"].tolist()
        prod_iasc = st.selectbox("Producto", productos_iasc, key="est1_prod_detalle")
        fila_iasc = df_iasc[df_iasc["Producto"] == prod_iasc].iloc[0]
        st.caption(fila_iasc["Recomendación"])
        st.dataframe(formato_tablero_est1_detalle(fila_iasc), use_container_width=True)

        st.divider()
        st.subheader("KPI Estratégico 2 — Brecha por canal y calidad")
        prods_e2, cals_e2, chans_e2 = widget_filtros_estrategico_2(data["df_canal_cal"], "est2")
        df_canal_f = filtrar_estrategico_2(data["df_canal_cal"], prods_e2, cals_e2, chans_e2)
        render_echart(
            chart_estrategico_2(df_canal_f),
            height="520px",
            key=_clean_key(f"est2_{','.join(prods_e2)}_{','.join(map(str,cals_e2))}_{','.join(chans_e2)}"),
        )
        st.markdown("**Tablero estratégico 2**")
        if data["brechas_ok"]:
            tabla_e2 = data["tabla_est2"]
            if prods_e2:
                tabla_e2 = tabla_e2[tabla_e2["producto"].isin(prods_e2)]
            if cals_e2:
                tabla_e2 = tabla_e2[tabla_e2["calidad"].isin(cals_e2)]
        else:
            tabla_e2 = df_canal_f
        st.dataframe(
            formato_tablero_est2(tabla_e2, data["brechas_ok"]),
            use_container_width=True,
            hide_index=True,
        )
        st.download_button("📥 Exportar Brechas CSV", _df_to_csv(tabla_e2), "brechas_canal_calidad.csv", "text/csv")

    elif seccion == "Táctico":
        anios = meta["anios"]

        st.subheader("KPI Táctico 1 — Amplitud de mercado semanal")
        prods_t1, anio_t1, meses_t1 = widget_filtros_kpi(productos, anios, "tac1")
        titulo_t1 = titulo_periodo_filtros(prods_t1, anio_t1, meses_t1)
        tabla_t1 = aplicar_filtros_kpi(data["tabla_amp"], prods_t1, anio_t1, meses_t1)
        prods_t1_graf = productos_para_grafico(productos, prods_t1)
        key_t1 = f"{','.join(prods_t1 or [])}_{anio_t1}_{','.join(map(str, meses_t1 or []))}"
        render_echart(
            chart_tactico_1_grid(tabla_t1, prods_t1_graf, titulo_t1, anio_t1, meses_t1),
            height=altura_grafico_multiproducto(len(prods_t1_graf)),
            key=_clean_key(f"tac1_grid_{key_t1}"),
        )
        st.markdown("**Tablero táctico 1**")
        st.dataframe(formato_tablero_tact1(tabla_t1), use_container_width=True, hide_index=True)
        st.download_button("📥 Exportar Amplitud CSV", _df_to_csv(tabla_t1), "amplitud_semanal.csv", "text/csv")

        st.divider()
        st.subheader("KPI Táctico 2 — Estabilidad mensual (CV%) + brecha Feria–Supermercado")
        prods_t2, anio_t2, meses_t2 = widget_filtros_kpi(productos, anios, "tac2")
        titulo_t2 = titulo_periodo_filtros(prods_t2, anio_t2, meses_t2)
        kpi_t2_f = aplicar_filtros_kpi(data["kpi_t2"], prods_t2, anio_t2, meses_t2)
        prods_t2_graf = productos_para_grafico(productos, prods_t2)
        key_t2 = f"{','.join(prods_t2 or [])}_{anio_t2}_{','.join(map(str, meses_t2 or []))}"
        h_t2 = altura_grafico_multiproducto(len(prods_t2_graf))
        render_echart(
            chart_tactico_2_cv_grid(kpi_t2_f, prods_t2_graf, titulo_t2, anio_t2, meses_t2),
            height=h_t2,
            key=_clean_key(f"tac2_cv_{key_t2}"),
        )
        render_echart(
            chart_tactico_2_brecha_grid(kpi_t2_f, prods_t2_graf, titulo_t2, anio_t2, meses_t2),
            height=h_t2,
            key=_clean_key(f"tac2_brecha_{key_t2}"),
        )
        st.markdown("**Tablero táctico 2**")
        st.dataframe(formato_tablero_tact2(kpi_t2_f), use_container_width=True, hide_index=True)
        st.download_button("📥 Exportar Estabilidad CSV", _df_to_csv(kpi_t2_f), "estabilidad_mensual.csv", "text/csv")

    else:
        anios = meta["anios"]

        st.subheader("KPI Operativo 1 — Precio vs. referencial")
        prods_o1, anio_o1, meses_o1 = widget_filtros_kpi(productos, anios, "oper1", mes_single=True)
        titulo_o1 = titulo_periodo_filtros(prods_o1, anio_o1, meses_o1)
        df_o1 = aplicar_filtros_kpi(data["df_diario"], prods_o1, anio_o1, meses_o1)
        prods_o1_graf = productos_para_grafico(productos, prods_o1)
        key_o1 = f"{','.join(prods_o1 or [])}_{anio_o1}_{','.join(map(str, meses_o1 or []))}"
        render_echart(
            chart_operativo_1_grid(df_o1, prods_o1_graf, titulo_o1),
            height=altura_grafico_multiproducto(len(prods_o1_graf)),
            key=_clean_key(f"oper1_grid_{key_o1}"),
        )
        st.markdown("**Tablero operativo 1**")
        st.dataframe(estilo_tablero_oper1(df_o1), use_container_width=True, hide_index=True)
        st.download_button("📥 Exportar Precio vs Referencial CSV", _df_to_csv(df_o1), "precio_vs_referencial.csv", "text/csv")

        st.divider()
        st.subheader("KPI Operativo 2 — Umbral óptimo de cosecha")
        prods_o2, anio_o2, meses_o2 = widget_filtros_kpi(productos, anios, "oper2", mes_single=True)
        titulo_o2 = titulo_periodo_filtros(prods_o2, anio_o2, meses_o2)
        tablero_o2 = aplicar_filtros_kpi(data["tablero_oper2"], prods_o2, anio_o2, meses_o2).reset_index(drop=True)
        tablero_o2["_punto_id"] = tablero_o2.index
        prods_o2_graf = productos_para_grafico(productos, prods_o2)
        filtro_key = f"{','.join(prods_o2 or [])}_{anio_o2}_{','.join(map(str, meses_o2 or []))}"
        click_id = render_echart(
            chart_operativo_2_grid(tablero_o2, prods_o2_graf, titulo_o2),
            height=altura_grafico_multiproducto(len(prods_o2_graf)),
            key=_clean_key(f"oper2_grid_{filtro_key}"),
            events=OPER2_CLICK_EVENT,
        )
        if click_id is not None and not isinstance(click_id, str):
            st.session_state["oper2_punto_id"] = click_id
            st.session_state["oper2_filtro_key"] = filtro_key
        if st.session_state.get("oper2_filtro_key") != filtro_key:
            st.session_state.pop("oper2_punto_id", None)
        punto_id = st.session_state.get("oper2_punto_id")
        if punto_id is not None:
            try:
                punto_id = int(punto_id)
            except (TypeError, ValueError):
                punto_id = None
        if punto_id is not None and punto_id in tablero_o2["_punto_id"].values:
            st.markdown("**Punto seleccionado** — haz clic en otro punto del gráfico para actualizar")
            fila_sel = tablero_o2[tablero_o2["_punto_id"] == punto_id]
            st.dataframe(estilo_tablero_oper2(fila_sel), use_container_width=True, hide_index=True)
        else:
            st.markdown("**Tablero operativo 2** — selecciona un punto en el gráfico para ver su detalle")
            st.dataframe(estilo_tablero_oper2(tablero_o2), use_container_width=True, hide_index=True)
        st.download_button("📥 Exportar Cosecha CSV", _df_to_csv(tablero_o2), "umbral_cosecha.csv", "text/csv")


if __name__ == "__main__":
    main()
