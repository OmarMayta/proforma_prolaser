import streamlit as st
from supabase import create_client

# Conexión a Supabase
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

st.title("📝 Proforma ProLaser")
st.write("Creamos lo que Imaginas")

# --- SECCIÓN CLIENTES ---
with st.expander("📌 Registrar Nuevo Cliente"):
    with st.form("form_cliente"):
        nombre_cliente = st.text_input("Nombre del Cliente*", key="nombre_cliente")
        celular_cliente = st.text_input("Celular", key="celular_cliente")
        if st.form_submit_button("Guardar Cliente"):
            if nombre_cliente:
                supabase.table("clientes").insert({
                    "nombre": nombre_cliente,
                    "celular": celular_cliente
                }).execute()
                st.success("¡Cliente guardado!")
                st.rerun()
            else:
                st.error("¡El nombre es obligatorio!")

# --- SECCIÓN PROFORMAS ---
with st.expander("💰 Crear Nueva Proforma", expanded=True):
    with st.form("form_proforma"):
        clientes = supabase.table("clientes").select("*").execute().data
        opciones_clientes = {f"{c['nombre']} ({c['celular']})": c["id_cliente"] for c in clientes}
        
        col1, col2 = st.columns(2)
        with col1:
            cliente_existente = st.selectbox(
                "Seleccionar cliente existente",
                options=[""] + list(opciones_clientes.keys()),
                index=0
            )
        with col2:
            st.write("<div style='height:27px'></div>", unsafe_allow_html=True)
            registrar_nuevo = st.checkbox("Registrar nuevo cliente")
        
        if registrar_nuevo:
            nuevo_nombre = st.text_input("Nombre del nuevo cliente*")
            nuevo_celular = st.text_input("Celular")
        
        st.subheader("Detalles del Trabajo")
        descripcion = st.text_area("Descripción*", placeholder="Ej: Corte láser en acrílico 5mm")
        total = st.number_input("Total (S/.)*", min_value=0.0, format="%.2f")
        
        if st.form_submit_button("Guardar Proforma"):
            if not descripcion or total <= 0:
                st.error("¡Descripción y total son obligatorios!")
            else:
                if registrar_nuevo and nuevo_nombre:
                    cliente_response = supabase.table("clientes").insert({
                        "nombre": nuevo_nombre,
                        "celular": nuevo_celular
                    }).execute()
                    id_cliente = cliente_response.data[0]["id_cliente"]
                elif cliente_existente:
                    id_cliente = opciones_clientes[cliente_existente]
                else:
                    st.error("¡Selecciona o registra un cliente!")
                    st.stop()
                
                supabase.table("ventas").insert({
                    "id_cliente": id_cliente,
                    "descripcion_servicio": descripcion,
                    "total_venta": total,
                    "fecha_venta": "now()"
                }).execute()
                st.success("¡Proforma guardada!")
                st.rerun()

# --- HISTORIAL DE PROFORMAS CON GASTOS ---
st.divider()
st.subheader("📋 Historial de Proformas")

proformas = supabase.table("ventas").select("*, clientes(nombre, celular)").execute().data

if proformas:
    for venta in proformas:
        with st.expander(f"Proforma #{venta['id_venta']} - {venta['clientes']['nombre']}"):
            st.write(f"**Cliente:** {venta['clientes']['nombre']} ({venta['clientes']['celular']})")
            st.write(f"**Descripción:** {venta['descripcion_servicio']}")
            st.write(f"**Total:** S/. {venta['total_venta']:.2f}")
            st.write(f"**Fecha:** {venta['fecha_venta']}")
            
            # --- SECCIÓN DE GASTOS ---
            st.markdown("---")
            st.subheader("💸 Gastos Asociados")
            
            gastos = supabase.table("gastos").select("*").eq("id_venta", venta["id_venta"]).execute().data
            
            if gastos:
                total_gastos = 0
                for i, gasto in enumerate(gastos):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**{gasto['concepto']}**")
                    with col2:
                        st.write(f"S/. {gasto['monto']:.2f}")
                    total_gastos += gasto["monto"]
                
                st.success(f"**Total gastado:** S/. {total_gastos:.2f}")
                
                # Calcular utilidad
                utilidad = venta["total_venta"] - total_gastos
                st.metric("💰 Utilidad estimada", f"S/. {utilidad:.2f}")
            else:
                st.warning("No hay gastos registrados para esta proforma.")
            
            # Botón para agregar gastos
            if st.button(f"➕ Agregar gastos", key=f"btn_gastos_{venta['id_venta']}"):
                st.session_state["proforma_seleccionada"] = venta["id_venta"]
                st.rerun()
else:
    st.warning("No hay proformas registradas aún.")

# --- FORMULARIO DE GASTOS ---
if "proforma_seleccionada" in st.session_state:
    st.divider()
    st.subheader("📝 Registrar Nuevos Gastos")
    
    with st.form("form_gastos"):
        # Mostrar proforma seleccionada
        proforma = supabase.table("ventas").select("*, clientes(nombre)").eq("id_venta", st.session_state["proforma_seleccionada"]).execute().data[0]
        st.write(f"**Proforma seleccionada:** #{proforma['id_venta']} - {proforma['clientes']['nombre']}")
        
        # Campos para gastos
        concepto = st.text_input("Concepto* (Ej: Materiales)", key="concepto")
        monto = st.number_input("Monto (S/.)*", min_value=0.0, format="%.2f", key="monto")
        
        if st.form_submit_button("Guardar Gastos"):
            if concepto and monto > 0:
                supabase.table("gastos").insert({
                    "id_venta": st.session_state["proforma_seleccionada"],
                    "concepto": concepto,
                    "monto": monto,
                    "fecha_gasto": "now()"
                }).execute()
                st.success("¡Gasto registrado!")
                st.session_state.pop("proforma_seleccionada")
                st.rerun()
            else:
                st.error("¡Concepto y monto son obligatorios!")