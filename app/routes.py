from flask import render_template, flash, redirect, url_for, request, jsonify
from flask_login import current_user, login_user, logout_user, login_required
from flask_mail import Message
from werkzeug.urls import url_parse
from app import app, csrf, mail
from app.forms import LoginForm, MachineForm, LocationForm, UserForm
from app.finders import Finders
from app.handlers import Handlers
import json
from types import SimpleNamespace
import hashlib

@app.route("/health")
def health():
    return "alive"

@app.route("/")
@app.route("/home")
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    form = LoginForm()
    if form.validate_on_submit():
        user = Finders.get_user_from_username(form.username.data)
        if user is None or not user.check_password(form.password.data):
            flash("Invalid username or password")
            return redirect(url_for("login"))
        login_user(user, remember=form.remember_me.data)
        
        next_page = request.args.get("next")
        if not next_page or url_parse(next_page).netloc != "":
            next_page = url_for("index")
        return redirect(next_page)

    return render_template("login.html", title="Sign In", form=form)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("index"))

@app.route("/users", methods=["GET"])
@login_required
def users():
    users = Finders.get_users()

    return render_template("users.html", title="Users", users=users)

@app.route("/user", methods=["GET", "POST"])
@login_required
def create_user():
    form = UserForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.username.data
        if Finders.get_user_from_username(username):
            flash("Username already in use")
            return render_template("create_form.html", title="Create User", form=form)
    
        if Finders.get_user_from_email(email):
            flash("Email already in use")
            return render_template("create_form.html", title="Create User", form=form)

        user, error = Handlers.create_user(username, email)
        if user is None:
            flash(error)
            return render_template("create_form.html", title="Create User", form=form)

        return redirect(url_for("users"))

    return render_template("create_form.html", title="Create User", form=form)

@app.route("/user/<int:user_id>/delete", methods=["POST"])
@login_required
def delete_user(user_id):
    user = Finders.get_user_from_id(user_id)
    if user is None:
        flash("Cant find user")
        return redirect(url_for("users"))    

    Handlers.delete_user(user)
    
    return redirect(url_for("users"))

@app.route("/locations", methods=["GET"])
@login_required
def locations():
    page = request.args.get("page", 1)
    locations = Finders.get_locations()

    return render_template("locations.html", title="Locations", locations=locations)

@app.route("/location", methods=["GET", "POST"])
@login_required
def create_location():
    form = LocationForm()
    if form.validate_on_submit():
        name = form.name.data
        latitude = form.latitude.data
        longitude = form.longitude.data
        if Finders.get_location_by_name(name):
            flash("Location already exists")
            return render_template("create_form.html", title="Create Location", form=form)
    
        if Handlers.create_location(name, latitude, longitude) is None:
            flash("Failed to create location")
            return render_template("create_form.html", title="Create Location", form=form)

        return redirect(url_for("locations"))

    return render_template("create_form.html", title="Create Location", form=form)

@app.route("/location/<int:location_id>/delete", methods=["POST"])
@login_required
def delete_location(location_id):
    location = Finders.get_location_by_id(location_id)
    if location is None:
        flash("Cant find location")
        return redirect(url_for("locations"))    

    Handlers.delete_location(location)
    
    return redirect(url_for("locations"))

@app.route("/location/<int:location_id>/machines", methods=["GET"])
@login_required
def location(location_id):
    location = Finders.get_location_by_id(location_id)
    if location is None:
        flash("Cant find location")
        return redirect(url_for("locations"))

    return render_template("location.html", title=location.name, location=location)

@app.route("/machine", methods=["GET", "POST"])
@login_required
def create_machine():
    location_id = request.args.get("location_id", None)

    if request.method == "GET":
        form = MachineForm(location_id=location_id)
    elif request.method == "POST":
        form = MachineForm()

    if form.validate_on_submit():
        location_id = form.location_id.data
        location = Finders.get_location_by_id(location_id)
        if not location:
            flash("Machine already exists")
            return redirect(url_for("locations"))

        name = form.name.data
        if Finders.get_machine_by_name(name):
            form.location_id = location_id
            flash("Machine already exists")
            return render_template("create_form.html", title="Create Machine", form=form)

        machine = Handlers.create_machine(name, location_id)
        if machine is None:
            form.location_id = location_id
            flash("Failed to create machine")
            return render_template("create_form.html", title="Create Machine", form=form)

        first_reading = Handlers.create_reading(machine_id = machine.id)
        if first_reading is None:
            flash("Failed to create machine reading")
            Handlers.delete_machine(machine)
            return render_template("create_form.html", title="Create Machine", form=form)

        if form.master.data:
            Handlers.update_location(location, master_id=machine.id)

        return redirect(url_for("location", location_id=location_id))

    return render_template("create_form.html", title="Create Machine", form=form)

@app.route("/machine/<string:machine_id>/delete", methods=["POST"])
@login_required
def delete_machine(machine_id):
    machine = Finders.get_machine_by_id(machine_id)
    if machine is None:
        flash("Cant find machine")
        return redirect(url_for("locations"))

    location_id = machine.location_id
    if not Handlers.delete_machine(machine):
        flash("Failed to delete machine")
        
    return redirect(url_for("location", location_id=location_id))

@app.route("/machine/<int:machine_id>", methods=["GET"])
@login_required
def machine(machine_id):
    machine = Finders.get_machine_by_id(machine_id)
    if machine is None:
        flash("Cant find machine")
        return redirect(url_for("locations"))

    return render_template("machine.html", title=machine.name, machine=machine)

