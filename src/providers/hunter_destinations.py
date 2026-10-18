"""
Exporta a la carpeta de la clasificación de proveedores los países de destino
que infirió Hunter para cada IP anycast, para poder cruzarlos con la estimación
del escenario (a, b o c) de cada IP.

Fuente: ROUTES_FREQUENCY_NON_SUSPICIOUS_FILEPATH (salida del cuaderno de
análisis, con columnas target, origin_country, result_country, count y
outside_EEE). Se usan los mismos criterios que el cuaderno: los resultados
"Indeterminate" no cuentan como país de destino.

Salidas (restringidas a las IPs de la clasificación de proveedores si existe):

  * ANYCAST_HUNTER_PAIR_DESTINATIONS_FILEPATH: una fila por par (IP, país de
    origen) con columnas
        target, origin_country, result_countries_count, result_countries,
        outside_EEE, non_adequate, determinate_count, indeterminate_count
    result_countries_count es la agregación por par del cuaderno.

  * ANYCAST_HUNTER_IP_DESTINATIONS_FILEPATH: una fila por IP con columnas
        target, origin_countries_count, result_countries_count,
        result_countries, outside_EEE_countries, non_adequate_countries,
        determinate_count, indeterminate_count

Los países se separan con "|". outside_EEE indica si algún destino está fuera
del EEE y non_adequate si alguno está además fuera de los países con decisión
de adecuación.
"""
# external imports
import json
import os
import pandas as pd
# internal imports
from src.utils.constants import (
    EEE_COUNTRIES_FILEPATH,
    ROUTES_FREQUENCY_NON_SUSPICIOUS_FILEPATH,
    ANYCAST_PROVIDER_CLASSIFICATION_FILEPATH,
    ANYCAST_HUNTER_PAIR_DESTINATIONS_FILEPATH,
    ANYCAST_HUNTER_IP_DESTINATIONS_FILEPATH,
)

ADEQUATE_COUNTRIES_FILEPATH = os.path.join(
    os.path.dirname(EEE_COUNTRIES_FILEPATH), "adequate_international_transfer_countries.json")
INDETERMINATE = "Indeterminate"


def country_set(filepath):
    with open(filepath) as f:
        return {country["alpha-2"] for country in json.load(f)}


def join_countries(countries):
    return "|".join(sorted(set(countries)))


def summarize_group(group, eee, adequate):
    determinate = group.loc[group["result_country"] != INDETERMINATE]
    countries = determinate["result_country"].tolist()
    outside = [c for c in countries if c not in eee]
    non_adequate = [c for c in outside if c not in adequate]
    return {
        "result_countries_count": len(set(countries)),
        "result_countries": join_countries(countries),
        "outside_EEE_countries": join_countries(outside),
        "non_adequate_countries": join_countries(non_adequate),
        "determinate_count": int(determinate["count"].sum()),
        "indeterminate_count": int(group.loc[group["result_country"] == INDETERMINATE, "count"].sum()),
    }


def export_hunter_destinations(routes_frequency=ROUTES_FREQUENCY_NON_SUSPICIOUS_FILEPATH,
                               classification=ANYCAST_PROVIDER_CLASSIFICATION_FILEPATH,
                               pair_outfile=ANYCAST_HUNTER_PAIR_DESTINATIONS_FILEPATH,
                               ip_outfile=ANYCAST_HUNTER_IP_DESTINATIONS_FILEPATH):
    routes = pd.read_csv(routes_frequency, sep=",")
    if os.path.exists(classification):
        ips = set(pd.read_csv(classification, sep=",")["ip"])
        routes = routes.loc[routes["target"].isin(ips)]
    eee, adequate = country_set(EEE_COUNTRIES_FILEPATH), country_set(ADEQUATE_COUNTRIES_FILEPATH)

    # Por par (IP, país de origen)
    pair_rows = []
    for (target, origin), group in routes.groupby(["target", "origin_country"]):
        summary = summarize_group(group, eee, adequate)
        pair_rows.append({
            "target": target,
            "origin_country": origin,
            "result_countries_count": summary["result_countries_count"],
            "result_countries": summary["result_countries"],
            "outside_EEE": bool(summary["outside_EEE_countries"]),
            "non_adequate": bool(summary["non_adequate_countries"]),
            "determinate_count": summary["determinate_count"],
            "indeterminate_count": summary["indeterminate_count"],
        })
    pd.DataFrame(pair_rows).sort_values(
        by=["result_countries_count", "target"], ascending=[False, True]
    ).to_csv(pair_outfile, sep=",", index=False)

    # Por IP
    ip_rows = []
    for target, group in routes.groupby("target"):
        ip_rows.append({"target": target,
                        "origin_countries_count": group["origin_country"].nunique(),
                        **summarize_group(group, eee, adequate)})
    pd.DataFrame(ip_rows).sort_values(by="target").to_csv(ip_outfile, sep=",", index=False)
    return pair_outfile, ip_outfile


def hunter_destinations_stats(ip_file=ANYCAST_HUNTER_IP_DESTINATIONS_FILEPATH):
    df = pd.read_csv(ip_file, sep=",", keep_default_na=False)
    total = len(df)
    outside = (df["outside_EEE_countries"] != "").sum()
    non_adequate = (df["non_adequate_countries"] != "").sum()
    print(f"\nDestinos inferidos por Hunter ({total} IPs con resultados):")
    print(f"  con algún destino fuera del EEE:                {outside:>5} ({outside / total:.1%})")
    print(f"  con algún destino fuera del EEE sin adecuación: {non_adequate:>5} ({non_adequate / total:.1%})")
