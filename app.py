"""Aplicación académica de soporte técnico. Consulte README.md antes de iniciar."""
import os
from datetime import datetime, timezone
from pathlib import Path

import click
from dotenv import load_dotenv
from flask import Flask, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect, FlaskForm
from flask_wtf.csrf import CSRFError
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from wtforms import StringField, TextAreaField
from wtforms.validators import DataRequired, Length

# No sobrescribe las variables suministradas por Render.
load_dotenv(Path(__file__).with_name('.env'), override=False)
db = SQLAlchemy()
csrf = CSRFProtect()


class Solicitud(db.Model):
    __tablename__ = 'solicitudes'
    id = db.Column(db.Integer, primary_key=True)
    solicitante = db.Column(db.String(120), nullable=False)
    equipo = db.Column(db.String(40), nullable=False)
    descripcion = db.Column(db.String(2000), nullable=False)
    estado = db.Column(db.String(12), nullable=False, default='Pendiente')
    creada_en = db.Column(db.DateTime(timezone=True), nullable=False,
                          default=lambda: datetime.now(timezone.utc))
    __table_args__ = (db.CheckConstraint(
        "estado IN ('Pendiente', 'Resuelta')", name='ck_solicitud_estado'),)


def limpiar(valor):
    return valor.strip() if isinstance(valor, str) else valor


class SolicitudForm(FlaskForm):
    solicitante = StringField('Solicitante', filters=[limpiar], validators=[
        DataRequired(message='Escriba un solicitante; no se aceptan solo espacios.'),
        Length(max=120, message='Máximo 120 caracteres.')])
    equipo = StringField('Equipo', filters=[limpiar], validators=[
        DataRequired(message='Escriba el equipo.'),
        Length(max=40, message='Máximo 40 caracteres.')])
    descripcion = TextAreaField('Descripción', filters=[limpiar], validators=[
        DataRequired(message='Escriba la descripción.'),
        Length(max=2000, message='Máximo 2000 caracteres.')])


class ResolverForm(FlaskForm):
    """Formulario con token CSRF para actualizar el estado."""


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(MAX_CONTENT_LENGTH=64 * 1024,
                      SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
                      SESSION_COOKIE_SECURE=bool(os.environ.get('RENDER')),
                      SQLALCHEMY_TRACK_MODIFICATIONS=False)
    if test_config is not None:
        if not test_config.get('TESTING'):
            raise ValueError('La configuración alternativa requiere TESTING=True.')
        app.config.update(test_config)
    else:
        # Sin valores por defecto: el taller requiere configurar ambas variables.
        database_url = os.environ['DATABASE_URL'].strip()
        secret_key = os.environ['SECRET_KEY'].strip()
        if len(secret_key) < 32:
            raise RuntimeError('Genere SECRET_KEY con secrets.token_hex(32).')
        if database_url.startswith('postgres://'):
            database_url = 'postgresql://' + database_url[len('postgres://'):]
        try:
            parsed = make_url(database_url)
        except Exception:
            raise RuntimeError('DATABASE_URL debe ser una URL PostgreSQL válida.') from None
        if parsed.get_backend_name() != 'postgresql':
            raise RuntimeError('El taller requiere PostgreSQL en DATABASE_URL.')
        if parsed.drivername not in ('postgresql', 'postgresql+psycopg2'):
            raise RuntimeError('Utilice el controlador PostgreSQL psycopg2.')
        parsed = parsed.set(drivername='postgresql+psycopg2')
        app.config.update(SECRET_KEY=secret_key, SQLALCHEMY_DATABASE_URI=parsed,
                          SQLALCHEMY_ENGINE_OPTIONS={
                              'pool_pre_ping': True, 'pool_size': 3, 'max_overflow': 2,
                              'connect_args': {'sslmode': 'require', 'connect_timeout': 10}})
    db.init_app(app)
    csrf.init_app(app)

    @app.cli.command('init-db')
    def init_db():
        """Crea tablas ausentes sin eliminar registros ni migrar columnas."""
        try:
            db.create_all()
        except SQLAlchemyError:
            db.session.rollback()
            raise click.ClickException(
                'No se pudo inicializar PostgreSQL. Revise DATABASE_URL, estado, '
                'región y permisos de conexión. No publique las credenciales.') from None
        click.echo('Tabla solicitudes disponible.')

    def mostrar(form=None, codigo=200):
        estado = request.args.get('estado', '')
        if estado not in ('', 'Pendiente', 'Resuelta'):
            abort(400, description='Filtro de estado no válido.')
        consulta = db.select(Solicitud).order_by(Solicitud.id.desc())
        if estado:
            consulta = consulta.where(Solicitud.estado == estado)
        solicitudes = db.session.execute(consulta).scalars().all()
        return render_template('index.html', form=form or SolicitudForm(),
                               resolver_form=ResolverForm(), solicitudes=solicitudes,
                               estado=estado), codigo

    @app.get('/')
    def index():
        return mostrar()

    @app.post('/solicitudes')
    def crear_solicitud():
        form = SolicitudForm()
        if not form.validate_on_submit():
            return mostrar(form, 400)
        solicitud = Solicitud(solicitante=form.solicitante.data, equipo=form.equipo.data,
                              descripcion=form.descripcion.data)
        db.session.add(solicitud)
        db.session.commit()
        flash(f'Solicitud #{solicitud.id} registrada como Pendiente.', 'exito')
        return redirect(url_for('index'), code=303)

    @app.post('/solicitudes/<int:solicitud_id>/resolver')
    def resolver(solicitud_id):
        form = ResolverForm()
        if not form.validate_on_submit():
            abort(400, description='Formulario no válido. Recargue la página.')
        solicitud = db.get_or_404(Solicitud, solicitud_id)
        solicitud.estado = 'Resuelta'
        db.session.commit()
        flash(f'Solicitud #{solicitud.id} marcada como Resuelta.', 'exito')
        return redirect(url_for('index'), code=303)

    @app.get('/health')
    def health():
        # Comprueba conexión, no comprueba si existe solicitudes.
        try:
            db.session.execute(text('SELECT 1'))
            return jsonify(status='ok', database='ok'), 200
        except SQLAlchemyError:
            db.session.rollback()
            return jsonify(status='error', database='unavailable'), 503

    @app.errorhandler(CSRFError)
    def error_csrf(error):
        return render_template('error.html', titulo='Formulario vencido o no válido',
                               mensaje='Recargue la página y vuelva a enviar el formulario. '
                               'No desactive la protección CSRF.'), 400

    @app.errorhandler(SQLAlchemyError)
    def error_database(error):
        db.session.rollback()
        # No volcar URL, parámetros de conexión ni contenido del formulario a logs.
        app.logger.error('Error de base de datos: %s', type(error).__name__)
        return render_template('error.html', titulo='Base de datos no disponible',
                               mensaje='Revise la conexión, la disponibilidad de PostgreSQL '
                               'y la ejecución de init-db.'), 503

    @app.errorhandler(413)
    def demasiado_grande(error):
        return render_template('error.html', titulo='Formulario demasiado grande',
                               mensaje='Use los límites de longitud indicados.'), 413

    return app


# Objeto requerido por flask --app app y por gunicorn app:app.
app = create_app()
