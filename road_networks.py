import geodata
import time
import osmnx as ox
import matplotlib.pyplot as plt
import geopandas as gpd


def main():
    # pulling driveable roads for a specific area
    G = ox.graph_from_place(
        "Australian Capital Territory, Australia", network_type="drive"
    )

    # converting graph to node and edge GeoDataFrames
    # nodes are intersections or endpoints
    # edges are the roads connecting nodes
    nodes, edges = ox.graph_to_gdfs(G)
    edges_projected = edges.to_crs("EPSG:32754")
    road_buffer = edges_projected.buffer(500).union_all()
    road_buffer_gdf = gpd.GeoDataFrame(geometry=[road_buffer], crs="EPSG:32754")

    visualize_data(edges_projected, road_buffer_gdf)


def visualize_data(edges_projected, road_buffer_gdf):
    sightings_act = geodata.sightings[
        geodata.sightings["STE_NAME21"] == "Australian Capital Territory"
    ]

    fig, ax = plt.subplots(figsize=(12, 10))

    edges_projected.plot(ax=ax, color="gray", linewidth=0.5, alpha=0.5)
    road_buffer_gdf.plot(ax=ax, color="blue", alpha=0.2)

    print(sightings_act.columns.to_list())
    high_risk = gpd.sjoin(
        sightings_act.drop(columns="index_right", errors="ignore"),
        road_buffer_gdf,
        how="inner",
        predicate="within",
    )

    low_risk = sightings_act[~sightings_act.index.isin(high_risk.index)]
    high_risk.plot(ax=ax, color="red", markersize=8, alpha=0.9, label="High risk")
    low_risk.plot(ax=ax, color="green", markersize=8, alpha=0.9, label="Low risk")

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
