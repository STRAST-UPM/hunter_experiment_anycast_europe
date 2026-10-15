"""
Clasifica las IPs anycast de destino según el proveedor y, cuando es posible,
el producto que las servía en la fecha de cada conexión, para estimar en qué
escenario (a, b o c) estaba cada comunicación.

Fuentes históricas (repositorios de Git que guardan copias periódicas de los
rangos publicados por cada proveedor; se clonan automáticamente en
IP_RANGES_HISTORY_DIR):

  * AWS         joetek/aws-ip-ranges-json      ip-ranges.json por servicio
                (CLOUDFRONT = L7, GLOBALACCELERATOR = L4)
  * Google      jay0lee/google-ip-range-tracker  goog.json y cloud.json
                (goog - cloud = servicios de Google, servidos por GFE = L7;
                 cloud con ámbito global = balanceadores globales de clientes
                 de Google Cloud, que pueden ser L7 o L4)
  * Cloudflare  lord-alfred/ipranges           rangos publicados por Cloudflare
  * Microsoft   lord-alfred/ipranges           Azure Service Tags agregados

Fuente opcional para el resto de proveedores (operador por número de AS):

  * pyasn con una tabla de RouteViews de la fecha de las medidas. Se activa si
    existe el fichero ASN_DB_FILEPATH. Para generarlo:
        pip install pyasn
        echo 20231214 > fechas.txt
        pyasn_util_download.py --dates-from-file fechas.txt
        pyasn_util_convert.py --single rib.20231214.*.bz2 ipasn_20231214.dat
    y copiar ipasn_20231214.dat a ASN_DB_FILEPATH.

Entrada: ANYCAST_DESTINATIONS_FILEPATH (CSV ip,date,dns con las IPs anycast y
         el nombre DNS de la petición; se genera a partir de
         TRAFFIC_LOGS_IP_CLASSIFIED_FILEPATH si no existe).
Salida:  ANYCAST_PROVIDER_CLASSIFICATION_FILEPATH con columnas
         ip,date,dns,provider,product,layer,scenario,source,snapshot_date

Todas las rutas están en src/utils/constants.py. Punto de entrada:
main_providers_classification.py en la raíz del repositorio.
"""
import csv, ipaddress, json, os, subprocess, sys
from functools import lru_cache

from src.utils.constants import (
    TRAFFIC_LOGS_IP_CLASSIFIED_FILEPATH,
    ANYCAST_DESTINATIONS_FILEPATH,
    ANYCAST_PROVIDER_CLASSIFICATION_FILEPATH,
    ASN_DB_FILEPATH,
    IP_RANGES_HISTORY_DIR,
)

HISTORY_REPOS = {
    "aws": ("https://github.com/joetek/aws-ip-ranges-json", f"{IP_RANGES_HISTORY_DIR}/aws-ip-history"),
    "google": ("https://github.com/jay0lee/google-ip-range-tracker", f"{IP_RANGES_HISTORY_DIR}/google-ip-history"),
    "lordalfred": ("https://github.com/lord-alfred/ipranges", f"{IP_RANGES_HISTORY_DIR}/multi-ip-history"),
}

# Operadores conocidos por número de AS (solo para la fuente opcional pyasn)
KNOWN_ASNS = {
    13335: "Cloudflare", 15169: "Google", 396982: "Google Cloud",
    16509: "Amazon", 14618: "Amazon", 8075: "Microsoft",
    54113: "Fastly", 20940: "Akamai", 16625: "Akamai",
    15133: "Edgio (Edgecast)", 22822: "Edgio (Limelight)",
    32934: "Meta", 36459: "GitHub",
}
# Proveedores cuyo servicio habitual es una CDN de capa 7 (escenario a probable)
L7_CDN_PROVIDERS = {"Fastly", "Akamai", "Edgio (Edgecast)", "Edgio (Limelight)"}

L7, L4, UNK = "L7", "L4", "?"
SCENARIO = {L7: "a", L4: "b", UNK: "?"}


# ---------------------------------------------------------------------------
# Utilidades de Git
# ---------------------------------------------------------------------------

def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, check=True).stdout

def ensure_repo(key):
    url, path = HISTORY_REPOS[key]
    if not os.path.isdir(path):
        subprocess.run(["git", "clone", "--filter=blob:none", url, path], check=True)
    return path

