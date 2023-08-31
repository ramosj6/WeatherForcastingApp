import os
from bson import ObjectId
from flask import Flask, json, render_template, request, redirect, session, jsonify
from flask_bcrypt import Bcrypt
from flask_session import Session
from mongo_connect import client
import requests
from get_coords import get_latitude_longitude_from_zip
from dotenv import load_dotenv #pip install python-dotenv
from bson import json_util
from datetime import datetime

from collections import defaultdict

load_dotenv()

app = Flask(__name__, static_url_path='/static')
app.config["SECRET_KEY"] = "your_secret_key"
app.config["SESSION_TYPE"] = "filesystem"

bcrypt = Bcrypt(app)
Session(app)

db = client["Weather"]

# For general weather data
weather_collection = db["weather"]

# For hourly weather data
weather_collection_hourly = db["weather_hourly"]


def parse_json(data):
    return json.loads(json_util.dumps(data))

def process_weekly_forecast(data):
    grouped_forecast = defaultdict(list)
    for period in data[0]["forecast_data"]["properties"]["periods"]:
        day_of_week = period["dayOfWeek"]
        grouped_forecast[day_of_week].append(period)
    
    grouped_forecast_list = []
    for day_name, day_forecasts in grouped_forecast.items():
        min_temperature = min(forecast["temperature"] for forecast in day_forecasts)
        max_temperature = max(forecast["temperature"] for forecast in day_forecasts)

        # Find the forecast with the max temperature and get its shortForecast
        max_temp_forecast = next(forecast for forecast in day_forecasts if forecast["temperature"] == max_temperature)["shortForecast"]

        grouped_forecast_list.append(
            {
                day_name : {
                    "minTemp": min_temperature,
                    "maxTemp": max_temperature,
                    "forecast": max_temp_forecast
                }
            }
        )

    data[0]["forecast_data"]["properties"]["grouped_forecast"] = grouped_forecast_list


def fetch_and_store_weather(latitude, longitude, zip_code):
    nws_api_endpoint = f"https://api.weather.gov/points/{latitude},{longitude}"
    
    response = requests.get(nws_api_endpoint)
    if "properties" in response.json():
        forecast_hourly_endpoint = response.json()["properties"]["forecastHourly"]
        forecast_endpoint = response.json()["properties"]["forecast"]
        
        forecast_response = requests.get(forecast_endpoint)
        if forecast_response.status_code == 200:
            forecast_data = forecast_response.json()
            #print(forecast_data)
            # Check if the latitude and longitude combination already exists
            existing_record = db.weather_hourly.find_one({"latitude": latitude, "longitude": longitude})
            if existing_record:
                # Update the existing record with new forecast data
                weather_collection_hourly.update_one(
                    {"latitude": latitude, "longitude": longitude},
                    {"$set": {"forecast_data": forecast_data}}
                )
                print("Weather data updated successfully.")
            else:
                # Store the forecast data along with latitude, longitude, and zip code
                weather_collection_hourly.insert_one({
                    "latitude": latitude,
                    "longitude": longitude,
                    "zip_code": zip_code,
                    "forecast_data": forecast_data
                })
                print("Weather data stored successfully.")
        else:
            print(f"API request failed with status code: {forecast_response.status_code}")
    else:
        print("No forecast data found.")


@app.route("/")
def index():
    """Renders the index page."""
    if "user_id" in session:
        user = db.users.find_one({"_id": session["user_id"]})
        
        # Fetch latitude and longitude based on user's zip code
        latitude, longitude, formatted_address, locality, administrative_area = get_latitude_longitude_from_zip(
            user["zip_code"], os.environ.get("GOOGLE_API")
        )
        
        # Fetch and store weather data based on extracted locality and administrative area
        if latitude and longitude:
            fetch_and_store_weather(latitude, longitude, user["zip_code"])
        
        weather_data = parse_json(weather_collection_hourly.find({"zip_code": user['zip_code']}))

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

        process_weekly_forecast(weather_data)

        print(formatted_address)
        weather_data[0]["formattedAddress"] = formatted_address
        return render_template("index.html", user=user, weather_data=weather_data, user_logged_in=True)
    return render_template("index.html", user_logged_in=False)

    
@app.route("/map")
def map_page():
    if "user_id" in session:
        user = db.users.find_one({"_id": session["user_id"]})
        latitude, longitude, formatted_address, locality, administrative_area = get_latitude_longitude_from_zip(
            user["zip_code"], os.environ.get("GOOGLE_API")
        )
        weather_data = list(db.weather.find(projection={"_id": False}))
    else:
        user = None
        weather_data = []

    default_latitude = latitude if latitude else 39.8283
    default_longitude = longitude if longitude else -98.5795

    # Prepare the weather data to include only relevant information for JavaScript
    processed_weather_data = []
    for entry in weather_data:
        periods = entry.get("properties", {}).get("periods", [])
        if periods:
            first_period = periods[0]
            temperature = first_period.get("temperature")
            icon_url = first_period.get("icon")
            if temperature and icon_url:
                processed_weather_data.append({
                    "latitude": entry["geometry"]["coordinates"][1],
                    "longitude": entry["geometry"]["coordinates"][0],
                    "temperature": temperature,
                    "icon_url": icon_url
                })

    return render_template(
        "map.html",
        user=user,  # Pass the user information to the template
        default_latitude=default_latitude,
        default_longitude=default_longitude,
        weather_data=processed_weather_data
    )


