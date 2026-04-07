import json, os, time
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# getting the variables from the .env file
KANGAROO_KEY = int(os.getenv("KANGAROO_KEY"))
WOMBAT_KEY = int(os.getenv("WOMBAT_KEY"))
KANGAROO_SCIENTIFIC_NAME = os.getenv("KANGAROO_SCIENTIFIC_NAME")
WOMBAT_SCIENTIFIC_NAME = os.getenv("WOMBAT_SCIENTIFIC_NAME")
GBIF_URL = os.getenv("GBIF_URL")
ALA_URL = os.getenv("ALA_URL")


def main():
    get_ala_data(KANGAROO_SCIENTIFIC_NAME)


def get_gbif_data(species_key: int):
    offset = 0
    results = []

    while True:
        # parameters for Macropus giganteus in Australia
        params = {
            "taxonKey": species_key,
            "country": "AU",
            "hasCoordinate": "true",
            "limit": 300,
            "offset": offset,
        }

        print(f"Offset: {offset}")

        # sending the requests
        response = requests.get(GBIF_URL, params=params)

        # checking if the request was successful
        if response.status_code == 200:
            data = response.json()
            results.extend(data["results"])

            # stopping if it's the end of the dataset
            if data["endOfRecords"] or offset > 2500:
                break
            offset += 300
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return 1

        # for avoiding HTTP 429 error
        time.sleep(1)

    file_name = f"{results[0]['species'].lower().replace(' ', '_')}_sightings_gbif.json"

    # exporting the json file
    with open(file_name, "w") as file:
        json.dump(results, file)
    print(f"✅Data exported to {file_name} successfully. ")


def get_ala_data(species_scientific_name: str):
    offset = 0
    results = []

    while True:
        # parameters for Macropus giganteus in Australia
        params = {
            "q": species_scientific_name,
            "fq": "country:Australia",
            "pageSize": 100,  # records per page (max 1000)
            "startIndex": offset,  # for pagination
            "fl": "scientificName,raw_countryCode,year,decimalLatitude,decimalLongitude",  # fields to return
        }
        headers = {"Accept": "application/json"}

        print(f"Data Pulled: {offset}")

        # sending the requests
        response = requests.get(ALA_URL, params=params, headers=headers)

        # checking if the request was successful
        if response.status_code == 200:
            data = response.json()
            results.extend(data["occurrences"])

            # stopping if it's the end of the dataset
            if data["totalRecords"] < (offset + 100) or offset > 2500:
                break
            offset += 100
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return 1

        # for avoiding HTTP 429 error
        time.sleep(1)

    file_name = (
        f"{results[0]['scientificName'].lower().replace(' ', '_')}_sightings_ala.json"
    )

    # exporting the json file
    with open(file_name, "w") as file:
        json.dump(results, file)
    print(f"✅Data exported to {file_name} successfully. ")


def clean_data(file_name: str):
    # loading the file
    with open(file_name, "r") as file:
        data: list = json.load(file)

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
    df.to_csv(f"{file_name.replace('.json', '.csv')}", index=False)


main()
