from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'secreto123'

# PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:brainer1@localhost:5432/tareas_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# MODELOS
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    contrasena = db.Column(db.String(200), nullable=False)
    tareas = db.relationship('Tarea', backref='usuario', lazy=True)

class Tarea(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    completado = db.Column(db.Boolean, default=False)
    vencimiento = db.Column(db.String(20))
    categoria = db.Column(db.String(50))
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)

# RUTAS
@app.route('/')
def home():
    usuario_id = session.get('usuario_id')
    if usuario_id:
        usuario = Usuario.query.get(usuario_id)
        return render_template('index.html', nombre=usuario.nombre)
    return redirect(url_for('login'))

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        contrasena = generate_password_hash(request.form['contrasena'])
        if Usuario.query.filter((Usuario.nombre == nombre) | (Usuario.email == email)).first():
            session['error'] = 'Ese usuario o correo ya existe.'
            return redirect(url_for('registro'))

        nuevo_usuario = Usuario(nombre=nombre, email=email, contrasena=contrasena)
        db.session.add(nuevo_usuario)
        db.session.commit()
        session['mensaje'] = 'Cuenta creada exitosamente. Ahora inicia sesión.'
        return redirect(url_for('login'))
    return render_template('registro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nombre = request.form['nombre']
        contrasena = request.form['password']
        usuario = Usuario.query.filter_by(nombre=nombre).first()
        if usuario and check_password_hash(usuario.contrasena, contrasena):
            session.permanent = True
            session['usuario_id'] = usuario.id
            return redirect(url_for('home'))
        else:
            session['error'] = 'Credenciales inválidas'
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/recuperar', methods=['GET', 'POST'])
def recuperar():
    if request.method == 'POST':
        email = request.form.get('email')
        usuario = Usuario.query.filter_by(email=email).first()
        if usuario:
            session['recuperar_id'] = usuario.id
            return redirect(url_for('nueva_contrasena'))
        else:
            session['error'] = 'Correo no encontrado'
            return redirect(url_for('recuperar'))
    return render_template('recuperar.html')

@app.route('/nueva-contrasena', methods=['GET', 'POST'])
def nueva_contrasena():
    usuario_id = session.get('recuperar_id')
    if not usuario_id:
        session['error'] = 'Sesión de recuperación expirada'
        return redirect(url_for('recuperar'))

    usuario = Usuario.query.get(usuario_id)

    if request.method == 'POST':
        nueva_pass = request.form.get('password')
        if not nueva_pass:
            session['error'] = 'Falta la nueva contraseña'
            return render_template('nueva_contrasena.html', nombre=usuario.nombre)

        usuario.contrasena = generate_password_hash(nueva_pass)
        db.session.commit()
        session.pop('recuperar_id', None)
        session['mensaje'] = 'Contraseña actualizada exitosamente'
        return redirect(url_for('login'))

    return render_template('nueva_contrasena.html', nombre=usuario.nombre)

@app.route('/api/tareas', methods=['GET', 'POST'])
def tareas():
    if 'usuario_id' not in session:
        return jsonify({'error': 'No autenticado'}), 401

    if request.method == 'POST':
        data = request.get_json()
        nueva_tarea = Tarea(
            titulo=data['titulo'],
            completado=False,
            vencimiento=data.get('vencimiento', ''),
            categoria=data.get('categoria', 'Otro'),
            usuario_id=session['usuario_id']
        )
        db.session.add(nueva_tarea)
        db.session.commit()
        return jsonify({'mensaje': 'Tarea agregada'})

    tareas = Tarea.query.filter_by(usuario_id=session['usuario_id']).all()
    return jsonify([{
        'id': t.id,
        'titulo': t.titulo,
        'completado': t.completado,
        'vencimiento': t.vencimiento,
        'categoria': t.categoria
    } for t in tareas])

@app.route('/api/tareas/<int:id>', methods=['PATCH', 'DELETE'])
def manejar_tarea(id):
    tarea = Tarea.query.get_or_404(id)
    if tarea.usuario_id != session.get('usuario_id'):
        return jsonify({'error': 'No autorizado'}), 403

    if request.method == 'PATCH':
        tarea.completado = not tarea.completado
        db.session.commit()
        return jsonify({'mensaje': 'Tarea actualizada'})

    if request.method == 'DELETE':
        db.session.delete(tarea)
        db.session.commit()
        return jsonify({'mensaje': 'Tarea eliminada'})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
