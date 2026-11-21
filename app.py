"""Optimización multiobjetivo de una unidad HDS simplificada.

Ejecutar con:  streamlit run app.py
"""
import numpy as np
import pandas as pd
import streamlit as st

from utilidades import graficos, modelo, pareto
from utilidades.carga import calcular_frontera, calcular_malla

st.set_page_config(page_title="HDS multiobjetivo", page_icon=":material/science:", layout="wide")

# Valores por defecto de los controles (se usan también para el botón de reinicio)
DEFAULTS = {
    "t_in": 610.0, "eps": 0.90, "m": 100_000.0, "s_in": 500.0, "cp": 2.5,
    "ea": 80_000.0, "f_k0": 1.0, "tau": 0.5, "n_t": 201, "n_e": 61,
}
for clave, valor in DEFAULTS.items():
    st.session_state.setdefault(clave, valor)


def reiniciar():
    for clave, valor in DEFAULTS.items():
        st.session_state[clave] = valor


# ------------------------------------------------------------------ barra lateral
with st.sidebar:
    st.header("Controles")
    st.slider("Temperatura del reactor T_in (K)", 550.0, 650.0, step=0.5, key="t_in")
    st.slider("Efectividad del intercambiador ε", 0.60, 0.90, step=0.01, key="eps")

    with st.expander("Parámetros del modelo"):
        st.number_input("Flujo másico ṁ (kg/h)", 90_000.0, 110_000.0, step=1000.0, key="m")
        st.number_input("Azufre de alimentación S_in (ppm)", 450.0, 550.0, step=5.0, key="s_in")
        st.number_input("Capacidad calorífica Cp (kJ/kg·K)", 2.25, 2.75, step=0.05, key="cp")
        st.number_input("Energía de activación Ea (J/mol)", 72_000.0, 88_000.0, step=500.0, key="ea")
        st.slider("Factor sobre k₀ calibrado", 0.90, 1.10, step=0.01, key="f_k0",
                  help="k₀ se calibra para X_S(600 K) = 0.985 con los valores base.")
        st.number_input("Tiempo espacial τ (h)", 0.45, 0.55, step=0.01, key="tau")

    with st.expander("Resolución de la malla"):
        st.select_slider("Puntos en T_in", [51, 101, 201, 401], key="n_t")
        st.select_slider("Puntos en ε", [16, 31, 61, 121], key="n_e")

    st.button("Restablecer valores", on_click=reiniciar)

ss = st.session_state
p = modelo.Parametros(m=ss.m, s_in=ss.s_in, cp=ss.cp, ea=ss.ea,
                      k0=modelo.K0_BASE * ss.f_k0, tau=ss.tau)

malla = calcular_malla(p.m, p.s_in, p.cp, p.ea, p.k0, p.tau, ss.n_t, ss.n_e)
frontera, idx_rodilla, dist = calcular_frontera(malla)
actual = modelo.evaluar(ss.t_in, ss.eps, p)

# ------------------------------------------------------------------ cabecera
st.title("Hidrodesulfuración de nafta: conversión vs. carga térmica")
st.caption("Modelo simplificado: reactor de primer orden aparente, balance adiabático "
           "pedagógico e intercambiador por efectividad.")

tab_op, tab_par, tab_sens, tab_val, tab_mod = st.tabs(
    ["Punto de operación", "Pareto y rodilla", "Sensibilidad", "Validación", "Modelo"])

# ------------------------------------------------------------------ punto de operación
with tab_op:
    if actual["factible"]:
        st.success(f"Cumple la especificación: S_out = {float(actual['S_out']):.2f} ppm (≤ 10 ppm).")
    else:
        st.error(f"No cumple la especificación: S_out = {float(actual['S_out']):.2f} ppm (> 10 ppm).")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Conversión X_S", f"{float(actual['X_S']):.5f}")
    c2.metric("S_out", f"{float(actual['S_out']):.2f} ppm")
    c3.metric("Q_horno", f"{float(actual['Q_kW']):,.0f} kW")
    c4.metric("T_efluente", f"{float(actual['T_efluente']):.1f} K")

    izq, der = st.columns([3, 2])
    with izq:
        st.plotly_chart(graficos.fig_factibilidad(malla, ss.t_in, ss.eps), width="stretch")
    with der:
        st.subheader("Temperaturas")
        st.table(pd.DataFrame({
            "Corriente": ["Alimentación", "Salida del intercambiador", "Entrada al reactor", "Efluente"],
            "T (K)": [modelo.T_ALIM, float(actual["T_intercambiador"]), ss.t_in,
                      float(actual["T_efluente"])],
        }).round(2).set_index("Corriente"))
        st.caption(f"Q_horno = {float(actual['Q_kJh']):,.0f} kJ/h. Si sale negativo, la "
                   "aproximación predice excedente de calor (no se recorta).")

