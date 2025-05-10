import streamlit as st
from supabase import create_client, Client
from datetime import datetime

# Configuración inicial
st.set_page_config(page_title="ProLaser: Sistema Contable", layout="wide")
st.title("🧾 ProLaser – Sistema Contable")

# Conexión a Supabase
@st.cache_resource
def init_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_supabase()

# Funciones auxiliares
def validar_celular(numero):
    return numero.isdigit() and len(numero) == 9

# Componente para registrar clientes
def registrar_cliente():
    with st.expander("👤 Registrar Cliente", expanded=True):
        with st.form("cliente_form", clear_on_submit=True):
            cols = st.columns([2,1,1,2])
            nombre = cols[0].text_input("Nombre completo*")
            dni = cols[1].text_input("DNI (opcional)")
            ruc = cols[2].text_input("RUC (opcional)")
            celular = cols[3].text_input("Celular*")
            
            distrito = st.selectbox("Distrito/Provincia", ["Lima", "Ate", "Surco", "Otro"])
            direccion = st.text_input("Dirección")
            instalacion = st.checkbox("Requiere servicio de instalación")
            
            if st.form_submit_button("Guardar Cliente"):
                if not nombre or not celular:
                    st.error("Nombre y celular son obligatorios")
                elif not validar_celular(celular):
                    st.error("Celular debe tener 9 dígitos")
                else:
                    cliente_data = {
                        "nombre": nombre.strip(),
                        "dni": dni.strip() if dni else None,
                        "ruc": ruc.strip() if ruc else None,
                        "celular": celular.strip(),
                        "distrito": distrito,
                        "direccion": direccion.strip(),
                        "servicio_instalacion": instalacion
                    }
                    supabase.table("clientes").insert(cliente_data).execute()
                    st.success("Cliente registrado exitosamente!")

# Componente para crear ventas
def crear_venta():
    with st.expander("💼 Nueva Operación", expanded=True):
        # Selección de cliente
        clientes = supabase.table("clientes").select("*").execute().data
        if not clientes:
            st.warning("Registra al menos un cliente primero")
            return
            
        cliente_opts = {f"{c['nombre']} | {c['celular']}": c['id'] for c in clientes}
        cliente_selec = st.selectbox("Seleccionar Cliente", options=list(cliente_opts.keys()))
        
        # Tipo de documento
        tipo_doc = st.radio("Tipo de documento", ["proforma", "contrato"], horizontal=True)
        
        # Items de venta
        st.subheader("📦 Productos/Servicios")
        items = []
        if 'items' not in st.session_state:
            st.session_state.items = [{"desc": "", "precio": 0.0, "cantidad": 1}]
        
        for i, item in enumerate(st.session_state.items):
            cols = st.columns([4,1,1,2])
            with cols[0]:
                desc = st.text_input(f"Descripción {i+1}", key=f"desc_{i}")
            with cols[1]:
                precio = st.number_input("Precio Unit.", min_value=0.0, key=f"precio_{i}")
            with cols[2]:
                cantidad = st.number_input("Cant.", min_value=1, key=f"cant_{i}")
            with cols[3]:
                st.write(f"Subtotal: S/{(precio * cantidad):.2f}")
            
            st.session_state.items[i] = {
                "desc": desc,
                "precio": precio,
                "cantidad": cantidad
            }
        
        c1, c2 = st.columns([1,4])
        if c1.button("➕ Añadir Ítem"):
            st.session_state.items.append({"desc": "", "precio": 0.0, "cantidad": 1})
        
        # Calculos totales
        total_venta = sum(item['precio'] * item['cantidad'] for item in st.session_state.items)
        
        # Sección de pagos
        st.subheader("💰 Gestión de Pagos")
        adelanto = st.number_input("Adelanto Recibido", min_value=0.0, max_value=total_venta, value=0.0)
        saldo = total_venta - adelanto
        st.write(f"**Saldo Pendiente:** S/ {saldo:.2f}")
        
        # Fecha de entrega
        fecha_entrega = st.date_input("Fecha Estimada de Entrega")
        
        if st.button("💾 Guardar Operación"):
            # Guardar venta principal
            venta_data = {
                "cliente_id": cliente_opts[cliente_selec],
                "tipo_documento": tipo_doc,
                "total_venta": total_venta,
                "adelanto": adelanto,
                "fecha_entrega": fecha_entrega.isoformat() if fecha_entrega else None
            }
            venta = supabase.table("ventas").insert(venta_data).execute().data[0]
            
            # Guardar items
            for item in st.session_state.items:
                supabase.table("items_venta").insert({
                    "venta_id": venta['id'],
                    "descripcion": item['desc'],
                    "precio_unitario": item['precio'],
                    "cantidad": item['cantidad']
                }).execute()
            
            st.success(f"Operación {tipo_doc.capitalize()} #{venta['id']} guardada!")
            st.session_state.items = []  # Reset items

