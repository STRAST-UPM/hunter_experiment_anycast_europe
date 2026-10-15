# hunter_experiment_anycast_europe

Analysis of data getted from the execution of Hunter using RIPEAtlas probes as origin distributed along all Europe

## Anycast Providers Classification

```bash
echo 20231214 > fechas.txt
pyasn_util_download.py --dates-from-file fechas.txt
pyasn_util_convert.py --single rib.20231214.*.bz2 ipasn_20231214.dat
mkdir -p replication_package_europe_anycast_experiment/providers_classification/sources
mv ipasn_20231214.dat replication_package_europe_anycast_experiment/providers_classification/sources/ipasn.dat
rm fechas.txt rib.20231214.*.bz2
```

Clasificación y estadísticas

```bash
python3 main_providers_classification.py
```

Clasificación y estadísticas + comprobación de cabeceras (escenarios ? y b)

```bash
python3 main_providers_classification.py --check-edges
```

Clasificación y estadísticas + comprobación de cabeceras (todos los pares)

```bash
python3 main_providers_classification.py --check-edges --all
```

Los CSVs generados se guardan en `replication_package_europe_anycast_experiment/providers_classification/`
y las fuentes de datos (historial de rangos de IP y tabla de AS) en su subcarpeta `sources/`.
