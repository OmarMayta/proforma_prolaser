import streamlit as st
from supabase import create_client, Client
from decimal import Decimal
import logging

# Configuración inicial
logging.basicConfig(level=logging.DEBUG)
st.set_page_config(page_title="ProLaser: Sistema Contable", layout="wide")
st.title("🧾 ProLaser – Sistema Contable")

# Inicializar variables de sesión
if 'items' not in st.session_state:
    st.session_state.items = [{"desc": "", "precio": 0.0, "cantidad": 1}]

# Conexión a Supabase
@st.cache_resource
def init_supabase():
    try:
        return create_client(
            st.secrets["SUPABASE_URL"],
            st.secrets["SUPABASE_KEY"]
        )
    except Exception as e:
        st.error(f"Error de conexión: {str(e)}")
        return None

supabase = init_supabase()

# Funciones auxiliares
def validar_celular(numero):
    return numero.isdigit() and len(numero) == 9

# Componente para registrar clientes
def registrar_cliente():
    with st.expander("👤 Registrar Cliente", expanded=True):
        with st.form("cliente_form", clear_on_submit=True):
            cols = st.columns([3, 2, 2, 2])
            nombre = cols[0].text_input("Nombre completo*")
            dni = cols[1].text_input("DNI (8 dígitos)", max_chars=8)
            ruc = cols[2].text_input("RUC (11 dígitos)", max_chars=11)
            celular = cols[3].text_input("Celular* (9 dígitos)", max_chars=9)
            
            cols2 = st.columns([3, 3])
            distrito = cols2[0].text_input("Distrito/Provincia")  # Cambiado a text_input
            direccion = cols2[1].text_input("Dirección")
            
            instalacion = st.checkbox("Requiere servicio de instalación")
            
            if st.form_submit_button("Guardar Cliente"):
                valid = True
                if not nombre.strip():
                    st.error("Nombre es obligatorio")
                    valid = False
                if not celular.isdigit() or len(celular) != 9:
                    st.error("Celular debe tener 9 dígitos numéricos")
                    valid = False
                if dni and (not dni.isdigit() or len(dni) != 8):
                    st.error("DNI debe tener 8 dígitos")
                    valid = False
                if ruc and (not ruc.isdigit() or len(ruc) != 11):
                    st.error("RUC debe tener 11 dígitos")
                    valid = False
                
                if valid:
                    try:
                        cliente_data = {
                            "nombre": nombre.strip(),
                            "dni": dni if dni else None,
                            "ruc": ruc if ruc else None,
                            "celular": celular,
                            "distrito": distrito.strip(),
                            "direccion": direccion.strip(),
                            "servicio_instalacion": instalacion
                        }
                        supabase.table("clientes").insert(cliente_data).execute()
                        st.success("Cliente registrado exitosamente!")
                    except Exception as e:
                        st.error(f"Error al guardar: {str(e)}")

# Componente para crear ventas
def crear_venta():
    with st.expander("💼 Nueva Operación", expanded=True):
        if not supabase:
            st.error("No hay conexión a la base de datos")
            return
            
        try:
            clientes = supabase.table("clientes").select("*").execute().data
        except Exception as e:
            st.error(f"Error al cargar clientes: {str(e)}")
            return
            
        if not clientes:
            st.warning("Registra al menos un cliente primero")
            return
            
        cliente_opts = {f"{c['nombre']} | {c['celular']}": c['id'] for c in clientes}
        cliente_selec = st.selectbox("Seleccionar Cliente", options=list(cliente_opts.keys()))
        
        tipo_doc = st.radio("Tipo de documento", ["proforma", "contrato"], horizontal=True)
        
        st.subheader("📦 Productos/Servicios")
        
        # Asegurar que items siempre es una lista
        if not isinstance(st.session_state.items, list):
            st.session_state.items = [{"desc": "", "precio": 0.0, "cantidad": 1}]
            
        # Crear nuevos items si la lista está vacía
        if len(st.session_state.items) == 0:
            st.session_state.items.append({"desc": "", "precio": 0.0, "cantidad": 1})
            
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
            
            st.session_state.items[i] = {"desc": desc, "precio": precio, "cantidad": cantidad}
        
        c1, c2 = st.columns([1,4])
        if c1.button("➕ Añadir Ítem"):
            st.session_state.items.append({"desc": "", "precio": 0.0, "cantidad": 1})
        
        total_venta = sum(item['precio'] * item['cantidad'] for item in st.session_state.items)
        
        st.subheader("💰 Gestión de Pagos")
        adelanto = st.number_input("Adelanto Recibido", min_value=0.0, max_value=float(total_venta), value=0.0)
        saldo = total_venta - adelanto
        st.write(f"**Saldo Pendiente:** S/ {saldo:.2f}")
        
        fecha_entrega = st.date_input("Fecha Estimada de Entrega")
        
        if st.button("💾 Guardar Operación"):
            try:
                if total_venta <= 0:
                    raise ValueError("El total de venta debe ser mayor a 0")
                
                venta_data = {
                    "cliente_id": cliente_opts[cliente_selec],
                    "tipo_documento": tipo_doc,
                    "total_venta": Decimal(total_venta).quantize(Decimal('0.00')),
                    "adelanto": Decimal(adelanto).quantize(Decimal('0.00')),
                    "fecha_entrega": fecha_entrega.isoformat() if fecha_entrega else None
                }
                
                venta = supabase.table("ventas").insert(venta_data).execute().data[0]
                
                for item in st.session_state.items:
                    if item['desc'].strip():  # Solo guardar items con descripción
                        item_data = {
                            "venta_id": venta['id'],
                            "descripcion": item['desc'],
                            "precio_unitario": Decimal(item['precio']).quantize(Decimal('0.00')),
                            "cantidad": item['cantidad']
                        }
                        supabase.table("items_venta").insert(item_data).execute()
                
                st.success(f"Operación {tipo_doc.capitalize()} #{venta['id']} guardada!")
                # Resetear manteniendo la estructura correcta
                st.session_state.items = [{"desc": "", "precio": 0.0, "cantidad": 1}]
                
            except Exception as e:
                st.error(f"Error al guardar: {str(e)}")

# Resto del código de mostrar_historial() se mantiene igual...

# Ejecutar la aplicación
if supabase:
    registrar_cliente()
    st.markdown("---")
    crear_venta()
    st.markdown("---")
    mostrar_historial()
else:
    st.error("No se pudo conectar a la base de datos. Verifica las credenciales.")