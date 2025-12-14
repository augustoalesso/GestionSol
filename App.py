import streamlit as st
import pandas as pd
import numpy as np
import io
import re
from datetime import datetime

# ==========================================================
# --- CONFIGURACIÓN Y CONSTANTES ---
# ==========================================================

VENTAS_FILE = 'ventas_historico.csv'
EGRESOS_FILE = 'egresos_historico.csv'
EGRESO_TYPES_CONFIG_FILE = 'egreso_types_config.txt' # Archivo de tipos
PROVEEDOR_CONFIG_FILE = 'proveedor_config.txt'      # Nuevo archivo de proveedores

# Mapeo de abreviaturas para Ventas
MAPEO_MEDIO_COBRO = {'e': 'Efectivo', 't': 'Transferencia', 'd': 'Débito', 'c': 'Crédito'}
MAPEO_SOCIO = {'f': 'Fernando', 'n': 'Ignacio (Nacho)'}
COLUMNAS_VENTAS_FINALES = ['Fecha', 'Importe de venta', 'Medio de cobro', 'Facturado', 'Socio']

# Tipos de Egreso predeterminados
DEFAULT_EGRESO_TYPES = ['Mercadería', 'Servicio', 'Empleado', 'Otros']
DEFAULT_PROVEEDORES = ['Proveedor Genérico']
COLUMNAS_EGRESOS_FINALES = ['Fecha_Registro', 'Tipo_Egreso', 'Proveedor', 'Importe', 'Fecha_Vencimiento', 'Facturado']


# ==========================================================
# --- FUNCIONES DE PERSISTENCIA DE CONFIGURACIÓN ---
# ==========================================================

def load_egreso_types():
    """Carga los tipos de egreso desde el archivo de configuración o usa los predeterminados."""
    try:
        with open(EGRESO_TYPES_CONFIG_FILE, 'r') as f:
            types = [line.strip() for line in f if line.strip()]
        if not types:
            return DEFAULT_EGRESO_TYPES
        return types
    except FileNotFoundError:
        save_egreso_types(DEFAULT_EGRESO_TYPES)
        return DEFAULT_EGRESO_TYPES
    except Exception as e:
        st.error(f"Error al cargar tipos de egreso: {e}")
        return DEFAULT_EGRESO_TYPES

def save_egreso_types(types_list):
    """Guarda la lista actual de tipos de egreso en el archivo de configuración."""
    try:
        unique_sorted_types = sorted(list(set(types_list)))
        with open(EGRESO_TYPES_CONFIG_FILE, 'w') as f:
            for type_name in unique_sorted_types:
                f.write(f"{type_name}\n")
    except Exception as e:
        st.error(f"Error al guardar tipos de egreso: {e}")

# --- Nuevas Funciones para Proveedores ---
def load_proveedores():
    """Carga la lista de proveedores desde el archivo de configuración o usa los predeterminados."""
    try:
        with open(PROVEEDOR_CONFIG_FILE, 'r') as f:
            # Lee líneas no vacías y elimina el espacio en blanco
            proveedores = [line.strip() for line in f if line.strip()]
        if not proveedores:
            return DEFAULT_PROVEEDORES
        return proveedores
    except FileNotFoundError:
        save_proveedores(DEFAULT_PROVEEDORES)
        return DEFAULT_PROVEEDORES
    except Exception as e:
        st.error(f"Error al cargar proveedores: {e}")
        return DEFAULT_PROVEEDORES

def save_proveedores(proveedores_list):
    """Guarda la lista actual de proveedores en el archivo de configuración."""
    try:
        # Usa set() para eliminar duplicados y sorted() para ordenarlos
        unique_sorted_proveedores = sorted(list(set(proveedores_list)))
        with open(PROVEEDOR_CONFIG_FILE, 'w') as f:
            for proveedor_name in unique_sorted_proveedores:
                f.write(f"{proveedor_name}\n")
    except Exception as e:
        st.error(f"Error al guardar proveedores: {e}")