@lru_cache(maxsize=None)
def commit_at(repo, date):
    """Último commit anterior o igual a la fecha. Si la fecha es anterior al
    primer commit, devuelve el primero (y su fecha lo deja visible en la salida)."""
    commit = git(repo, "rev-list", "-1", f"--before={date} 23:59:59", "HEAD").strip()
    if not commit:
        commit = git(repo, "rev-list", "--max-parents=0", "HEAD").strip().splitlines()[0]
    return commit, git(repo, "show", "-s", "--format=%ad", "--date=short", commit).strip()

def show(repo, commit, *candidates):
    """Contenido del primer fichero existente entre los candidatos (los nombres
    de los ficheros cambian a lo largo del historial)."""
    for path in candidates:
        try:
            return git(repo, "show", f"{commit}:{path}")
        except subprocess.CalledProcessError:
            continue
    return None

def nets_from_lines(text):
    return [ipaddress.ip_network(l.strip(), strict=False) for l in (text or "").splitlines() if l.strip()]

def contains(nets, addr):
    return any(addr in n for n in nets if n.version == addr.version)


# ---------------------------------------------------------------------------
# Proveedores
# ---------------------------------------------------------------------------

@lru_cache(maxsize=None)
def aws_snapshot(date):
    repo = ensure_repo("aws")
    commit, cdate = commit_at(repo, date)
    nets = {}
    for service, fname in {"GLOBALACCELERATOR": "ip-ranges-globalaccelerator.json",
                           "CLOUDFRONT": "ip-ranges-cloudfront.json",
                           "AMAZON": "ip-ranges-amazon.json"}.items():
        data = json.loads(show(repo, commit, fname) or "{}")
        nets[service] = [ipaddress.ip_network(p["ip_prefix"]) for p in data.get("prefixes", [])] + \
                        [ipaddress.ip_network(p["ipv6_prefix"]) for p in data.get("ipv6_prefixes", [])]
    return cdate, nets

def classify_aws(addr, date):
    cdate, nets = aws_snapshot(date)
    if contains(nets["GLOBALACCELERATOR"], addr):
        return "AWS", "Global Accelerator", L4, "aws-ip-ranges", cdate
    if contains(nets["CLOUDFRONT"], addr):
        return "AWS", "CloudFront", L7, "aws-ip-ranges", cdate
    if contains(nets["AMAZON"], addr):
        return "AWS", "otro servicio", UNK, "aws-ip-ranges", cdate
    return None

def google_prefixes(text, keep_global_only=False):
    out = []
    for p in json.loads(text or '{"prefixes": []}').get("prefixes", []):
        if keep_global_only and p.get("scope", "").lower() != "global":
            continue
        prefix = p.get("ipv4Prefix") or p.get("ipv6Prefix")
        if prefix:
            out.append(ipaddress.ip_network(prefix))
    return out

@lru_cache(maxsize=None)
def google_snapshot(date):
    repo = ensure_repo("google")
    commit, cdate = commit_at(repo, date)
    goog = show(repo, commit, "ips/goog.json", "ips/google-owned-ips.json")
    cloud = show(repo, commit, "ips/cloud.json", "ips/google-cloud-customer-ips.json")
    return cdate, google_prefixes(goog), google_prefixes(cloud), google_prefixes(cloud, keep_global_only=True)

def classify_google(addr, date):
    cdate, goog, cloud, cloud_global = google_snapshot(date)
    if contains(cloud_global, addr):
        # Balanceadores globales de clientes: de aplicación (L7) o de red (L4)
        return "Google Cloud", "balanceador global de cliente", UNK, "google-ip-ranges", cdate
    if contains(cloud, addr):
        return "Google Cloud", "rango regional de cliente", UNK, "google-ip-ranges", cdate
    if contains(goog, addr):
        return "Google", "servicios de Google (GFE)", L7, "google-ip-ranges", cdate
    return None

@lru_cache(maxsize=None)
def lordalfred_snapshot(provider, date):
    repo = ensure_repo("lordalfred")
    commit, cdate = commit_at(repo, date)
    text = (show(repo, commit, f"{provider}/ipv4.txt") or "") + "\n" + (show(repo, commit, f"{provider}/ipv6.txt") or "")
    nets = nets_from_lines(text)
    if not nets:
        # El proveedor aún no estaba en el historial en esa fecha: se usa la
        # primera versión disponible (la fecha de la instantánea lo indica)
        first = git(repo, "log", "--reverse", "--format=%H", "--", f"{provider}/ipv4.txt").split()[0]
        cdate = git(repo, "show", "-s", "--format=%ad", "--date=short", first).strip()
        text = (show(repo, first, f"{provider}/ipv4.txt") or "") + "\n" + (show(repo, first, f"{provider}/ipv6.txt") or "")
        nets = nets_from_lines(text)
    return cdate, nets

