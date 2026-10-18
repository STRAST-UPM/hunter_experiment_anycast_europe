"""
Combina la clasificación por rangos de IP (classify_providers) con la
comprobación de cabeceras y tiempos (check_edge_headers) para estimar, por IP
anycast, si TLS termina en el último elemento de la conexión IP (lo que
localiza Hunter) o más allá de él.

Reglas por par (IP, host) que respondió en la comprobación:
  * cabecera de proxy de capa 7               -> TLS en el extremo IP
  * sin cabecera y TLS-TCP <= LOW_MS          -> TLS en el extremo IP (tiempos)
  * sin cabecera y TLS-TCP >= HIGH_MS         -> TLS más allá del extremo IP
  * sin cabecera y entre ambos umbrales       -> ambiguo

Umbrales obtenidos de los propios datos:
  * LOW_MS:  percentil 99 de TLS-TCP en los pares con cabecera de capa 7.
  * HIGH_MS: percentil 10 de TLS-TCP en AWS Global Accelerator (capa 4).
Se recalculan con calibrate_thresholds() y se muestran al ejecutar.

Una IP se marca como (b) si alguno de sus pares termina TLS más allá del
extremo IP, como (a/c) si todos lo terminan en el extremo y como ambigua en el
resto de casos. Si los tiempos son ambiguos pero los rangos de IP identifican el
producto (escenario a o b), prevalece la clasificación por rangos. Las IPs sin
respuesta conservan también la clasificación por rangos.

Calibración: si existe ANYCAST_EDGE_HEADERS_CALIBRATION_FILEPATH (una
comprobación más amplia, por ejemplo con todas las IPs anycast y --all), los
umbrales se calculan con ella; si no, con la comprobación actual. Si alguna de
las dos muestras tiene menos de MIN_CALIBRATION_SAMPLES pares, se usan los
valores por defecto.

La columna basis indica "(IP actual)" cuando la comprobación se hizo con la
resolución DNS de hoy porque la IP histórica ya no atendía al host.

Entrada: ANYCAST_PROVIDER_CLASSIFICATION_FILEPATH y ANYCAST_EDGE_HEADERS_CHECK_FILEPATH.
Salida:  ANYCAST_SCENARIOS_FILEPATH con columnas
         ip,provider,product,scenario_by_ranges,final_estimate,basis
"""
# external imports
import csv
import os
from collections import Counter, defaultdict
# internal imports
from src.utils.constants import (
    ANYCAST_PROVIDER_CLASSIFICATION_FILEPATH,
    ANYCAST_EDGE_HEADERS_CHECK_FILEPATH,
    ANYCAST_SCENARIOS_FILEPATH,
    ANYCAST_EDGE_HEADERS_CALIBRATION_FILEPATH,
)

LOW_PERCENTILE, HIGH_PERCENTILE = 0.99, 0.10
MIN_CALIBRATION_SAMPLES = 20
DEFAULT_LOW_MS, DEFAULT_HIGH_MS = 45.0, 65.0

AT_ENDPOINT = "(a/c) TLS en el extremo IP"
BEYOND = "(b) TLS más allá del extremo IP"
AMBIGUOUS = "ambiguo"
BY_RANGES = {"a": "(a) solo por rangos", "b": "(b) solo por rangos"}
UNDETERMINED = "sin determinar"


def percentile(values, p):
    values = sorted(values)
    return values[min(len(values) - 1, int(p * len(values)))]


def responded(row):
    return row["http_code"] != "sin respuesta" and row["tls_minus_tcp_ms"] != ""


def calibrate_thresholds(edge_check=ANYCAST_EDGE_HEADERS_CHECK_FILEPATH, only_ips=None):
    """Umbrales de TLS-TCP a partir de los casos de escenario conocido de la
    propia comprobación: pares con cabecera de capa 7 y pares de AWS clasificados
    como escenario (b) por rangos (Global Accelerator). Con only_ips, solo se
    usan esas IPs (por ejemplo, las de la clasificación actual)."""
    l7, l4 = [], []
    with open(edge_check) as f:
        for row in csv.DictReader(f):
            if (only_ips is not None and row["ip"] not in only_ips) or not responded(row):
                continue
            delta = float(row["tls_minus_tcp_ms"])
            if row["edge_product"]:
                l7.append(delta)
            elif row["provider"] == "AWS" and row["scenario_by_ranges"] == "b":
                l4.append(delta)
    if len(l7) < MIN_CALIBRATION_SAMPLES or len(l4) < MIN_CALIBRATION_SAMPLES:
        print(f"Aviso: muestras insuficientes para calibrar (capa 7 n={len(l7)}, "
              f"Global Accelerator n={len(l4)}; mínimo {MIN_CALIBRATION_SAMPLES}); "
              f"se usan los valores por defecto.")
        return DEFAULT_LOW_MS, DEFAULT_HIGH_MS
    low = percentile(l7, LOW_PERCENTILE)
    high = percentile(l4, HIGH_PERCENTILE)
    print(f"Calibración TLS-TCP: capa 7 n={len(l7)} -> umbral bajo {low:.1f} ms "
          f"(p{LOW_PERCENTILE * 100:.0f}); Global Accelerator n={len(l4)} -> umbral alto {high:.1f} ms "
          f"(p{HIGH_PERCENTILE * 100:.0f})")
    if low >= high:
        print("Aviso: los umbrales se solapan; se usan los valores por defecto.")
        return DEFAULT_LOW_MS, DEFAULT_HIGH_MS
    return low, high