# ==========================================================
# --- FUNCIONES DE PERSISTENCIA: VENTAS ---
# (Se mantienen iguales)
# ==========================================================

def load_ventas_data():
    """Carga el DataFrame histórico de ventas o crea uno vacío."""
    try:
        df = None
        for encoding, sep in [('latin-1', ','), ('utf-8', ';'), ('utf-8', ',')]:
            try:
                df = pd.read_csv(VENTAS_FILE, encoding=encoding, sep=sep)
                break
            except Exception:
                continue
                
        if df is not None:
            df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce').dt.date
            df = df.dropna(subset=['Importe de venta']).dropna(how='all')
            return df
    except Exception as e:
        st.sidebar.error(f"Error al cargar historial de VENTAS: {e}")

    return pd.DataFrame(columns=COLUMNAS_VENTAS_FINALES)

def save_ventas_data(df):
    """Guarda el DataFrame de ventas en el archivo histórico."""
    try:
        df.to_csv(VENTAS_FILE, index=False, sep=',')
    except Exception as e:
        st.error(f"Error al guardar los datos de ventas: {e}")

def add_new_sale(fecha, importe, medio, factura, socio):
    """Agrega la nueva venta al historial y lo guarda."""
    df_historico = load_ventas_data()
    
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
    
    new_row_df = pd.DataFrame([new_data])
    df_actualizado = pd.concat([df_historico, new_row_df], ignore_index=True)

    df_actualizado['Importe de venta'] = pd.to_numeric(df_actualizado['Importe de venta'], errors='coerce')
    df_final = df_actualizado.dropna(subset=['Importe de venta'])
    
    save_ventas_data(df_final)
    return df_final


# ==========================================================
# --- FUNCIONES DE PERSISTENCIA: EGRESOS ---
# (Se mantienen iguales)
# ==========================================================

def load_egresos_data():
    """Carga el DataFrame histórico de egresos o crea uno vacío."""
    try:
        df = None
        for encoding, sep in [('latin-1', ','), ('utf-8', ';'), ('utf-8', ',')]:
            try:
                df = pd.read_csv(EGRESOS_FILE, encoding=encoding, sep=sep)
                break
            except Exception:
                continue
                
        if df is not None:
            df['Fecha_Vencimiento'] = pd.to_datetime(df['Fecha_Vencimiento'], errors='coerce').dt.date
            df['Fecha_Registro'] = pd.to_datetime(df['Fecha_Registro'], errors='coerce').dt.date
            df = df.dropna(subset=['Importe']).dropna(how='all')
            return df
    except Exception as e:
        st.sidebar.error(f"Error al cargar historial de EGRESOS: {e}")

    return pd.DataFrame(columns=COLUMNAS_EGRESOS_FINALES)


def save_egresos_data(df):
    """Guarda el DataFrame de egresos en el archivo histórico."""
    try:
        df.to_csv(EGRESOS_FILE, index=False, sep=',')
    except Exception as e:
        st.error(f"Error al guardar los datos de egresos: {e}")

def add_new_egreso(tipo, proveedor, importe, vencimiento, factura):
    """Agrega el nuevo egreso al historial y lo guarda."""
    df_historico = load_egresos_data()
    
    facturado_str = 'Facturado' if factura == 'f' else 'No Facturado'
    tipo_str = tipo 

    new_data = {
        'Fecha_Registro': datetime.now().date(),
        'Tipo_Egreso': tipo_str,
        'Proveedor': proveedor,
        'Importe': importe,
        'Fecha_Vencimiento': vencimiento,
        'Facturado': facturado_str
    }
    
    new_row_df = pd.DataFrame([new_data])
    df_actualizado = pd.concat([df_historico, new_row_df], ignore_index=True)

    df_actualizado['Importe'] = pd.to_numeric(df_actualizado['Importe'], errors='coerce')
    df_final = df_actualizado.dropna(subset=['Importe'])
    
    save_egresos_data(df_final)
    return df_final


