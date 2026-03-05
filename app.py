from transformers import pipeline
import streamlit as st

st.title("AI Agent Browser")

generator = pipeline("text-generation", model="distilgpt2")

prompt = st.text_input("Ask something")

if prompt:
    result = generator(prompt, max_length=100)
    st.write(result[0]["generated_text"])
