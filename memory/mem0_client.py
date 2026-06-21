import os
import streamlit as st

from dotenv import load_dotenv
from mem0 import MemoryClient


load_dotenv()


def get_mem0_client():

    # Local .env
    api_key = os.getenv(
        "MEM0_API_KEY"
    )


    # Streamlit Cloud secrets
    if not api_key:

        try:
            api_key = st.secrets["MEM0_API_KEY"]

        except Exception:
            raise Exception(
                "MEM0_API_KEY not found in .env or Streamlit secrets"
            )


    return MemoryClient(
        api_key=api_key
    )