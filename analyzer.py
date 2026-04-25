import time, gc
import matplotlib.pyplot as plt
import geopandas as gpd
import pandas as pd
import seaborn as sns

LATITUDE_COLUMN = "latitude"
LONGITUDE_COLUMN = "longitude"

MAIN_STATES = (
    "New South Wales",
    "Victoria",
    "Queensland",
    "Western Australia",
    "South Australia",
    "Tasmania",
    "Australian Capital Territory",
    "Northern Territory",
)

sightings_df = pd.read_csv("sightings.csv")


def main():
    (
        modeling_gdf,
        states_projected,
        roads_projected,
        roads_with_buffer,
    ) = prepare_spatial_data(sightings_df)

    print("Starting Visualization.....")

    visualize(
        modeling_gdf,
        states_projected,
        roads_projected,
        roads_with_buffer,
    )


def prepare_spatial_data(df: pd.DataFrame) -> tuple[gpd.GeoDataFrame]:
    # converting pandas DataFrame to GeoDataFrame
    sightings = gpd.GeoDataFrame(
        df,
        # creating the geometry column
        geometry=gpd.points_from_xy(df[LONGITUDE_COLUMN], df[LATITUDE_COLUMN]),
        crs="EPSG:4326",
    )
    sightings_projected = sightings.to_crs("EPSG:32754")
    # freeing up memory space
    del sightings
    gc.collect()

    print("Loading the state data....")
    # loading the whole map
    states = gpd.read_file(
        "maps/SA1_2021_AUST_GDA2020.shp", columns=["STE_NAME21", "geometry"]
    )

    # filtering to just the main states
    states = states[states["STE_NAME21"].isin(MAIN_STATES)]
    states_projected = states.to_crs("EPSG:32754")
    # freeing up memory space
    del states
    gc.collect()

    # finding sightings within states
    sightings_with_states = gpd.sjoin(
        sightings_projected, states_projected, how="inner", predicate="within"
    )
    # dropping unnecessary columns
    sightings_with_states = sightings_with_states.drop(
        columns=["index_right", "countryCode"]
    )

    sightings_with_states = sightings_with_states.rename(
        columns={"STE_NAME21": "state"}
    )
    # freeing up memory space
    del sightings_projected
    gc.collect()

    print("Loading the roads data....")
    # loading the roads data
    roads = gpd.read_file("maps/australia.gpkg", layer="gis_osm_roads_free")
    # keeping the main roads
    roads = roads[["osm_id", "fclass", "name", "geometry"]]

    # filtering roads
    relevant_roads = [
        "motorway",
        "trunk",
        "primary",
        "secondary",
        "tertiary",
        "unclassified",
        "residential",
    ]
    # filtering to keep the relevant roads
    roads = roads[roads["fclass"].isin(relevant_roads)]
    roads_projected = roads.to_crs("EPSG:32754")
    # freeing up memory space
    del roads
    gc.collect()

    # adding buffer of 500m around the roads
    roads_with_buffer = gpd.GeoDataFrame(
        geometry=roads_projected.buffer(500), crs="EPSG:32754"
    ).reset_index(drop=True)

    # spatial join sightings to nearest road
    sightings_with_roads = gpd.sjoin_nearest(
        sightings_with_states,
        roads_projected[["fclass", "geometry"]],
        how="left",
        distance_col="distance_to_road",
    )
    # freeing up memory space
    del sightings_with_states
    gc.collect()

    # drop unnecessary column
    sightings_with_roads = sightings_with_roads.drop(columns=["index_right"])

    print("Finding sightings within 500m of a road....")
    # finding sightings within 500m of a road
    high_risk_sightings = gpd.sjoin(
        sightings_with_roads, roads_with_buffer, how="inner", predicate="within"
    )

    # dropping the duplicate sightings
    high_risk_sightings = high_risk_sightings[
        ~high_risk_sightings.index.duplicated(keep="first")
    ]

    # finding sightings not within 500m of a road
    low_risk_sightings = sightings_with_roads[
        ~sightings_with_roads.index.isin(high_risk_sightings.index)
    ]
    # freeing up memory space
    del sightings_with_roads
    gc.collect()

    # adding risk labels
    high_risk_sightings["risk_label"] = 1
    low_risk_sightings["risk_label"] = 0

    # concatenating the two dataframes
    modeling_gdf = pd.concat(
        [high_risk_sightings, low_risk_sightings], ignore_index=True
    )

    return (
        modeling_gdf,
        states_projected,
        roads_projected,
        roads_with_buffer,
    )


def visualize(
    modeling_gdf: gpd.GeoDataFrame,
    states_projected: gpd.GeoDataFrame,
    roads_projected: gpd.GeoDataFrame,
    roads_with_buffer: gpd.GeoDataFrame,
):
    # setting the background theme
    sns.set_theme(style="whitegrid", palette="deep")

    # creating the figure and axes
    fig, ax = plt.subplots(figsize=(12, 10))

    # plotting the whole map
    states_projected.plot(ax=ax, color="green", alpha=0.2)

    # plotting the roads and roads with buffer
    roads_projected.plot(ax=ax, color="black", linewidth=0.5, alpha=0.5)
    roads_with_buffer.plot(ax=ax, color="grey", alpha=0.2)

    # creating a copy of the modeling dataframe
    sightings_plot_data = modeling_gdf.copy()

    # adding x and y coordinates
    sightings_plot_data["x"] = sightings_plot_data.geometry.x
    sightings_plot_data["y"] = sightings_plot_data.geometry.y

    # adding risk labels
    sightings_plot_data["Risk"] = sightings_plot_data["risk_label"].map(
        {1: "High risk", 0: "Low risk"}
    )

    # plotting the sightings using seaborn for styled scatter points
    sns.scatterplot(
        data=sightings_plot_data,
        x="x",
        y="y",
        hue="Risk",
        hue_order=["High risk", "Low risk"],
        palette={"High risk": "#e74c3c", "Low risk": "#3498db"},
        size="Risk",
        sizes={"High risk": 20, "Low risk": 12},
        alpha=0.9,
        ax=ax,
    )

    # labeling the map
    ax.set_title("Sightings across Australia", fontsize=14)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_aspect("equal")

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    print(f"Time taken: {end_time - start_time} seconds")
