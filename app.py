from flask import Flask, render_template, request, redirect, session
from flask_bcrypt import Bcrypt
from flask_session import Session
from mongo_connect import client

app = Flask(__name__)
app.config["SECRET_KEY"] = "your_secret_key"
app.config["SESSION_TYPE"] = "filesystem"

bcrypt = Bcrypt(app)
Session(app)

db = client["Weather"]


@app.route("/")
def index():
    if "user_id" in session:
        user = db.users.find_one({"_id": session["user_id"]})
        weather_data = db.weather_data.find()
        return render_template("index.html", user=user, weather_data=weather_data, user_logged_in=True)
    return render_template("index.html", user_logged_in=False)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
        db.users.insert_one({"username": username, "password": hashed_password})
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