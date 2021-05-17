from app.models import User, Location, Machine, Reading, Soil
from app import app, db, mail
from app.finders import Finders
import hashlib
import random
import string
import csv
from datetime import datetime, timedelta

class Handlers():

    @classmethod
    def create_user(cls, username, email):
        try:
            user = User(username=username, email=email)
            password = cls.generate_secret()
            user.set_password(password)
            user.save()
        except:
            return None, "Failed to create user"
        
        if user:
            subject="Lysimeters Portal - Registration"
            message=f'Successfully registered in <a href="https://google.pt">Lysimeters Portal</a><br><br><b>Username</b>: {user.username}<br><b>Password</b>: {password}'
            print(message)
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
        return User.update(user, **kwargs)

    @classmethod
    def delete_user(cls, user):
        return User.delete(user)

    @classmethod
    def generate_secret(cls, length=16):
        return ''.join((random.choice(string.ascii_letters) for x in range(length)))

    @classmethod
    def create_location(cls, name, latitude, longitude):
        return Location.create(name=name, latitude=latitude, longitude=longitude)

    @classmethod
    def update_location(cls, location, **kwargs):
        return Location.update(location, **kwargs)

    @classmethod
    def delete_location(cls, location):
        Location.delete(location)

    @classmethod
    def create_machine(cls, name, location_id, soil_id):
        return Machine.create(name=name, location_id=location_id, soil_id=soil_id)

    @classmethod
    def update_machine(cls, machine, **kwargs):
        return Machine.update(machine, **kwargs)

    @classmethod
    def delete_machine(cls, machine):
        return Machine.delete(machine)

    @classmethod
    def create_soil(cls, name, humidity_level):
        return Soil.create(name=name, humidity_level=humidity_level)

    @classmethod
    def update_soil(cls, soil, **kwargs):
        return Soil.update(soil, **kwargs)

    @classmethod
    def delete_soil(cls, soil):
        return Soil.delete(soil)   

    @classmethod
    def create_reading(cls, **kwargs):
        return Reading.create(**kwargs)

    @classmethod
    def delete_reading(cls, reading):
        return Reading.delete(reading)

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
        params = {"appid":app.config.OPEN_WEATHER_KEY, "exclude":"minutely,daily,current", "lat":location.latitude, "lon":location.longitude}
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

    @classmethod
    def get_machine_csv(cls, machine):
        try:
            outfile = open(app.config.CSV_FILE_PATH, 'w')
            outcsv = csv.writer(outfile)
            records = machine.readings
            outcsv.writerow([column.name for column in Reading.__mapper__.columns])
            [outcsv.writerow([getattr(curr, column.name) for column in Reading.__mapper__.columns]) for curr in records]
            return True
        except:
            return False