@app.route("/api/reading", methods=["POST"])
@csrf.exempt
def reading():
    api_key = request.headers.get("Authorization", None)
    if api_key is None or api_key != "Bearer 123":
        return jsonify({"status":"error", "msg":"Unauthorized"}), 401

    try:
        data = request.get_json()["data"]
        data = json.loads(data, object_hook=lambda d: SimpleNamespace(**d))
    except:
        return jsonify({"status":"error", "msg":"Wrong format"}), 500    

    try:
        id = data.i
        time = data.t
    except AttributeError:
        return jsonify({"status":"error", "msg":"Missing info"}), 500

    if(not Handlers.check_time_hash(time)):
        return jsonify({"status":"error", "msg":"Wrong info"}), 500

    machine = Finders.get_machine_by_id(id)
    if not machine:
        return jsonify({"status":"error", "msg":"Device not registered"}), 404

    last = Finders.get_last_reading_from_machine_id(id)

    humidity_20 = getattr(data, "h20", None)
    humidity_40 = getattr(data, "h40", None)
    humidity_60 = getattr(data, "h60", None)
    pressure = getattr(data, "p", None)

    if None in [humidity_20, humidity_40, humidity_60, pressure]:
        return jsonify({"status":"error", "msg":"Missing data"}), 500
    
    if hasattr(data, "l20"):
        Handlers.create_reading(machine_id=id, humidity_20=humidity_20, humidity_40=humidity_40, humidity_60=humidity_60, pressure=pressure, \
            motor_20=(data.l20=="start"), motor_40=last.motor_40, motor_60=last.motor_60, \
            water_level_20=(data.l20=="end"), water_level_40=last.water_level_40, water_level_60=last.water_level_60)
        
        if Handlers.send_sample_email(machine.name, "20cm lysimeter", machine.location):
            return jsonify({{"status":"pickup"}})
        else:
            return jsonify({"status":"error", "msg":"Failed to send email"}), 500

    elif hasattr(data, "l40"):
        Handlers.create_reading(machine_id=id, humidity_20=humidity_20, humidity_40=humidity_40, humidity_60=humidity_60, pressure=pressure, \
            motor_40=(data.l40=="start"), motor_20=last.motor_20, motor_60=last.motor_60, \
            water_level_40=(data.l40=="end"), water_level_20=last.water_level_20, water_level_60=last.water_level_60)
        
        if Handlers.send_sample_email(machine.name, "40cm lysimeter", machine.location):
            return jsonify({{"status":"pickup"}})
        else:
            return jsonify({"status":"error", "msg":"Failed to send email"}), 500
    
    elif hasattr(data, "l60"):
        Handlers.create_reading(machine_id=id, humidity_20=humidity_20, humidity_40=humidity_40, humidity_60=humidity_60, pressure=pressure, \
            motor_60=(data.l60=="start"), motor_40=last.motor_40, motor_20=last.motor_20, \
            water_level_60=(data.l60=="end"), water_level_40=last.water_level_40, water_level_20=last.water_level_20)
        
        if Handlers.send_sample_email(machine.name, "60cm lysimeter", machine.location):
            return jsonify({{"status":"pickup"}})
        else:
            return jsonify({"status":"error", "msg":"Failed to send email"}), 500

    elif hasattr(data, "b"):
        Handlers.create_reading(machine_id=id, humidity_20=humidity_20, humidity_40=humidity_40, humidity_60=humidity_60, pressure=pressure, \
            motor_60=(data.l60=="start"), motor_40=last.motor_40, motor_20=last.motor_20, \
            water_level_60=(data.l60=="end"), water_level_40=last.water_level_40, water_level_20=last.water_level_20)
        
        if Handlers.send_battery_email(machine.name, machine.location):
            return jsonify({{"status":"pickup"}})
        else:
            return jsonify({"status":"error", "msg":"Failed to send email"}), 500

    else:
        if hasattr(data, "init"):
            Handlers.create_reading(machine_id=id, humidity_20=humidity_20, humidity_40=humidity_40, humidity_60=humidity_60, pressure=pressure, \
                motor_20=False, motor_40=False, motor_60=False, \
                water_level_20=False, water_level_40=False, water_level_60=False)
        else:
            if last is None:
                Handlers.create_reading(machine_id=id, humidity_20=humidity_20, humidity_40=humidity_40, humidity_60=humidity_60, pressure=pressure, \
                    motor_20=False, motor_40=False, motor_60=False, \
                    water_level_20=False, water_level_40=False, water_level_60=False)

            try:
                Handlers.create_reading(machine_id=id, humidity_20=humidity_20, humidity_40=humidity_40, humidity_60=humidity_60, pressure=pressure, \
                    motor_20=last.motor_20, motor_40=last.motor_40, motor_60=last.motor_60, \
                    water_level_20=last.water_level_20, water_level_40=last.water_level_40, water_level_60=last.water_level_60)
            except:
                return jsonify({"status":"error", "msg":"Failed to set values"}), 500

        rain_time = Handlers.get_rain_time(machine.location)
        if rain_time is None:
            return jsonify({"status":"error", "msg":"Failed to fetch weather"}), 500
        else:
            return jsonify({"status":"ok", "wake":rain_time.timestamp})

    return jsonify({"status":"ok"})