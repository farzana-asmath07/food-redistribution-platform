
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user,
    logout_user, login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///food.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "development-secret-key"

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# USER DATABASE TABLE
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)


# FOOD DATABASE TABLE
class Food(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    food_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500))
    status = db.Column(db.String(30), default="Available")
    donor_id = db.Column(db.Integer, db.ForeignKey("user.id"))


# FOOD REQUEST DATABASE TABLE
class FoodRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    food_id = db.Column(db.Integer, db.ForeignKey("food.id"), nullable=False)
    volunteer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    status = db.Column(db.String(30), default="Pending")

    food = db.relationship("Food")
    volunteer = db.relationship("User")


# LOGIN MANAGER
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# HOME PAGE
@app.route("/")
def home():
    return render_template("index.html")


# REGISTRATION
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":

        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        role = request.form["role"]

        if not name or not email or len(password) < 8:
            flash("Enter valid details. Password must be at least 8 characters.")
            return redirect(url_for("register"))

        if role not in ["Donor", "Volunteer"]:
            flash("Please select a valid role.")
            return redirect(url_for("register"))

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            flash("Email already registered!")
            return redirect(url_for("register"))

        new_user = User(
            name=name,
            email=email,
            password=generate_password_hash(password),
            role=role
        )

        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! Please log in.")
        return redirect(url_for("login"))

    return render_template("register.html")


# LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        email = request.form["email"].strip().lower()
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("dashboard"))

        flash("Invalid email or password!")

    return render_template("login.html")


# DASHBOARD
@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


# ADD FOOD DONATION
@app.route("/donate", methods=["GET", "POST"])
@login_required
def donate():

    if current_user.role != "Donor":
        flash("Only food donors can add donations.")
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        food_name = request.form["food_name"]
        quantity = request.form["quantity"]
        location = request.form["location"]
        description = request.form["description"]

        new_food = Food(
            food_name=food_name,
            quantity=quantity,
            location=location,
            description=description,
            donor_id=current_user.id
        )

        db.session.add(new_food)
        db.session.commit()

        flash("Food donation added successfully!")
        return redirect(url_for("dashboard"))

    return render_template("donate.html")


# VIEW AVAILABLE FOOD
@app.route("/available-food")
@login_required
def available_food():

    if current_user.role != "Volunteer":
        flash("Only volunteers can view available food.")
        return redirect(url_for("dashboard"))

    foods = Food.query.filter_by(status="Available").all()

    return render_template("available_food.html", foods=foods)


# REQUEST FOOD
@app.route("/request-food/<int:food_id>", methods=["POST"])
@login_required
def request_food(food_id):

    if current_user.role != "Volunteer":
        flash("Only volunteers can request food.")
        return redirect(url_for("dashboard"))

    food = db.session.get(Food, food_id)

    if food is None or food.status != "Available":
        flash("This food is no longer available.")
        return redirect(url_for("available_food"))

    existing_request = FoodRequest.query.filter_by(
        food_id=food_id,
        volunteer_id=current_user.id,
        status="Pending"
    ).first()

    if existing_request:
        flash("You have already requested this food.")
        return redirect(url_for("available_food"))

    new_request = FoodRequest(
        food_id=food_id,
        volunteer_id=current_user.id
    )

    db.session.add(new_request)
    db.session.commit()

    flash("Food request submitted successfully!")
    return redirect(url_for("available_food"))


# VIEW FOOD REQUESTS (DONOR)
@app.route("/my-requests")
@login_required
def my_requests():

    if current_user.role != "Donor":
        flash("Only donors can view food requests.")
        return redirect(url_for("dashboard"))

    requests = FoodRequest.query.join(Food).filter(
        Food.donor_id == current_user.id
    ).all()

    return render_template("requests.html", requests=requests)


# LOGOUT
@app.route("/logout", methods=["POST"])
@login_required
def logout():

    logout_user()
    flash("You have logged out successfully.")

    return redirect(url_for("login"))


# CREATE DATABASE
with app.app_context():
    db.create_all()
    print("Database ready!")


# RUN APPLICATION
if __name__ == "__main__":
    app.run(debug=True)