# ------------------------------------------------------------------ pareto
with tab_par:
    n_fact = int(malla["factible"].sum())
    frac = n_fact / len(malla)
    c1, c2, c3 = st.columns(3)
    c1.metric("Malla evaluada", f"{len(malla):,} puntos")
    c2.metric("Fracción factible", f"{frac:.1%}")
    c3.metric("Rango de S_out", f"{malla['S_out'].min():.3g} – {malla['S_out'].max():.0f} ppm")

    if frontera.empty:
        st.warning("Con estos parámetros ningún punto de la malla cumple S_out ≤ 10 ppm.")
    else:
        rod = frontera.iloc[idx_rodilla]
        o1, o2, o3 = st.columns(3)
        eje = o1.radio("Eje horizontal", ["1-X_S", "X_S"], horizontal=True,
                       help="El problema se plantea minimizando 1 − X_S; X_S es el mismo "
                            "objetivo visto como maximización.")
        log_x = o2.toggle("Escala logarítmica en x", value=True, disabled=(eje == "X_S"),
                          help="Solo aplica a 1 − X_S, que varía en varios órdenes de magnitud.")
        solo_fact = o3.toggle("Mostrar solo puntos factibles", value=False)
        st.plotly_chart(graficos.fig_pareto(malla, frontera, idx_rodilla, eje=eje, log_x=log_x,
                                            solo_factibles=solo_fact), width="stretch")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Knee point: T_in", f"{rod['T_in']:.1f} K")
        c2.metric("ε", f"{rod['eps']:.2f}")
        c3.metric("S_out", f"{rod['S_out']:.2f} ppm")
        c4.metric("Q_horno", f"{rod['Q_kW']:,.0f} kW")

        st.subheader("Puntos representativos de la frontera")
        posiciones = sorted(set(np.linspace(0, len(frontera) - 1, 6).astype(int)) | {idx_rodilla})
        repres = frontera.iloc[posiciones][["T_in", "eps", "X_S", "S_out", "Q_kJh", "Q_kW"]].copy()
        repres.insert(0, "nota", ["knee point" if i == idx_rodilla else "" for i in posiciones])
        st.dataframe(repres, hide_index=True, column_config={
            "T_in": st.column_config.NumberColumn("T_in (K)", format="%.1f"),
            "eps": st.column_config.NumberColumn("ε", format="%.3f"),
            "X_S": st.column_config.NumberColumn("X_S", format="%.5f"),
            "S_out": st.column_config.NumberColumn("S_out (ppm)", format="%.3f"),
            "Q_kJh": st.column_config.NumberColumn("Q (kJ/h)", format="%.3e"),
            "Q_kW": st.column_config.NumberColumn("Q (kW)", format="%.0f"),
        })

        st.caption(f"Rango de Q_horno en la malla completa: {malla['Q_kJh'].min():.3e} a "
                   f"{malla['Q_kJh'].max():.3e} kJ/h ({malla['Q_kW'].min():,.0f} a "
                   f"{malla['Q_kW'].max():,.0f} kW).")

        with st.expander("Resolución de la malla y limitaciones"):
            dt = 100 / (ss.n_t - 1)
            de = 0.30 / (ss.n_e - 1)
            st.write(
                f"La malla usa pasos de {dt:.2f} K en T_in y {de:.4f} en ε. La frontera es "
                "un conjunto discreto: su posición real puede quedar entre dos nodos, así "
                "que el knee point tiene una incertidumbre del orden de un paso de malla en "
                "T_in. Afinar la malla mejora la forma de la curva, pero el costo crece como "
                "n_T × n_ε. Como el modelo es algebraico, incluso 12 000 puntos se evalúan "
                "en milisegundos. Un grid search no garantiza el óptimo exacto; para eso "
                "habría que usar un método continuo (por ejemplo, NSGA-II o ε-constraint).")
            st.write(
                "Observación: X_S depende solo de T_in, y a T_in fijo Q_horno baja cuando ε "
                "sube. Por eso todos los puntos con ε < ε_max quedan dominados y la frontera "
                "se forma sobre la línea ε = 0.90.")
            st.plotly_chart(graficos.fig_distancias(frontera, dist, idx_rodilla), width="stretch")

        with st.expander("Sensibilidad del knee point al precio de la energía (opcional)"):
            st.write("Se minimiza una suma ponderada de los objetivos normalizados; w grande "
                     "equivale a una energía más cara frente a la calidad. No es un modelo "
                     "económico completo.")
            tabla_w = pareto.rodilla_vs_peso_energia(frontera)
            st.plotly_chart(graficos.fig_rodilla_precio(tabla_w), width="stretch")
            st.dataframe(tabla_w, hide_index=True)

        st.download_button("Descargar frontera (CSV)",
                           frontera.drop(columns="f1").to_csv(index=False).encode("utf-8"),
                           file_name="frontera_pareto.csv", mime="text/csv")

