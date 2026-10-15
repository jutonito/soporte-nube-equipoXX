# Proyecto Soporte Nube

Aplicación base del **Taller de despliegue de aplicaciones en la nube**.
Ingeniería de Sistemas · Computación en la Nube · Profesor Jhon F Linares A.

La carpeta `soporte_nube` contiene `app.py` y `requirements.txt` directamente en su raíz, como exige el taller. Suba el **contenido de esta carpeta** al repositorio. No suba la carpeta contenedora con otra carpeta `soporte_nube` dentro.

## 1. Archivos

- `app.py`: configuración, modelo `Solicitud`, rutas y comando `init-db`.
- `templates/index.html`: formulario, filtros y tabla; aquí se cambia el `h1` del ejercicio 9.
- `templates/error.html` y `static/styles.css`: errores y presentación.
- `requirements.txt`: versiones de dependencias para Python 3.12.
- `.python-version`: selecciona Python 3.12 en Render; conserve este archivo oculto al subir a Git.
- `.env.example`: plantilla de variables, sin credenciales reales.
- `.gitignore`: exclusiones de secretos y archivos locales.
- `verificacion.sql`: consultas opcionales de lectura, para PostgreSQL.
- `datos_practica.csv`: los cinco casos ficticios del taller, solo como referencia. No se importan automáticamente.
- `tests/test_app.py`: pruebas locales de comportamiento.

## 2. Preparación en Windows PowerShell

Abra una terminal **dentro de `soporte_nube`**. Ejecute una línea a la vez:

```powershell
py --version
git --version
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
```

Pegue la clave generada en `SECRET_KEY` del archivo `.env`. Pegue en `DATABASE_URL` la URL **EXTERNA** de la base PostgreSQL que cree en Render según la sección 4 del taller:

```dotenv
DATABASE_URL=postgresql://USUARIO:CLAVE@HOST/BASE?sslmode=require
SECRET_KEY=PEGUE_AQUI_LA_CLAVE_GENERADA
```

Los valores anteriores son marcadores; debe reemplazarlos. `SECRET_KEY` no puede quedar vacía. La aplicación solicita al menos 32 caracteres. El comando indicado genera 64 caracteres hexadecimales.

Agregue `?sslmode=require` si la URL no tiene parámetros o `&sslmode=require` si ya tiene `?`. Si `sslmode` existe, cambie su valor sin duplicarlo. El código exige además TLS a través del controlador psycopg2. Copie la URL completa desde Render para conservar la codificación de la contraseña.

