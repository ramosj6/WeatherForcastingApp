import os
from flask import Flask, json, render_template, request, redirect, session
from flask_bcrypt import Bcrypt
from flask_session import Session
from mongo_connect import client
import requests
from get_coords import get_latitude_longitude_from_zip
from dotenv import load_dotenv #pip install python-dotenv
from bson import json_util
from datetime import datetime

from geopy.geocoders import Nominatim

load_dotenv()


app = Flask(__name__, static_url_path='/static')
app.config["SECRET_KEY"] = "your_secret_key"
app.config["SESSION_TYPE"] = "filesystem"

bcrypt = Bcrypt(app)
Session(app)

db = client["Weather"]
weather_collection = db["weather"]

geolocator = Nominatim(user_agent="weatherApp")


def parse_json(data):
    return json.loads(json_util.dumps(data))

def fetch_and_store_weather(latitude, longitude, zip_code):
    nws_api_endpoint = f"https://api.weather.gov/points/{latitude},{longitude}"
    
    response = requests.get(nws_api_endpoint)
    if "properties" in response.json():
        forecast_hourly_endpoint = response.json()["properties"]["forecastHourly"]
        
        forecast_hourly_response = requests.get(forecast_hourly_endpoint)
        if forecast_hourly_response.status_code == 200:
            forecast_data = forecast_hourly_response.json()
            
            # Check if the latitude and longitude combination already exists
            existing_record = db.weather.find_one({"latitude": latitude, "longitude": longitude})
            if existing_record:
                # Update the existing record with new forecast data
                weather_collection.update_one(
                    {"latitude": latitude, "longitude": longitude},
                    {"$set": {"forecast_data": forecast_data}}
                )
                print("Weather data updated successfully.")
            else:
                # Store the forecast data along with latitude, longitude, and zip code
                weather_collection.insert_one({
                    "latitude": latitude,
                    "longitude": longitude,
                    "zip_code": zip_code,
                    "forecast_data": forecast_data
                })
                print("Weather data stored successfully.")
        else:
            print(f"API request failed with status code: {forecast_hourly_response.status_code}")
    else:
        print("No forecast data found.")


@app.route("/")
def index():
    if "user_id" in session:
        user = db.users.find_one({"_id": session["user_id"]})
        
        # Fetch latitude and longitude based on user's zip code
        latitude, longitude, formatted_address, locality, administrative_area = get_latitude_longitude_from_zip(
            user["zip_code"], os.environ.get("GOOGLE_API")
        )
        
        # Fetch and store weather data based on extracted locality and administrative area
        if latitude and longitude:
            fetch_and_store_weather(latitude, longitude, user["zip_code"])
        
        weather_data = parse_json(weather_collection.find({"zip_code": user['zip_code']}))

        # Implementing pre-processing on the data for the start and end times
        for period in weather_data[0]["forecast_data"]["properties"]["periods"]:
            start_time = datetime.strptime(
                period["startTime"], "%Y-%m-%dT%H:%M:%S%z"
            )

            end_time = datetime.strptime(
                period["endTime"], "%Y-%m-%dT%H:%M:%S%z"
            )

            todays_day = datetime.today().strftime('%A')
            day_of_week = start_time.strftime('%A')

            start_hour = start_time.strftime("%I").lstrip("0")
            end_hour = end_time.strftime("%I").lstrip("0")

            period["startTime"] = f"{start_hour}:{start_time.strftime('%M %p')}"
            period["endTime"] = f"{end_hour}:{end_time.strftime('%M %p')}"
            period["dayOfWeek"] = 'Today' if todays_day == day_of_week else day_of_week


        # Getting Address information from zip code
        address = geolocator.geocode(weather_data[0]["zip_code"]).address
        print(address)
        weather_data[0]["metro"] = address
        return render_template("index.html", user=user, weather_data=weather_data, user_logged_in=True)
    return render_template("index.html", user_logged_in=False)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        email = request.form["email"]
        zip_code = request.form["zip_code"]
        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
        db.users.insert_one({"username": username, "password": hashed_password, "email": email, "zip_code": zip_code})
        return redirect("/login")
    return render_template("register.html", message=None)  # Pass a message to the template if needed

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = db.users.find_one({"username": username})
        if user and bcrypt.check_password_hash(user["password"], password):
            session["user_id"] = user["_id"]
            return redirect("/")
        else:
            message = "Invalid username or password"  # Add an error message if login fails
            return render_template("login.html", message=message)
    return render_template("login.html", message=None)

@app.route("/logout")
def logout():
    session.clear()  # Clear the user's session data
    return render_template("logout.html")

if __name__ == "__main__":
    app.run(debug=True)
