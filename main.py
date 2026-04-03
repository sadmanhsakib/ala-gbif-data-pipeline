import json, time
import requests
import pandas as pd

KANGAROO_KEY = 5219981
WOMBAT_KEY = 2440301
GBIF_URL = "https://api.gbif.org/v1/occurrence/search"


def main():
    get_gbif_data()

    with open("kangaroo.json", "r", encoding="utf-8") as file:
        data = json.load(file)

    clean_data(data)


def get_gbif_data():
    offset = 0
    results = []

    while True:
        # for avoiding HTTP 429 error
        time.sleep(0.4)

        # parameters for Macropus giganteus in Australia
        params = {
            "taxonKey": KANGAROO_KEY,
            "country": "AU",
            "hasCoordinate": "true",
            "limit": 300,
            "offset": offset,
        }

        # sending the requests
        response = requests.get(GBIF_URL, params=params)

        # checking if the request was successful
        if response.status_code == 200:
            data = response.json()
            results.extend(data["results"])

            # stopping if it's the end of the dataset
            if data["endOfRecords"]:
                break
            offset += 300
        else:
            print(f"Error: {response.status_code}")
            print(response.text)

    # exporting the json file
    with open("kangaroo.json", "w") as file:
        json.dump(results, file)
    print("✅Data exported successfully. ")


def clean_data(data: list):
    # loading the dataframe
    df = pd.DataFrame(data)

    # only keeping rows in Australia
    df = df[df["countryCode"] == "AU"]

    # removing the unnecessary columns
    df = df[["species", "countryCode", "year", "decimalLatitude", "decimalLongitude"]]

    # renmaing the columns
    df = df.rename(
        columns={
            "decimalLatitude": "latitude",
            "decimalLongitude": "longitude",
        }
    )

    # removing rows with missing coordinates
    df = df.dropna(subset=["latitude", "longitude"])

    # removing duplicates
    df = df.drop_duplicates(subset=["latitude", "longitude"])

    print(df.info())

    # exporting the csv file
    df.to_csv("wildlife_sightings.csv", index=False)


main()