# ------------------------------------------------------------------ sensibilidad
with tab_sens:
    opciones = ["Punto del panel lateral"]
    if not frontera.empty:
        opciones.insert(0, "Knee point")
    base_sel = st.radio("Punto de referencia", opciones, horizontal=True)
    if base_sel == "Knee point":
        t_ref, e_ref = float(frontera.iloc[idx_rodilla]["T_in"]), float(frontera.iloc[idx_rodilla]["eps"])
    else:
        t_ref, e_ref = ss.t_in, ss.eps
    st.caption(f"Referencia: T_in = {t_ref:.1f} K, ε = {e_ref:.2f}")

    sens = modelo.sensibilidad(t_ref, e_ref, p)
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(graficos.fig_tornado(sens, "dQ_%", "Efecto sobre Q_horno (%)"), width="stretch")
    with c2:
        barrido = modelo.barrido_s_in(t_ref, e_ref, p)
        st.plotly_chart(graficos.fig_s_in(barrido), width="stretch")

    st.subheader("Perturbaciones de ±10 %")
    st.dataframe(sens, hide_index=True, column_config={
        "parametro": "Parámetro",
        "cambio_%": st.column_config.NumberColumn("Cambio (%)", format="%+.0f"),
        "Q_kJh": st.column_config.NumberColumn("Q (kJ/h)", format="%.4e"),
        "dQ_%": st.column_config.NumberColumn("ΔQ (%)", format="%+.3f"),
        "S_out_ppm": st.column_config.NumberColumn("S_out (ppm)", format="%.3f"),
        "dS_out_%": st.column_config.NumberColumn("ΔS_out (%)", format="%+.1f"),
        "factible": "¿Factible?",
    })
    st.download_button("Descargar sensibilidad (CSV)", sens.to_csv(index=False).encode("utf-8"),
                       file_name="sensibilidad.csv", mime="text/csv")

# ------------------------------------------------------------------ validación
with tab_val:
    v = modelo.validaciones(p)
    st.write("Los tres chequeos del enunciado, con los parámetros actuales del panel lateral.")

    c1 = v["check1"]
    st.subheader("1. T_in = 650 K, ε = 0.90")
    a, b, c, d = st.columns(4)
    a.metric("X_S", f"{float(c1['X_S']):.7f}")
    b.metric("S_out", f"{float(c1['S_out']):.4f} ppm")
    c.metric("Factible", "Sí" if c1["factible"] else "No")
    d.metric("Q_horno", f"{float(c1['Q_kJh']):.4e} kJ/h")
    st.caption(f"Equivale a {float(c1['Q_kW']):,.1f} kW.")

    c2 = v["check2"]
    st.subheader("2. T_in = 550 K, ε = 0.75")
    a, b = st.columns(2)
    a.metric("S_out", f"{float(c2['S_out']):.1f} ppm")
    b.metric("Factible", "Sí" if c2["factible"] else "No")

    c3 = v["check3"]
    st.subheader("3. Límite ε → 1 (evaluado a T_in = 650 K)")
    a, b, c = st.columns(3)
    a.metric("T_intercambiador", f"{float(c3['T_intercambiador']):.3f} K")
    b.metric("T_efluente", f"{float(c3['T_efluente']):.3f} K")
    c.metric("Q_horno", f"{float(c3['Q_kJh']):.4e} kJ/h")
    st.caption(f"ṁ·Cp·(T_in − T_efluente) = {v['q_limite_kJh']:.4e} kJ/h. El signo negativo "
               "indica que el efluente está más caliente que la entrada al reactor: con un "
               "intercambiador ideal sobraría calor, y no se necesitaría horno.")

# ------------------------------------------------------------------ modelo
with tab_mod:
    st.subheader("Cinética y calidad")
    st.latex(r"k(T)=k_0\,e^{-E_a/(RT)},\quad X_S=1-e^{-k\tau},\quad S_{out}=S_{in}(1-X_S)")
    st.latex(r"k_0=\frac{-\ln(1-0.985)}{\tau\,e^{-E_a/(R\cdot 600)}}")
    st.subheader("Balance térmico")
    st.latex(r"\Delta T_{ad}=15\,X_S,\quad T_{ef}=T_{in}+\Delta T_{ad}")
    st.latex(r"T_{int}=T_{alim}+\varepsilon\,(T_{ef}-T_{alim}),\quad "
             r"Q_{horno}=\dot m\,C_p\,(T_{in}-T_{int})")
    st.subheader("Problema multiobjetivo")
    st.latex(r"\max_{T_{in},\varepsilon}\;X_S\qquad \min_{T_{in},\varepsilon}\;Q_{horno}"
             r"\qquad \text{s.a. } S_{out}\le 10\ \text{ppm}")
    st.markdown(
        "- La calibración de k₀ es pedagógica, no un dato de literatura.\n"
        "- El incremento adiabático de 15 K a conversión completa es una elección didáctica.\n"
        "- El intercambiador usa efectividad constante, con Cp constante y sin pérdidas.\n"
        "- Q_horno negativo se conserva: indica excedente de calor.")
