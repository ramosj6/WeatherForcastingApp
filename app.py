import os
from flask import Flask, render_template, request, redirect, session
from flask_bcrypt import Bcrypt
from flask_session import Session
from mongo_connect import client
import requests
from get_coords import get_latitude_longitude_from_zip
from dotenv import load_dotenv #pip install python-dotenv

load_dotenv()



app = Flask(__name__)
app.config["SECRET_KEY"] = "your_secret_key"
app.config["SESSION_TYPE"] = "filesystem"

bcrypt = Bcrypt(app)
Session(app)

db = client["Weather"]
weather_collection = db["weather"]


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
        
        weather_data = db.weather_data.find()
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

@app.route("/update_zipcode", methods=["POST"])
def update_zipcode():
    if "user_id" in session:
        if request.method == "POST":
            new_zipcode = request.form["new_zipcode"]
            # Update the user's zipcode in the database
            db.users.update_one(
                {"_id": session["user_id"]},
                {"$set": {"zip_code": new_zipcode}}
            )
            return redirect("/")  # Redirect to the homepage or any other appropriate page after updating
    return redirect("/login")  # Redirect to the login page if the user is not logged in

if __name__ == "__main__":
    app.run(debug=True)
