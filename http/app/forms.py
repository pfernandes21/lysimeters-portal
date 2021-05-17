from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, HiddenField, IntegerField, SelectField
from wtforms.fields.html5 import EmailField
from wtforms.validators import DataRequired
from app.finders import Finders

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class UserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = EmailField('Email', validators=[DataRequired()])
    submit = SubmitField('Add User')

class LocationForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    latitude = StringField('Latitude', validators=[DataRequired()])
    longitude = StringField('Longitude', validators=[DataRequired()])
    submit = SubmitField('Add Location')

class MachineForm(FlaskForm):
    location_id = HiddenField()
    name = StringField('Name', validators=[DataRequired()])
    soil_id = SelectField('Soil', choices=[(soil.id,soil.name) for soil in Finders.get_soils()])
    master = BooleanField('Master')
    submit = SubmitField('Add Machine')

class SoilForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    humidity_level = IntegerField('Humidity Level', validators=[DataRequired()])
    submit = SubmitField('Add Soil')