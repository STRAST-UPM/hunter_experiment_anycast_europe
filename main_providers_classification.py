"""
Punto de entrada del estudio de proveedores de las IPs anycast de destino.

Pasos:
  1. Extrae las IPs anycast con su fecha y nombre DNS de los logs de tráfico
     (se reutiliza el CSV si ya existe).
  2. Clasifica cada IP por proveedor, producto y escenario (a, b o c) usando el
     historial de rangos publicados y muestra las estadísticas.
  3. Opcional (--check-edges): comprueba hoy las cabeceras y tiempos del
     elemento que responde en cada IP.
  4. Opcional (--summarize, implícito con --check-edges): combina rangos,
     cabeceras y tiempos en una estimación final del escenario por IP.

Los CSVs generados se guardan en PROVIDERS_CLASSIFICATION_DIR y las fuentes de
datos (historial de rangos, tabla de AS) en PROVIDERS_SOURCES_DIR.

Uso:
    python3 main_providers_classification.py
    python3 main_providers_classification.py --check-edges          # escenarios "?" y "b"
    python3 main_providers_classification.py --check-edges --all    # todos los pares
    python3 main_providers_classification.py --summarize            # solo resumen, con la comprobación ya hecha
"""
# external imports
import argparse
# internal imports
from src.providers.classify_providers import (
    destinations_csv,
    classify_destinations,
    stats,
)
from src.providers.check_edge_headers import check_edge_headers
from src.providers.summarize_scenarios import summarize_scenarios, scenarios_stats

########################################################################################################################

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clasificación de proveedores de las IPs anycast")
    parser.add_argument("--check-edges", action="store_true",
                        help="comprobar las cabeceras del elemento que responde en cada IP")
    parser.add_argument("--all", action="store_true",
                        help="con --check-edges, comprobar todos los pares y no solo los escenarios ? y b")
    parser.add_argument("--summarize", action="store_true",
                        help="estimar el escenario final por IP con la comprobación de cabeceras ya existente")
    args = parser.parse_args()

    classify_destinations(destinations_csv())
    stats()

    if args.check_edges:
        check_edge_headers(check_all=args.all)

    if args.check_edges or args.summarize:
        summarize_scenarios()
        scenarios_stats()
