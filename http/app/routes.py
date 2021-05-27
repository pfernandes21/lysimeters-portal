from flask import render_template, flash, redirect, url_for, request, jsonify, send_file, abort
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.urls import url_parse
from app import app, csrf
from app.forms import LoginForm, DeviceForm, LocationForm, UserForm, SoilForm
from app.finders import Finders
from app.handlers import Handlers
from app.values import LocationsValue, LocationValue, DeviceValue
import json
from types import SimpleNamespace
from datetime import datetime, timedelta

@app.route("/health")
def health():
    return "alive"

@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

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

@app.route("/location/<int:location_id>/devices", methods=["GET"])
@login_required
def location(location_id):
    location = Finders.get_location_by_id(location_id)
    if location is None:
        flash("Cant find location")
        return redirect(url_for("locations"))

    return render_template("location.html", title=location.name, location=location)

@app.route("/soils", methods=["GET"])
@login_required
def soils():
    soils = Finders.get_soils()
    return render_template("soils.html", title="Soils", soils=soils)

@app.route("/soil", methods=["GET", "POST"])
@login_required
def create_soil():
    form = SoilForm()
    if form.validate_on_submit():
        name = form.name.data
        humidity_level = form.humidity_level.data
        if Finders.get_soil_by_name(name):
            flash("Soil already exists")
            return render_template("create_form.html", title="Create Soil", form=form)
    
        if Handlers.create_soil(name, humidity_level) is None:
            flash("Failed to create soil")
            return render_template("create_form.html", title="Create Soil", form=form)

        return redirect(url_for("soils"))

    return render_template("create_form.html", title="Create Soil", form=form)

@app.route("/soil/<string:soil_id>/delete", methods=["POST"])
@login_required
def delete_soil(soil_id):
    soil = Finders.get_soil_by_id(soil_id)
    if soil is None:
        flash("Cant find soil")
        return redirect(url_for("soils"))

    if not Handlers.delete_soil(soil):
        flash("Failed to delete soil")
        
    return redirect(url_for("soils"))

@app.route("/device", methods=["GET", "POST"])
@login_required
def create_device():
    location_id = request.args.get("location_id", None)

    if request.method == "GET":
        form = DeviceForm(location_id=location_id)
    elif request.method == "POST":
        form = DeviceForm()

    if form.validate_on_submit():
        location_id = form.location_id.data
        location = Finders.get_location_by_id(location_id)
        if not location:
            flash("Location not found")
            return redirect(url_for("locations"))

        name = form.name.data
        if Finders.get_device_by_name(name):
            flash("Device already exists")
            return redirect(url_for("locations"))

        device = Handlers.create_device(name, location_id, form.soil_20_id.data, form.soil_40_id.data, form.soil_60_id.data)
        if device is None:
            form.location_id = location_id
            flash("Failed to create device")
            return render_template("create_form.html", title="Create Device", form=form)

        if form.master.data:
            Handlers.update_location(location, master_id=device.id)

        return redirect(url_for("location", location_id=location_id))

    return render_template("create_form.html", title="Create Device", form=form)

@app.route("/device/<string:device_id>/edit", methods=["GET", "POST"])
@login_required
def edit_device(device_id):
    device = Finders.get_device_by_id(device_id)
    if device is None:
        flash("Cant find device")
        return redirect(url_for("locations"))

    if request.method == "GET":
        form = DeviceForm(location_id=device.location_id, name=device.name, soil_20_id=device.soil_20_id, soil_40_id=device.soil_40_id, soil_60_id=device.soil_60_id, master=device.is_master())
    elif request.method == "POST":
        form = DeviceForm()

    if form.validate_on_submit():
        device = Handlers.update_device(device, name=form.name.data, location_id=form.location_id.data, \
                                soil_20_id=form.soil_20_id.data, soil_40_id=form.soil_40_id.data, soil_60_id=form.soil_60_id.data, \
                                updating_20=int(form.soil_20_id.data)!=device.soil_20_id or device.updating_20, \
                                updating_40=int(form.soil_40_id.data)!=device.soil_40_id or device.updating_40, \
                                updating_60=int(form.soil_60_id.data)!=device.soil_60_id or device.updating_60)
        return redirect(url_for("location", location_id=device.location_id))

    return render_template("create_form.html", title="Edit Device", form=form)

@app.route("/device/<string:device_id>/delete", methods=["POST"])
@login_required
def delete_device(device_id):
    device = Finders.get_device_by_id(device_id)
    if device is None:
        flash("Cant find device")
        return redirect(url_for("locations"))

    location_id = device.location_id
    if not Handlers.delete_device(device):
        flash("Failed to delete device")
        
    return redirect(url_for("location", location_id=location_id))