# ==========================================================
# --- FUNCIONES DE REPORTE ---
# (Se mantienen iguales)
# ==========================================================

def generar_resumen_ventas(df):
    """Genera y muestra el reporte de ventas."""
    if df.empty:
        st.info("Aún no hay ventas registradas. Use el formulario para añadir la primera venta.")
        return

    st.subheader(f"📊 Reporte Acumulado de Ventas")
    st.markdown("---")

    total_ventas = df['Importe de venta'].sum()
    total_facturado = df[df['Facturado'] == 'Facturado']['Importe de venta'].sum()
    
    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    col_kpi1.metric("💰 Venta Total Acumulada", f"${total_ventas:,.2f}")
    col_kpi2.metric("✅ Monto Facturado", f"${total_facturado:,.2f}")
    col_kpi3.metric("🧾 Total de Registros", df.shape[0])

    st.markdown("---")

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

    st.subheader("💳 Resumen por Medio de Cobro")
    df_cobro = df.groupby('Medio de cobro')['Importe de venta'].sum().reset_index()
    df_cobro.columns = ['Medio de Cobro', 'Monto Cobrado']
    st.dataframe(df_cobro.style.format({'Monto Cobrado': "${:,.2f}"}), use_container_width=True, hide_index=True)

    st.markdown("---")
    csv_output = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="⬇️ Descargar Historial de Ventas en CSV",
        data=csv_output,
        file_name=f"Historial_Ventas_Acumulado_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        key="descarga_csv_historico_ventas"
    )
    st.dataframe(df.tail(10), use_container_width=True, caption="Últimas 10 filas registradas")


def generar_reporte_egresos(df):
    """Genera y muestra el reporte de egresos (To-Do List)."""
    if df.empty:
        st.info("Aún no hay egresos registrados.")
        return

    st.subheader("📅 Pendientes de Pago (Egresos)")
    st.markdown("---")
    
    df['Vencido'] = df['Fecha_Vencimiento'] < datetime.now().date()
    df_pendientes_hoy = df[~df['Vencido']] 
    
    total_importe = df_pendientes_hoy['Importe'].sum()
    total_vencido = df[df['Vencido']]['Importe'].sum()

    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    col_kpi1.metric("💸 Total Pendiente", f"${total_importe:,.2f}")
    col_kpi2.metric("❌ Vencido (Histórico)", f"${total_vencido:,.2f}")
    col_kpi3.metric("📝 Egresos Registrados", df.shape[0])

    st.markdown("---")

    col_resumen1, col_resumen2 = st.columns(2)
    with col_resumen1:
        st.subheader("Clasificación por Tipo")
        df_tipo = df_pendientes_hoy.groupby('Tipo_Egreso')['Importe'].sum().reset_index()
        st.dataframe(df_tipo.style.format({'Importe': "${:,.2f}"}), use_container_width=True, hide_index=True)

    with col_resumen2:
        st.subheader("Clasificación por Facturación")
        df_fact = df_pendientes_hoy.groupby('Facturado')['Importe'].sum().reset_index()
        st.dataframe(df_fact.style.format({'Importe': "${:,.2f}"}), use_container_width=True, hide_index=True)

    st.markdown("---")

    st.subheader("Detalle de Pagos Pendientes (Vencimiento Ascendente)")
    df_detalle = df.sort_values(by=['Vencido', 'Fecha_Vencimiento'], ascending=[False, True])
    df_detalle_display = df_detalle.copy()

    df_detalle_display['Importe'] = df_detalle_display['Importe'].apply(lambda x: f"${x:,.2f}")
    df_detalle_display['Vencimiento'] = df_detalle_display['Fecha_Vencimiento'].apply(lambda x: x.strftime('%d-%m-%Y'))
    
    df_detalle_display['Estado'] = df_detalle_display['Vencido'].apply(lambda x: '❌ VENCIDO' if x else '✅ PENDIENTE')

    st.dataframe(
        df_detalle_display[['Estado', 'Vencimiento', 'Proveedor', 'Tipo_Egreso', 'Importe', 'Facturado']],
        use_container_width=True,
        hide_index=True
    )
    
    csv_output = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="⬇️ Descargar Historial de Egresos en CSV",
        data=csv_output,
        file_name=f"Historial_Egresos_Acumulado_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        key="descarga_csv_historico_egresos"
    )