@app.route("/weather")
def weather_data():
    if "user_id" in session:
        user = db.users.find_one({"_id": session["user_id"]})
    weather_data = list(db.weather.find(projection={"_id": False}))
    # Convert ObjectId to string in each entry
    for entry in weather_data:
        if "_id" in entry:
            entry["_id"] = str(entry["_id"])
            print(weather_data)



        return jsonify(weather_data)

        print(formatted_address)
        weather_data[0]["formattedAddress"] = formatted_address
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


def generate_powerbi_embed_token(report_id):
    client_id = os.environ.get("POWERBI_CLIENT_ID")
    client_secret = os.environ.get("POWERBI_CLIENT_SECRET")
    tenant_id = os.environ.get("POWERBI_TENANT_ID")

    token_endpoint = f"https://api.powerbi.com/v1.0/myorg/groups/{tenant_id}/reports/{report_id}/GenerateToken"

    token_request_data = {"accessLevel": "view"}
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {get_access_token(client_id, client_secret, tenant_id)}"
    }

    response = requests.post(token_endpoint, json=token_request_data, headers=headers)
    
    if response.status_code == 200:
        return response.json()["token"]
    else:
        print("Error generating embed token:", response.status_code, response.text)
        return None

def get_access_token(client_id, client_secret, tenant_id):
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/token"
    token_request_data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "resource": "https://analysis.windows.net/powerbi/api"
    }

    response = requests.post(token_url, data=token_request_data)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print("Error getting access token:", response.status_code, response.text)
        return None

@app.route("/dashboard")
def dashboard():
    if "user_id" in session:
        user = db.users.find_one({"_id": session["user_id"]})
        if not user:
            return "User not found", 404  # or redirect to another page

        # Ensure you're fetching this environment variable correctly
        GOOGLE_API = os.environ.get("GOOGLE_API")
        if not GOOGLE_API:
            raise ValueError("GOOGLE_API environment variable not set!")

        # Assuming you have a get_latitude_longitude_from_zip() function from the initial code
        # latitude, longitude, formatted_address, locality, administrative_area = get_latitude_longitude_from_zip(user["zip_code"], GOOGLE_API)

        report_id = "471bb37a-6f83-4f8f-b857-1e94404b0350"
        embed_token = generate_powerbi_embed_token(report_id)
        if not embed_token:
            return "Error generating PowerBI embed token", 500

        return render_template("dashboard.html", user=user, embed_token=embed_token)
    else:
        return redirect("/login")

@app.route("/profile")
def profile():
    if "user_id" in session:
        user = db.users.find_one({"_id": session["user_id"]})
        return render_template("profile.html", username=user["username"], user_logged_in=True)
    return redirect("/login")

@app.route("/update_zipcode", methods=["POST"])
def update_zipcode():
    if "user_id" in session:
        if request.method == "POST":
            new_zipcode = request.form["new_zipcode"]
            user = db.users.find_one({"_id": session["user_id"]})
            # Update the user's zipcode in the database
            db.users.update_one(
                {"_id": session["user_id"]},
                {"$set": {"zip_code": new_zipcode}}
            )
            success_message = "Zipcode updated successfully."
            return render_template("profile.html", username=user["username"],  success_message=success_message, user_logged_in=True)
    return redirect("/login")  # Redirect to the login page if the user is not logged in

@app.route("/update_password", methods=["POST"])
def update_password():
    if "user_id" in session:
        if request.method == "POST":
            current_password = request.form["current_password"]
            new_password = request.form["new_password"]
            confirm_new_password = request.form["confirm_new_password"]
            user = db.users.find_one({"_id": session["user_id"]})
            
            if bcrypt.check_password_hash(user["password"], current_password):
            
                if new_password == confirm_new_password:
                    # Hash and update the new password in the database
                    hashed_password = bcrypt.generate_password_hash(new_password).decode("utf-8")
                    db.users.update_one(
                        {"_id": session["user_id"]},
                        {"$set": {"password": hashed_password}}
                    )
                    # Pass a success message to the template
                    success_message = "Password changed successfully."
                    return render_template("profile.html", username=user["username"], success_message=success_message, user_logged_in=True)
                else:
                    error_message = "New password and confirmation do not match."
                    return render_template("profile.html", username=user["username"], error_message=error_message, user_logged_in=True)
            else:
                error_message = "Current password is incorrect."
                return render_template("profile.html", username=user["username"], error_message=error_message, user_logged_in=True)
        return redirect("/login")            


if __name__ == "__main__":
    app.run(debug=True)
