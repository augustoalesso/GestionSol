import streamlit as st
import pandas as pd
import numpy as np
import io
import re
from datetime import datetime

# ==========================================================
# --- CONFIGURACIÓN Y MAPPING DE DATOS ---
# ==========================================================

# Mapeo de abreviaturas a nombres completos para los reportes
MAPEO_MEDIO_COBRO = {
    'e': 'Efectivo',
    't': 'Transferencia',
    'd': 'Débito',
    'c': 'Crédito'
}

MAPEO_SOCIO = {
    'f': 'Fernando',
    'n': 'Ignacio (Nacho)'
}

# Columnas esperadas en el archivo de entrada
COLUMNAS_INPUT = ['Importe de venta', 'Medio de cobro', 'Factura?', 'Socio']

# ==========================================================
# --- FUNCIÓN DE CARGA Y TRANSFORMACIÓN ---
# ==========================================================

def extraer_fecha_de_nombre(nombre_archivo):
    """Extrae la fecha del nombre del archivo (Ej: V 01-01-26.xlsx)."""
    # El regex busca el patrón DD-MM-AA
    match = re.search(r'(\d{2}-\d{2}-\d{2})', nombre_archivo)
    if match:
        fecha_str = match.group(1)
        try:
            # Asume que el formato es Día-Mes-Año
            return datetime.strptime(fecha_str, '%d-%m-%y').date()
        except ValueError:
            return None
    else:
        return None

def cargar_y_transformar_datos(uploaded_file):
    """Carga, valida y transforma los datos del archivo subido."""
    
    fecha_venta = extraer_fecha_de_nombre(uploaded_file.name)
    if fecha_venta is None:
        st.error(f"⚠️ Error: No se encontró la fecha con formato DD-MM-AA en el nombre del archivo: **{uploaded_file.name}**")
        return None, None

    try:
        # LECTURA DE ARCHIVO XLSX SUBIDO (Requiere openpyxl)
        df = pd.read_excel(uploaded_file, engine='openpyxl')
    except Exception as e:
        # Si esto falla, el error es 'openpyxl' no está instalado (lo que Packages.txt debería resolver).
        st.error(f"Error al cargar el archivo de Excel: {e}")
        st.info("❌ ERROR CLAVE: Asegúrese que la librería 'openpyxl' esté instalada correctamente.")
        return None, None

    if not all(col in df.columns for col in COLUMNAS_INPUT):
        st.error(f"❌ Error: El archivo no contiene las columnas requeridas: {COLUMNAS_INPUT}")
        return None, None
    
    # Iniciar la transformación
    
    # Añadir la fecha a cada fila
    df['Fecha'] = fecha_venta
    
    # Limpiar y estandarizar las abreviaturas (a minúsculas)
    for col in ['Medio de cobro', 'Factura?', 'Socio']:
        df[col] = df[col].astype(str).str.lower().str.strip().fillna('')

    # Aplicar los mapeos
    df['Medio de cobro'] = df['Medio de cobro'].map(MAPEO_MEDIO_COBRO).fillna('Desconocido')
    df['Socio'] = df['Socio'].map(MAPEO_SOCIO).fillna('Desconocido')
    df['Facturado'] = df['Factura?'].apply(lambda x: 'Facturado' if x == 'f' else 'No Facturado')
    
    # Conversión de Monto
    df['Importe de venta'] = pd.to_numeric(df['Importe de venta'], errors='coerce')
    df = df.dropna(subset=['Importe de venta'])
    
    # Seleccionamos las columnas útiles para el reporte
    COLUMNAS_REPORTE = ['Fecha', 'Importe de venta', 'Medio de cobro', 'Facturado', 'Socio']
    return df[COLUMNAS_REPORTE], fecha_venta


# ==========================================================
# --- FUNCIÓN DE REPORTE Y DESCARGA (PRINCIPAL) ---
# ==========================================================

