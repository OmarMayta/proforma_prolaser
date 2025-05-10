import streamlit as st
from supabase import create_client
import pandas as pd

# Conexión a Supabase
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()

# Configuración de página
st.set_page_config(page_title="Sistema de Proformas", layout="wide")
st.title("📋 Sistema de Proformas ProLaser")

# --- FUNCIONES ---
def calcular_total(items):
    return sum(item["precio"] for item in items)

def calcular_utilidad(total_venta, gastos):
    total_gastos = sum(gasto["monto"] for gasto in gastos)
    return total_venta - total_gastos

# --- SECCIÓN CLIENTES ---
with st.expander("👤 Registrar Nuevo Cliente", expanded=True):
    with st.form("form_cliente"):
        nombre = st.text_input("Nombre completo*")
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
st.divider()
with st.expander("💰 Crear Nueva Proforma", expanded=True):
    clientes = supabase.table("clientes").select("*").execute().data
    
    if not clientes:
        st.warning("Primero registra al menos un cliente")
    else:
        with st.form("form_proforma"):
            # Selección de cliente
            cliente_seleccionado = st.selectbox(
                "Seleccionar cliente*",
                options=[f"{c['nombre']} ({c['celular']})" for c in clientes],
                index=0
            )
            
            # Items del servicio
            st.subheader("📝 Items del Servicio")
            items = []
            for i in range(3):  # 3 items iniciales
                col1, col2 = st.columns([3, 1])
                with col1:
                    desc = st.text_input(f"Descripción item {i+1}", key=f"desc_{i}")
                with col2:
                    precio = st.number_input(f"Precio (S/.)", min_value=0.0, format="%.2f", key=f"precio_{i}")
                if desc and precio > 0:
                    items.append({"descripcion": desc, "precio": precio})
            
            # Botón para agregar más items
            if st.button("➕ Agregar otro item"):
                st.session_state["num_items"] = st.session_state.get("num_items", 3) + 1
                st.rerun()
            
            if st.form_submit_button("Guardar Proforma") and items:
                id_cliente = next(c["id_cliente"] for c in clientes if f"{c['nombre']} ({c['celular']})" == cliente_seleccionado)
                total = calcular_total(items)
                
                # Guardar cabecera
                venta = supabase.table("ventas").insert({
                    "id_cliente": id_cliente,
                    "total_venta": total
                }).execute().data[0]
                
                # Guardar items
                for item in items:
                    supabase.table("items_venta").insert({
                        "id_venta": venta["id_venta"],
                        "descripcion": item["descripcion"],
                        "precio": item["precio"]
                    }).execute()
                
                st.success(f"Proforma #{venta['id_venta']} guardada (Total: S/. {total:.2f})")
                st.rerun()

# --- SECCIÓN HISTORIAL ---
st.divider()
st.subheader("📋 Historial de Proformas")

proformas = supabase.table("ventas").select("*, clientes(nombre, celular)").execute().data

if proformas:
    for venta in proformas:
        with st.expander(f"Proforma #{venta['id_venta']} - {venta['clientes']['nombre']} (Total: S/. {venta['total_venta']:.2f})"):
            # Datos básicos
            st.write(f"**Cliente:** {venta['clientes']['nombre']} ({venta['clientes']['celular']})")
            st.write(f"**Fecha:** {venta['fecha_venta']}")
            
            # Items del servicio
            st.markdown("---")
            st.subheader("Servicios contratados")
            items = supabase.table("items_venta").select("*").eq("id_venta", venta["id_venta"]).execute().data
            for item in items:
                st.write(f"- {item['descripcion']}: S/. {item['precio']:.2f}")
            
            # Gastos
            st.markdown("---")
            st.subheader("💸 Gastos asociados")
            gastos = supabase.table("gastos").select("*").eq("id_venta", venta["id_venta"]).execute().data
            
            if gastos:
                for gasto in gastos:
                    st.write(f"- {gasto['concepto']}: S/. {gasto['monto']:.2f}")
                total_gastos = sum(g["monto"] for g in gastos)
                st.success(f"**Total gastos:** S/. {total_gastos:.2f}")
                
                # Utilidad
                utilidad = calcular_utilidad(venta["total_venta"], gastos)
                st.metric("💰 Utilidad del trabajo", f"S/. {utilidad:.2f}")
            else:
                st.warning("No hay gastos registrados")
            
            # Formulario para nuevos gastos
            with st.form(f"form_gastos_{venta['id_venta']}"):
                st.write("**Registrar nuevo gasto**")
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
                        st.error("Complete los campos")
else:
    st.warning("No hay proformas registradas") #hola
    