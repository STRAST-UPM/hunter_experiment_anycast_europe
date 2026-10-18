"""
Comprueba hoy, para cada par (IP anycast, host) cuyo escenario no se pudo
determinar por rangos de IP, qué tipo de elemento responde en esa IP.

Para cada par se hace una petición HTTPS al host forzando la conexión a la IP
histórica (curl --resolve), de modo que el SNI y la cabecera Host son los del
servicio original y la conexión va a la misma dirección anycast que en las
medidas. Se registran:

  * Las cabeceras de respuesta que delatan un proxy de capa 7 (Via, Server,
    CF-Ray, X-Amz-Cf-Pop, X-Served-By, X-Azure-Ref, ...). Si aparecen, el
    elemento que termina la conexión procesa HTTP y, por tanto, descifra TLS:
    escenario (a).
  * Los tiempos de establecimiento de TCP y de TLS (curl -w). Una diferencia
    grande entre ambos indica que TLS termina más allá del elemento que termina
    TCP, como en el escenario (b). Es solo un indicio: se guarda el valor y la
    decisión queda para el análisis.
  * Si el host sigue resolviendo hoy a la misma IP que en las medidas. Si es así,
    la dirección sigue asignada al mismo servicio y la comprobación es mucho más
    representativa de la situación original.

Entrada: ANYCAST_PROVIDER_CLASSIFICATION_FILEPATH (salida de
         classify_providers, con la columna dns).
Salida:  ANYCAST_EDGE_HEADERS_CHECK_FILEPATH con una fila por par (ip, dns).

Por defecto solo se comprueban los escenarios "?" y "b"; con check_all=True,
todos los pares. Punto de entrada: main_providers_classification.py.

Requiere curl en el sistema.
"""
import csv, socket, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

from src.utils.constants import (
    ANYCAST_PROVIDER_CLASSIFICATION_FILEPATH,
    ANYCAST_EDGE_HEADERS_CHECK_FILEPATH,
)

TIMEOUT_S = 10
WORKERS = 16

# (cabecera, fragmento del valor en minúsculas o None si basta con que exista, producto)
EDGE_SIGNATURES = [
    ("cf-ray", None, "Cloudflare (proxy L7)"),
    ("x-amz-cf-pop", None, "AWS CloudFront (L7)"),
    ("x-amz-cf-id", None, "AWS CloudFront (L7)"),
    ("via", "cloudfront", "AWS CloudFront (L7)"),
    ("via", "google", "Google Front End / balanceador de aplicación (L7)"),
    ("server", "google frontend", "Google Front End (L7)"),
    ("server", "gws", "Google Front End (L7)"),
    ("server", "esf", "Google Front End (L7)"),
    ("x-served-by", "cache-", "Fastly (L7)"),
    ("via", "varnish", "Fastly u otro Varnish (L7)"),
    ("x-azure-ref", None, "Azure Front Door (L7)"),
    ("x-msedge-ref", None, "Azure Front Door / CDN (L7)"),
    ("server", "akamaighost", "Akamai (L7)"),
    ("x-akamai-transformed", None, "Akamai (L7)"),
    ("server", "ecacc", "Edgio / Edgecast (L7)"),
    ("server", "ecs", "Edgio / Edgecast (L7)"),
]
HEADERS_TO_KEEP = ["server", "via", "cf-ray", "x-amz-cf-pop", "x-served-by",
                   "x-azure-ref", "x-msedge-ref", "x-cache", "alt-svc"]

CURL_FORMAT = "\\n__TIMING__ %{http_code} %{time_connect} %{time_appconnect} %{time_starttransfer}\\n"


def resolves_to(host, ip):
    try:
        addrs = {a[4][0] for a in socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)}
    except socket.gaierror:
        return "no resuelve", ""
    return ("sí" if ip in addrs else "no"), " ".join(sorted(addrs))


def parse_headers(text):
    headers = {}
    for line in text.splitlines():
        if ":" in line and not line.startswith("HTTP/"):
            k, v = line.split(":", 1)
            headers.setdefault(k.strip().lower(), v.strip())
    return headers


def edge_product(headers):
    found = []
    for name, fragment, product in EDGE_SIGNATURES:
        value = headers.get(name)
        if value is not None and (fragment is None or fragment in value.lower()) and product not in found:
            found.append(product)
    return "; ".join(found)


def probe(ip, host):
    """Petición HTTPS al host. Con ip, fuerza la conexión a esa dirección
    (curl --resolve); con ip=None, usa la resolución DNS actual."""
    resolve = ["--resolve", f"{host}:443:{ip}"] if ip else []
    cmd = ["curl", "-s", "-o", "/dev/null", "-D", "-", "-I",
           "--max-time", str(TIMEOUT_S), *resolve,
           "-w", CURL_FORMAT, f"https://{host}/"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT_S + 5).stdout
    except subprocess.TimeoutExpired:
        out = ""
    head, _, timing = out.partition("__TIMING__")
    parts = timing.split()
    if len(parts) == 4 and parts[0] != "000":
        code, t_tcp, t_tls, t_fb = parts[0], *(float(x) * 1000 for x in parts[1:])
        timings = (code, f"{t_tcp:.1f}", f"{t_tls:.1f}", f"{t_tls - t_tcp:.1f}", f"{t_fb:.1f}")
    else:
        timings = ("sin respuesta", "", "", "", "")
    headers = parse_headers(head)
    return timings, headers


def check(pair):
    ip, host, scenario, provider = pair
    same_ip, current = resolves_to(host, ip)
    (code, t_tcp, t_tls, tls_minus_tcp, t_fb), headers = probe(ip, host)
    target = "IP histórica"
    if code == "sin respuesta" and same_ip == "no":
        # La IP histórica ya no atiende al host: se prueba con su resolución
        # actual. Es una evidencia más débil (puede ser otro despliegue).
        (code, t_tcp, t_tls, tls_minus_tcp, t_fb), headers = probe(None, host)
        target = "IP actual"
    product = edge_product(headers)
    inferred = "a" if product else ("?" if code != "sin respuesta" else "-")
    return [ip, host, provider, scenario, same_ip, current, target, code, product, inferred,
            t_tcp, t_tls, tls_minus_tcp, t_fb, *[headers.get(h, "") for h in HEADERS_TO_KEEP]]


def check_edge_headers(check_all=False, infile=ANYCAST_PROVIDER_CLASSIFICATION_FILEPATH,
                       outfile=ANYCAST_EDGE_HEADERS_CHECK_FILEPATH):
    pairs = {}
    with open(infile) as f:
        for row in csv.DictReader(f):
            if check_all or row["scenario"] in ("?", "b"):
                for host in row["dns"].split("|"):
                    host = host.strip().rstrip(".")
                    if host:
                        pairs[(row["ip"], host)] = (row["ip"], host, row["scenario"], row["provider"])
    print(f"Pares (IP, host) a comprobar: {len(pairs)}", file=sys.stderr)
    with ThreadPoolExecutor(WORKERS) as pool:
        rows = list(pool.map(check, pairs.values()))
    with open(outfile, "w", newline="") as out:
        w = csv.writer(out)
        w.writerow(["ip", "dns", "provider", "scenario_by_ranges", "resolves_today_to_same_ip",
                    "current_ips", "probe_target", "http_code", "edge_product", "scenario_by_headers",
                    "tcp_ms", "tls_ms", "tls_minus_tcp_ms", "first_byte_ms",
                    *[f"h_{h}" for h in HEADERS_TO_KEEP]])
        w.writerows(rows)
    print(f"Resultados en {outfile}", file=sys.stderr)
