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
            if nombre_cliente:  # Validación básica
                supabase.table("clientes").insert({
                    "nombre": nombre_cliente,
                    "celular": celular_cliente
                }).execute()
                st.success("¡Cliente guardado!")
                st.rerun()  # Actualiza la vista
            else:
                st.error("¡El nombre es obligatorio!")

# --- SECCIÓN PROFORMAS ---
with st.expander("💰 Crear Nueva Proforma", expanded=True):
    with st.form("form_proforma"):
        # Seleccionar cliente existente o registrar uno nuevo
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
        
        # Detalles del servicio
        st.subheader("Detalles del Trabajo")
        descripcion = st.text_area("Descripción*", placeholder="Ej: Corte láser en acrílico 5mm")
        total = st.number_input("Total (S/.)*", min_value=0.0, format="%.2f")
        
        if st.form_submit_button("Guardar Proforma"):
            if not descripcion or total <= 0:
                st.error("¡Descripción y total son obligatorios!")
            else:
                # Manejo del cliente
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
                
                # Guardar proforma
                supabase.table("ventas").insert({
                    "id_cliente": id_cliente,
                    "descripcion_servicio": descripcion,
                    "total_venta": total,
                    "fecha_venta": "now()"
                }).execute()
                st.success("¡Proforma guardada!")
                st.rerun()

# --- HISTORIAL ---
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
            st.markdown("---")
            st.subheader("📝 Gastos Registrados")
            
            # --- SECCIÓN DE GASTOS DENTRO DE CADA PROFORMA ---
            st.markdown("---")
            st.subheader("📝 Gastos Asociados")
            
            # Obtener gastos de ESTA proforma específica
            gastos = supabase.table("gastos").select("*").eq("id_venta", venta["id_venta"]).execute().data
            
            if gastos:
                total_gastos = 0
                for gasto in gastos:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**Concepto:** {gasto['concepto']}")
                    with col2:
                        st.write(f"**Monto:** S/. {gasto['monto']:.2f}")
                    total_gastos += gasto["monto"]
                
                st.success(f"**Total de gastos:** S/. {total_gastos:.2f}")
                
                # Calcular utilidad (Total Venta - Total Gastos)
                utilidad = venta["total_venta"] - total_gastos
                st.metric("💰 Utilidad estimada", f"S/. {utilidad:.2f}")
            else:
                st.warning("No hay gastos registrados para esta proforma.")
            
            # Botón para agregar más gastos (redirige a la sección de abajo)
            if st.button(f"➕ Agregar gastos a esta proforma", key=f"btn_gastos_{venta['id_venta']}"):
                st.session_state["proforma_seleccionada"] = venta["id_venta"]
                st.rerun()
else:
    st.warning("No hay proformas registradas aún.")

# --- SECCIÓN GASTOS ---
st.divider()
st.subheader("💸 Registrar Gastos por Proforma")

# Si se seleccionó una proforma desde el botón
proforma_seleccionada_id = st.session_state.get("proforma_seleccionada", None)

# Obtener todas las proformas para el selectbox
proformas_disponibles = supabase.table("ventas").select("id_venta, descripcion_servicio, clientes(nombre)").execute().data

if not proformas_disponibles:
    st.warning("No hay proformas registradas para agregar gastos.")
else:
    # Crear diccionario para el selectbox
    opciones_proformas = {
        f"Proforma #{p['id_venta']} - {p['clientes']['nombre']}": p["id_venta"] 
        for p in proformas_disponibles
    }
    
    with st.form("form_gastos"):
        # Seleccionar proforma (auto-selecciona si viene del botón)
        if proforma_seleccionada_id:
            proforma_seleccionada_nombre = next(
                k for k, v in opciones_proformas.items() 
                if v == proforma_seleccionada_id
            )
            proforma_seleccionada = st.selectbox(
                "Proforma seleccionada",
                options=[proforma_seleccionada_nombre],
                index=0
            )
        else:
            proforma_seleccionada = st.selectbox(
                "Seleccionar Proforma*",
                options=list(opciones_proformas.keys())
            )
        
        id_venta = opciones_proformas[proforma_seleccionada]
        
        # Campos para gastos
        st.write("**Detalles de Gastos:**")
        concepto_1 = st.text_input("Concepto 1* (Ej: Materiales)", key="concepto1")
        monto_1 = st.number_input("Monto 1 (S/.)*", min_value=0.0, format="%.2f", key="monto1")
        
        concepto_2 = st.text_input("Concepto 2 (Ej: Transporte)", key="concepto2")
        monto_2 = st.number_input("Monto 2 (S/.)", min_value=0.0, format="%.2f", key="monto2")
        
        if st.form_submit_button("Guardar Gastos"):
            # Validar y guardar
            gastos = []
            if concepto_1 and monto_1:
                gastos.append({
                    "id_venta": id_venta,
                    "concepto": concepto_1,
                    "monto": monto_1,
                    "fecha_gasto": "now()"
                })
            if concepto_2 and monto_2:
                gastos.append({
                    "id_venta": id_venta,
                    "concepto": concepto_2,
                    "monto": monto_2,
                    "fecha_gasto": "now()"
                })
            
            if gastos:
                supabase.table("gastos").insert(gastos).execute()
                st.success("¡Gastos registrados!")
                st.session_state.pop("proforma_seleccionada", None)  # Limpiar selección
                st.rerun()
            else:
                st.error("¡Ingresa al menos un gasto válido!")