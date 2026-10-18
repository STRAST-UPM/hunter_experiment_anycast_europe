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
resto de casos. Las IPs sin respuesta conservan la clasificación por rangos.

Entrada: ANYCAST_PROVIDER_CLASSIFICATION_FILEPATH y ANYCAST_EDGE_HEADERS_CHECK_FILEPATH.
Salida:  ANYCAST_SCENARIOS_FILEPATH con columnas
         ip,provider,product,scenario_by_ranges,final_estimate,basis
"""
# external imports
import csv
from collections import Counter, defaultdict
# internal imports
from src.utils.constants import (
    ANYCAST_PROVIDER_CLASSIFICATION_FILEPATH,
    ANYCAST_EDGE_HEADERS_CHECK_FILEPATH,
    ANYCAST_SCENARIOS_FILEPATH,
)

LOW_PERCENTILE, HIGH_PERCENTILE = 0.99, 0.10
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


def calibrate_thresholds(edge_check=ANYCAST_EDGE_HEADERS_CHECK_FILEPATH,
                         classification=ANYCAST_PROVIDER_CLASSIFICATION_FILEPATH):
    """Umbrales de TLS-TCP a partir de los casos de escenario conocido. Solo se
    usan las IPs presentes en la clasificación, aunque la comprobación de
    cabeceras incluya más."""
    classified_ips, global_accelerator_ips = set(), set()
    with open(classification) as f:
        for row in csv.DictReader(f):
            classified_ips.add(row["ip"])
            if row["provider"] == "AWS" and row["product"] == "Global Accelerator":
                global_accelerator_ips.add(row["ip"])
    l7, l4 = [], []
    with open(edge_check) as f:
        for row in csv.DictReader(f):
            if row["ip"] not in classified_ips or not responded(row):
                continue
            delta = float(row["tls_minus_tcp_ms"])
            if row["edge_product"]:
                l7.append(delta)
            elif row["ip"] in global_accelerator_ips:
                l4.append(delta)
    low = percentile(l7, LOW_PERCENTILE) if l7 else DEFAULT_LOW_MS
    high = percentile(l4, HIGH_PERCENTILE) if l4 else DEFAULT_HIGH_MS
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
                        outfile=ANYCAST_SCENARIOS_FILEPATH):
    low_ms, high_ms = calibrate_thresholds(edge_check, classification)

    by_range = {}
    with open(classification) as f:
        for row in csv.DictReader(f):
            by_range.setdefault(row["ip"], (row["scenario"], row["provider"], row["product"]))

    labels = defaultdict(list)
    with open(edge_check) as f:
        for row in csv.DictReader(f):
            label = pair_label(row, low_ms, high_ms)
            if label:
                labels[row["ip"]].append(label)

    rows = []
    for ip, (scenario, provider, product) in by_range.items():
        ip_labels = labels.get(ip)
        if ip_labels:
            if "beyond" in ip_labels:
                final = BEYOND
            elif all(label == "endpoint" for label in ip_labels):
                final = AT_ENDPOINT
            else:
                final = AMBIGUOUS
            basis = "cabeceras y tiempos"
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
