# external imports

# internal imports
from src.graphics.visualization import visualize_probes_selection_grid


########################################################################################################################

if __name__ == "__main__":
    visualize_probes_selection_grid(
        output_filepath="tpls_experiment_mesh_grid.svg",
        use_tile_basemap=False
    )
