"""Hospeda o mapa de campo (Projeto_Digital_Ante_Campo.html) dentro do Streamlit.

Toda a logica de marcar postes, cor por pessoa, selecao em massa e
sincronizacao com a Planilha Google ja esta pronta dentro do proprio html
(veja HTML PUBLICADO/COMO_SINCRONIZAR_COM_PLANILHA.md para configurar a
planilha). Este arquivo so serve o html -- nao reimplementa nada disso em
Python.

A unica adaptacao necessaria pra rodar aqui dentro: o html tenta buscar
"cod_ids_processados.csv" (lista dos postes que ja tem foto) com um
fetch relativo, que nao funciona de dentro do iframe do Streamlit. Por
isso, lemos o csv aqui e injetamos o conteudo direto no html antes de
renderizar (troca o placeholder CSV_BASE_INLINE=null).
"""
import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Projeto Digital - Postes", layout="wide")
st.markdown(
    "<style>div.block-container{padding-top:1rem;padding-bottom:0}</style>",
    unsafe_allow_html=True,
)

BASE_DIR = Path(__file__).parent / "HTML PUBLICADO"
HTML_PATH = BASE_DIR / "Projeto_Digital_Ante_Campo.html"
CSV_PATH = BASE_DIR / "cod_ids_processados.csv"

if not HTML_PATH.exists():
    st.error(f"Nao encontrei o arquivo: {HTML_PATH}")
    st.stop()

html = HTML_PATH.read_text(encoding="utf-8")

if CSV_PATH.exists():
    csv_js = json.dumps(CSV_PATH.read_text(encoding="utf-8"))
    html = html.replace("const CSV_BASE_INLINE=null;", f"const CSV_BASE_INLINE={csv_js};", 1)
else:
    st.warning(f"cod_ids_processados.csv nao encontrado em {BASE_DIR} -- os postes ja fotografados nao vao aparecer pintados de 'Robo'.")

components.html(html, height=1400, scrolling=True)