En macOS/Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
.venv/bin/python -c "import secrets; print(secrets.token_hex(32))"
```

Adapte las invocaciones posteriores a `.venv/bin/python`. No necesita activar el entorno virtual. Las dependencias se descargan de Internet; el ZIP no contiene Python ni las bibliotecas instaladas.

## 3. Inicializar y probar

Después de completar `.env`:

```powershell
.\.venv\Scripts\python.exe -m flask --app app init-db
.\.venv\Scripts\python.exe -m flask --app app run
```

Debe aparecer `Tabla solicitudes disponible.`. Visite:

- http://127.0.0.1:5000
- http://127.0.0.1:5000/health

La tabla queda inicialmente vacía. Registre `Estudiante 1`, `LAB-01`, `El equipo no inicia sesión`. Su estado inicial es **Pendiente**; pulse **Resolver** para cambiarlo a **Resuelta**.

`/health` devuelve HTTP 200 con `{"database":"ok","status":"ok"}` si `SELECT 1` funciona. No comprueba por sí solo que la tabla exista. Si PostgreSQL no responde, devuelve HTTP 503 con `database: unavailable`. La página principal comprueba además que la tabla pueda consultarse.

`init-db` crea tablas ausentes sin borrar registros. No es una migración de columnas, ni una copia de seguridad. No necesita ejecutar un script SQL de creación por separado.

## 4. Publicar en GitHub

Cree un repositorio vacío sin archivos iniciales y ejecute:

```powershell
git init
git add .
git status
git check-ignore .env
```

Confirme que `.env` NO está preparado y que el último comando imprime `.env`. Luego:

```powershell
git commit -m "Aplicacion inicial de soporte"
git branch -M main
git remote add origin URL_DEL_REPOSITORIO
git push -u origin main
git rev-parse --short HEAD
```

Sustituya la URL y complete la identidad/autenticación de Git si se solicita. `.env.example` sí se comparte porque solo contiene marcadores. Nunca incluya `.env` en un commit.

## 5. Configurar Render según el taller

Cree primero PostgreSQL y después un Web Service vinculado al repositorio, en la misma cuenta y región. Configure:

| Campo | Valor |
| --- | --- |
| Branch | `main` |
| Language | Python 3 |
| Root Directory | Vacío |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `flask --app app init-db && gunicorn app:app -b 0.0.0.0:$PORT -w 1` |
| Health Check Path | `/health` |
| Plan | El del taller, sujeto a disponibilidad y condiciones del servicio |

El comando de inicio se pega en Render, donde corre Linux; no se ejecuta en PowerShell. Gunicorn atiende la URL pública. Flask `run` se usa solo para la prueba local.

Antes de desplegar, agregue variables en el servicio:

- `DATABASE_URL`: URL **INTERNA** de la misma PostgreSQL, con `sslmode=require`.
- `SECRET_KEY`: otra clave aleatoria generada por su equipo.

Render proporciona `PORT`. `.python-version` selecciona la rama 3.12. Si ya configuró `PYTHON_VERSION` en el panel, esa variable prevalece: elimínela para usar el archivo o establezca una versión completa compatible de Python 3.12. No transfiera `.env` al servicio.

El despliegue requiere sus cuentas de GitHub y Render y completar las variables; el ZIP por sí solo no crea servicios ni credenciales. Revise el plan, la caducidad de PostgreSQL y los costos en el panel antes de crear recursos. Los datos viven en PostgreSQL separado del proceso web.

## 6. Funciones que se comprueban en el taller

| Acción | Ruta o comportamiento |
| --- | --- |
| Consultar | `GET /` |
| Registrar | `POST /solicitudes` |
| Resolver | `POST /solicitudes/<id>/resolver` |
| Filtrar pendientes | `GET /?estado=Pendiente` |
| Filtrar resueltas | `GET /?estado=Resuelta` |
| Comprobar conexión | `GET /health` |

Los campos se recortan con `strip()`. El servidor rechaza campos vacíos, solo espacios y longitudes excesivas con HTTP 400, sin insertar. El atributo HTML `required` puede detener primero los campos vacíos en el navegador. Los formularios de registro y resolución llevan token CSRF. Recargar permite obtener un token nuevo si caduca.

Cree manualmente los cinco casos del taller, resuelva dos y anote sus ID. El CSV es una ayuda de lectura y no reemplaza la evidencia de registro desde la URL pública. Al filtrar, diferencie esos cinco casos del registro inicial.

Para la prueba con dos equipos, recargue en ambos: no hay actualización en tiempo real. Para persistencia, vuelva a desplegar sin borrar la base. Para la nueva versión, cambie el `h1` de `templates/index.html`, haga commit y push, y compruebe encabezado y registros en la URL pública.

**Alcance académico:** no hay autenticación ni roles. Cualquier visitante con la URL puede consultar y resolver solicitudes. CSRF no es control de acceso. Use solo datos ficticios. El HTML escapa los textos ingresados; las consultas del ORM no concatenan SQL con los formularios.

## 7. Diagnóstico rápido

- `KeyError: DATABASE_URL` o `SECRET_KEY`: complete `.env` local o las variables del servicio.
- Error por clave corta: genere la clave con el comando indicado y recargue el formulario.
- Error al conectar desde su computador: compruebe URL externa, estado y acceso a la base.
- Error desde Render: compruebe URL interna, misma cuenta/región y disponibilidad de la base.
- Tabla inexistente: ejecute `init-db` con la base correcta; `/health` no valida el esquema.
- Error CSRF: recargue, revise `SECRET_KEY` y permita cookies. No desactive CSRF.
- `ModuleNotFoundError: app`: revise la raíz del repositorio y Root Directory.
- Registros aparentemente perdidos: quite el filtro y compruebe la identidad de la base.
- No se detecta puerto: revise `0.0.0.0:$PORT` en el comando de Gunicorn.

La aplicación evita mostrar detalles de conexión en páginas de error. Revise sus capturas antes de compartirlas y oculte todas las cadenas de conexión.

## 8. Pruebas incluidas

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Las pruebas crean una SQLite temporal **exclusivamente como sustituto de pruebas**, mediante `TESTING=True`; no conectan a su PostgreSQL, no leen sus datos ni sustituyen los ejercicios del taller. Comprueban validación, CSRF habilitado, filtros, actualización, persistencia al recrear la aplicación y respuestas de salud. La ejecución normal exige PostgreSQL; no tiene una alternativa automática a SQLite.

La conexión PostgreSQL real, HTTPS, los logs y la persistencia en Render deben comprobarse en su despliegue con las evidencias E01 a E10.

## 9. Documentación oficial

- https://render.com/docs/deploy-flask
- https://render.com/docs/python-version
- https://render.com/docs/postgresql-creating-connecting
- https://flask-sqlalchemy.palletsprojects.com/en/stable/quickstart/
- https://flask-wtf.readthedocs.io/en/1.2.x/csrf/

Proyecto preparado para acompañar el documento entregado por el docente. Conserve las instrucciones y respuestas del taller en su entrega académica.