def classify_cloudflare(addr, date):
    cdate, nets = lordalfred_snapshot("cloudflare", date)
    if contains(nets, addr):
        # Mismos rangos para el proxy estándar (L7) y para Spectrum o Regional
        # Services; el proxy estándar es el caso habitual
        return "Cloudflare", "proxy estándar (probable)", L7, "cloudflare-ip-ranges", cdate
    return None

def classify_microsoft(addr, date):
    cdate, nets = lordalfred_snapshot("microsoft", date)
    if contains(nets, addr):
        return "Microsoft", "producto no identificado", UNK, "azure-service-tags", cdate
    return None

@lru_cache(maxsize=None)
def asn_db():
    if not os.path.exists(ASN_DB_FILEPATH):
        return None
    import pyasn
    return pyasn.pyasn(ASN_DB_FILEPATH)

def classify_asn(addr, date):
    db = asn_db()
    if db is None:
        return None
    asn, prefix = db.lookup(str(addr))
    if asn is None:
        return None
    provider = KNOWN_ASNS.get(asn, f"AS{asn}")
    layer = L7 if provider in L7_CDN_PROVIDERS else UNK
    return provider, f"prefijo {prefix}", layer, "routeviews-asn", os.path.basename(ASN_DB_FILEPATH)

CLASSIFIERS = [classify_aws, classify_google, classify_cloudflare, classify_microsoft, classify_asn]


# ---------------------------------------------------------------------------
# Clasificación y resumen
# ---------------------------------------------------------------------------

def classify(ip, date):
    addr = ipaddress.ip_address(ip)
    for classifier in CLASSIFIERS:
        result = classifier(addr, date)
        if result:
            provider, product, layer, source, snapshot_date = result
            return provider, product, layer, SCENARIO[layer], source, snapshot_date
    return "desconocido", "-", UNK, SCENARIO[UNK], "-", "-"

def destinations_csv(traffic_logs=TRAFFIC_LOGS_IP_CLASSIFIED_FILEPATH, outfile=ANYCAST_DESTINATIONS_FILEPATH):
    """Genera un CSV ip,date,dns (sin duplicados) con la IP de destino, la fecha
    y el nombre DNS (columna host) de cada petición a una IP marcada como
    anycast. Una IP puede aparecer varias veces el mismo día con distintos
    nombres. Si el fichero ya existe, se reutiliza."""
    if os.path.exists(outfile):
        return outfile
    csv.field_size_limit(sys.maxsize)   # la columna stackTrace es muy larga
    os.makedirs(os.path.dirname(outfile), exist_ok=True)
    rows = set()
    with open(traffic_logs, newline="") as f:
        for row in csv.DictReader(f):
            ip = row["ip_dest"].strip()
            if ip and row["ip_anycast"] == "True":
                rows.add((ip, row["asctime"][:10], row["host"].strip()))
    with open(outfile, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ip", "date", "dns"])
        w.writerows(sorted(rows, key=lambda r: (r[1], r[0], r[2])))
    return outfile

def classify_destinations(infile=ANYCAST_DESTINATIONS_FILEPATH, outfile=ANYCAST_PROVIDER_CLASSIFICATION_FILEPATH):
    os.makedirs(os.path.dirname(outfile), exist_ok=True)
    with open(infile) as f, open(outfile, "w", newline="") as out:
        w = csv.writer(out)
        w.writerow(["ip", "date", "dns", "provider", "product", "layer", "scenario", "source", "snapshot_date"])
        for row in csv.DictReader(f):
            ip, date = row["ip"].strip(), row["date"].strip()
            w.writerow([ip, date, row["dns"].strip(), *classify(ip, date)])

def stats(infile=ANYCAST_PROVIDER_CLASSIFICATION_FILEPATH):
    """IPs distintas por escenario y por proveedor/producto."""
    by_scenario, by_product = {}, {}
    with open(infile) as f:
        for row in csv.DictReader(f):
            by_scenario.setdefault(row["scenario"], set()).add(row["ip"])
            by_product.setdefault(f'{row["provider"]} / {row["product"]}', set()).add(row["ip"])
    total = len(set().union(*by_scenario.values()))
    print(f"IPs distintas: {total}\n\nPor escenario:")
    for k, v in sorted(by_scenario.items(), key=lambda x: -len(x[1])):
        print(f"  {k:<4} {len(v):>6} ({len(v) / total:.1%})")
    print("\nPor proveedor / producto:")
    for k, v in sorted(by_product.items(), key=lambda x: -len(x[1])):
        print(f"  {k:<55} {len(v):>6} ({len(v) / total:.1%})")
