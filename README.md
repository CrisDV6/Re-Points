# Re-Points

Re-Points es un proyecto universitario de reciclaje que identificará usuarios mediante códigos QR, clasificará botellas y asignará puntos por establecimiento.

La versión actual contiene autenticación mediante sesiones, QR personal, registro protegido de botellas plásticas y de vidrio, acreditación automática de puntos, historial del cliente y panel de métricas para el dueño del establecimiento.

## Requisitos

- Windows/backend: Python 3.13 recomendado.
- Raspberry Pi 5/TFLite: Python 3.11 recomendado.

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

Cuenta cliente de demostración: `usuario@repoints.com`. Su contraseña se define con `DEMO_CLIENT_PASSWORD`.

Cuenta de administración general: `admin@repoints.com`. Su contraseña se define con `DEMO_ADMIN_PASSWORD`.

Los puntos por local están disponibles en `/mi-historial` y en `GET /api/users/me/points`.

Cada tarjeta abre el detalle del local en `/locales/{id}`. El historial puede filtrarse con `/mi-historial?localId={id}` y mediante `GET /api/users/me/recycling-history?localId={id}`. Los locales públicos están disponibles en `GET /api/locals`.

## Fase 3: Raspberry Pi simulada

Los dispositivos demo son `RASPI-ECO-001`, `RASPI-GREEN-001` y `RASPI-RECYCLE-001`. La clave se configura con `DEMO_DEVICE_API_KEY` y se almacena únicamente mediante hash. Envían una botella a `POST /api/recycling-events` con la cabecera `X-Device-Api-Key`.

El backend valida dispositivo, local, QR, confianza, regla de puntos y operación única antes de acreditar el saldo del local dentro de una sola transacción.

## Cliente para Raspberry Pi con dos cámaras

La carpeta `raspberry/` contiene el programa de estación. La cámara configurada como `QR_CAMERA_INDEX` lee el QR del cliente y `BOTTLE_CAMERA_INDEX` observa el depósito. Ambas deben usar índices diferentes.

1. Instala las dependencias:

```bash
python -m pip install -r requirements-raspberry.txt
python -m pip install -r raspberry/ai/requirements-tflite.txt
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

El modo real requiere el MobileNetV2 exportado a TensorFlow Lite. Los modelos están excluidos de Git hasta que se entregue y confirme el artefacto documentado. El backend vuelve a validar dispositivo, local, usuario, decisión, confianza y operación aunque el cliente Raspberry sea manipulado.

## Inteligencia artificial de Re-Points

La inteligencia artificial de Re-Points se limita a **botellas de plástico PET** y **botellas de vidrio**; no clasifica todos los residuos ni todos los tipos de plástico.

La cámara A lee el QR público del cliente. El backend comprueba usuario, dispositivo y local. La cámara B captura la botella, que se redimensiona a 224x224 y recibe exactamente el preprocesamiento MobileNetV2 (`x / 127.5 - 1`). TensorFlow Lite devuelve la predicción, confianza y tiempo de inferencia. El sistema experto aplica:

- confianza `>= 0.85`: `accepted`;
- confianza `>= 0.60` y `< 0.85`: `recapture`;
- confianza `< 0.60`: `unknown`.

Solo `accepted` puede registrarse. El backend calcula los puntos usando `LocalRewardRule`; la Raspberry nunca decide la cantidad. El saldo permanece separado por usuario y local en `CustomerBalance`.

### Variables del backend

```dotenv
APP_NAME=Re-Points
APP_ENV=development
SECRET_KEY=change-this-value
DATABASE_URL=sqlite:///./re_points.db
MASTER_LOCAL_CODE=change-this-master-local-code
AI_ACCEPT_THRESHOLD=0.85
DEMO_CLIENT_PASSWORD=change-this-demo-client-password
DEMO_ADMIN_PASSWORD=change-this-demo-admin-password
DEMO_DEVICE_API_KEY=change-this-demo-device-key
```

El mecanismo existente del dispositivo se conserva: `DEVICE_CODE` identifica la Raspberry y `X-Device-Api-Key` transporta la clave, cuyo hash se almacena en la base. No hay secretos escritos dentro del código.

### Variables de Raspberry Pi

```dotenv
REPOINTS_API_URL=http://127.0.0.1:8000
DEVICE_CODE=RASPI-ECO-001
DEVICE_API_KEY=change-this-device-key
QR_CAMERA_INDEX=0
BOTTLE_CAMERA_INDEX=1
AI_MODEL_PATH=raspberry/ai/models/re_points_mobilenetv2.tflite
AI_LABELS_PATH=raspberry/ai/models/labels.json
AI_ACCEPT_THRESHOLD=0.85
AI_RECAPTURE_THRESHOLD=0.60
AI_MODEL_VERSION=1.0.0
AI_MOCK_MODE=false
REQUEST_TIMEOUT_SECONDS=10
REQUEST_MAX_RETRIES=3
PENDING_EVENTS_PATH=raspberry/ai/data/pending_events.jsonl
```

### Modelo real y etiquetas

No se entregó el `.tflite`, por lo que no se incluye ni se inventa un modelo. Con `AI_MOCK_MODE=false`, la aplicación falla de forma segura si falta el archivo. Los informes entregados se contradicen: uno documenta plástico=1/vidrio=0 y otro afirma que la salida es la probabilidad de vidrio. Como no se encontró notebook, `class_indices`, modelo ni otra fuente primaria, `raspberry/ai/models/labels.json` tiene `validated: false` y bloquea puntos.

Cuando se entregue el modelo, valida el mapeo con imágenes conocidas:

```bash
python -m raspberry.ai.verify_labels --model raspberry/ai/models/re_points_mobilenetv2.tflite pet_1.jpg vidrio_1.jpg
```

Solo tras comprobar varios ejemplos de ambas clases debe cambiarse `validated` a `true`.

### Modo mock

`AI_MOCK_MODE=true` activa un clasificador marcado como `mock-*`. Permite comprobar cámaras, flujo y reglas, pero conserva las etiquetas como no validadas y por eso no acredita puntos. Nunca se activa de manera implícita.

### Endpoint de inteligencia artificial de Re-Points

`POST /api/recycling-events` usa la cabecera `X-Device-Api-Key`. También se mantienen los nombres anteriores (`operationId`, `userQrToken`, `capturedAt`) por compatibilidad.

```json
{
  "eventId": "8d75c715-078f-4c8a-a084-98b5749fe2cf",
  "captureId": "8d75c715-078f-4c8a-a084-98b5749fe2cf",
  "deviceId": "RASPI-ECO-001",
  "localId": 1,
  "userQr": "identificador-publico-del-usuario",
  "material": "plastic",
  "confidence": 0.963,
  "decision": "accepted",
  "modelVersion": "1.0.0",
  "inferenceTimeMs": 145,
  "labelsValidated": true,
  "timestamp": "2026-07-30T12:00:00Z"
}
```

Respuesta abreviada:

```json
{
  "success": true,
  "message": "Botella registrada correctamente",
  "eventId": 42,
  "operationId": "8d75c715-078f-4c8a-a084-98b5749fe2cf",
  "tokensEarned": 10,
  "localBalance": 60,
  "decision": "accepted",
  "modelVersion": "1.0.0",
  "inferenceTimeMs": 145.0
}
```

El backend rechaza QR/usuario inexistente, local que no corresponde al dispositivo, dispositivo inactivo o con clave inválida, materiales fuera de `plastic`/`glass`, decisiones distintas de `accepted`, confianza insuficiente, etiquetas sin confirmar, `eventId` repetido y `captureId` repetido. La transacción de evento, movimiento y saldo es atómica.

### Instalación en Raspberry Pi

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -r requirements-raspberry.txt
cp raspberry/.env.example raspberry/.env
python -m raspberry.main
```

El cliente usa timeout, reintentos exponenciales y una cola JSONL para eventos sin conexión. La cola no contiene la clave del dispositivo ni imágenes. Los detalles del módulo están en `raspberry/ai/README.md`.

En Windows con Python 3.13, `requirements.txt` contiene únicamente backend, frontend y pruebas. No instala dependencias de cámaras. La prueba opcional de un modelo real usa `raspberry/ai/requirements-tflite-windows.txt`; TensorFlow no se instala como requisito general. En Raspberry Pi se recomienda Python 3.11 porque el paquete liviano `tflite-runtime 2.14.0` no declara soporte para Python 3.12/3.13.

La guía consolidada se encuentra en `docs/INTEGRACION_IA_RE_POINTS.md` y los tres informes fuente están versionados en `docs/ia/`.

### Limitaciones actuales

- Falta el archivo TFLite documentado y no pudo medirse inferencia real en Raspberry Pi.
- El mapeo de etiquetas permanece bloqueado hasta verificarlo contra el modelo real.
- El dataset tiene fondos y ángulos muy repetitivos; la exactitud documentada de 97.02% puede no trasladarse al campus.
- Deben realizarse pruebas físicas con ambas cámaras y capturas reales de PET transparente y vidrio claro.

## Estructura actual

- `backend/app`: aplicación FastAPI.
- `backend/app/database`: conexión, sesiones e inicialización de SQLite.
- `backend/app/models`: entidades y relaciones del sistema.
- `backend/tests`: pruebas automáticas del backend.
- `.env.example`: variables de entorno de referencia.
- `requirements.txt`: dependencias directas del proyecto.
