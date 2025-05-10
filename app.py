import streamlit as st
from supabase import create_client, Client
from typing import List, Dict

# — Conexión a Supabase —
@st.cache_resource(show_spinner=False)
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# — Funciones contables —
def total_items(items: List[Dict]) -> float:
    return sum(it["precio_unitario"] * it["cantidad"] for it in items)

def total_gastos(gastos: List[Dict]) -> float:
    return sum(g["monto"] for g in gastos)

def utilidad(venta: float, gastos_tot: float) -> float:
    return venta - gastos_tot

# — Registrar cliente —
def registrar_cliente():
    st.header("👤 Registrar Cliente")
    with st.form("form_cliente", clear_on_submit=True):
        nombre  = st.text_input("Nombre completo")
        celular = st.text_input("Celular")
        if st.form_submit_button("Guardar"):
            if not nombre.strip():
                st.error("El nombre es obligatorio.")
            else:
                supabase.table("clientes").insert({
                    "nombre": nombre.strip(),
                    "celular": celular.strip() or None
                }).execute()
                st.success(f"Cliente «{nombre}» registrado.")
                st.experimental_rerun()

# — Crear proforma/venta —
def crear_venta():
    st.header("💼 Nueva Proforma / Venta")
    # Traer clientes
    resp = supabase.table("clientes").select("*").order("fecha_creacion", desc=True).execute()
    clientes = resp.data or []
    if not clientes:
        st.warning("Registra al menos un cliente primero.")
        return

    # Mapa nombre→id
    opts = {f"{c['nombre']} ({c.get('celular') or '—'})": c["id"] for c in clientes}
    elegido = st.selectbox("Selecciona Cliente", list(opts.keys()))

    # Ítems de servicio/producto
    if "n_items" not in st.session_state: st.session_state.n_items = 1
    if st.button("➕ Añadir ítem"):
        st.session_state.n_items += 1

    items: List[Dict] = []
    st.subheader("Detalle de ítems")
    for i in range(st.session_state.n_items):
        c1, c2, c3 = st.columns([4,1,1])
        desc = c1.text_input(f"Ítem #{i+1} – Descripción", key=f"desc_{i}")
        pre  = c2.number_input(f"Precio S/.", min_value=0.0, format="%.2f", key=f"pre_{i}")
        cnt  = c3.number_input(f"Cant.", min_value=1, step=1, key=f"cnt_{i}")
        if desc and pre > 0:
            items.append({
                "descripcion": desc.strip(),
                "precio_unitario": pre,
                "cantidad": int(cnt)
            })

    # Gastos asociados
    st.subheader("Gastos asociados (opcional)")
    if "n_gastos" not in st.session_state: st.session_state.n_gastos = 0
    if st.button("➕ Añadir gasto"):
        st.session_state.n_gastos += 1

    gastos: List[Dict] = []
    for j in range(st.session_state.n_gastos):
        d1, d2 = st.columns([3,1])
        cpto = d1.text_input(f"Gasto #{j+1} – Concepto", key=f"cpto_{j}")
        mto  = d2.number_input(f"S/.", min_value=0.0, format="%.2f", key=f"mto_{j}")
        if cpto and mto > 0:
            gastos.append({"concepto": cpto.strip(), "monto": mto})

    # Botón guardar
    if st.button("✅ Guardar Proforma"):
        if not items:
            st.error("Añade al menos un ítem con descripción y precio.")
        else:
            tot_venta = total_items(items)
            id_cliente = opts[elegido]

            # Inserta cabecera
            v = supabase.table("ventas").insert({
                "cliente_id": id_cliente,
                "total_venta": tot_venta
            }).execute().data[0]
            venta_id = v["id"]

            # Inserta ítems
            for it in items:
                supabase.table("items_venta").insert({
                    "venta_id": venta_id,
                    **it
                }).execute()

            # Inserta gastos
            for ex in gastos:
                supabase.table("gastos").insert({
                    "venta_id": venta_id,
                    **ex
                }).execute()

            st.success(f"Proforma ID: {venta_id} guardada.")
            st.experimental_rerun()

# — Mostrar historial —
def mostrar_historial():
    st.header("📚 Historial de Proformas")
    res = (
        supabase.table("ventas")
        .select("*, cliente:clientes(nombre,celular), items_venta(*), gastos(*)")
        .order("fecha_venta", desc=True)
        .execute()
    )
    ventas = res.data or []

    if not ventas:
        st.info("No hay proformas registradas.")
        return

    for ven in ventas:
        título = f"ID {ven['id']} — {ven['cliente']['nombre']} — S/. {ven['total_venta']:.2f}"
        with st.expander(título):
            st.write(f"**Fecha venta:** {ven['fecha_venta']}")
            st.write(f"**Cliente:** {ven['cliente']['nombre']} ({ven['cliente']['celular'] or '—'})")
            st.markdown("**Ítems**")
            for it in ven["items_venta"]:
                st.write(f"- {it['descripcion']} x{it['cantidad']} @ S/. {it['precio_unitario']:.2f} = S/. {it['total_linea']:.2f}")
            st.success(f"Total venta: S/. {ven['total_venta']:.2f}")

            if ven["gastos"]:
                st.markdown("**Gastos**")
                for ex in ven["gastos"]:
                    st.write(f"- {ex['concepto']}: S/. {ex['monto']:.2f}")
                tg = total_gastos(ven["gastos"])
                st.error(f"Total gastos: S/. {tg:.2f}")
                utl = utilidad(ven["total_venta"], tg)
                st.metric("Utilidad", f"S/. {utl:.2f}")
            else:
                st.info("Sin gastos registrados.")

# — Layout principal —
st.set_page_config(page_title="ProLaser: Sistema Contable", layout="wide")
st.title("🧾 ProLaser – Sistema Contable")

registrar_cliente()
st.markdown("---")
crear_venta()
st.markdown("---")
mostrar_historial()
