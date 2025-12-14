import streamlit as st
import pandas as pd
import numpy as np
import io
import re
from datetime import datetime

# ==========================================================
# --- CONFIGURACIÓN Y MAPPING DE DATOS ---
# ==========================================================

HISTORICO_FILE = 'ventas_historico.csv'

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
COLUMNAS_INPUT_FORM = ['Importe de venta', 'Medio de cobro', 'Factura?', 'Socio']

# ==========================================================
# --- FUNCIONES DE PERSISTENCIA (CSV) ---
# ==========================================================

def load_data():
    """Carga el DataFrame histórico o crea uno vacío si no existe."""
    try:
        # Intentamos leer con coma o punto y coma (para compatibilidad)
        try:
            df = pd.read_csv(HISTORICO_FILE, sep=';')
        except Exception:
            df = pd.read_csv(HISTORICO_FILE, sep=',')
            
        # Asegurarse de que 'Fecha' sea un objeto datetime.date
        df['Fecha'] = pd.to_datetime(df['Fecha']).dt.date
        return df
    except FileNotFoundError:
        st.error("Error: Archivo de historial no encontrado. Asegúrese de que existe 'ventas_historico.csv'.")
        # Si falla la carga, retorna un DataFrame vacío con las columnas finales esperadas
        return pd.DataFrame(columns=['Fecha', 'Importe de venta', 'Medio de cobro', 'Facturado', 'Socio'])
    except Exception as e:
        st.error(f"Error al cargar el historial CSV: {e}")
        return pd.DataFrame(columns=['Fecha', 'Importe de venta', 'Medio de cobro', 'Facturado', 'Socio'])

def save_data(df):
    """Guarda el DataFrame en el archivo histórico usando UTF-8."""
    try:
        df.to_csv(HISTORICO_FILE, index=False, sep=',') # Usamos coma como separador estándar
        # Nota: La persistencia real en Streamlit Cloud requiere GitHub/otro servicio, 
        # pero para el demo guardamos en el mismo archivo del repositorio.
    except Exception as e:
        st.error(f"Error al guardar los datos: {e}")

def add_new_sale(fecha, importe, medio, factura, socio):
    """Agrega la nueva venta al historial y lo guarda."""
    df_historico = load_data()
    
    # Crear la fila de datos con las transformaciones
    facturado_str = 'Facturado' if factura == 'f' else 'No Facturado'
    medio_str = MAPEO_MEDIO_COBRO.get(medio, 'Desconocido')
    socio_str = MAPEO_SOCIO.get(socio, 'Desconocido')

    new_data = {
        'Fecha': fecha,
        'Importe de venta': importe,
        'Medio de cobro': medio_str,
        'Facturado': facturado_str,
        'Socio': socio_str
    }
    
    # Añadir al DataFrame
    new_row_df = pd.DataFrame([new_data])
    df_actualizado = pd.concat([df_historico, new_row_df], ignore_index=True)

    # Limpiar columnas por si acaso
    df_actualizado['Importe de venta'] = pd.to_numeric(df_actualizado['Importe de venta'], errors='coerce')
    df_final = df_actualizado.dropna(subset=['Importe de venta'])
    
    # Guardar los datos actualizados
    save_data(df_final)
    return df_final


# ==========================================================
# --- FUNCIÓN DE REPORTE (PRINCIPAL) ---
# ==========================================================

