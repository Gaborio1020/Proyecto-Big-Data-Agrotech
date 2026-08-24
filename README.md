 # Proyecto Big Data: Análisis y segmentación para la agricultura de la Región de Coquimbo, AgroTech

> **Nota sobre este repositorio**
> Este proyecto fue desarrollado como trabajo grupal para el curso **"Big Data para la Toma de Decisiones"**, dictado por la profesora **Vannessa Duarte Correa**. 
> El repositorio original fue gestionado mediante GitHub Classroom; esta copia fue clonada a mi cuenta personal con el único fin de exhibir mi contribución como parte de mi portafolio profesional individual, y no debe utilizarse ni distribuirse con otros fines sin la autorización correspondiente.

**Curso:** Big Data para la Toma de Decisiones
**Profesora:** Vannessa Duarte Correa

## Integrantes y Roles Organizacionales
* **Maximiliano Berrios** (Especialista en Elaboración de Informes)
* **Sebastián Castillo** (Ingeniero de Datos - PySpark)
* **Lissette Mathieu** (Especialista en Gráficos y Diseños)
* **Alejandro Núñez** (Especialista en Web Scrapping)
* **Gabriel Tenorio** (Analista de Datos - Modelamiento/Clustering)
* **Mathieus Villavicencio** (Analista de BI - Tableros & Storytelling)


## Arquitectura del Proyecto
El proyecto sigue una arquitectura basada en contenedores Docker, compuesta por tres servicios principales interconectados mediante una red compartida:

## Contenedores

| Contenedor | Descripción |
|------------|-------------|
| `bigdata_workspace` | Ambiente de desarrollo con Jupyter, Spark (PySpark), Selenium y librerías de visualización (Matplotlib, Seaborn). También incluye Streamlit para dashboards interactivos. |
| `bigdata_ui_local` | Interfaz gráfica Mongo Express para administración visual de la base de datos local. |
| `database` | Instancia de MongoDB para almacenamiento local durante el desarrollo. |

## Procesamiento de Datos

El pipeline de datos utiliza **PySpark** para procesamiento en memoria bajo arquitectura distribuida, realizando:
- Transformaciones y limpieza de datos
- Análisis exploratorio (EDA)
- Generación de DataFrames para visualización

## Almacenamiento Externo

MongoDB Atlas proporciona la base de datos centralizada en la nube, permitiendo acceso colaborativo a los datasets que alimentan las visualizaciones del proyecto.



##  Resumen de Indicadores Clave (KPIs)
# Tabla Resumen de Indicadores (KPIs)

Esta tabla consolida los 6 indicadores del tablero de gestión, organizados por nivel jerárquico de toma de decisiones.

| Nivel | Nombre del Indicador | KPI / Métrica principal | Variables utilizadas | Propósito | Horizonte temporal | Audiencia | Semáforo / Criterio de decisión | Acción recomendada |
|-------|---------------------|------------------------|----------------------|-----------|-------------------|-----------|--------------------------------|-------------------|
| **Estratégico 1** | IASC — Índice de Atractivo de Siembra y Comercialización | Score 0–100: 40% retorno canal + 35% estabilidad (1/CV%) + 25% viabilidad climática (R² OLS) | precio, lugar_monitoreo, temperatura, humedad, precipitaciones, radiacion_uv | Clasificar y priorizar qué productos conviene sembrar y comercializar según rentabilidad, estabilidad de precios y viabilidad climática | Trimestral / Semestral | Alta dirección | Verde ≥ 70: Priorizar · Amarillo 40–69: Monitorear · Rojo < 40: Postergar | Enfocar inversión en productos de zona verde; reducir exposición en zona roja |
| **Estratégico 2** | Brecha de valor por canal y calidad | Precio promedio por combinación producto × calidad × canal de venta | precio, lugar_monitoreo, calidad | Identificar qué combinación canal–calidad maximiza el margen de comercialización por producto | Trimestral / Semestral | Alta dirección | Brecha Supermercado − Feria ≥ 0 → priorizar supermercado | Segmentar producción por calidad y redirigir lotes de mayor calidad al canal de mayor precio |
| **Táctico 1** | Amplitud de mercado semanal | Amplitud = precio máx − precio mín por semana y producto | precio, fecha (semana ISO), producto | Evaluar la volatilidad intra-semanal para decidir si concentrar o escalonar la venta | Semanal | Category managers / Jefes de área | Amplitud alta → mercado dinámico (escalonar) · Amplitud baja → mercado predecible (concentrar) | Escalonar venta en semanas de alta amplitud; concentrar en semanas de baja amplitud |
| **Táctico 2** | Estabilidad mensual (CV%) + Brecha Feria–Supermercado | CV% mensual por producto + diferencia absoluta y porcentual Feria vs. Supermercado | precio, mes_num, lugar_monitoreo, producto | Combinar volatilidad mensual con brecha de canal para definir estrategia de fijación de precio y tipo de contrato | Mensual | Category managers / Jefes de área | CV% alto + brecha alta → Volátil + priorizar supermercado · CV% bajo + brecha baja → Estable + contrato viable | Contratar precio fijo en meses de baja variabilidad; mantener flexibilidad en meses volátiles |
| **Operativo 1** | Umbral óptimo de venta vs. precio referencial mensual | Precio diario vs. precio referencial mensual (promedio del mes por producto) | precio, fecha, producto, anio, mes_num | Orientar la decisión diaria de venta comparando el precio del día con el promedio mensual de referencia | Diario | Supervisores / Productores | Precio día ≥ referencial → Vender · Precio día < referencial → Postergar | Vender cuando el precio diario supera el referencial; diferir la venta en días por debajo del umbral |
| **Operativo 2** | Umbral óptimo de cosecha según temperatura y humedad | Clasificación Óptimo / Parcial / No óptimo según rangos agronómicos por producto | temperatura, humedad, fecha, producto, calidad | Determinar si las condiciones climáticas del día son adecuadas para cosechar cada producto sin pérdida de calidad | Diario | Supervisores / Productores | Verde Óptimo: ambos rangos OK · Amarillo Parcial: un rango OK · Rojo No óptimo: fuera de ambos rangos | Cosechar en días óptimos; postergar en días no óptimos para preservar calidad del lote |



##  Estructura del Repositorio
* `/scrapers`: Contiene S1.py , S2.py , S3.py , S4.py , S5.py , S6.py
* `/notebooks`: Proyecto_Final.ipynb, Limpieza, Descripcion.ipynb (EDA completo), Prediccion.ipynb (cluster, clasificación o regresión), Storytelling.ipynb (Gráficos y Storytelling), .
* `/docker`: Dockerfiles y docker-compose del ecosistema.
* `main`: main.py (unión de los scraper), tableros.py (Streamlit con tableros)
* `/informes`: informe entrega 2.pdf, Proyecto_Final.ipynb
