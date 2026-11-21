"""Cálculos pesados con caché, para que los reruns de Streamlit sean baratos."""
import streamlit as st

from utilidades import modelo, pareto


@st.cache_data(show_spinner="Evaluando la malla...")
def calcular_malla(m, s_in, cp, ea, k0, tau, n_t, n_e):
    p = modelo.Parametros(m=m, s_in=s_in, cp=cp, ea=ea, k0=k0, tau=tau)
    return modelo.malla(p, n_t, n_e)


@st.cache_data
def calcular_frontera(df):
    fr = pareto.frontera_pareto(df[df["factible"]])
    if fr.empty:
        return fr, 0, []
    idx, dist = pareto.punto_rodilla(fr)
    return fr, idx, dist
