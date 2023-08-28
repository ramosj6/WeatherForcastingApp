# This script will fetch weather data from the national weather service api and store it on our mongo database
import requests
from pprint import pprint
from mongo_connect import client


# MongoDB details
db = client["Weather"]
collection = ["weather"]

# Setting up endpoint
nws_api_endpoint = "https://api.weather.gov/points/"

# This is for Beloit, WI
lat = 42.508361
lon = -89.031804


# Making the api requests
response = requests.get(nws_api_endpoint + str(lat) + "," + str(lon))

if response.status_code == 200:
    data = response.json()
    forecast_hourly_endpoint = data["properties"]["forecastHourly"]

    forecast_hourly_response = requests.get(forecast_hourly_endpoint)
    if forecast_hourly_response.status_code == 200:
        forecast_data = forecast_hourly_response.json()
        # pprint(forecast_data)
    else:
        print(f"API request failed with status code: {forecast_hourly_response.status_code}")
else: 
    print(f"API request failed with status code: {response.status_code}")