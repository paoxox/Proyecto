"""Funciones que devuelven figuras de Plotly (sin dibujar nada en Streamlit)."""
import plotly.graph_objects as go

AZUL, ROJO, GRIS, VERDE, NARANJA = "#1F77B4", "#D62728", "#9AA0A6", "#2CA02C", "#FF7F0E"


def fig_factibilidad(df, t_in=None, eps=None):
    """Mapa T_in vs eps coloreado por S_out."""
    fig = go.Figure()
    fig.add_trace(go.Scattergl(
        x=df["T_in"], y=df["eps"], mode="markers",
        marker=dict(size=5, color=df["S_out"], colorscale="RdYlGn_r",
                    cmax=50, cmin=0, colorbar=dict(title="S_out (ppm)")),
        customdata=df[["X_S", "Q_kW"]],
        hovertemplate="T_in=%{x:.1f} K<br>eps=%{y:.3f}<br>S_out=%{marker.color:.2f} ppm"
                      "<br>X_S=%{customdata[0]:.4f}<br>Q=%{customdata[1]:.0f} kW<extra></extra>",
        name="malla"))
    if t_in is not None:
        fig.add_trace(go.Scatter(x=[t_in], y=[eps], mode="markers", name="punto elegido",
                                 marker=dict(size=14, symbol="x", color="black")))
    fig.update_layout(xaxis_title="T_in (K)", yaxis_title="Efectividad ε",
                      title="Dominio de decisión (verde: cumple S_out ≤ 10 ppm)",
                      margin=dict(t=50, b=40))
    return fig


def fig_pareto(df, frontera, idx_rodilla=None):
    fig = go.Figure()
    nofact = df[~df["factible"]]
    fact = df[df["factible"]]
    fig.add_trace(go.Scattergl(x=1 - nofact["X_S"], y=nofact["Q_kW"], mode="markers",
                               name="no factible", marker=dict(size=4, color=GRIS, opacity=0.35)))
    fig.add_trace(go.Scattergl(x=1 - fact["X_S"], y=fact["Q_kW"], mode="markers",
                               name="factible", marker=dict(size=4, color=AZUL, opacity=0.4)))
    if len(frontera):
        fig.add_trace(go.Scatter(
            x=1 - frontera["X_S"], y=frontera["Q_kW"], mode="lines+markers",
            name="frontera de Pareto", line=dict(color=ROJO, width=2), marker=dict(size=6),
            customdata=frontera[["T_in", "eps", "S_out"]],
            hovertemplate="1-X_S=%{x:.5f}<br>Q=%{y:.0f} kW<br>T_in=%{customdata[0]:.1f} K"
                          "<br>ε=%{customdata[1]:.3f}<br>S_out=%{customdata[2]:.2f} ppm<extra></extra>"))
    if idx_rodilla is not None and len(frontera):
        k = frontera.iloc[idx_rodilla]
        fig.add_trace(go.Scatter(x=[1 - k["X_S"]], y=[k["Q_kW"]], mode="markers", name="knee point",
                                 marker=dict(size=16, symbol="star", color=NARANJA,
                                             line=dict(color="black", width=1))))
    fig.update_layout(xaxis_title="1 − X_S (minimizar)", yaxis_title="Q_horno (kW) (minimizar)",
                      title="Compromiso conversión vs. carga térmica", margin=dict(t=50, b=40))
    return fig


def fig_distancias(frontera, dist, idx):
    fig = go.Figure(go.Scatter(x=frontera["T_in"], y=dist, mode="lines", line=dict(color=AZUL)))
    if len(frontera):
        fig.add_vline(x=float(frontera.iloc[idx]["T_in"]), line_dash="dash", line_color=NARANJA)
    fig.update_layout(xaxis_title="T_in sobre la frontera (K)",
                      yaxis_title="Distancia perpendicular (normalizada)",
                      title="Cómo se localiza la rodilla", margin=dict(t=50, b=40))
    return fig


def fig_tornado(sens, columna="dQ_%", titulo="Efecto sobre Q_horno"):
    nombres = {"m": "ṁ", "cp": "Cp", "ea": "Ea", "k0": "k₀", "tau": "τ"}
    fig = go.Figure()
    for signo, color in ((-10, VERDE), (10, ROJO)):
        sub = sens[sens["cambio_%"].round() == signo]
        fig.add_trace(go.Bar(y=[nombres[x] for x in sub["parametro"]], x=sub[columna],
                             orientation="h", name=f"{signo:+d} %", marker_color=color))
    fig.update_layout(barmode="relative", xaxis_title="Variación (%)", title=titulo,
                      margin=dict(t=50, b=40))
    return fig


def fig_s_in(barrido):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=barrido["S_in_ppm"], y=barrido["S_out_ppm"], mode="lines+markers",
                             line=dict(color=AZUL), name="S_out"))
    fig.add_hline(y=10, line_dash="dash", line_color=ROJO, annotation_text="límite 10 ppm")
    fig.update_layout(xaxis_title="S_in (ppm)", yaxis_title="S_out (ppm)",
                      title="Efecto del azufre de alimentación", margin=dict(t=50, b=40))
    return fig


def fig_rodilla_precio(tabla):
    fig = go.Figure(go.Scatter(x=tabla["peso_energia"], y=tabla["T_in"], mode="lines+markers",
                               line=dict(color=NARANJA)))
    fig.update_layout(xaxis_title="Peso relativo de la energía (w)",
                      yaxis_title="T_in del punto elegido (K)",
                      title="Punto elegido según el peso de la energía", margin=dict(t=50, b=40))
    return fig
