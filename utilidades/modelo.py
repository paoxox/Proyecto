"""Modelo simplificado de la unidad HDS (reactor, balance térmico y horno).

Todo está escrito con numpy para poder evaluar mallas completas de una vez.
"""
from dataclasses import dataclass, replace

import numpy as np
import pandas as pd

R = 8.314             # J/(mol K)
T_ALIM = 300.0        # K, temperatura de la alimentación fresca
DT_AD_MAX = 15.0      # K, elevación adiabática a conversión completa
S_MAX = 10.0          # ppm, especificación del producto
T_CALIB = 600.0       # K, punto de calibración de k0
X_CALIB = 0.985       # conversión en el punto de calibración
EA_BASE = 80_000.0    # J/mol
TAU_BASE = 0.5        # h

# k0 se calibra una sola vez con los valores base de Ea y tau. Si luego el usuario
# cambia Ea o tau, k0 NO se recalcula: se perturba por separado (+-10 %), tal como
# pide el enunciado.
K0_BASE = float(-np.log(1 - X_CALIB) / (TAU_BASE * np.exp(-EA_BASE / (R * T_CALIB))))


@dataclass(frozen=True)
class Parametros:
    m: float = 100_000.0     # kg/h
    s_in: float = 500.0      # ppm peso
    cp: float = 2.5          # kJ/(kg K)
    ea: float = EA_BASE      # J/mol
    k0: float = K0_BASE      # 1/h
    tau: float = TAU_BASE    # h


def constante_cinetica(t_in, p: Parametros):
    return p.k0 * np.exp(-p.ea / (R * np.asarray(t_in, dtype=float)))


def conversion(t_in, p: Parametros):
    return 1.0 - np.exp(-constante_cinetica(t_in, p) * p.tau)


def azufre_salida(t_in, p: Parametros):
    return p.s_in * (1.0 - conversion(t_in, p))


def temp_efluente(t_in, p: Parametros):
    return np.asarray(t_in, dtype=float) + DT_AD_MAX * conversion(t_in, p)


def temp_intercambiador(t_in, eps, p: Parametros):
    t_ef = temp_efluente(t_in, p)
    return T_ALIM + np.asarray(eps, dtype=float) * (t_ef - T_ALIM)


def q_horno(t_in, eps, p: Parametros):
    """Carga del horno en kJ/h. Puede ser negativa (excedente de calor)."""
    return p.m * p.cp * (np.asarray(t_in, dtype=float) - temp_intercambiador(t_in, eps, p))


def kjh_a_kw(q):
    return np.asarray(q) / 3600.0


def evaluar(t_in, eps, p: Parametros) -> dict:
    """Evalúa un punto (o arreglos del mismo tamaño) y devuelve un diccionario."""
    x = conversion(t_in, p)
    s = p.s_in * (1.0 - x)
    q = q_horno(t_in, eps, p)
    return {
        "T_in": t_in,
        "eps": eps,
        "X_S": x,
        "S_out": s,
        "factible": s <= S_MAX,
        "T_efluente": temp_efluente(t_in, p),
        "T_intercambiador": temp_intercambiador(t_in, eps, p),
        "Q_kJh": q,
        "Q_kW": kjh_a_kw(q),
    }


def malla(p: Parametros, n_t: int = 201, n_e: int = 61) -> pd.DataFrame:
    """Grid search completo sobre el dominio T_in x eps."""
    t = np.linspace(550.0, 650.0, n_t)
    e = np.linspace(0.60, 0.90, n_e)
    tt, ee = np.meshgrid(t, e)
    return pd.DataFrame(evaluar(tt.ravel(), ee.ravel(), p))


def sensibilidad(t_in: float, eps: float, p: Parametros, frac: float = 0.10) -> pd.DataFrame:
    """Perturba cada parámetro +-frac y reporta el efecto en Q_horno y S_out."""
    base = evaluar(t_in, eps, p)
    filas = []
    for nombre in ("m", "cp", "ea", "k0", "tau"):
        for signo in (-1, 1):
            q_nuevo = replace(p, **{nombre: getattr(p, nombre) * (1 + signo * frac)})
            r = evaluar(t_in, eps, q_nuevo)
            filas.append({
                "parametro": nombre,
                "cambio_%": signo * frac * 100,
                "Q_kJh": float(r["Q_kJh"]),
                "dQ_%": float((r["Q_kJh"] / base["Q_kJh"] - 1) * 100),
                "S_out_ppm": float(r["S_out"]),
                "dS_out_%": float((r["S_out"] / base["S_out"] - 1) * 100),
                "factible": bool(r["factible"]),
            })
    return pd.DataFrame(filas)


def barrido_s_in(t_in: float, eps: float, p: Parametros, n: int = 11) -> pd.DataFrame:
    """S_in se explora dentro del rango de la tabla (450-550 ppm)."""
    filas = []
    for s in np.linspace(450.0, 550.0, n):
        r = evaluar(t_in, eps, replace(p, s_in=float(s)))
        filas.append({"S_in_ppm": float(s), "S_out_ppm": float(r["S_out"]),
                      "factible": bool(r["factible"]), "Q_kJh": float(r["Q_kJh"])})
    return pd.DataFrame(filas)


def validaciones(p: Parametros) -> dict:
    """Los tres sanity checks del enunciado."""
    c1 = evaluar(650.0, 0.90, p)
    c2 = evaluar(550.0, 0.75, p)
    # Tercer check: eps -> 1 (1.0 se usa solo como límite teórico)
    c3 = evaluar(650.0, 1.0, p)
    q_limite = p.m * p.cp * (650.0 - float(c3["T_efluente"]))
    return {"check1": c1, "check2": c2, "check3": c3, "q_limite_kJh": q_limite}
