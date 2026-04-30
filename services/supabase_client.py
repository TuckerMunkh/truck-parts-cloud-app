import streamlit as st
from supabase import create_client

BUCKET = "part-photos"

@st.cache_resource
def get_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
