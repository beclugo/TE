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

myDB = 'AIMV.db'
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

#Config Stream
defaultCam = cv2.VideoCapture(0)


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

def get_stream_frame():
    ok, frame = defaultCam.read()
    if not ok:
        return False, None
    # Codificar la imagen como JPG
    _, bufer = cv2.imencode(".jpg", frame)
    imagen = bufer.tobytes()
    return True, imagen

def generate_frames():
    while True:
        ok, imagen = get_stream_frame()
        if not ok:
            break
        else:
            # Regresar la imagen en modo de respuesta HTTP
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + imagen + b"\r\n"

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
    return Response(resp,headers={'Server': 'AIMV Lite/1.0'})

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
    return Response(resp,headers={'Server': 'AIMV Lite/1.0'})

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
    return Response(resp,headers={'Server': 'AIMV Lite/1.0'})

@app.route("/v1/streaming")
@login_required
def streaming_camara():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route("/v1/classify", methods=['POST'])
@login_required
def upload_image():
    filename = str(uuid.uuid4()) + ".jpg"
    ok, frame = defaultCam.read()
    if ok:
        cv2.imwrite(os.path.join(UPLOAD_FOLDER , filename), frame)
        status_pieza, accuracy = classify_img(filename)
        return jsonify({'filename': filename, 'status_pieza': status_pieza, 'accuracy':str(accuracy)})
    else:
        return jsonify({'error':'Imagen no guardada.'})

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route("/dashboard")
@login_required
def dashboard():
    resp = render_template('dashboard.html',nombre=current_user.Nombre, title='Inicio')
    return Response(resp,headers={'Server': 'AIMV Lite/1.0'})

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

    resp = render_template('profile.html', update=update,usuario=current_user, nombre=current_user.Nombre, title='Perfil')
    return Response(resp,headers={'Server': 'AIMV Lite/1.0'})

@app.route("/api_help")
@login_required
def api_help():
    resp = render_template('api_help.html', nombre=current_user.Nombre, title='Ayuda API')
    return Response(resp,headers={'Server': 'AIMV Lite/1.0'})

@app.route("/api_token", methods=["GET", "POST"])
@login_required
def api_token():
    if request.method == 'POST':
        var_cambio = usuarios.query.filter_by(Email=current_user.Email).first()
        var_cambio.Token = str(uuid.uuid4())
        db.session.commit()
    resp = render_template('api_token.html', token=current_user.Token,nombre=current_user.Nombre, title='Token API')
    return Response(resp,headers={'Server': 'AIMV Lite/1.0'})

@app.route('/favicon.ico')
def favicon():
    resp = send_from_directory(os.path.join(app.root_path), 'favicon.ico')
    resp.headers['Server'] = 'AIMV Lite/1.0' 
    return resp

if __name__ == '__main__':
    app.run(host="0.0.0.0",debug=True)