def generar_resumen_reporte(df, titulo_adicional=""):
    """Genera los DataFrames de resumen y el archivo de descarga."""
    
    total_ventas = df['Importe de venta'].sum()
    total_facturado = df[df['Facturado'] == 'Facturado']['Importe de venta'].sum()
    
    st.subheader(f"📊 Reporte Acumulado de Ventas {titulo_adicional}")
    st.markdown("---")

    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    
    col_kpi1.metric("💰 Venta Total Acumulada", f"${total_ventas:,.2f}")
    col_kpi2.metric("✅ Monto Facturado", f"${total_facturado:,.2f}")
    col_kpi3.metric("🧾 Total de Registros", df.shape[0])

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

    # 4. Generación y Descarga del Archivo CSV Consolidado
    
    csv_output = df.to_csv(index=False).encode('utf-8')
        
    st.download_button(
        label="⬇️ Descargar Historial Completo en CSV",
        data=csv_output,
        file_name=f"Historial_Ventas_Acumulado_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        key="descarga_csv_historico"
    )
    st.success("Historial guardado y disponible para descarga.")
    st.dataframe(df.tail(10), use_container_width=True, caption="Últimas 10 filas registradas")


# ==========================================================
# --- ESTRUCTURA PRINCIPAL DE LA APLICACIÓN STREAMLIT ---
# ==========================================================

st.set_page_config(page_title="GestionSol - Reporte Diario", layout="wide")

st.title("GestionSol: Registro y Reporte de Ventas 📈")
st.markdown("Registre cada venta para mantener un historial acumulado y generar reportes instantáneos.")
st.markdown("---")


# Formulario de Registro
with st.form("registro_venta_form", clear_on_submit=True):
    st.subheader("1. Registrar Nueva Venta")
    
    fecha_input = st.date_input("🗓️ Fecha de la Venta", datetime.now().date())
    
    # Campo para el importe
    importe_input = st.number_input("💵 Importe de venta", min_value=0.0, step=0.01, format="%.2f", key="importe_input")

    # Selección de medio de cobro
    medio_options = {'e': 'Efectivo', 't': 'Transferencia', 'd': 'Débito', 'c': 'Crédito'}
    medio_input = st.selectbox("💳 Medio de cobro", list(medio_options.keys()), format_func=lambda x: medio_options[x])

    col_fac, col_soc = st.columns(2)
    
    # Selección de facturación
    with col_fac:
        factura_input = st.radio("🧾 ¿Factura?", ['f', 'no'], format_func=lambda x: "Facturado (f)" if x == 'f' else "No Facturado (dejar vacío)", index=1, horizontal=True)
        # Convertir 'no' a vacío para la lógica interna (simulando que la celda queda vacía)
        factura_to_save = 'f' if factura_input == 'f' else '' 

    # Selección de socio
    with col_soc:
        socio_options = {'f': 'Fernando', 'n': 'Nacho'}
        socio_input = st.radio("👤 Socio", list(socio_options.keys()), format_func=lambda x: socio_options[x], horizontal=True)
    
    # Botón de envío
    submitted = st.form_submit_button("✅ Registrar Venta")

if submitted:
    if importe_input <= 0:
        st.error("El importe de la venta debe ser mayor a cero.")
    else:
        # 2. Procesar y Guardar Datos
        with st.spinner(f"Guardando venta del {fecha_input.strftime('%d-%m-%Y')}..."):
            df_historico_actualizado = add_new_sale(
                fecha=fecha_input,
                importe=importe_input,
                medio=medio_input,
                factura=factura_to_save,
                socio=socio_input
            )
        
        st.success(f"Venta de ${importe_input:,.2f} registrada exitosamente.")
        
        # 3. Mostrar Reporte basado en el historial completo
        generar_resumen_reporte(df_historico_actualizado)
        
else:
    # Si no hay envío, muestra el reporte del historial actual al cargar la página
    df_historico = load_data()
    if not df_historico.empty:
        generar_resumen_reporte(df_historico)
    else:
        st.info("Aún no hay ventas registradas. Use el formulario para añadir la primera venta.")

# --- Instrucciones y Ayuda ---
with st.expander("📚 Detalles de las Abreviaturas"):
    st.markdown("""
    Los mapeos usados para el registro son:
    * **Medio de cobro**: `e` (Efectivo), `t` (Transferencia), `d` (Débito), `c` (Crédito).
    * **Factura?**: `f` (Facturado) o "No Facturado".
    * **Socio**: `f` (Fernando) o `n` (Nacho).
    """)
