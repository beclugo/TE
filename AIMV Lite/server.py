# -*- coding: utf-8 -*-
from tensorflow.keras.preprocessing.image import img_to_array
from tensorflow.keras.models import load_model
import numpy as np
import cv2

import os
import flask
from flask import Flask, Response, flash, request, url_for,redirect, jsonify, send_from_directory, render_template
from flask_sqlalchemy import SQLAlchemy
from forms import SignupForm, LoginForm, ActualizarDatos, addLoc, editLoc, addSensor, editSensor
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from werkzeug.datastructures import  FileStorage
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import uuid
from functools import wraps

myDB = 'db_redes.db'
db_path = os.path.join(os.path.dirname(__file__), myDB)
db_uri = 'sqlite:///{}'.format(db_path)

app = Flask(__name__, static_url_path='', static_folder='static')
UPLOAD_FOLDER = 'static/uploads/'
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])
app.config['SECRET_KEY'] = 'E4B73EACAD9842E9'
app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class locaciones(db.Model):
    ID = db.Column(db.Integer, primary_key=True)
    Nombre = db.Column(db.String)

class arduino_names(db.Model):
    ID = db.Column(db.Integer, primary_key=True)
    Nombre = db.Column(db.String)
    ID_Location = db.Column(db.Integer)

class valores(db.Model):
    ID = db.Column(db.Integer, primary_key=True)
    ID_Name = db.Column(db.Integer)
    ID_Location = db.Column(db.Integer)
    calidad_aire = db.Column(db.String)
    fecha = db.Column(db.String)

class usuarios(UserMixin, db.Model):
    ID = db.Column(db.Integer, primary_key=True)
    Nombre = db.Column(db.String)
    Email = db.Column(db.String, unique=True)
    Password = db.Column(db.String)
    Token = db.Column(db.String)
    def get_id(self):
        return (self.ID)
def token_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        token = None

        if 'x-access-tokens' in request.headers:
            token = request.headers['x-access-tokens']

        if not token:
            return jsonify({'message': 'Falta el parametro token'})

        api_user = usuarios.query.filter_by(Token=token).first()
        if api_user == None:
            return jsonify({'message': 'Token invalida'})

        return f(api_user, *args, **kwargs)
    return decorator
@login_manager.user_loader
def load_user(user_id):
    return usuarios.query.get(int(user_id))

def is_directory_traversal(file_name):
    current_directory = os.path.abspath(os.curdir)
    requested_path = os.path.relpath(file_name, start=current_directory)
    requested_path = os.path.abspath(requested_path)
    common_prefix = os.path.commonprefix([requested_path, current_directory])
    return common_prefix != current_directory
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def last_alerts():
    list_alert = []
    for i in range(1,4):
        try:
            obj = valores.query.order_by(valores.ID)[-i]
            list_alert.append(obj)
        except:
            break
    return list_alert

def classify_img(img):
    IMG_SIZE = 100

    print("[INFO] loading network...")
    model = load_model('te_cnn_model_v2')

    image = cv2.imread(os.path.join(UPLOAD_FOLDER,img), cv2.IMREAD_GRAYSCALE)
    image = cv2.resize(image, (IMG_SIZE, IMG_SIZE))
    image = np.array(image).reshape(-1, IMG_SIZE, IMG_SIZE, 1)
    image = image / 255
    accuracy = 0
    proba = model.predict(image)[0]
    label = np.where(proba > .5, 1,0)
    classification = "OK!" if label == 1 else "DEFECTO"
    if label == 1:
        accuracy = proba * 100
    else:
        accuracy = (1-proba) * 100
    return classification, accuracy[0]

def sensors_list():
    sensors_list = []
    objs = arduino_names.query.all()
    for obj in objs:
        obj_loc = locaciones.query.filter_by(ID=obj.ID_Location).first()
        new_obj  = {'ID':obj.ID, 'Nombre':obj.Nombre, 'Locacion':obj_loc.Nombre}
        sensors_list.append(new_obj)
    return sensors_list