def pair_label(row, low_ms, high_ms):
    if not responded(row):
        return None
    if row["edge_product"]:
        return "endpoint"
    delta = float(row["tls_minus_tcp_ms"])
    if delta <= low_ms:
        return "endpoint"
    if delta >= high_ms:
        return "beyond"
    return "ambiguous"


def summarize_scenarios(classification=ANYCAST_PROVIDER_CLASSIFICATION_FILEPATH,
                        edge_check=ANYCAST_EDGE_HEADERS_CHECK_FILEPATH,
                        outfile=ANYCAST_SCENARIOS_FILEPATH,
                        calibration_check=ANYCAST_EDGE_HEADERS_CALIBRATION_FILEPATH):
    # Calibración con una comprobación más amplia si existe (p. ej., todas las
    # IPs anycast con --all): mismo método y ubicación, más casos conocidos
    if os.path.exists(calibration_check):
        print(f"Calibración con {os.path.basename(calibration_check)}")
        low_ms, high_ms = calibrate_thresholds(calibration_check)
    else:
        with open(classification) as f:
            classified_ips = {row["ip"] for row in csv.DictReader(f)}
        low_ms, high_ms = calibrate_thresholds(edge_check, only_ips=classified_ips)

    by_range = {}
    with open(classification) as f:
        for row in csv.DictReader(f):
            by_range.setdefault(row["ip"], (row["scenario"], row["provider"], row["product"]))

    labels, targets = defaultdict(list), defaultdict(set)
    with open(edge_check) as f:
        for row in csv.DictReader(f):
            label = pair_label(row, low_ms, high_ms)
            if label:
                labels[row["ip"]].append(label)
                targets[row["ip"]].add(row.get("probe_target", "IP histórica"))

    rows = []
    for ip, (scenario, provider, product) in by_range.items():
        ip_labels = labels.get(ip)
        if ip_labels:
            evidence = "cabeceras y tiempos" + \
                ("" if targets[ip] == {"IP histórica"} else " (IP actual)")
            if "beyond" in ip_labels:
                final, basis = BEYOND, evidence
            elif all(label == "endpoint" for label in ip_labels):
                final, basis = AT_ENDPOINT, evidence
            elif scenario in BY_RANGES:
                # Tiempos en la zona ambigua: decide el producto identificado por rangos
                final, basis = BY_RANGES[scenario], "rangos de IP (tiempos ambiguos)"
            else:
                final, basis = AMBIGUOUS, evidence
        else:
            final = BY_RANGES.get(scenario, UNDETERMINED)
            basis = "rangos de IP"
        rows.append([ip, provider, product, scenario, final, basis])

    with open(outfile, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ip", "provider", "product", "scenario_by_ranges", "final_estimate", "basis"])
        w.writerows(rows)
    return outfile


def scenarios_stats(infile=ANYCAST_SCENARIOS_FILEPATH):
    """IPs distintas por estimación final y cotas del escenario (b)."""
    with open(infile) as f:
        counts = Counter(row["final_estimate"] for row in csv.DictReader(f))
    total = sum(counts.values())
    print(f"\nEstimación final por IP ({total} IPs distintas):")
    for k, v in counts.most_common():
        print(f"  {k:<40} {v:>6} ({v / total:.1%})")
    b = counts[BEYOND] + counts[BY_RANGES["b"]]
    unresolved = counts[AMBIGUOUS] + counts[UNDETERMINED]
    print(f"\nEscenario (b): {b / total:.1%} identificado; "
          f"hasta {(b + unresolved) / total:.1%} si todos los ambiguos e indeterminados lo fueran")
