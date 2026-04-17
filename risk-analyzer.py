import time
import osmnx as ox
import matplotlib.pyplot as plt
import geopandas as gpd
import pandas as pd

kangaroo_csv = "sightings/kangaroo_sightings.csv"
wombat_csv = "sightings/wombat_sightings.csv"
koala_csv = "sightings/koala_sightings.csv"

LATITUDE_COLUMN = "latitude"
LONGITUDE_COLUMN = "longitude"

kangaroo_df = pd.read_csv(kangaroo_csv)
wombat_df = pd.read_csv(wombat_csv)
koala_df = pd.read_csv(koala_csv)


def main():
    sightings, states_projected, edges_projected, road_buffer = prepare_spatial_data(
        wombat_df
    )

    visualize_data(sightings, states_projected, edges_projected, road_buffer)


def prepare_spatial_data(df: pd.DataFrame) -> tuple[gpd.GeoDataFrame]:
    # converting pandas DataFrame to GeoDataFrame
    gdf = gpd.GeoDataFrame(
        df,
        # creating the geometry column
        geometry=gpd.points_from_xy(df[LONGITUDE_COLUMN], df[LATITUDE_COLUMN]),
        crs="EPSG:4326",
    )

    # converting to projected CRS
    gdf_projected = gdf.to_crs("EPSG:32754")

    states = gpd.read_file("roads/SA1_2021_AUST_GDA2020.shp")

    # Filter to just the main states if territories are included
    states = states[states["STE_NAME21"].notna()]
    columns = [
        "SA1_CODE21",
        "CHG_FLAG21",
        "CHG_LBL21",
        "SA2_CODE21",
        "SA2_NAME21",
        "SA3_CODE21",
        "SA3_NAME21",
        "SA4_CODE21",
        "SA4_NAME21",
        "GCC_CODE21",
        "GCC_NAME21",
        "AUS_CODE21",
        "AUS_NAME21",
        "AREASQKM21",
        "LOCI_URI21",
    ]
    # removing unnecessary columns
    states = states.drop(columns=columns)
    states_projected = states.to_crs(gdf_projected.crs)

    # finding sightings within states
    sightings = gpd.sjoin(
        gdf_projected, states_projected, how="inner", predicate="within"
    )

    # pulling driveable roads for a specific area
    G = ox.graph_from_place(
        "Australian Capital Territory, Australia", network_type="drive"
    )

    # converting graph to node and edge GeoDataFrames
    # nodes are intersections or endpoints
    # edges are the roads connecting nodes
    nodes, edges = ox.graph_to_gdfs(G)

    # converting to projected CRS
    edges_projected = edges.to_crs("EPSG:32754")
    # creating a buffer of 500m around the roads
    road_buffer = edges_projected.buffer(500).union_all()
    road_buffer = gpd.GeoDataFrame(geometry=[road_buffer], crs="EPSG:32754")

    return sightings, states_projected, edges_projected, road_buffer


def visualize_data(sightings, states_projected, edges_projected, road_buffer):
    # isolating sightings to a specific area
    sightings_act = sightings[sightings["STE_NAME21"] == "Australian Capital Territory"]

    act = states_projected[
        states_projected["STE_NAME21"] == "Australian Capital Territory"
    ]

    fig, ax = plt.subplots(figsize=(12, 10))

    # plotting the states
    act.plot(ax=ax, color="green", alpha=0.2)
    # plotting the edges and roads
    edges_projected.plot(ax=ax, color="black", linewidth=0.5, alpha=0.5)
    road_buffer.plot(ax=ax, color="grey", alpha=0.2)

    # finding sightings within 500m of a road
    high_risk = gpd.sjoin(
        sightings_act.drop(columns="index_right", errors="ignore"),
        road_buffer,
        how="inner",
        predicate="within",
    )
    # finding sightings not within 500m of a road
    low_risk = sightings_act[~sightings_act.index.isin(high_risk.index)]

    # plotting the sightings
    high_risk.plot(ax=ax, color="red", markersize=8, alpha=0.9, label="High risk")
    low_risk.plot(ax=ax, color="blue", markersize=8, alpha=0.9, label="Low risk")

    # labeling the map
    ax.set_title("Road Network (Driveable)", fontsize=14)
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
