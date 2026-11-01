import os
import streamlit as st
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

def get_supabase_client() -> Client:
    supabase_url = None
    supabase_key = None

    # 1. Try reading from Streamlit secrets
    try:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
    except Exception:
        pass

    # 3. Validate that valid keys exist
    if not supabase_url or not supabase_key or supabase_url == "YOUR_SUPABASE_URL":
        raise ValueError("Supabase URL and Key are missing! Please check your .streamlit/secrets.toml or environment variables.")

    return create_client(supabase_url, supabase_key)