# Historial y gestión de gastos
def mostrar_historial():
    with st.expander("📚 Historial y Gestión", expanded=True):
        ventas = supabase.table("ventas").select("*, cliente:clientes(*), items_venta(*), gastos(*)").execute().data
        
        # Estadísticas rápidas
        st.subheader("📊 Estado Financiero")
        col1, col2, col3 = st.columns(3)
        total_ventas = sum(v['total_venta'] for v in ventas)
        total_adelantos = sum(v['adelanto'] for v in ventas)
        col1.metric("Ventas Totales", f"S/ {total_ventas:.2f}")
        col2.metric("En Caja", f"S/ {total_adelantos:.2f}")
        col3.metric("Por Cobrar", f"S/ {total_ventas - total_adelantos:.2f}")
        
        # Detalle de operaciones
        st.subheader("📋 Detalle de Operaciones")
        for venta in ventas:
            with st.container():
                cols = st.columns([1,3,2,2])
                cols[0].write(f"**ID:** {venta['id']}")
                cols[1].write(f"**Cliente:** {venta['cliente']['nombre']}")
                cols[2].write(f"**Total:** S/ {venta['total_venta']:.2f}")
                cols[3].write(f"**Saldo:** S/ {venta['saldo']:.2f}")
                
                # Sección editable
                with st.expander("Ver detalles completos"):
                    # Editar datos básicos
                    with st.form(f"editar_venta_{venta['id']}"):
                        nuevo_adelanto = st.number_input("Modificar Adelanto", value=float(venta['adelanto']), 
                                                       max_value=float(venta['total_venta']))
                        if st.form_submit_button("Actualizar Adelanto"):
                            supabase.table("ventas").update({"adelanto": nuevo_adelanto})\
                                   .eq("id", venta['id']).execute()
                            st.rerun()
                    
                    # Gestión de gastos
                    st.write("**Gastos Asociados:**")
                    gastos = venta['gastos']
                    for gasto in gastos:
                        cols = st.columns([3,1,1])
                        cols[0].write(gasto['concepto'])
                        cols[1].write(f"S/ {gasto['monto']:.2f}")
                        if cols[2].button("🗑️", key=f"del_gasto_{gasto['id']}"):
                            supabase.table("gastos").delete().eq("id", gasto['id']).execute()
                            st.rerun()
                    
                    with st.form(f"nuevo_gasto_{venta['id']}"):
                        concepto = st.text_input("Concepto del Gasto")
                        monto = st.number_input("Monto", min_value=0.0)
                        if st.form_submit_button("➕ Añadir Gasto"):
                            supabase.table("gastos").insert({
                                "venta_id": venta['id'],
                                "concepto": concepto,
                                "monto": monto
                            }).execute()
                            st.rerun()

# Ejecutar la aplicación
registrar_cliente()
st.markdown("---")
crear_venta()
st.markdown("---")
mostrar_historial()