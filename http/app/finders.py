from app.models import Users, Locations, Machines, Readings, Soils

class Finders():

    @classmethod
    def get_user_from_id(cls, id):
        return Users.query.filter_by(id=id).first()

    @classmethod
    def get_user_from_username(cls, username):
        return Users.query.filter_by(username=username).first()

    @classmethod
    def get_user_from_email(cls, email):
        return Users.query.filter_by(email=email).first()

    @classmethod
    def get_users(cls):
        return Users.query.all()

    @classmethod
    def get_locations(cls):
        return Locations.query.all()

    @classmethod
    def get_location_by_id(cls, id):
        return Locations.query.filter_by(id=id).first()

    @classmethod
    def get_location_by_name(cls, name):
        return Locations.query.filter_by(name=name).first()

    @classmethod
    def get_soils(cls):
        return Soils.query.all()

    @classmethod
    def get_soil_by_id(cls, id):
        return Soils.query.filter_by(id=id).first()

    @classmethod
    def get_soil_by_name(cls, name):
        return Soils.query.filter_by(name=name).first()

    @classmethod
    def get_machine_by_id(cls, id):
        return Machines.query.filter_by(id=id).first()

    @classmethod
    def get_machine_by_name(cls, name):
        return Machines.query.filter_by(name=name).first()

    @classmethod
    def get_reading_by_msg_id(cls, msg_id):
        return Readings.query.filter_by(msg_id=msg_id).first()

    @classmethod
    def get_last_reading_from_machine_id(cls, id):
        return Readings.query.filter_by(machine_id=id).order_by(Readings.created_at.desc()).first()