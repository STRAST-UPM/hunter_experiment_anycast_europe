"""
Cruza la estimación del escenario por IP (summarize_scenarios) con los países
de destino que infirió Hunter (hunter_destinations) y con el número de
comunicaciones con datos personales de cada IP.

Responde a dos preguntas:
  1. Qué peso tiene cada escenario, en IPs y en comunicaciones con datos
     personales (la unidad de análisis del capítulo 4).
  2. En las IPs en escenario (b), donde Hunter localiza un elemento que no
     termina TLS, qué destinos infirió Hunter. Si infirió destinos dentro del
     EEE pero la diferencia TLS-TCP indica un extremo TLS lejano, el error de
     Hunter va en contra de las conclusiones sobre destinos fuera del EEE
     (resultado conservador).

Entradas:
  ANYCAST_SCENARIOS_FILEPATH, ANYCAST_HUNTER_IP_DESTINATIONS_FILEPATH,
  ANYCAST_EDGE_HEADERS_CHECK_FILEPATH y ANYCAST_PII_TRAFFIC_LOGS_FILEPATH.

Salidas:
  * ANYCAST_SCENARIOS_HUNTER_CROSS_FILEPATH: una fila por IP con el escenario,
    la diferencia TLS-TCP máxima medida, las comunicaciones con datos
    personales y los destinos de Hunter.
  * ANYCAST_SCENARIOS_HUNTER_SUMMARY_FILEPATH: una fila por estimación final
    con IPs, comunicaciones y proporción de IPs con destinos fuera del EEE.
  * Un resumen por pantalla, incluido el detalle de las IPs en escenario (b).
"""
# external imports
import csv
import sys
from collections import Counter, defaultdict
# internal imports
from src.utils.constants import (
    ANYCAST_SCENARIOS_FILEPATH,
    ANYCAST_HUNTER_IP_DESTINATIONS_FILEPATH,
    ANYCAST_EDGE_HEADERS_CHECK_FILEPATH,
    ANYCAST_PII_TRAFFIC_LOGS_FILEPATH,
    ANYCAST_SCENARIOS_HUNTER_CROSS_FILEPATH,
    ANYCAST_SCENARIOS_HUNTER_SUMMARY_FILEPATH,
)

# Diferencia TLS-TCP a partir de la cual el extremo TLS está probablemente
# fuera de Europa desde un punto de observación europeo (el RTT entre países
# europeos suele estar por debajo de este valor). Es una cota orientativa.
FAR_TLS_ENDPOINT_MS = 100.0


def pii_communications(traffic_logs=ANYCAST_PII_TRAFFIC_LOGS_FILEPATH):
    """Comunicaciones con datos personales por IP anycast de destino (mismo
    filtro que classify_providers.destinations_csv)."""
    csv.field_size_limit(sys.maxsize)   # la columna stackTrace es muy larga
    counts = Counter()
    with open(traffic_logs, newline="") as f:
        for row in csv.DictReader(f):
            ip = row["ip_dest"].strip()
            if ip and row["ip_anycast"] == "True" and row["PII"].strip() not in ("", "No-PII"):
                counts[ip] += 1
    return counts


def max_tls_gap(edge_check=ANYCAST_EDGE_HEADERS_CHECK_FILEPATH):
    """Diferencia TLS-TCP máxima medida por IP (cadena vacía si no respondió)."""
    gaps = defaultdict(list)
    with open(edge_check) as f:
        for row in csv.DictReader(f):
            if row["tls_minus_tcp_ms"]:
                gaps[row["ip"]].append(float(row["tls_minus_tcp_ms"]))
    return {ip: max(values) for ip, values in gaps.items()}


def read_by_key(filepath, key):
    with open(filepath) as f:
        return {row[key]: row for row in csv.DictReader(f)}