def loc_list():
    loc_lista = []
    objs = locaciones.query.all()
    for obj in objs:
        loc_lista.append(obj)
    return loc_lista


def data_list():
    data_lista = []
    objs = valores.query.all()
    for obj in objs:
        obj_med = [0,0,0]
        obj_sensor = arduino_names.query.filter_by(ID=obj.ID_Name).first()
        obj_loc = locaciones.query.filter_by(ID=obj_sensor.ID_Location).first()
        try:
            obj_med = obj.calidad_aire.split(",")
        except:
            pass
        new_obj = {'ID':obj.ID, 'Sensor':obj_sensor.Nombre, 'Locacion':obj_loc.Nombre, 'TVOC':obj_med[0],'eCO2':obj_med[1],'RawH2':obj_med[2],'Fecha':obj.fecha}
        data_lista.append(new_obj)
    return data_lista


@app.errorhandler(404)
def page_not_found(e):
    return redirect('/')

@app.route("/", methods=["GET", "POST"])
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = SignupForm()
    form2 = LoginForm()
    resp = render_template('index.html', form=form, form2=form2)
    return Response(resp,headers={'Server': 'Redes/1.0'})
@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = SignupForm()
    form2 = LoginForm()
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        password = form.password.data
        password = generate_password_hash(password, method='sha256')
        nuevo_usuario = usuarios(Nombre=name, Email=email, Password=password, Token=str(uuid.uuid4()))
        db.session.add(nuevo_usuario)
        db.session.commit()
        next = request.args.get('next', None)
        if next:
            return redirect(next)
        login_user(nuevo_usuario, remember=True)
        return redirect(url_for('dashboard'))
    resp = render_template('index.html', form=form, form2=form2)
    return Response(resp,headers={'Server': 'Redes/1.0'})

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = SignupForm()
    form2 = LoginForm()
    if form2.validate_on_submit():
        email = form.email.data
        password = form.password.data
        usuario = usuarios.query.filter_by(Email=email).first()
        if usuario:
            if check_password_hash(usuario.Password, password):
                login_user(usuario, remember=True)
                return redirect(url_for('dashboard'))
        return '<h1>Correo o contraseña invalidos</h1>'
    resp = render_template('index.html', form=form, form2=form2)
    return Response(resp,headers={'Server': 'Redes/1.0'})

@app.route('/display/<filename>')
def display_image(filename):
    return redirect(url_for('static', filename='uploads/' + filename), code=301)