@app.route("/device/<int:device_id>", methods=["GET"])
@login_required
def device(device_id):
    device = Finders.get_device_by_id(device_id)
    if device is None:
        flash("Cant find device")
        return redirect(url_for("locations"))

    return render_template("device.html", title=device.name, device=device)

@app.route("/device/<int:device_id>/csv", methods=["GET"])
@login_required
def device_csv(device_id):
    device = Finders.get_device_by_id(device_id)
    if device is None:
        flash("Cant find device")
        return redirect(url_for("locations"))

    if not Handlers.get_device_csv(device):
        abort(500)

    try:
        return send_file(app.config.CSV_FILE_PATH, as_attachment=True)
    except FileNotFoundError:
        abort(404)

@app.route("/vitality-check", methods=["POST"])
@csrf.exempt
@login_required
def vitality_check():
    inactive_devices = []
    for device in Finders.get_active_devices():
        last_reading = Finders.get_device_last_reading(device)
        if last_reading is not None and last_reading.created_at < datetime.now() - timedelta(days=3):
            Handlers.update_device(device, status=False)
            inactive_devices.append(device)

    if len(inactive_devices) > 0:
        if not Handlers.send_inactive_devices_email(inactive_devices):
            for device in inactive_devices:
                Handlers.update_device(device, status=True)
            return jsonify("Failed"), 500
    
    return jsonify("Success")

@app.route("/api/locations", methods=["GET"])
@csrf.exempt
@login_required
def locations_api():
    locations = Finders.get_locations()
    return LocationsValue(locations).json()

@app.route("/api/location/<int:location_id>", methods=["GET"])
@csrf.exempt
@login_required
def location_api(location_id):
    location = Finders.get_location_by_id(location_id)
    return LocationValue(location).json()

@app.route("/api/device/<int:device_id>", methods=["GET"])
@csrf.exempt
@login_required
def device_api(device_id):
    device = Finders.get_device_by_id(device_id)
    return DeviceValue(device).json()