def cross_scenarios_hunter(scenarios=ANYCAST_SCENARIOS_FILEPATH,
                           hunter=ANYCAST_HUNTER_IP_DESTINATIONS_FILEPATH,
                           edge_check=ANYCAST_EDGE_HEADERS_CHECK_FILEPATH,
                           traffic_logs=ANYCAST_PII_TRAFFIC_LOGS_FILEPATH,
                           outfile=ANYCAST_SCENARIOS_HUNTER_CROSS_FILEPATH,
                           summary_outfile=ANYCAST_SCENARIOS_HUNTER_SUMMARY_FILEPATH):
    scen = read_by_key(scenarios, "ip")
    hunt = read_by_key(hunter, "target")
    gaps = max_tls_gap(edge_check)
    comms = pii_communications(traffic_logs)

    rows = []
    for ip, s in scen.items():
        h = hunt.get(ip, {})
        gap = gaps.get(ip)
        rows.append({
            "ip": ip,
            "provider": s["provider"],
            "product": s["product"],
            "final_estimate": s["final_estimate"],
            "basis": s["basis"],
            "max_tls_minus_tcp_ms": f"{gap:.1f}" if gap is not None else "",
            "far_tls_endpoint": gap is not None and gap >= FAR_TLS_ENDPOINT_MS,
            "pii_communications": comms.get(ip, 0),
            "hunter_has_results": bool(h),
            "hunter_result_countries": h.get("result_countries", ""),
            "hunter_outside_EEE_countries": h.get("outside_EEE_countries", ""),
            "hunter_non_adequate_countries": h.get("non_adequate_countries", ""),
            "hunter_determinate_count": h.get("determinate_count", ""),
            "hunter_indeterminate_count": h.get("indeterminate_count", ""),
        })
    rows.sort(key=lambda r: (r["final_estimate"], -r["pii_communications"]))
    with open(outfile, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # Resumen por estimación final
    groups = defaultdict(list)
    for r in rows:
        groups[r["final_estimate"]].append(r)
    total_ips, total_comms = len(rows), sum(r["pii_communications"] for r in rows)
    summary = []
    for estimate, rs in sorted(groups.items(), key=lambda kv: -sum(r["pii_communications"] for r in kv[1])):
        with_hunter = [r for r in rs if r["hunter_has_results"]]
        outside = sum(1 for r in with_hunter if r["hunter_outside_EEE_countries"])
        non_adequate = sum(1 for r in with_hunter if r["hunter_non_adequate_countries"])
        c = sum(r["pii_communications"] for r in rs)
        summary.append({
            "final_estimate": estimate,
            "ips": len(rs),
            "ips_pct": f"{len(rs) / total_ips:.1%}",
            "pii_communications": c,
            "pii_communications_pct": f"{c / total_comms:.1%}" if total_comms else "",
            "ips_with_hunter_results": len(with_hunter),
            "ips_hunter_outside_EEE": outside,
            "ips_hunter_non_adequate": non_adequate,
        })
    with open(summary_outfile, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        w.writeheader()
        w.writerows(summary)
    return outfile, summary_outfile


def cross_stats(cross_file=ANYCAST_SCENARIOS_HUNTER_CROSS_FILEPATH,
                summary_file=ANYCAST_SCENARIOS_HUNTER_SUMMARY_FILEPATH):
    with open(summary_file) as f:
        summary = list(csv.DictReader(f))
    print("\nEscenarios ponderados por comunicaciones con datos personales:")
    print(f"  {'estimación final':<40} {'IPs':>12} {'comunicaciones':>18} {'fuera EEE (Hunter)':>20}")
    for s in summary:
        print(f"  {s['final_estimate']:<40} {s['ips']:>5} ({s['ips_pct']:>6}) "
              f"{s['pii_communications']:>8} ({s['pii_communications_pct']:>6}) "
              f"{s['ips_hunter_outside_EEE']:>8}/{s['ips_with_hunter_results']:<4}")

    with open(cross_file) as f:
        b_rows = [r for r in csv.DictReader(f) if r["final_estimate"].startswith("(b)")]
    print(f"\nIPs en escenario (b) ({len(b_rows)}): destinos de Hunter frente a la diferencia TLS-TCP")
    conservative = 0
    for r in sorted(b_rows, key=lambda r: -int(r["pii_communications"])):
        only_eee = r["hunter_has_results"] == "True" and not r["hunter_outside_EEE_countries"]
        far = r["far_tls_endpoint"] == "True"
        conservative += only_eee and far
        mark = "  <- Hunter solo EEE y extremo TLS lejano" if only_eee and far else ""
        print(f"  {r['ip']:<16} {r['product'][:22]:<22} comms={r['pii_communications']:>5} "
              f"TLS-TCP={r['max_tls_minus_tcp_ms'] or '-':>7} Hunter={r['hunter_result_countries'] or '-'}{mark}")
    print(f"\nIPs (b) con destinos de Hunter solo en el EEE y extremo TLS probablemente lejano "
          f"(TLS-TCP >= {FAR_TLS_ENDPOINT_MS:.0f} ms): {conservative} de {len(b_rows)}")