@app.route("/subir_imagen", methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        flash('No file part')
        return None
    file = request.files['file']
    if file.filename == '':
        flash('No image selected for uploading')
        return None
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        #print('upload_image filename: ' + filename)
        flash('Image successfully uploaded and displayed below')
        status_pieza, accuracy = classify_img(filename)
        return jsonify({'filename': filename, 'status_pieza': status_pieza, 'accuracy':str(accuracy)})
    else:
        flash('Allowed image types are - png, jpg, jpeg, gif')
        return None

@app.route("/API/insertar_datos", methods=['POST'])
@token_required
def insertar_datos(api_user):
    raw_json = flask.request.json
    json_data = raw_json["Medidas"]
    if json_data != None:
        try:
            for json in json_data:
                id_name = json["ID_Name"]
                id_location = json["ID_Locacion"]
                calidad_aire = json["Calidad Aire"]
                fecha = json["Fecha"]
                nuevos_valores  = valores(ID_Name=id_name,ID_Location=id_location,calidad_aire=calidad_aire,fecha=fecha)
                db.session.add(nuevos_valores)
                db.session.commit()
            return jsonify({'message': 'Se guardaron con exito los datos.'})
        except:
            return jsonify({'message': 'Se detecto un error.'})
    else:
        resp = redirect("/")
        resp.headers['Server'] = 'Redes/1.0' 
        return resp

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route("/dashboard")
@login_required
def dashboard():
    resp = render_template('dashboard.html',nombre=current_user.Nombre, title='Inicio', alertas=last_alerts())
    return Response(resp,headers={'Server': 'Redes/1.0'})

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    update = ActualizarDatos()
    if update.validate_on_submit():
        if update.name.data != '':
            var_cambio = usuarios.query.filter_by(Email=current_user.Email).first()
            var_cambio.Nombre = update.name.data
            db.session.commit()
        return redirect(url_for('profile'))

    resp = render_template('profile.html', update=update,usuario=current_user, nombre=current_user.Nombre, title='Perfil', alertas=last_alerts())
    return Response(resp,headers={'Server': 'Redes/1.0'})

@app.route("/locations", methods=["GET", "POST"])
@login_required
def locations():
    form_add =  addLoc()
    form_edit = editLoc()
    if request.method == 'POST':
        form_name = request.form['form-name']
        if form_name == 'add_location':
            if form_add.validate():
                nueva_loc = locaciones(Nombre=form_add.name.data)
                db.session.add(nueva_loc)
                db.session.commit()
            return redirect(url_for('locations'))
        if form_name == 'edit_location':
            if form_edit.validate():
                loc_id = request.form['loc-id']
                var_cambio = locaciones.query.filter_by(ID=loc_id).first()
                var_cambio.Nombre = form_edit.name.data
                db.session.commit()
            return redirect(url_for('locations'))
    resp = render_template('locations.html', form_edit=form_edit, form_add=form_add, locaciones=loc_list(), nombre=current_user.Nombre, title='Locaciones', alertas=last_alerts())
    return Response(resp,headers={'Server': 'Redes/1.0'})

@app.route("/sensors", methods=["GET", "POST"])
@login_required
def sensors():
    form_add =  addSensor()
    form_edit = editSensor()
    if request.method == 'POST':
        form_name = request.form['form-name']
        if form_name == 'add_sensor':
            if form_add.validate():
                nueva_loc = arduino_names(Nombre=form_add.name.data,ID_Location=request.form['loc-id-add'])
                db.session.add(nueva_loc)
                db.session.commit()
            return redirect(url_for('sensors'))
        if form_name == 'edit_sensor':
            if form_edit.validate():
                sensor_id = request.form['sensor-id']
                var_cambio = arduino_names.query.filter_by(ID=sensor_id).first()
                var_cambio.Nombre = form_edit.name.data
                var_cambio.ID_Location = request.form['loc-id-edit']
                db.session.commit()
            return redirect(url_for('sensors'))
    resp = render_template('sensors.html', form_add=form_add, form_edit=form_edit, locaciones=loc_list(),sensores=sensors_list(),nombre=current_user.Nombre, title='Sensores', alertas=last_alerts())
    return Response(resp,headers={'Server': 'Redes/1.0'})

@app.route("/api_help")
@login_required
def api_help():
    resp = render_template('api_help.html', nombre=current_user.Nombre, title='Ayuda API', alertas=last_alerts())
    return Response(resp,headers={'Server': 'Redes/1.0'})

@app.route("/api_token", methods=["GET", "POST"])
@login_required
def api_token():
    if request.method == 'POST':
        var_cambio = usuarios.query.filter_by(Email=current_user.Email).first()
        var_cambio.Token = str(uuid.uuid4())
        db.session.commit()
    resp = render_template('api_token.html', token=current_user.Token,nombre=current_user.Nombre, title='Token API', alertas=last_alerts())
    return Response(resp,headers={'Server': 'Redes/1.0'})

@app.route("/alldata")
@login_required
def alldata():
    resp = render_template('alldata.html', datos=data_list(),nombre=current_user.Nombre, title='Mediciones', alertas=last_alerts())
    return Response(resp,headers={'Server': 'Redes/1.0'})

@app.route('/favicon.ico')
def favicon():
    resp = send_from_directory(os.path.join(app.root_path), 'favicon.ico')
    resp.headers['Server'] = 'Redes/1.0' 
    return resp

if __name__ == '__main__':
    app.run(host="0.0.0.0",debug=True)