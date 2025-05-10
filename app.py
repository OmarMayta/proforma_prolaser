import streamlit as st
from supabase import create_client, Client
from typing import List, Dict
from uuid import UUID

# --- Inicialización Supabase ---
@st.cache_resource(show_spinner=False)
def get_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = get_supabase()

# --- Helpers contables ---
def calc_items_total(items: List[Dict]) -> float:
    return sum(item["unit_price"] * item["quantity"] for item in items)

def calc_expenses_total(expenses: List[Dict]) -> float:
    return sum(e["amount"] for e in expenses)

def calc_profit(sale_total: float, expenses_total: float) -> float:
    return sale_total - expenses_total

# --- UI: Registrar Cliente ---
def register_customer():
    st.header("👤 Registrar Cliente")
    with st.form("form_customer", clear_on_submit=True):
        name  = st.text_input("Nombre completo", max_chars=100)
        phone = st.text_input("Celular / Teléfono")
        if st.form_submit_button("Guardar Cliente"):
            if not name.strip():
                st.error("El nombre es obligatorio.")
            else:
                supabase.table("customers").insert({
                    "name": name.strip(),
                    "phone": phone.strip() or None
                }).execute()
                st.success(f"Cliente «{name}» registrado.")
                st.experimental_rerun()

# --- UI: Crear Proforma/Venta ---
def create_sale():
    st.header("💼 Nueva Proforma / Venta")
    # Carga de clientes
    res = supabase.table("customers").select("*").order("created_at", desc=True).execute()
    customers = res.data or []
    if not customers:
        st.warning("No hay clientes. Registra uno primero.")
        return

    # Selección de cliente
    cust_map = {f"{c['name']} — {c.get('phone','') or '—'}": c["id"] for c in customers}
    cust_choice = st.selectbox("Selecciona Cliente", list(cust_map.keys()))

    # Dinámica de items
    if "n_items" not in st.session_state:
        st.session_state.n_items = 1
    if st.button("➕ Añadir ítem"):
        st.session_state.n_items += 1

    items: List[Dict] = []
    st.markdown("**Detalle de Servicios / Productos**")
    for idx in range(st.session_state.n_items):
        cols = st.columns([4, 1, 1])
        desc  = cols[0].text_input(f"Descripción ítem #{idx+1}", key=f"desc_{idx}")
        price = cols[1].number_input(f"Precio S/.", min_value=0.0, format="%.2f", key=f"price_{idx}")
        qty   = cols[2].number_input(f"Qty", min_value=1, step=1, key=f"qty_{idx}")
        if desc and price > 0:
            items.append({
                "description": desc.strip(),
                "unit_price": price,
                "quantity": int(qty)
            })

    # Dinámica de gastos (opcional al final)
    st.markdown("**Gastos asociados (opcional)**")
    if "n_expenses" not in st.session_state:
        st.session_state.n_expenses = 0
    if st.button("➕ Añadir gasto"):
        st.session_state.n_expenses += 1

    expenses: List[Dict] = []
    for j in range(st.session_state.n_expenses):
        c1, c2 = st.columns([3,1])
        concept = c1.text_input(f"Gasto #{j+1} – Concepto", key=f"exp_concept_{j}")
        amount  = c2.number_input(f"S/.", min_value=0.0, format="%.2f", key=f"exp_amt_{j}")
        if concept and amount > 0:
            expenses.append({"concept": concept.strip(), "amount": amount})

    # Botón final
    if st.button("✅ Guardar Proforma"):
        if not items:
            st.error("Debes añadir al menos un ítem con descripción y precio.")
        else:
            sale_total = calc_items_total(items)
            cust_id = cust_map[cust_choice]

            # Insertar venta
            sale_resp = supabase.table("sales").insert({
                "customer_id": cust_id,
                "total_amount": sale_total
            }).execute()
            sale_id = sale_resp.data[0]["id"]

            # Insertar items
            for it in items:
                supabase.table("sale_items").insert({
                    "sale_id": sale_id,
                    **it
                }).execute()

            # Insertar gastos
            for ex in expenses:
                supabase.table("expenses").insert({
                    "sale_id": sale_id,
                    **ex
                }).execute()

            st.success(f"Proforma guardada con ID: {sale_id}")
            st.experimental_rerun()

# --- UI: Historial y Detalle ---
def show_history():
    st.header("📚 Historial de Proformas")
    res = supabase.table("sales") \
        .select("*, customer:customers(name,phone), sale_items(*), expenses(*)") \
        .order("issue_date", desc=True) \
        .execute()
    sales = res.data or []

    if not sales:
        st.info("Aún no hay proformas registradas.")
        return

    for s in sales:
        header = f"Proforma {s['id']} — {s['customer']['name']} — S/. {s['total_amount']:.2f}"
        with st.expander(header):
            st.write(f"- **Fecha:** {s['issue_date']}")
            st.write(f"- **Cliente:** {s['customer']['name']} ({s['customer']['phone'] or '—'})")
            st.markdown("**Servicios / Productos**")
            for it in s["sale_items"]:
                st.write(f"> {it['description']} — {it['quantity']} × S/. {it['unit_price']:.2f} = S/. {it['line_total']:.2f}")
            st.success(f"**Total Venta:** S/. {s['total_amount']:.2f}")

            if s["expenses"]:
                st.markdown("**Gastos**")
                for ex in s["expenses"]:
                    st.write(f"> {ex['concept']} — S/. {ex['amount']:.2f}")
                total_exp = calc_expenses_total(s["expenses"])
                st.error(f"**Total Gastos:** S/. {total_exp:.2f}")
                profit = calc_profit(s["total_amount"], total_exp)
                st.metric("💰 Utilidad", f"S/. {profit:.2f}")
            else:
                st.info("No hay gastos registrados para esta proforma.")

# --- Layout principal ---
st.set_page_config(page_title="Sistema Contable ProLaser", layout="wide")
st.title("🧮 Sistema Contable ProLaser")

register_customer()
st.markdown("---")
create_sale()
st.markdown("---")
show_history()
