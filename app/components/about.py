import streamlit as st
import fsspec

fs = fsspec.filesystem("")

def about_page():
    with fs.open(f"about.md", 'r') as of:
        text = of.read()
    st.write(text)