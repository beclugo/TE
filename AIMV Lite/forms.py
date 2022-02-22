from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired, Email, Length

class SignupForm(FlaskForm):
    name = StringField('Nombre', validators=[DataRequired(), Length(max=64)])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Registrar')
class LoginForm(FlaskForm):
    password = PasswordField('Contraseña', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Entrar')

class ActualizarDatos(FlaskForm):
    name = StringField('Nombre:', validators=[Length(max=64)])
    submit = SubmitField('Actualizar')

class addLoc(FlaskForm):
    name = StringField('Nombre:', validators=[DataRequired(), Length(max=64)])
    submit = SubmitField('Añadir')

class editLoc(FlaskForm):
    name = StringField('Nuevo Nombre:', validators=[DataRequired(), Length(max=64)])
    submit = SubmitField('Modificar')

class addSensor(FlaskForm):
    name = StringField('Nombre:', validators=[DataRequired(), Length(max=64)])
    submit = SubmitField('Añadir')

class editSensor(FlaskForm):
    name = StringField('Nuevo Nombre:', validators=[DataRequired(), Length(max=64)])
    submit = SubmitField('Modificar')