# ==========================================================
# --- ESTRUCTURA PRINCIPAL DE LA APLICACIÓN STREAMLIT ---
# ==========================================================

st.set_page_config(page_title="GestionSol - Finanzas", layout="wide")

st.title("GestionSol: Finanzas Diarias 📊")

# Inicializar o cargar la lista de tipos de egreso y proveedores
if 'egreso_types' not in st.session_state:
    st.session_state.egreso_types = load_egreso_types()

if 'proveedores' not in st.session_state:
    st.session_state.proveedores = load_proveedores()

tab_ventas, tab_egresos = st.tabs(["💰 Ventas (Ingresos)", "💸 Egresos (Gastos)"])

# -------------------------
# --- PESTAÑA DE VENTAS ---
# -------------------------

with tab_ventas:
    st.header("Registro y Reporte de Ventas")

    with st.form("registro_venta_form", clear_on_submit=True):
        st.subheader("1. Registrar Venta (Agregada)")
        
        fecha_input = st.date_input("🗓️ Fecha de la Venta", datetime.now().date())
        importe_input = st.number_input("💵 Importe de venta", min_value=0.0, step=0.01, format="%.2f", key="v_importe_input")

        medio_options = MAPEO_MEDIO_COBRO
        medio_input = st.selectbox("💳 Medio de cobro", list(medio_options.keys()), format_func=lambda x: medio_options[x], key="v_medio_input")

        col_fac, col_soc = st.columns(2)
        
        with col_fac:
            factura_input = st.radio("🧾 ¿Factura?", ['f', 'no'], format_func=lambda x: "Facturado (f)" if x == 'f' else "No Facturado", index=1, horizontal=True, key="v_factura_input")
            factura_to_save = 'f' if factura_input == 'f' else '' 

        with col_soc:
            socio_options = MAPEO_SOCIO
            socio_input = st.radio("👤 Socio", list(socio_options.keys()), format_func=lambda x: socio_options[x], horizontal=True, key="v_socio_input")
        
        submitted = st.form_submit_button("✅ Registrar Venta")

    if submitted:
        if importe_input <= 0:
            st.error("El importe de la venta debe ser mayor a cero.")
        else:
            with st.spinner("Guardando venta..."):
                df_historico_actualizado = add_new_sale(
                    fecha=fecha_input, importe=importe_input, medio=medio_input, factura=factura_to_save, socio=socio_input
                )
            st.success(f"Venta de ${importe_input:,.2f} registrada exitosamente.")
            generar_resumen_ventas(df_historico_actualizado)
            
    else:
        generar_resumen_ventas(load_ventas_data())

# --------------------------
# --- PESTAÑA DE EGRESOS ---
# --------------------------

