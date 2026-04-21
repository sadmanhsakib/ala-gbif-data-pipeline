import time, gc
import matplotlib.pyplot as plt
import geopandas as gpd
import pandas as pd

LATITUDE_COLUMN = "latitude"
LONGITUDE_COLUMN = "longitude"

sightings_df = pd.read_csv("sightings.csv")

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


def main():
    (
        high_risk_sightings,
        low_risk_sightings,
        states_projected,
        roads_projected,
        roads_buffer_gdf,
    ) = prepare_spatial_data(sightings_df)

    visualize_data(
        high_risk_sightings,
        low_risk_sightings,
        states_projected,
        roads_projected,
        roads_buffer_gdf,
    )


def prepare_spatial_data(df: pd.DataFrame) -> tuple[gpd.GeoDataFrame]:
    # converting pandas DataFrame to GeoDataFrame
    gdf = gpd.GeoDataFrame(
        df,
        # creating the geometry column
        geometry=gpd.points_from_xy(df[LONGITUDE_COLUMN], df[LATITUDE_COLUMN]),
        crs="EPSG:4326",
    )
    gdf_projected = gdf.to_crs("EPSG:32754")
    del gdf
    gc.collect()

    print("Loading the state data....")
    states = gpd.read_file(
        "maps/SA1_2021_AUST_GDA2020.shp", columns=["STE_NAME21", "geometry"]
    )

    # Filter to just the main states
    states = states[states["STE_NAME21"].isin(MAIN_STATES)]
    states_projected = states.to_crs("EPSG:32754")
    del states
    gc.collect()

    # finding sightings within states
    sightings = gpd.sjoin(
        gdf_projected, states_projected, how="inner", predicate="within"
    )
    # dropping unnecessary columns
    sightings = sightings.drop(columns=["index_right", "countryCode"])
    sightings = sightings.rename(columns={"STE_NAME21": "state"})
    del gdf_projected
    gc.collect()

    print("loading the roads data....")
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
    roads = roads[roads["fclass"].isin(relevant_roads)]
    roads_projected = roads.to_crs("EPSG:32754")
    del roads
    gc.collect()

    # adding buffer of 500m around the roads
    roads_buffer = roads_projected.copy()
    roads_buffer["geometry"] = roads_buffer.buffer(500)
    roads_buffer_gdf = roads_buffer[["geometry"]].reset_index(drop=True)

    # finding sightings within 500m of a road
    high_risk_sightings = gpd.sjoin(
        sightings, roads_buffer_gdf, how="inner", predicate="within"
    )

    # finding sightings not within 500m of a road
    low_risk_sightings = sightings[~sightings.index.isin(high_risk_sightings.index)]

    return (
        high_risk_sightings,
        low_risk_sightings,
        states_projected,
        roads_projected,
        roads_buffer_gdf,
    )


def visualize_data(
    high_risk_sightings,
    low_risk_sightings,
    states_projected,
    roads_projected,
    roads_buffer_gdf,
):
    fig, ax = plt.subplots(figsize=(12, 10))

    # plotting the whole country
    states_projected.plot(ax=ax, color="green", alpha=0.2)

    # plotting the edges and roads
    roads_projected.plot(ax=ax, color="black", linewidth=0.5, alpha=0.5)
    roads_buffer_gdf.plot(ax=ax, color="grey", alpha=0.2)

    # plotting the sightings
    high_risk_sightings.plot(
        ax=ax, color="red", markersize=8, alpha=0.9, label="High risk"
    )
    low_risk_sightings.plot(
        ax=ax, color="blue", markersize=6, alpha=0.9, label="Low risk"
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
