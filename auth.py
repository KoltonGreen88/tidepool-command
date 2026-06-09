"""
Simple password gate for Streamlit Community Cloud.
Call check_password() at the top of app.py to gate the entire app.
"""
import os
import streamlit as st


def check_password() -> bool:
    app_password = os.getenv("APP_PASSWORD", "tidepool2025")

    if st.session_state.get("authenticated"):
        return True

    st.markdown("""
    <style>
      .stApp { background-color: #0a0f0f; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align:center; padding: 4rem 0 2rem 0;">
      <div style="font-size:2rem; font-weight:800; color:#00C2A8; letter-spacing:0.12em; font-family:monospace;">TIDEPOOL</div>
      <div style="font-size:0.75rem; color:#4a7070; letter-spacing:0.08em; margin-top:4px; font-family:monospace;">Command Agent · S&OP Brain</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([2, 2, 2])
    with col2:
        pwd = st.text_input("Access code", type="password", key="pwd_input", label_visibility="collapsed", placeholder="Enter access code...")
        if st.button("Enter", use_container_width=True):
            if pwd == app_password:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Incorrect access code")

    return False
