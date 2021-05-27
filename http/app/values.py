from flask import make_response, jsonify


class ValueComposite(object):
    message = None

    def initialize(self, initial_message):
        self.message = initial_message

    def serialize_with(self, **entry):
        self.message.update(entry)

    def to_dict(self):
        return dict(self.message)

    def json(self, code=200):
        return make_response(jsonify(self.message), code)

class ReadingsValue(ValueComposite):
	def __init__(self, readings):
		super(ReadingsValue, self).initialize({})
		readings_array = []
		for reading in readings:
			reading_value = {
                "id": reading.id,
				"created_at": reading.created_at,
                "motor_20": reading.motor_20,
                "motor_40": reading.motor_40,
                "motor_60": reading.motor_60,
                "humidity_20": reading.humidity_20,
                "humidity_40": reading.humidity_40,
                "humidity_60": reading.humidity_60,
                "pressure": reading.pressure,
                "water_level_20": reading.water_level_20,
                "water_level_40": reading.water_level_40,
                "water_level_60": reading.water_level_60,
			}
			readings_array.append(reading_value)
		self.serialize_with(data=readings_array)

class LocationValue(ValueComposite):
    def __init__(self, location):
        super(LocationValue, self).initialize({})
        self.serialize_with(id=location.id)
        self.serialize_with(name=location.name)
        self.serialize_with(status=location.status)
        self.serialize_with(latitude=location.latitude)
        self.serialize_with(longitude=location.longitude)
        self.serialize_with(machines=MachinesValue(location.machines).to_dict())

class LocationsValue(ValueComposite):
    def __init__(self, locations):
        super(LocationsValue, self).initialize({})
        locations_array = []
        for location in locations:
            location_value = {
                "id": location.id,
				"name": location.name,
                "status": location.status,
                "latitude": location.latitude,
                "longitude": location.longitude,
                "machines": MachinesValue(location.machines).to_dict()
            }
            locations_array.append(location_value)
        self.serialize_with(data=locations_array)

class SoilValue(ValueComposite):
    def __init__(self, soil):
        super(SoilValue, self).initialize({})
        self.serialize_with(name=soil.name)
        self.serialize_with(humidity_level=soil.humidity_level)

class MachineValue(ValueComposite):
    def __init__(self, machine):
        super(MachineValue, self).initialize({})
        self.serialize_with(id=machine.id)
        self.serialize_with(name=machine.name)
        self.serialize_with(master=machine.is_master())
        self.serialize_with(soil_20=SoilValue(machine.soil_20).to_dict())
        self.serialize_with(soil_40=SoilValue(machine.soil_40).to_dict())
        self.serialize_with(soil_60=SoilValue(machine.soil_60).to_dict())
        self.serialize_with(readings=ReadingsValue(machine.readings).to_dict())

class MachinesValue(ValueComposite):
    def __init__(self, machines):
        super(MachinesValue, self).initialize({})
        machines_array = []
        for machine in machines:
            machine_value = {
                "id": machine.id,
				"name": machine.name,
                "master": machine.is_master(),
                "soil_20": SoilValue(machine.soil_20).to_dict(),
                "soil_40": SoilValue(machine.soil_40).to_dict(),
                "soil_60": SoilValue(machine.soil_60).to_dict(),
                "readings": ReadingsValue(machine.readings).to_dict()
            }
            machines_array.append(machine_value)
        self.serialize_with(data=machines_array)