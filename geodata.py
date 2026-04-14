import time
import pandas as pd
import geopandas as gpd

file_name = "vombatus_ursinus_sightings_gbif.csv"
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

states = gpd.read_file("SA1_2021_AUST_GDA2020.shp")
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
states = states.drop(columns=columns)
states_projected = states.to_crs(gdf_projected.crs)

sightings = gpd.sjoin(gdf_projected, states_projected, how="inner", predicate="within")


def main():
    pass


if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    print(f"Time taken: {end_time - start_time} seconds")
