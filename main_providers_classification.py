"""
Punto de entrada del estudio de proveedores de las IPs anycast de destino que
reciben datos personales (PII).

Pasos:
  1. Extrae las IPs anycast con PII, su fecha y nombre DNS de los logs de
     tráfico (Anycast_PII_traffic_logs.csv; se reutiliza el CSV si ya existe).
  2. Clasifica cada IP por proveedor, producto y escenario (a, b o c) usando el
     historial de rangos publicados y muestra las estadísticas.
  3. Opcional (--check-edges): comprueba hoy las cabeceras y tiempos del
     elemento que responde en cada IP.
  4. Opcional (--summarize, implícito con --check-edges): combina rangos,
     cabeceras y tiempos en una estimación final del escenario por IP.
  5. Opcional (--hunter-destinations): exporta los países de destino que
     infirió Hunter para cada IP clasificada, por IP y por par (IP, origen).
  6. Opcional (--cross): cruza el escenario de cada IP con los destinos de
     Hunter y con sus comunicaciones con datos personales.

Los CSVs generados se guardan en PROVIDERS_CLASSIFICATION_DIR y las fuentes de
datos (historial de rangos, tabla de AS) en PROVIDERS_SOURCES_DIR.

Uso:
    python3 main_providers_classification.py
    python3 main_providers_classification.py --check-edges          # escenarios "?" y "b"
    python3 main_providers_classification.py --check-edges --all    # todos los pares
    python3 main_providers_classification.py --summarize            # solo resumen, con la comprobación ya hecha
    python3 main_providers_classification.py --hunter-destinations  # países inferidos por Hunter por IP
    python3 main_providers_classification.py --summarize --cross    # cruce escenarios / Hunter / comunicaciones
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
from src.providers.hunter_destinations import export_hunter_destinations, hunter_destinations_stats
from src.providers.cross_scenarios_hunter import cross_scenarios_hunter, cross_stats

########################################################################################################################

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clasificación de proveedores de las IPs anycast")
    parser.add_argument("--check-edges", action="store_true",
                        help="comprobar las cabeceras del elemento que responde en cada IP")
    parser.add_argument("--all", action="store_true",
                        help="con --check-edges, comprobar todos los pares y no solo los escenarios ? y b")
    parser.add_argument("--summarize", action="store_true",
                        help="estimar el escenario final por IP con la comprobación de cabeceras ya existente")
    parser.add_argument("--hunter-destinations", action="store_true",
                        help="exportar los países de destino inferidos por Hunter para cada IP clasificada")
    parser.add_argument("--cross", action="store_true",
                        help="cruzar escenarios, destinos de Hunter y comunicaciones con datos personales "
                             "(implica --hunter-destinations)")
    args = parser.parse_args()

    classify_destinations(destinations_csv())
    stats()

    if args.check_edges:
        check_edge_headers(check_all=args.all)

    if args.check_edges or args.summarize:
        summarize_scenarios()
        scenarios_stats()

    if args.hunter_destinations or args.cross:
        export_hunter_destinations()
        hunter_destinations_stats()

    if args.cross:
        cross_scenarios_hunter()
        cross_stats()