def generar_resumen_reporte(df, fecha):
    """Genera los DataFrames de resumen y el archivo de descarga."""
    
    st.subheader(f"Análisis de Ventas del Día: {fecha.strftime('%d-%m-%Y')}")
    st.markdown("---")

    # 1. Métricas Clave (Totales)
    total_ventas = df['Importe de venta'].sum()
    total_facturado = df[df['Facturado'] == 'Facturado']['Importe de venta'].sum()
    
    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    
    col_kpi1.metric("💰 Venta Total del Día", f"${total_ventas:,.2f}")
    col_kpi2.metric("✅ Monto Facturado", f"${total_facturado:,.2f}")
    col_kpi3.metric("🧾 Registros de Venta", df.shape[0])

    st.markdown("---")

    # 2. Discriminación por Socio y Facturación
    col_resumen1, col_resumen2 = st.columns(2)

    # Resumen por Socio
    df_socio = df.groupby('Socio')['Importe de venta'].sum().reset_index()
    df_socio.columns = ['Socio', 'Venta Total']
    with col_resumen1:
        st.subheader("👥 Resumen por Socio")
        st.dataframe(df_socio.style.format({'Venta Total': "${:,.2f}"}), use_container_width=True, hide_index=True)

    # Resumen por Facturación
    df_fact = df.groupby('Facturado')['Importe de venta'].sum().reset_index()
    df_fact.columns = ['Estado', 'Venta Total']
    with col_resumen2:
        st.subheader("🧾 Resumen por Facturación")
        st.dataframe(df_fact.style.format({'Venta Total': "${:,.2f}"}), use_container_width=True, hide_index=True)

    # 3. Discriminación por Medio de Cobro
    st.subheader("💳 Resumen por Medio de Cobro")
    df_cobro = df.groupby('Medio de cobro')['Importe de venta'].sum().reset_index()
    df_cobro.columns = ['Medio de Cobro', 'Monto Cobrado']
    st.dataframe(df_cobro.style.format({'Monto Cobrado': "${:,.2f}"}), use_container_width=True, hide_index=True)

    st.markdown("---")

    # 4. Generación y Descarga del Archivo Excel Consolidado (Requiere openpyxl)
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        # Hoja 1: Detalle Completo
        df.to_excel(writer, sheet_name='Detalle Diario', index=False)
        # Hoja 2: Resumen por Socio
        df_socio.to_excel(writer, sheet_name='Resumen Socio', index=False)
        # Hoja 3: Resumen por Facturación
        df_fact.to_excel(writer, sheet_name='Resumen Factura', index=False)
        # Hoja 4: Resumen por Cobro
        df_cobro.to_excel(writer, sheet_name='Resumen Cobro', index=False)
        
    st.download_button(
        label="⬇️ Descargar Reporte Consolidado en Excel",
        data=buffer.getvalue(),
        file_name=f"Reporte_Ventas_Diario_{fecha}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="descarga_excel_diario"
    )
    st.success("Reporte generado. Revise el archivo Excel que contiene el detalle y los 4 resúmenes en hojas separadas.")
    st.dataframe(df.head(), use_container_width=True, caption="Detalle de las primeras filas cargadas")


# ==========================================================
# --- ESTRUCTURA PRINCIPAL DE LA APLICACIÓN STREAMLIT ---
# ==========================================================

st.set_page_config(page_title="GestionSol - Reporte Diario", layout="wide")

st.title("GestionSol: Reporte de Ventas Diario 📈")
st.markdown("Cargue el archivo de ventas diario (**XLSX**) para generar un reporte resumido instantáneo.")
st.markdown("---")


# Contenedor para la carga de archivos
with st.container(border=True):
    st.subheader("1. Subir Archivo Diario")
    st.info("⚠️ El archivo debe ser formato **XLSX** y el nombre debe contener la fecha en formato **DD-MM-AA** (Ej: V 01-01-26.xlsx)")
    
    uploaded_file = st.file_uploader(
        "Archivo de Ventas (Excel)", 
        type=['xlsx', 'xls'], 
        key="ventas_file"
    )

if uploaded_file is not None:
    # 2. Procesar Datos
    with st.spinner("Procesando y generando reporte..."):
        df_ventas_dia, fecha_procesada = cargar_y_transformar_datos(uploaded_file)
    
    if df_ventas_dia is not None:
        # 3. Mostrar Resumen y Descarga
        generar_resumen_reporte(df_ventas_dia, fecha_procesada)
        
# --- Instrucciones y Ayuda ---
with st.expander("📚 Requisitos y Formato de Archivo"):
    st.markdown("""
    El archivo subido debe ser formato **XLSX**. Las cuatro columnas requeridas son:
    * **`Importe de venta`**: El valor numérico de la venta.
    * **`Medio de cobro`**: Abreviaturas permitidas: **`e`** (Efectivo), **`t`** (Transferencia), **`d`** (Débito), **`c`** (Crédito).
    * **`Factura?`**: Ponga **`f`** si está facturada, y deje la celda **vacía** si no lo está.
    * **`Socio`**: Abreviaturas permitidas: **`f`** (Fernando) o **`n`** (Nacho).
    """)
