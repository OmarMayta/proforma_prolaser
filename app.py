import streamlit as st
from supabase import create_client

# Conexión a Supabase
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()

# Configuración de la página
st.set_page_config(page_title="Proforma ProLaser", layout="wide")
st.title("📝 Proforma ProLaser")
st.write("Creamos lo que Imaginas")

# --- FUNCIONES REUTILIZABLES ---
def get_clientes():
    return supabase.table("clientes").select("*").execute().data

def get_proformas():
    return supabase.table("ventas").select("*, clientes(nombre, celular)").execute().data

def get_gastos(id_venta):
    return supabase.table("gastos").select("*").eq("id_venta", id_venta).execute().data

# --- SECCIÓN CLIENTES ---
with st.expander("📌 Registrar Nuevo Cliente", expanded=False):
    with st.form("form_cliente"):
        nombre = st.text_input("Nombre del Cliente*")
        celular = st.text_input("Celular")
        if st.form_submit_button("Guardar Cliente"):
            if nombre:
                supabase.table("clientes").insert({
                    "nombre": nombre, 
                    "celular": celular
                }).execute()
                st.success("Cliente registrado!")
                st.rerun()
            else:
                st.error("El nombre es obligatorio")

# --- SECCIÓN PROFORMAS ---
with st.expander("💰 Crear Nueva Proforma", expanded=True):
    with st.form("form_proforma"):
        # Selección de cliente
        clientes = get_clientes()
        cliente_seleccionado = st.selectbox(
            "Seleccionar cliente existente",
            options=[f"{c['nombre']} ({c['celular']})" for c in clientes],
            index=0
        )
        
        # Detalles del servicio
        st.subheader("Detalles del Trabajo")
        descripcion = st.text_area("Descripción*")
        total = st.number_input("Total (S/.)*", min_value=0.0, format="%.2f")
        
        if st.form_submit_button("Guardar Proforma"):
            if descripcion and total > 0:
                id_cliente = next(c["id_cliente"] for c in clientes if f"{c['nombre']} ({c['celular']})" == cliente_seleccionado)
                
                supabase.table("ventas").insert({
                    "id_cliente": id_cliente,
                    "descripcion_servicio": descripcion,
                    "total_venta": total,
                    "fecha_venta": "now()"
                }).execute()
                st.success("Proforma creada!")
                st.rerun()
            else:
                st.error("Descripción y total son obligatorios")

# --- HISTORIAL CON GASTOS ---
st.divider()
st.subheader("📋 Historial de Proformas")

proformas = get_proformas()

if not proformas:
    st.warning("No hay proformas registradas")
else:
    for venta in proformas:
        with st.expander(f"Proforma #{venta['id_venta']} - {venta['clientes']['nombre']}"):
            # Info básica
            st.write(f"**Cliente:** {venta['clientes']['nombre']} ({venta['clientes']['celular']})")
            st.write(f"**Descripción:** {venta['descripcion_servicio']}")
            st.write(f"**Total:** S/. {venta['total_venta']:.2f}")
            st.write(f"**Fecha:** {venta['fecha_venta']}")
            
            # --- SECCIÓN GASTOS ---
            st.markdown("---")
            st.subheader("💸 Gastos Asociados")
            
            gastos = get_gastos(venta["id_venta"])
            
            if gastos:
                total_gastos = 0
                for gasto in gastos:
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.write(f"**{gasto['concepto']}**")
                    with col2:
                        st.write(f"S/. {gasto['monto']:.2f}")
                    with col3:
                        if st.button("🗑️", key=f"del_{gasto['id_gasto']}"):
                            supabase.table("gastos").delete().eq("id_gasto", gasto["id_gasto"]).execute()
                            st.rerun()
                    total_gastos += gasto["monto"]
                
                st.success(f"**Total gastado:** S/. {total_gastos:.2f}")
                st.metric("💰 Utilidad estimada", f"S/. {venta['total_venta'] - total_gastos:.2f}")
            else:
                st.warning("No hay gastos registrados")
            
            # Formulario para nuevos gastos
            with st.form(f"form_nuevo_gasto_{venta['id_venta']}"):
                st.write("**Agregar nuevo gasto**")
                concepto = st.text_input("Concepto*", key=f"concepto_{venta['id_venta']}")
                monto = st.number_input("Monto (S/.)*", min_value=0.0, format="%.2f", key=f"monto_{venta['id_venta']}")
                
                if st.form_submit_button("Guardar Gasto"):
                    if concepto and monto > 0:
                        supabase.table("gastos").insert({
                            "id_venta": venta["id_venta"],
                            "concepto": concepto,
                            "monto": monto
                        }).execute()
                        st.success("Gasto registrado!")
                        st.rerun()
                    else:
                        st.error("Concepto y monto son obligatorios")
                        