@app.route("/api/reading", methods=["POST"])
@csrf.exempt
def reading():
    api_key = request.headers.get("Authorization", None)
    if api_key is None or api_key != "Bearer " + app.config['MACHINE_API_TOKEN']:
        return jsonify({"status":"error"}), 401

    try:
        data = request.get_json()["data"]
        data = json.loads(data, object_hook=lambda d: SimpleNamespace(**d))
    except Exception as e:
        return jsonify({"status":"error"}), 500    

    try:
        id = data.id
        msg_id = data.msg
    except AttributeError:
        return jsonify({"status":"error"}), 500

    # if not Handlers.check_time_hash(time.lower()):
    #     return jsonify({"status":"error"}), 401

    if Finders.get_reading_by_msg_id(msg_id):
        return jsonify({"status":"ack"}) 

    device = Finders.get_device_by_id(id)
    if not device:
        return jsonify({"status":"error"}), 404

    if not device.status:
        Handlers.update_device(device, status=True)

    last = Finders.get_last_reading_from_device_id(id)

    humidity_20 = getattr(data, "h20", None)
    humidity_40 = getattr(data, "h40", None)
    humidity_60 = getattr(data, "h60", None)
    pressure = getattr(data, "p", None)

    if None in [humidity_20, humidity_40, humidity_60, pressure]:
        return jsonify({"status":"error"}), 500

    if hasattr(data, "l20"):
        Handlers.create_reading(msg_id=msg_id, device_id=id, humidity_20=humidity_20, humidity_40=humidity_40, humidity_60=humidity_60, pressure=pressure, \
            motor_20=(data.l20=="start"), motor_40=last.motor_40, motor_60=last.motor_60, \
            water_level_20=(data.l20=="end"), water_level_40=last.water_level_40, water_level_60=last.water_level_60)
        
        if data.l20=="start" and Handlers.send_sample_start_email(device.name, "20cm lysimeter", device.location):
            return jsonify({"status":"pickup"})
        elif data.l20=="end" and Handlers.send_sample_end_email(device.name, "20cm lysimeter", device.location):
            return jsonify({"status":"pickup"})
        elif data.l20=="error" and Handlers.send_sample_error_email(device.name, "20cm lysimeter", device.location):
            return jsonify({"status":"pickup"})
        else:
            return jsonify({"status":"error"}), 500

    elif hasattr(data, "l40"):
        Handlers.create_reading(msg_id=msg_id, device_id=id, humidity_20=humidity_20, humidity_40=humidity_40, humidity_60=humidity_60, pressure=pressure, \
            motor_40=(data.l40=="start"), motor_20=last.motor_20, motor_60=last.motor_60, \
            water_level_40=(data.l40=="end"), water_level_20=last.water_level_20, water_level_60=last.water_level_60)
        
        if data.l40=="start" and Handlers.send_sample_start_email(device.name, "40cm lysimeter", device.location):
            return jsonify({"status":"pickup"})
        elif data.l40=="end" and Handlers.send_sample_end_email(device.name, "40cm lysimeter", device.location):
            return jsonify({"status":"pickup"})
        elif data.l40=="error" and Handlers.send_sample_error_email(device.name, "40cm lysimeter", device.location):
            return jsonify({"status":"pickup"})
        else:
            return jsonify({"status":"error"}), 500
    
    elif hasattr(data, "l60"):
        Handlers.create_reading(msg_id=msg_id, device_id=id, humidity_20=humidity_20, humidity_40=humidity_40, humidity_60=humidity_60, pressure=pressure, \
            motor_60=(data.l60=="start"), motor_40=last.motor_40, motor_20=last.motor_20, \
            water_level_60=(data.l60=="end"), water_level_40=last.water_level_40, water_level_20=last.water_level_20)
        
        if data.l60=="start" and Handlers.send_sample_start_email(device.name, "60cm lysimeter", device.location):
            return jsonify({"status":"pickup"})
        elif data.l60=="end" and Handlers.send_sample_end_email(device.name, "60cm lysimeter", device.location):
            return jsonify({"status":"pickup"})
        elif data.l60=="error" and Handlers.send_sample_error_email(device.name, "60cm lysimeter", device.location):
            return jsonify({"status":"pickup"})
        else:
            return jsonify({"status":"error"}), 500

    elif hasattr(data, "b"):
        Handlers.create_reading(msg_id=msg_id, device_id=id, humidity_20=humidity_20, humidity_40=humidity_40, humidity_60=humidity_60, pressure=pressure, \
            motor_20=last.motor_20, motor_40=last.motor_40, motor_60=last.motor_60, \
            water_level_20=last.water_level_20, water_level_40=last.water_level_40, water_level_60=last.water_level_60)

        if Handlers.send_battery_email(device.name, device.location):
            return jsonify({"status":"pickup"})
        else:
            return jsonify({"status":"error"}), 500

    else:
        if hasattr(data, "init"):
            Handlers.create_reading(msg_id=msg_id, device_id=id, humidity_20=humidity_20, humidity_40=humidity_40, humidity_60=humidity_60, pressure=pressure, \
                motor_20=False, motor_40=False, motor_60=False, \
                water_level_20=False, water_level_40=False, water_level_60=False)
        else:
            if last is None:
                Handlers.create_reading(msg_id=msg_id, device_id=id, humidity_20=humidity_20, humidity_40=humidity_40, humidity_60=humidity_60, pressure=pressure, \
                    motor_20=False, motor_40=False, motor_60=False, \
                    water_level_20=False, water_level_40=False, water_level_60=False)

            try:
                Handlers.create_reading(msg_id=msg_id, device_id=id, humidity_20=humidity_20, humidity_40=humidity_40, humidity_60=humidity_60, pressure=pressure, \
                    motor_20=last.motor_20, motor_40=last.motor_40, motor_60=last.motor_60, \
                    water_level_20=last.water_level_20, water_level_40=last.water_level_40, water_level_60=last.water_level_60)
            except:
                return jsonify({"status":"error"}), 500

        if hasattr(data, "config20"):
            Handlers.update_device(device, updating_20=False)
        elif hasattr(data, "config40"):
            Handlers.update_device(device, updating_40=False) 
        elif hasattr(data, "config60"):
            Handlers.update_device(device, updating_60=False) 
        elif device.updating_20:
            return jsonify({"status":"config20", "level":device.soil_20.humidity_level})
        elif device.updating_40:
            return jsonify({"status":"config40", "level":device.soil_40.humidity_level})
        elif device.updating_60:
            return jsonify({"status":"config60", "level":device.soil_60.humidity_level})

        rain_time = Handlers.get_rain_time(device.location)
        if rain_time is None:
            return jsonify({"status":"error"}), 500
        else:
            #return jsonify({"status":"ok", "wake":int(rain_time.timestamp())})
            return jsonify({"status":"ok", "wake":int(datetime.now().timestamp()) + 90})