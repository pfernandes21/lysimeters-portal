from app.models import User, Location, Machine, Reading, Soil

class Finders():

    @classmethod
    def get_user_from_id(cls, id):
        return User.query.filter_by(id=id).first()

    @classmethod
    def get_user_from_username(cls, username):
        return User.query.filter_by(username=username).first()

    @classmethod
    def get_user_from_email(cls, email):
        return User.query.filter_by(email=email).first()

    @classmethod
    def get_users(cls):
        return User.query.all()

    @classmethod
    def get_locations(cls):
        return Location.query.all()

    @classmethod
    def get_location_by_id(cls, id):
        return Location.query.filter_by(id=id).first()

    @classmethod
    def get_location_by_name(cls, name):
        return Location.query.filter_by(name=name).first()

    @classmethod
    def get_soils(cls):
        return Soil.query.all()

    @classmethod
    def get_soil_by_id(cls, id):
        return Soil.query.filter_by(id=id).first()

    @classmethod
    def get_soil_by_name(cls, name):
        return Soil.query.filter_by(name=name).first()

    @classmethod
    def get_machine_by_id(cls, id):
        return Machine.query.filter_by(id=id).first()

    @classmethod
    def get_machine_by_name(cls, name):
        return Machine.query.filter_by(name=name).first()

    @classmethod
    def get_last_reading_from_machine_id(cls, id):
        return Reading.query.filter_by(machine_id=id).order_by(Reading.created_at.desc()).first()