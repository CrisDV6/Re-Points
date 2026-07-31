# Integración de inteligencia artificial en Re-Points

## Qué es cada parte

**Re-Points es el sistema completo.** Administra usuarios, códigos QR, locales, dispositivos, reglas de recompensa, puntos separados por establecimiento, historial y la interfaz web.

**La inteligencia artificial forma parte de Re-Points.** Está dentro de `raspberry/ai` y se ocupa únicamente de clasificar botellas de plástico PET y botellas de vidrio. No es un proyecto separado ni pretende reconocer todos los residuos.

## Estado actual

Terminado:

- autenticación web, usuarios, QR y locales;
- puntos separados por usuario y local;
- autenticación de la Raspberry mediante código de dispositivo y clave con hash;
- flujo de dos cámaras separado entre lectura QR y captura de botella;
- preprocesamiento MobileNetV2 a 224×224 y rango `[-1, 1]`;
- reglas expertas: aceptar desde 0.85, recapturar desde 0.60 y desconocido por debajo de 0.60;
- idempotencia mediante `eventId` y `captureId`;
- reintentos, timeout y cola local de eventos pendientes;
- interfaz visual de la estación y simulador manual separado;
- pruebas automatizadas del backend y del módulo de inteligencia artificial de Re-Points.

Disponible solo para pruebas:

- `AI_MOCK_MODE=true` permite probar el recorrido de la aplicación sin modelo;
- el mock se identifica visualmente y nunca entrega puntos reales;
- el formulario “Modo simulación — solo para pruebas” permite verificar QR y crear registros manuales de desarrollo, pero no representa una inferencia.

## Archivos que todavía faltan

El compañero encargado de IA debe entregar:

1. `re_points_mobilenetv2.tflite`, exportado desde el entrenamiento documentado;
2. el notebook ejecutado o `class_indices` que demuestre el orden real de las clases;
3. varias imágenes conocidas de PET y vidrio para validar el mapeo;
4. idealmente el hash y versión del modelo entregado.

No se incluye un modelo inventado. Mientras falte, la interfaz muestra un aviso comprensible y el modo real termina de forma segura.

## Cómo agregar el modelo TFLite

Coloca el archivo en:

```text
raspberry/ai/models/re_points_mobilenetv2.tflite
```

Configura `raspberry/.env`:

```dotenv
AI_MODEL_PATH=raspberry/ai/models/re_points_mobilenetv2.tflite
AI_MODEL_VERSION=1.0.0
AI_MOCK_MODE=false
```

El `.tflite` está excluido de Git hasta confirmar que corresponde al entrenamiento documentado.

## Cómo confirmar labels.json

Los informes incluidos en `docs/ia` se contradicen sobre el índice positivo. Por eso `raspberry/ai/models/labels.json` continúa con `validated=false`.

Con el modelo real y varias imágenes conocidas:

```bash
python -m raspberry.ai.verify_labels \
  --model raspberry/ai/models/re_points_mobilenetv2.tflite \
  pet_conocida_1.jpg vidrio_conocido_1.jpg
```

Repite la comprobación con varias imágenes de cada clase. Solo después de verificar los resultados contra el notebook o `class_indices`, corrige el mapeo si es necesario y cambia manualmente `validated` a `true`. El script nunca lo cambia automáticamente.

## Entornos y versiones de Python

### Laptop Windows

- Recomendado: Python 3.13 para backend y frontend.
- Instalar solo `requirements.txt`.
- NumPy, OpenCV, cámaras y TensorFlow no son necesarios para usar la web.
- Para probar opcionalmente un `.tflite` real en Windows 3.13, usar `raspberry/ai/requirements-tflite-windows.txt`.

### Raspberry Pi 5

- Recomendado: Raspberry Pi OS de 64 bits y Python 3.11.
- Instalar `requirements.txt`, `requirements-raspberry.txt` y `raspberry/ai/requirements-tflite.txt`.
- `tflite-runtime 2.14.0` publica compatibilidad hasta Python 3.11; el marcador del archivo evita forzar su instalación en 3.12/3.13 o Windows.

## Cómo probar en Raspberry Pi 5

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -r requirements-raspberry.txt
python -m pip install -r raspberry/ai/requirements-tflite.txt
cp raspberry/.env.example raspberry/.env
```

Configura URL, dispositivo, clave e índices de cámaras en `raspberry/.env`. Después:

```bash
python -m pytest -q
python -m raspberry.main
```

Antes de una demostración real se debe comprobar físicamente la cámara A, cámara B, iluminación, enfoque, tiempo de inferencia, conexión con el backend y acreditación de un único evento. Estas pruebas físicas siguen pendientes porque el hardware y el modelo no forman parte del paquete actual.
