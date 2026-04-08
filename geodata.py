import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt


file_name = "macropus_rufus_sightings_gbif.csv"
LATITUDE_COLUMN = "latitude"
LONGITUDE_COLUMN = "longitude"

df = pd.read_csv(file_name)

# converting pandas DataFrame to GeoDataFrame
gdf = gpd.GeoDataFrame(
    df,
    # creating the geometry column
    geometry=gpd.points_from_xy(df[LONGITUDE_COLUMN], df[LATITUDE_COLUMN]),
    crs="EPSG:4326",
)

# converting to projected CRS
gdf_projected = gdf.to_crs("EPSG:32754")

# creaing a buffer of 1km
gdf_projected["buffer_1km"] = gdf_projected.geometry.buffer(1000)


def main():
    states = gpd.read_file("SA1_2021_AUST_GDA2020.shp")
    # Filter to just the main states if territories are included
    states = states[states["STE_NAME21"].notna()]
    states_projected = states.to_crs(gdf_projected.crs)

    print(gdf.crs)
    print(gdf_projected.crs)
    print(states_projected.crs)

    gdf_with_states = gpd.sjoin(
        gdf_projected, states_projected, how="left", predicate="within"
    )

    print(f"\nOriginal sightings: {len(gdf)}")
    print(f"Joined sightings: {len(gdf_with_states)}")
    print(
        f"\nNew columns added: {[col for col in gdf_with_states.columns if col not in gdf.columns]}"
    )
    print(f"\nFirst 5 rows with state assignment:")
    print(gdf_with_states[["geometry", "index_right", "STE_NAME21"]].head())


main()
