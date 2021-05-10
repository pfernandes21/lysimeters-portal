from app.models import User, Location, Machine, Reading
from app import db, mail, Config
from app.finders import Finders
import hashlib
import random
import string
from datetime import datetime, timedelta

class Handlers():

    @classmethod
    def create_user(cls, username, email):
        user = User(username=username, email=email)
        password = cls.generate_secret()
        user.set_password(password)

        user = create(user)
        if user:
            subject="Lysimeters Portal - Registration"
            message=f'Successfully registered in <a href="https://google.pt">Lysimeters Portal</a><br><br><b>Username</b>: {user.username}<br><b>Password</b>: {password}'

            try:
                mail.send_message(recipients=['pedrocoelhofernandes@gmail.com'], html=message, subject=subject)
                return user, None
            except:
                cls.delete_user(user)
                return None, "Failed to send registration email"
        else:
            return None, "Failed to create user"

    @classmethod
    def update_user(cls, user, **kwargs):
        return update(user, **kwargs)

    @classmethod
    def delete_user(cls, user):
        return delete(user)

    @classmethod
    def generate_secret(cls, length=16):
        return ''.join((random.choice(string.ascii_letters) for x in range(length)))

    @classmethod
    def create_location(cls, name, latitude, longitude):
        location = Location(name=name, latitude=latitude, longitude=longitude)
        return create(location)

    @classmethod
    def update_location(cls, location, **kwargs):
        return update(location, **kwargs)

    @classmethod
    def delete_location(cls, location):
        delete(location)

    @classmethod
    def create_machine(cls, name, location_id):
        machine = Machine(name=name, location_id=location_id)
        return create(machine)

    @classmethod
    def update_machine(cls, machine, **kwargs):
        return update(machine, **kwargs)

    @classmethod
    def delete_machine(cls, machine):
        return delete(machine)     

    @classmethod
    def create_reading(cls, **kwargs):
        reading = Reading(**kwargs)
        return create(reading)

    @classmethod
    def delete_reading(cls, reading):
        return delete(reading)

    @classmethod
    def check_time_hash(cls, time):
        now = datetime.now()

        for i in range(5):
            date = now + timedelta(minutes=i)
            date = date.hour + ':' + date.minute + "lisimetro"
            hash = hashlib.sha256(date.encode()).hexdigest()
            if hash[-10:] == time:
                return True
            
            date = now - timedelta(minutes=i)
            date = date.hour + ':' + date.minute + "lisimetro"
            hash = hashlib.sha256(date.encode()).hexdigest()
            if hash[-10:] == time:
                return True

        return False

    @classmethod
    def get_rain_time(cls, location):
        params = {"appid":Config.OPEN_WEATHER_KEY, "exclude":"minutely,daily,current", "lat":location.latitude, "lon":location.longitude}
        try:
            weather = requests.get("https://api.openweathermap.org/data/2.5/onecall", params=params)
            hourlyWeather = weather.json()["hourly"]
        except:
            return None

        for hour in hourlyWeather:
            if ("rain" in hour) and (hour["rain"]["1h"] > 0):
                hour_time = datetime.fromtimestamp(int(hour["dt"]))
                if hour_time > (datetime.now() + timedelta(days=3)):
                    return datetime.now().replace(hour=4, minute=0) + timedelta(days=2)
                elif hour_time > (datetime.now() + timedelta(hours=1, minutes=15)):
                    return hour_time

        final_date = datetime.fromtimestamp(int(hour["dt"]))
        if final_date > (datetime.now() + timedelta(hours=1, minutes=15)):
            return final_date

        return datetime.now().replace(hour=4, minute=0) + timedelta(days=2)

    @classmethod
    def send_sample_email(cls, machine, lysimeter, location):
        subject=f"Lysimeters Portal - Sample Collected in {location}"
        message=f"The {machine} {lysimeter} located in {location} has collected a sample at {datetime.now().strftime('%d/%m/%Y, %H:%M:%S')}."

        try:
            mail.send_message(recipients=[user.email for user in Finders.get_users()], html=message, subject=subject)
            return True
        except:
            return False

    @classmethod
    def send_battery_email(cls, machine, location):
        subject=f"Lysimeters Portal - Low battery device in {location}"
        message=f"The {machine} located in {location} is low on battery at {datetime.now().strftime('%d/%m/%Y, %H:%M:%S')}."

        try:
            mail.send_message(recipients=[user.email for user in Finders.get_users()], html=message, subject=subject)
            return True
        except:
            return False

def create(obj):
    try:
        db.session.add(obj)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return None, e
    else:
        return obj

def update(obj, **kwargs):
    try:
        db.session.query(obj.__class__).filter_by(id=obj.id).update(kwargs)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return None, e
    else:
        return obj

def delete(obj):
    try:
        db.session.delete(obj)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return False, e
    else:
        return True