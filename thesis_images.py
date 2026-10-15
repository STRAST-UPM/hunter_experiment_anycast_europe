# external imports

# internal imports
from src.graphics.visualization import (
    visualize_probes_selection_grid,
    visualize_ip_destination_countries_histogram,
)
from src.utils.common_functions import dict_to_json_file
from src.utils.constants import (
    RESULTS_MODES,
    REPLICATION_PACKAGE_DIR
)

ANALYSIS_MODE = RESULTS_MODES[1]
ANALYSIS_FOLDER = f"{REPLICATION_PACKAGE_DIR}/analysis_{ANALYSIS_MODE}"
IP_DESTINATIONS_COUNT_FILEPATH = f"{ANALYSIS_FOLDER}/ip_destinations_count_{ANALYSIS_MODE}.csv"

########################################################################################################################

if __name__ == "__main__":
    visualize_probes_selection_grid(
        output_filepath="tpls_experiment_mesh_grid.svg",
        use_tile_basemap=False
    )

    visualize_ip_destination_countries_histogram(
        output_filepath="ip_destination_countries_histogram.svg",
        ip_destinations_dataframe_path=IP_DESTINATIONS_COUNT_FILEPATH
    )
