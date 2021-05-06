from app import db, login
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin


@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return '<User {}>'.format(self.username)

class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), index=True, unique=True)
    status = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    latitude = db.Column(db.String(20))
    longitude = db.Column(db.String(20))
    master_id = db.Column(db.Integer)
    machines = db.relationship("Machine", back_populates="location")

    def __repr__(self):
        return '<Location {}>'.format(self.name)

class Machine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True, unique=True)
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'))
    location = db.relationship("Location", back_populates="machines")
    readings = db.relationship("Reading", back_populates="machine")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def is_master(self):
        return self.id == self.location.master_id

    def __repr__(self):
        return '<Machine {}, Location {}>'.format(self.id, self.location.name)

class Reading(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    machine_id = db.Column(db.Integer, db.ForeignKey('machine.id'))
    machine = db.relationship("Machine", back_populates="readings")
    motor_20 = db.Column(db.Boolean, default=False)
    motor_40 = db.Column(db.Boolean, default=False)
    motor_60 = db.Column(db.Boolean, default=False)
    humidity_20 = db.Column(db.Float)
    humidity_40 = db.Column(db.Float)
    humidity_60 = db.Column(db.Float)
    pressure = db.Column(db.Float)
    water_level_20 = db.Column(db.Boolean, default=False)
    water_level_40 = db.Column(db.Boolean, default=False)
    water_level_60 = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return '<Reading {}, Machine {}>'.format(self.id, self.machine.id)