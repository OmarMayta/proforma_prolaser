import streamlit as st
from supabase import create_client

# Conexión a Supabase
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()

# Configuración
st.set_page_config(layout="wide")
st.title("📝 Proforma ProLaser")
st.write("Creamos lo que Imaginas")

# --- FUNCIONES ---
def get_clientes():
    return supabase.table("clientes").select("*").execute().data

def get_proformas():
    return supabase.table("ventas").select("*, clientes(nombre, celular)").execute().data

def get_gastos(id_venta):
    return supabase.table("gastos").select("*").eq("id_venta", id_venta).execute().data

# --- SECCIÓN GASTOS ---
def mostrar_gastos(id_venta):
    gastos = get_gastos(id_venta)
    if gastos:
        st.subheader("📋 Gastos Registrados")
        total = 0
        for gasto in gastos:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**{gasto['concepto']}**")
            with col2:
                st.write(f"S/. {gasto['monto']:.2f}")
            total += gasto["monto"]
        st.success(f"**Total gastado:** S/. {total:.2f}")
    else:
        st.warning("No hay gastos registrados")

# --- FORMULARIO PROFORMAS ---
with st.expander("💰 Nueva Proforma", expanded=True):
    with st.form("form_proforma"):
        # Selección de cliente
        clientes = get_clientes()
        cliente_seleccionado = st.selectbox(
            "Cliente*",
            options=[f"{c['nombre']} ({c['celular']})" for c in clientes],
            index=0
        )
        
        # Detalles
        descripcion = st.text_area("Descripción del trabajo*")
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
                st.success("¡Proforma guardada!")
                st.rerun()
            else:
                st.error("¡Complete los campos obligatorios!")

# --- HISTORIAL ---
st.divider()
st.header("Historial de Proformas")

proformas = get_proformas()
if proformas:
    for venta in proformas:
        with st.expander(f"Proforma #{venta['id_venta']} - {venta['clientes']['nombre']}"):
            # Info básica
            st.write(f"**Cliente:** {venta['clientes']['nombre']} ({venta['clientes']['celular']})")
            st.write(f"**Descripción:** {venta['descripcion_servicio']}")
            st.write(f"**Total:** S/. {venta['total_venta']:.2f}")
            
            # --- GASTOS ---
            st.markdown("---")
            mostrar_gastos(venta["id_venta"])
            
            # Formulario para nuevos gastos
            with st.form(f"nuevo_gasto_{venta['id_venta']}"):
                concepto = st.text_input("Concepto*", key=f"c_{venta['id_venta']}")
                monto = st.number_input("Monto*", min_value=0.0, format="%.2f", key=f"m_{venta['id_venta']}")
                
                if st.form_submit_button("➕ Agregar Gasto"):
                    if concepto and monto > 0:
                        supabase.table("gastos").insert({
                            "id_venta": venta["id_venta"],
                            "concepto": concepto,
                            "monto": monto,
                            "fecha_gasto": "now()"
                        }).execute()
                        st.success("¡Gasto registrado!")
                        st.rerun()
                    else:
                        st.error("¡Complete los campos!")
else:
    st.warning("No hay proformas registradas")
    