with tab_egresos:
    st.header("Registro y Control de Gastos/Compras")
    
    # SECCIÓN DE ADMINISTRACIÓN
    with st.expander("🛠️ Administrar Tipos de Egreso y Proveedores"):
        col_types, col_providers = st.columns(2)
        
        # 1. Administrar Tipos de Egreso
        with col_types:
            st.subheader("Tipos de Egreso")
            with st.form("add_type_form", clear_on_submit=True):
                new_type_name = st.text_input("Añadir nuevo Tipo de Egreso:", help="Ej: Mantenimiento de Vehículos", key="new_type_name")
                submitted_type = st.form_submit_button("➕ Añadir Tipo")
                
                if submitted_type and new_type_name:
                    new_type_name = new_type_name.strip()
                    if new_type_name and new_type_name not in st.session_state.egreso_types:
                        st.session_state.egreso_types.append(new_type_name)
                        save_egreso_types(st.session_state.egreso_types) 
                        st.session_state.egreso_types = load_egreso_types() # Recargar la lista ordenada
                        st.success(f"Tipo '{new_type_name}' añadido y guardado.")
                    elif new_type_name in st.session_state.egreso_types:
                        st.warning(f"El tipo '{new_type_name}' ya existe.")
                    else:
                        st.error("Debe ingresar un nombre para el nuevo tipo de egreso.")
            st.markdown(f"**Tipos Actuales:** {', '.join(st.session_state.egreso_types)}")

        # 2. Administrar Proveedores (NUEVO)
        with col_providers:
            st.subheader("Proveedores")
            with st.form("add_provider_form", clear_on_submit=True):
                new_provider_name = st.text_input("Añadir nuevo Proveedor:", help="Ej: EPEC", key="new_provider_name")
                submitted_provider = st.form_submit_button("➕ Añadir Proveedor")
                
                if submitted_provider and new_provider_name:
                    new_provider_name = new_provider_name.strip()
                    if new_provider_name and new_provider_name not in st.session_state.proveedores:
                        st.session_state.proveedores.append(new_provider_name)
                        save_proveedores(st.session_state.proveedores)
                        st.session_state.proveedores = load_proveedores() # Recargar la lista ordenada
                        st.success(f"Proveedor '{new_provider_name}' añadido y guardado.")
                    elif new_provider_name in st.session_state.proveedores:
                        st.warning(f"El proveedor '{new_provider_name}' ya existe.")
                    else:
                        st.error("Debe ingresar un nombre para el nuevo proveedor.")
            st.markdown(f"**Proveedores Actuales:** {', '.join(st.session_state.proveedores)}")


    # Formulario de Registro de Egreso
    with st.form("registro_egreso_form", clear_on_submit=True):
        st.subheader("2. Registrar Egreso")
        
        # Proveedor (Ahora es un desplegable dinámico)
        proveedor_input = st.selectbox("🏢 Nombre del Proveedor", st.session_state.proveedores, key="e_proveedor_input")
        
        # Tipo de egreso (Lista dinámica)
        tipo_input = st.selectbox("📝 Tipo de Egreso", st.session_state.egreso_types, key="e_tipo_input")
        
        importe_input = st.number_input("💵 Importe a Pagar", min_value=0.0, step=0.01, format="%.2f", key="e_importe_input")

        col_fecha, col_fac = st.columns(2)

        # Fecha de Vencimiento
        with col_fecha:
            vencimiento_input = st.date_input("🗓️ Fecha de Vencimiento (o Pago)", datetime.now().date(), key="e_vencimiento_input")

        # Estado de Factura
        with col_fac:
            factura_input = st.radio("🧾 ¿Factura?", ['f', 'no'], format_func=lambda x: "Facturado (f)" if x == 'f' else "No Facturado", index=1, horizontal=True, key="e_factura_input")
            factura_to_save = 'f' if factura_input == 'f' else '' 
        
        submitted_egreso = st.form_submit_button("✅ Registrar Egreso")

    if submitted_egreso:
        if importe_input <= 0:
            st.error("Debe ingresar un importe válido.")
        elif not proveedor_input:
            st.error("Debe seleccionar un proveedor.")
        else:
            with st.spinner("Guardando egreso..."):
                df_egresos_actualizado = add_new_egreso(
                    tipo=tipo_input, proveedor=proveedor_input, importe=importe_input, vencimiento=vencimiento_input, factura=factura_to_save
                )
            st.success(f"Egreso a {proveedor_input} por ${importe_input:,.2f} registrado exitosamente.")
            generar_reporte_egresos(df_egresos_actualizado)
    else:
        generar_reporte_egresos(load_egresos_data())
