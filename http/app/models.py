from app import db, login
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin


@login.user_loader
def load_user(id):
    return Users.query.get(int(id))

class ModelMixin():
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def query(cls):
        try:
            result = db.session.query(cls)
            db.session.commit()
            return result
        except:
            db.session.rollback()
            return None

    @classmethod
    def all(cls):
        try:
            result = db.session.query(cls).all()
            db.session.commit()
            return result
        except:
            db.session.rollback()
            return None

    @classmethod
    def delete_all(cls):
        try:
            db.session.query(cls).delete()
            db.session.commit()
        except:
            db.session.rollback()
        return

    @classmethod
    def first(cls):
        try:
            result = db.session.query(cls).first()
            db.session.commit()
            return result
        except:
            db.session.rollback()
            return None

    @classmethod
    def last(cls):
        try:
            result = db.session.query(cls).order_by(cls.created_at.desc()).first()
            db.session.commit()
            return result
        except:
            db.session.rollback()
            return None

    @classmethod
    def get(cls, id):
        try:
            result = cls.query.get(id)
            db.session.commit()
            return result
        except:
            db.session.rollback()
            return None

    @classmethod
    def get_by(cls, **kw):
        try:
            result = cls.query.filter_by(**kw).first()
            db.session.commit()
            return result
        except:
            db.session.rollback()
            return None

    @classmethod
    def get_or_create(cls, **kw):
        r = cls.get_by(**kw)
        if not r:
            r = cls(**kw)
            try:
                db.session.add(r)
                db.session.commit()
            except:
                db.session.rollback()
        return r

    @classmethod
    def create(cls, **kw):
        r = cls(**kw)
        try:
            db.session.add(r)
            db.session.commit()
        except:
            db.session.rollback()
            return None
        else:
            return r

    def save(self):
        try:
            db.session.add(self)
            db.session.commit()
        except:
            db.session.rollback()
        return self

    def delete(self) -> bool:
        try:
            db.session.delete(self)
            db.session.commit()
        except:
            db.session.rollback()
            return False
        else:
            return True

    def update(self, **kwargs):
        try:
            db.session.query(self.__class__).filter_by(id=self.id).update(
                kwargs)
            db.session.commit()
        except Exception as e:
            print(e)
            db.session.rollback()
            return None
        else:
            return self

class Users(db.Model, ModelMixin, UserMixin):
    __tablename__ = 'users'

    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return '<User {}>'.format(self.username)

class Locations(db.Model, ModelMixin):
    __tablename__ = 'locations'

    name = db.Column(db.String(100), index=True, unique=True)
    latitude = db.Column(db.String(20))
    longitude = db.Column(db.String(20))
    master_id = db.Column(db.Integer)
    devices = db.relationship("Devices", back_populates="location")

    def __repr__(self):
        return '<Location {}>'.format(self.name)

class Soils(db.Model, ModelMixin):
    __tablename__ = 'soils'

    name = db.Column(db.String(64), index=True, unique=True)
    humidity_level = db.Column(db.Integer)

    def __repr__(self):
        return '<Name {}, Humidity Level {}>'.format(self.name, self.humidity_level)

class Devices(db.Model, ModelMixin):
    __tablename__ = 'devices'

    name = db.Column(db.String(64), index=True, unique=True)
    status = db.Column(db.Boolean, default=True)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'))
    location = db.relationship("Locations", back_populates="devices")
    soil_20_id = db.Column(db.Integer, db.ForeignKey('soils.id'))
    soil_20 = db.relationship("Soils", foreign_keys=soil_20_id)
    soil_40_id = db.Column(db.Integer, db.ForeignKey('soils.id'))
    soil_40 = db.relationship("Soils", foreign_keys=soil_40_id)
    soil_60_id = db.Column(db.Integer, db.ForeignKey('soils.id'))
    soil_60 = db.relationship("Soils", foreign_keys=soil_60_id)
    readings = db.relationship("Readings", back_populates="device")
    updating_20 = db.Column(db.Boolean, default=False)
    updating_40 = db.Column(db.Boolean, default=False)
    updating_60 = db.Column(db.Boolean, default=False)
    sample = db.Column(db.Integer, default=0)

    def is_master(self):
        return self.id == self.location.master_id

    def __repr__(self):
        return '<Device {}, Location {}>'.format(self.id, self.location.name)

class Readings(db.Model, ModelMixin):
    __tablename__ = 'readings'

    msg_id = db.Column(db.Integer, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'))
    device = db.relationship("Devices", back_populates="readings")
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
    sample = db.Column(db.Integer)

    def __repr__(self):
        return '<Reading {}, Device {}>'.format(self.id, self.device.id)