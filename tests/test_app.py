"""Pruebas aisladas con CSRF activo. No utilizan la base del estudiante."""
import os
import re
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

# Permite importar app sin secretos del estudiante; no se conecta a esta URL.
os.environ['DATABASE_URL'] = 'postgresql://pruebas:pruebas@127.0.0.1:1/pruebas'
os.environ['SECRET_KEY'] = 'clave-solo-para-pruebas-aisladas-1234567890'
from app import create_app, db, Solicitud
from sqlalchemy.exc import OperationalError


class TallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.config = {'TESTING': True, 'SECRET_KEY': 'clave-test-aislada',
                       'SQLALCHEMY_DATABASE_URI': 'sqlite:///' + str(Path(self.temp.name) / 'test.db'),
                       'WTF_CSRF_ENABLED': True}
        self.app = create_app(self.config)
        with self.app.app_context():
            db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()
        self.temp.cleanup()

    def token(self, client=None):
        html = (client or self.client).get('/').get_data(as_text=True)
        return re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html).group(1)

    def crear(self, nombre='Estudiante A', equipo='LAB-02', descripcion='El teclado no responde'):
        return self.client.post('/solicitudes', data={
            'csrf_token': self.token(), 'solicitante': nombre,
            'equipo': equipo, 'descripcion': descripcion})

    def test_01_tabla_vacia_y_health(self):
        self.assertIn('No hay solicitudes', self.client.get('/').get_data(as_text=True))
        self.assertEqual(self.client.get('/health').json, {'status': 'ok', 'database': 'ok'})

    def test_02_registro_y_espacios(self):
        self.assertEqual(self.crear('  Estudiante A  ').status_code, 303)
        with self.app.app_context():
            s = db.session.execute(db.select(Solicitud)).scalar_one()
            self.assertEqual((s.solicitante, s.estado), ('Estudiante A', 'Pendiente'))

    def test_03_rechazo_vacio_espacios_y_largo(self):
        for nombre, equipo, desc in [('   ', 'LAB', 'Caso'), ('A', '', 'Caso'),
                                     ('A', 'LAB', '  '), ('A' * 121, 'LAB', 'Caso')]:
            self.assertEqual(self.crear(nombre, equipo, desc).status_code, 400)
        with self.app.app_context():
            self.assertEqual(db.session.scalar(db.select(db.func.count()).select_from(Solicitud)), 0)

    def test_04_cinco_casos_dos_resueltos_y_filtros(self):
        for letra in 'ABCDE':
            self.crear('Estudiante ' + letra)
        for id_ in (1, 2):
            self.assertEqual(self.client.post(f'/solicitudes/{id_}/resolver',
                             data={'csrf_token': self.token()}).status_code, 303)
        for estado, n in [('Pendiente', 3), ('Resuelta', 2), ('', 5)]:
            html = self.client.get('/', query_string={'estado': estado}).get_data(as_text=True)
            self.assertEqual(len(re.findall(r'<tr data-id=', html)), n)
        self.assertEqual(self.client.get('/?estado=Otro').status_code, 400)

    def test_05_csrf_y_metodo_de_actualizacion(self):
        self.crear()
        self.assertEqual(self.client.post('/solicitudes', data={'solicitante': 'Sin token'}).status_code, 400)
        self.assertEqual(self.client.post('/solicitudes/1/resolver').status_code, 400)
        self.assertEqual(self.client.get('/solicitudes/1/resolver').status_code, 405)
        with self.app.app_context():
            self.assertEqual(db.session.get(Solicitud, 1).estado, 'Pendiente')

    def test_06_dos_clientes_y_reinicio(self):
        self.crear()
        cliente_b = self.app.test_client()
        cliente_b.post('/solicitudes/1/resolver', data={'csrf_token': self.token(cliente_b)})
        self.assertIn('Resuelta', self.client.get('/').get_data(as_text=True))
        runner = self.app.test_cli_runner()
        result = runner.invoke(args=['init-db'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('Tabla solicitudes disponible.', result.output)
        nueva = create_app(self.config)
        with nueva.app_context():
            self.assertEqual(db.session.get(Solicitud, 1).estado, 'Resuelta')
            db.session.remove()
            db.engine.dispose()

    def test_07_health_no_demuestra_tabla(self):
        with self.app.app_context():
            db.drop_all()  # Solo la SQLite temporal de este test.
        self.assertEqual(self.client.get('/health').status_code, 200)
        self.assertEqual(self.client.get('/').status_code, 503)

    def test_08_error_de_conexion_sin_secretos(self):
        with patch.object(db.session, 'execute', side_effect=OperationalError('secreto', {}, Exception('secreto'))):
            response = self.client.get('/health')
            self.assertEqual(response.status_code, 503)
            self.assertNotIn('secreto', response.get_data(as_text=True))

    def test_09_texto_se_escapa(self):
        self.crear(descripcion='<script>alert(1)</script>')
        html = self.client.get('/').get_data(as_text=True)
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('<script>alert(1)</script>', html)

    def test_10_id_inexistente(self):
        self.assertEqual(self.client.post('/solicitudes/999/resolver',
                         data={'csrf_token': self.token()}).status_code, 404)


if __name__ == '__main__':
    unittest.main()
