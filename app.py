# --- IMPORTS ---
import os
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# --- LOAD SECRETS FROM .env ---
load_dotenv()

# --- PAGE SETUP ---
st.set_page_config(page_title="Success Coach", page_icon="🎯", layout="centered")

# --- CHECK API KEY ---
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.error("OPENAI_API_KEY not found. Add it to your .env file.")
    st.stop()

# --- CREATE OPENAI CLIENT ---
client = OpenAI(api_key=api_key)

# --- UI HEADER ---
st.title("Talk with your Success Coach")
st.caption("Your personal success coach — ask anything.")

# --- COACH PERSONALITY (system message) ---
SYSTEM_PROMPT = """You are a supportive success coach. Help the user set goals,
stay motivated, and take practical next steps. Be concise and encouraging."""

# --- CHAT HISTORY (persists while app is open) ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- SHOW OLD MESSAGES ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- USER TYPES A NEW MESSAGE ---
if prompt := st.chat_input("Ask your success coach..."):
    # 1) Save and show user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2) Call OpenAI and show coach reply
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = client.chat.completions.create(
                model="gpt-5.4-mini-2026-03-17",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    *[
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state.messages
                    ],
                ],
            )
            reply = response.choices[0].message.content
        st.markdown(reply)

    # 3) Save coach reply for next turns
    st.session_state.messages.append({"role": "assistant", "content": reply})