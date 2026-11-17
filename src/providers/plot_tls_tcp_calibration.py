"""
Genera la figura de calibración de la duración del establecimiento de TLS
(capítulo 4 de la tesis) como SVG. No se genera si el punto de observación no
es válido (ver MAX_VANTAGE_EDGE_RTT_MS en summarize_scenarios.py).

Usa los mismos datos y criterios que summarize_scenarios.py:
  * Fuente: ANYCAST_EDGE_HEADERS_CALIBRATION_FILEPATH si existe; si no, la
    comprobación de cabeceras actual restringida a las IPs clasificadas.
  * Grupos: pares con cabecera de capa 7 (escenario a) y pares de AWS
    clasificados como escenario (b) por rangos (Global Accelerator).
  * Umbrales: los de calibrate_thresholds() (percentil 99 de capa 7 y
    percentil 10 de Global Accelerator).

La figura muestra la distribución acumulada de la duración del TLS de cada grupo, los dos
umbrales con la zona ambigua entre ellos.

El texto del SVG se guarda como texto (svg.fonttype = "none"), de modo que al
incluirlo en la tesis con \\includesvg se compone con la tipografía del documento.

Salida: TLS_TCP_CALIBRATION_FIGURE_FILEPATH. Al terminar se muestran por
pantalla las cifras que cita el texto de la tesis.
"""
# external imports
import csv
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
# internal imports
from src.utils.constants import (
    ANYCAST_PROVIDER_CLASSIFICATION_FILEPATH,
    ANYCAST_EDGE_HEADERS_CHECK_FILEPATH,
    ANYCAST_EDGE_HEADERS_CALIBRATION_FILEPATH,
    TLS_TCP_CALIBRATION_FIGURE_FILEPATH,
)
from src.providers.summarize_scenarios import (
    LOW_PERCENTILE,
    HIGH_PERCENTILE,
    calibration_samples,
    calibrate_thresholds,
    vantage_is_valid,
    vantage_edge_rtt,
)

X_MIN_MS, X_MAX_MS = 2, 1000
COLOR_LAYER7 = "#0072B2"
COLOR_LAYER4 = "#D55E00"


def calibration_source(classification=ANYCAST_PROVIDER_CLASSIFICATION_FILEPATH,
                       edge_check=ANYCAST_EDGE_HEADERS_CHECK_FILEPATH,
                       calibration_check=ANYCAST_EDGE_HEADERS_CALIBRATION_FILEPATH):
    """Misma fuente de calibración que summarize_scenarios()."""
    if os.path.exists(calibration_check):
        return calibration_check, None
    with open(classification) as f:
        return edge_check, {row["ip"] for row in csv.DictReader(f)}


def plot_tls_tcp_calibration(outfile=TLS_TCP_CALIBRATION_FIGURE_FILEPATH):
    source, only_ips = calibration_source()
    print(f"Figura de calibración con {os.path.basename(source)}")
    if not vantage_is_valid(source, only_ips):
        print("No se genera la figura: las medidas no son válidas para la calibración.")
        return None
    low_ms, high_ms = calibrate_thresholds(source, only_ips=only_ips)
    layer7, layer4 = (np.array(v) for v in calibration_samples(source, only_ips))

    plt.rcParams["svg.fonttype"] = "none"   # texto como texto en el SVG
    fig, ax = plt.subplots(figsize=(7.2, 3.8))

    ax.axvspan(low_ms, high_ms, color="0.88", zorder=0, label="Ambiguous range")
    for values, label, color in (
        (layer7, f"Connections with layer-7 headers, scenario (a) (n = {len(layer7)})", COLOR_LAYER7),
        (layer4, f"Connections to AWS Global Accelerator, scenario (b) (n = {len(layer4)})", COLOR_LAYER4),
    ):
        fraction = np.arange(1, len(values) + 1) / len(values)
        ax.step(values, fraction, where="post", color=color, linewidth=1.8, label=label)

    ax.axvline(low_ms, color=COLOR_LAYER7, linestyle="--", linewidth=1)
    ax.axvline(high_ms, color=COLOR_LAYER4, linestyle="--", linewidth=1)
    ax.text(low_ms, 0.03, f"{low_ms:.1f} ms \n(p{LOW_PERCENTILE * 100:.0f} layer-7) ",
            color=COLOR_LAYER7, fontsize=8, ha="right", va="bottom")
    ax.text(high_ms, 0.03, f" {high_ms:.1f} ms\n (p{HIGH_PERCENTILE * 100:.0f} Global Accelerator)",
            color=COLOR_LAYER4, fontsize=8, ha="left", va="bottom")

    ax.set_xscale("log")
    ax.set_xlim(X_MIN_MS, X_MAX_MS)
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("Duration of the TLS handshake (ms)")
    ax.set_ylabel("Cumulative fraction of connections")
    ax.grid(True, which="both", alpha=0.25)


    fig.legend(fontsize=8, loc="lower center", ncol=1, frameon=False, bbox_to_anchor=(0.5, 0))
    fig.tight_layout(rect=(0, 0.17, 1, 1))
    os.makedirs(os.path.dirname(outfile), exist_ok=True)
    fig.savefig(outfile)
    plt.close(fig)

    print(f"Figura guardada en {outfile}")
    print(f"  Mediana del handshake TCP hacia los bordes de capa 7: {vantage_edge_rtt(source, only_ips):.1f} ms")
    print(f"  Capa 7: n={len(layer7)}, mediana={np.median(layer7):.1f} ms, "
          f"umbral bajo={low_ms:.1f} ms")
    print(f"  Global Accelerator: n={len(layer4)}, mediana={np.median(layer4):.1f} ms, "
          f"umbral alto={high_ms:.1f} ms")
    print(f"  Capa 7 por encima de {high_ms:.1f} ms: {int((layer7 >= high_ms).sum())}; "
          f"Global Accelerator por debajo de {low_ms:.1f} ms: {int((layer4 <= low_ms).sum())}")
    return outfile
