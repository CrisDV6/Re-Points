# Re-Points

Re-Points es un proyecto universitario de reciclaje que identificará usuarios mediante códigos QR, clasificará botellas y asignará puntos por establecimiento.

La versión actual contiene autenticación mediante sesiones, QR personal, registro protegido de botellas plásticas y de vidrio, acreditación automática de puntos, historial del cliente y panel de métricas para el dueño del establecimiento.

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

## Fase 1: puntos separados por local

La base se amplía automáticamente al iniciar la aplicación, conservando los datos existentes. Para ejecutar manualmente la migración compatible y cargar nuevamente los datos iniciales idempotentes:

```powershell
.\.venv\Scripts\python.exe -m backend.scripts.seed_phase1
```

Cuenta cliente de demostración: `usuario@repoints.com` / `Demo123*`.

Cuenta de administración general: `admin@repoints.com` / `Admin123*`.

Los puntos por local están disponibles en `/mi-historial` y en `GET /api/users/me/points`.

Cada tarjeta abre el detalle del local en `/locales/{id}`. El historial puede filtrarse con `/mi-historial?localId={id}` y mediante `GET /api/users/me/recycling-history?localId={id}`. Los locales públicos están disponibles en `GET /api/locals`.

## Fase 3: Raspberry Pi simulada

Los dispositivos demo son `RASPI-ECO-001`, `RASPI-GREEN-001` y `RASPI-RECYCLE-001`. En desarrollo usan la clave `RaspiDemo2026*`, que se almacena únicamente mediante hash. Envían una botella a `POST /api/recycling-events` con la cabecera `X-Device-Api-Key`.

El backend valida dispositivo, local, QR, confianza, regla de puntos y operación única antes de acreditar el saldo del local dentro de una sola transacción.

## Cliente para Raspberry Pi con dos cámaras

La carpeta `raspberry/` contiene el programa de estación. La cámara configurada como `QR_CAMERA_INDEX` lee el QR del cliente y `BOTTLE_CAMERA_INDEX` observa el depósito. Ambas deben usar índices diferentes.

1. Instala las dependencias:

```bash
python -m pip install -r requirements-raspberry.txt
```

2. Copia `raspberry/.env.example` como `raspberry/.env` y configura URL, dispositivo, clave e índices de cámara.

3. Prueba la conexión sin cámaras ni modelo con el token mostrado en el QR:

```bash
python -m raspberry.simulate --qr-token TOKEN --material plastic
```

4. Inicia las dos cámaras y el clasificador real:

```bash
python -m raspberry.main
```

El modo real requiere un modelo ONNX con dos salidas: `plastic` y `glass`. Los modelos están excluidos de Git. El backend vuelve a validar dispositivo, local, usuario, confianza y operación aunque el cliente Raspberry sea manipulado.

## Estructura actual

- `backend/app`: aplicación FastAPI.
- `backend/app/database`: conexión, sesiones e inicialización de SQLite.
- `backend/app/models`: entidades y relaciones del sistema.
- `backend/tests`: pruebas automáticas del backend.
- `.env.example`: variables de entorno de referencia.
- `requirements.txt`: dependencias directas del proyecto.
