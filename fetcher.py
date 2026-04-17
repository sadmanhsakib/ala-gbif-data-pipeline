import json, os, time
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# getting the variables from the .env file
KANGAROO_KEY = int(os.getenv("KANGAROO_KEY"))
WOMBAT_KEY = int(os.getenv("WOMBAT_KEY"))
KOALA_KEY = int(os.getenv("KOALA_KEY"))
KANGAROO_SCIENTIFIC_NAME = os.getenv("KANGAROO_SCIENTIFIC_NAME")
WOMBAT_SCIENTIFIC_NAME = os.getenv("WOMBAT_SCIENTIFIC_NAME")
KOALA_SCIENTIFIC_NAME = os.getenv("KOALA_SCIENTIFIC_NAME")
GBIF_URL = os.getenv("GBIF_URL")
ALA_URL = os.getenv("ALA_URL")


def main():
    file_name = get_gbif_data(KANGAROO_KEY)

    if file_name:
        clean_data(file_name)

        merge_csv(
            "sightings/kangaroo_sightings.csv",
            "sightings/macropus_rufus_sightings_gbif.csv",
        )


def get_gbif_data(species_key: int) -> json:
    offset = 0
    results = []

    while True:
        params = {
            "taxonKey": species_key,
            "country": "AU",
            "stateProvince": "Australian Capital Territory",
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
            if data["endOfRecords"] or offset > 1000:
                break
            offset += 300
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return 1

        print(f"Data Pulled: {offset}")
        # for avoiding HTTP 429 error
        time.sleep(1)
    if results:
        file_name = f"sightings/{results[0]['species'].lower().replace(' ', '_')}_sightings_gbif.json"

        # exporting the json file
        with open(file_name, "w") as file:
            json.dump(results, file)
        print(f"✅Data exported to {file_name} successfully. ")

        return file_name
    else:
        print("No results found.")
        return None


def get_ala_data(species_scientific_name: str) -> json:
    offset = 0
    results = []

    while True:
        params = {
            "q": species_scientific_name,
            "fq": ["country:Australia"],
            "pageSize": 500,  # records per page (max 1000)
            "startIndex": offset,  # for pagination
            "fl": "scientificName,raw_countryCode,year,decimalLatitude,decimalLongitude",  # fields to return
        }
        headers = {"Accept": "application/json"}

        # sending the requests
        response = requests.get(ALA_URL, params=params, headers=headers)

        # checking if the request was successful
        if response.status_code == 200:
            data = response.json()
            results.extend(data["occurrences"])

            # stopping if it's the end of the dataset
            if data["totalRecords"] < (offset + 500) or offset > 5000:
                break
            offset += 500
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return 1

        print(f"Data Pulled: {offset}")
        # for avoiding HTTP 429 error
        time.sleep(1)

    if results:
        file_name = f"sightings/{results[0]['scientificName'].lower().replace(' ', '_')}_sightings_ala.json"

        # exporting the json file
        with open(file_name, "w") as file:
            json.dump(results, file)
        print(f"✅Data exported to {file_name} successfully. ")

        return file_name
    else:
        print("No results found.")
        return None


def clean_data(file_name: str):
    # loading the file
    with open(file_name, "r") as file:
        data: dict = json.load(file)

    # loading the dataframe
    df = pd.DataFrame(data)

    # for GBIF data
    try:
        # only keeping rows in Australia
        df = df[df["countryCode"] == "AU"]
        # removing the unnecessary columns
        df = df[
            ["species", "countryCode", "year", "decimalLatitude", "decimalLongitude"]
        ]
    # for ALA data
    except KeyError:
        # only keeping rows in Australia
        df = df[df["raw_countryCode"] == "AU"]
        # removing the unnecessary columns
        df = df[
            [
                "scientificName",
                "raw_countryCode",
                "year",
                "decimalLatitude",
                "decimalLongitude",
            ]
        ]
        # renmaing the ala specific columns
        df = df.rename(
            columns={
                "scientificName": "species",
                "raw_countryCode": "countryCode",
            }
        )

    # renmaing the other columns
    df = df.rename(
        columns={
            "decimalLatitude": "latitude",
            "decimalLongitude": "longitude",
        }
    )

    # removing rows with missing coordinates
    df = df.dropna(subset=["latitude", "longitude", "year"])

    # removing rows with older sighting data
    df = df.drop(df[df["year"] < 2020].index)

    # removing duplicates
    df = df.drop_duplicates(subset=["latitude", "longitude"])

    # removing the json file as it's pretty much useless
    os.remove(file_name)
    print(f"✅{file_name} removed successfully. ")

    file_name = file_name.replace(".json", ".csv")
    # exporting the csv file
    df.to_csv(f"{file_name}", index=False)
    print(f"✅Data exported to {file_name} successfully. ")


def merge_csv(file_name_1: str, file_name_2: str):
    # converting the csv files in pandas dataframe
    df_1 = pd.read_csv(file_name_1)
    df_2 = pd.read_csv(file_name_2)

    merged_df = pd.concat([df_1, df_2], ignore_index=True)

    # removing duplicates
    merged_df = merged_df.drop_duplicates(subset=["latitude", "longitude"])

    # getting the file name
    if file_name_1.__contains__("_gbif.csv"):
        file_name = file_name_1.replace("_gbif.csv", "")
    elif file_name_1.__contains__("_ala.csv"):
        file_name = file_name_1.replace("_ala.csv", "")
    else:
        file_name = file_name_1.replace(".csv", "")

    print(merged_df.info())

    # removing the json file as it's pretty much useless
    os.remove(file_name_1)
    os.remove(file_name_2)

    # exporting the csv file
    merged_df.to_csv(f"{file_name}.csv", index=False)


main()
