# HDS multiobjetivo con Streamlit

Aplicación para estudiar el compromiso entre conversión de azufre y carga térmica del
horno en una unidad de hidrodesulfuración simplificada (Curso de Optimización de
Procesos, Ingeniería Química).

## Cómo ejecutarla

```bash
python -m venv .venv
source .venv/bin/activate        # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Estructura

```
app.py                 interfaz (controles, pestañas, métricas)
requirements.txt
.streamlit/config.toml tema
utilidades/
    modelo.py          cinética, balance térmico, sensibilidad y validaciones
    pareto.py          frontera de Pareto, knee point, estudio de peso de energía
    graficos.py        figuras de Plotly
    carga.py           funciones con st.cache_data
```

## Qué incluye

- Controles para T_in, ε y los parámetros del modelo (con los rangos del enunciado).
- Malla T_in × ε con marcado de factibilidad (S_out ≤ 10 ppm).
- Frontera de Pareto (sin puntos dominados) y knee point por distancia perpendicular
  con objetivos normalizados min-max.
- Sensibilidad ±10 % en ṁ, Cp, Ea, k₀ y τ; barrido de S_in entre 450 y 550 ppm.
- Los tres sanity checks de validación.
- Estudio opcional de la rodilla frente al peso de la energía.

## Despliegue

Subir el repositorio a GitHub y crear la app en [Streamlit Community Cloud](https://share.streamlit.io)
apuntando a `app.py`.
