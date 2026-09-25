# external imports

# internal imports
from src.graphics.visualization import (
    visualize_probes_selection_grid,
    visualize_ip_destination_countries_histogram,
    get_ip_destination_countries_df
)
from src.utils.common_functions import dict_to_json_file


def generate_ip_destination_countries_report(
        output_filepath: str = "ip_destination_countries.json"):
    """Save, per IP, its destination countries count and country codes."""
    ip_destination_countries_df = get_ip_destination_countries_df()

    report = {
        row["target"]: {
            "destination_countries_count": row["destination_countries_count"],
            "destination_countries": row["destination_countries"]
        }
        for _, row in ip_destination_countries_df.iterrows()
    }

    dict_to_json_file(report, output_filepath, sort_keys=True)


########################################################################################################################

if __name__ == "__main__":
    visualize_probes_selection_grid(
        output_filepath="tpls_experiment_mesh_grid.svg",
        use_tile_basemap=False
    )

    visualize_ip_destination_countries_histogram(
        output_filepath="ip_destination_countries_histogram.svg"
    )

    generate_ip_destination_countries_report(
        output_filepath="ip_destination_countries.json"
    )
