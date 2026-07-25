# Re-Points

Re-Points es un proyecto universitario de reciclaje que identificará usuarios mediante códigos QR, clasificará botellas y asignará puntos por establecimiento.

La versión actual contiene la base de la API, SQLite, autenticación mediante sesiones, pantallas públicas y una vista protegida con el QR personal de cada cliente. Las cámaras, la clasificación de residuos y los flujos de puntos todavía no están implementados.

## Requisitos

- Python 3.10 o superior

## Ejecución local

Desde la carpeta `Re-Points`, activa el entorno virtual y ejecuta:

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn backend.app.main:app --reload
```

Luego visita `http://127.0.0.1:8000/health`.

## Pruebas

```powershell
pytest
```

## Estructura actual

- `backend/app`: aplicación FastAPI.
- `backend/app/database`: conexión, sesiones e inicialización de SQLite.
- `backend/app/models`: entidades y relaciones del sistema.
- `backend/tests`: pruebas automáticas del backend.
- `.env.example`: variables de entorno de referencia.
- `requirements.txt`: dependencias directas del proyecto.
