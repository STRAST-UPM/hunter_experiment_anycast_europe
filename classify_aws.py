"""
Clasifica direcciones IP según el servicio de AWS que las usaba en una fecha
concreta, a partir del historial del fichero ip-ranges.json de AWS
(repositorio https://github.com/joetek/aws-ip-ranges-json).

Entrada: TRAFFIC_LOGS_IP_CLASSIFIED_FILEPATH, del que se extrae un CSV ip,date
         con solo las IPs anycast que se guarda en
         TRAFFIC_LOGS_DESTINATIONS_FILEPATH (se reutiliza si ya existe).
Salida:  OUTPUT_FILEPATH, CSV con columnas ip,date,snapshot_date,aws_services,layer

El repositorio con el historial de AWS se clona en AWS_IP_HISTORY_DIR si no existe.

Uso:
    python3 classify_aws.py
"""
import csv, ipaddress, json, os, subprocess, sys
from functools import lru_cache

from src.utils.constants import (
    REPLICATION_PACKAGE_DIR, 
    TRAFFIC_LOGS_IP_CLASSIFIED_FILEPATH,
    TRAFFIC_LOGS_DESTINATIONS_FILEPATH)

AWS_IP_HISTORY_REPO = "https://github.com/joetek/aws-ip-ranges-json"
AWS_IP_HISTORY_DIR = f"{REPLICATION_PACKAGE_DIR}/aws-ip-history"
OUTPUT_FILEPATH = f"{REPLICATION_PACKAGE_DIR}/Traffic_logs_10K_aws_classification.csv"

# Servicios relevantes y capa en la que terminan la conexión del cliente
SERVICE_LAYER = {
    "GLOBALACCELERATOR": "L4 (escenario b)",   # proxy TCP/UDP, TLS en el endpoint regional
    "CLOUDFRONT": "L7 (escenario a)",          # CDN, termina TLS en el PoP
}
FILES = {
    "GLOBALACCELERATOR": "ip-ranges-globalaccelerator.json",
    "CLOUDFRONT": "ip-ranges-cloudfront.json",
    "AMAZON": "ip-ranges-amazon.json",
}

def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, check=True).stdout

@lru_cache(maxsize=None)
def snapshot(repo, date):
    """Último commit del historial anterior o igual a la fecha indicada."""
    commit = git(repo, "rev-list", "-1", f"--before={date} 23:59:59", "HEAD").strip()
    commit_date = git(repo, "show", "-s", "--format=%ad", "--date=short", commit).strip()
    nets = {}
    for service, fname in FILES.items():
        try:
            data = json.loads(git(repo, "show", f"{commit}:{fname}"))
        except subprocess.CalledProcessError:
            nets[service] = []          # el fichero aún no existía en esa fecha
            continue
        nets[service] = [ipaddress.ip_network(p["ip_prefix"]) for p in data.get("prefixes", [])] + \
                        [ipaddress.ip_network(p["ipv6_prefix"]) for p in data.get("ipv6_prefixes", [])]
    return commit_date, nets

def classify(repo, ip, date):
    commit_date, nets = snapshot(repo, date)
    addr = ipaddress.ip_address(ip)
    services = [s for s, ns in nets.items() if any(addr in n for n in ns if n.version == addr.version)]
    specific = [s for s in services if s != "AMAZON"]
    if specific:
        layer = "; ".join(SERVICE_LAYER.get(s, "?") for s in specific)
    elif services:
        layer = "AWS sin servicio identificado"
    else:
        layer = "No es AWS"
    return commit_date, "|".join(services) or "-", layer

def destinations_csv(traffic_logs=TRAFFIC_LOGS_IP_CLASSIFIED_FILEPATH, outfile=TRAFFIC_LOGS_DESTINATIONS_FILEPATH):
    """Genera un CSV ip,date (sin duplicados) con la IP de destino y la fecha de
    cada conexión a una IP marcada como anycast. Si ya existe, se reutiliza."""
    if os.path.exists(outfile):
        return outfile
    csv.field_size_limit(sys.maxsize)   # la columna stackTrace es muy larga
    pairs = set()
    with open(traffic_logs, newline="") as f:
        for row in csv.DictReader(f):
            ip = row["ip_dest"].strip()
            if ip and row["ip_anycast"] == "True":
                pairs.add((ip, row["asctime"][:10]))
    with open(outfile, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ip", "date"])
        w.writerows(sorted(pairs, key=lambda p: (p[1], p[0])))
    return outfile

def aws_ip_history(repo=AWS_IP_HISTORY_DIR):
    """Clona el historial de ip-ranges.json de AWS si aún no está descargado."""
    if not os.path.isdir(repo):
        subprocess.run(["git", "clone", AWS_IP_HISTORY_REPO, repo], check=True)
    return repo

def main(infile, repo, outfile=OUTPUT_FILEPATH):
    with open(infile) as f, open(outfile, "w", newline="") as out:
        w = csv.writer(out)
        w.writerow(["ip", "date", "snapshot_date", "aws_services", "layer"])
        for row in csv.DictReader(f):
            w.writerow([row["ip"], row["date"], *classify(repo, row["ip"].strip(), row["date"].strip())])

def layer_stats(infile=OUTPUT_FILEPATH):
    """Muestra por pantalla cuántas IPs distintas hay para cada valor de layer.
    Una IP con distinta clasificación según la fecha cuenta en cada layer."""
    ips = {}
    with open(infile) as f:
        for row in csv.DictReader(f):
            ips.setdefault(row["layer"], set()).add(row["ip"])
    total = len(set().union(*ips.values()))
    print(f"IPs distintas: {total}")
    for layer, layer_ips in sorted(ips.items(), key=lambda x: -len(x[1])):
        print(f"  {layer:<32} {len(layer_ips):>6} ({len(layer_ips) / total:.1%})")

if __name__ == "__main__":
    main(destinations_csv(), aws_ip_history())
    layer_stats()
