import streamlit as st
from supabase import create_client

# Conexión a Supabase (ahora seguro con st.secrets)
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

st.title("📝 Proforma Laser e Imprenta")
st.write("**App Online conectada a Supabase!**")

# Ejemplo: Formulario para agregar clientes
with st.form("Nuevo Cliente"):
    nombre = st.text_input("Nombre del Cliente")
    celular = st.text_input("Celular")
    if st.form_submit_button("Guardar Cliente"):
        supabase.table("clientes").insert({"nombre": nombre, "celular": celular}).execute()
        st.success("¡Cliente guardado en Supabase!")

# Mostrar tabla de clientes
clientes = supabase.table("clientes").select("*").execute()
st.dataframe(clientes.data)