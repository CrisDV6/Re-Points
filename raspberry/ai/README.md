# Inteligencia artificial de Re-Points en Raspberry Pi

El módulo de inteligencia artificial de Re-Points clasifica exclusivamente botellas PET y botellas de vidrio. No clasifica todos los residuos ni todos los plásticos.

## Flujo seguro

La cámara A lee el QR y el backend valida al cliente. La cámara B entrega una imagen RGB que se convierte a 224x224 y se preprocesa con la fórmula de MobileNetV2 `x / 127.5 - 1`. TensorFlow Lite produce la predicción; el sistema experto acepta desde 0.85, solicita recaptura entre 0.60 y 0.85, y marca desconocido por debajo de 0.60. Solo `accepted` puede llegar al backend.

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -r raspberry/ai/requirements.txt
python -m pip install -r raspberry/ai/requirements-tflite.txt
cp raspberry/.env.example raspberry/.env
```

Coloca el modelo entregado y verificado en `raspberry/ai/models/re_points_mobilenetv2.tflite`. Si `AI_MOCK_MODE=false` y el archivo falta, el inicio termina con un error claro; nunca se inventa un modelo.

Para backend y frontend en Windows 3.13 instala únicamente el `requirements.txt` de la raíz. Las dependencias de cámara están separadas en `requirements-raspberry.txt`. En Raspberry Pi 5 se recomienda Python 3.11 para poder usar `tflite-runtime 2.14.0`. La prueba opcional de TFLite en Windows 3.13 usa `requirements-tflite-windows.txt` y no es necesaria para la aplicación web.

## Verificación obligatoria de etiquetas

Los informes se contradicen sobre el índice positivo y no se entregaron notebook, `class_indices` ni modelo. Por ello `labels.json` tiene `validated: false` y el modo real no inicia. Cuando estén disponibles el modelo y fotos conocidas de ambos materiales:

```bash
python -m raspberry.ai.verify_labels --model raspberry/ai/models/re_points_mobilenetv2.tflite foto_pet.jpg foto_vidrio.jpg
```

Repite con varias imágenes. Solo tras comprobar ambas clases cambia `validated` a `true`. El script nunca hace ese cambio automáticamente.

## Modo mock

Actívalo únicamente con `AI_MOCK_MODE=true`. El resultado se identifica con versión `mock-*` y conserva `labels_validated=false`, por lo que sirve para probar cámaras y reglas sin acreditar puntos.

## Ejecución

```bash
python -m raspberry.main
python -m pytest -q
```

Los secretos se cargan desde `raspberry/.env`, que está excluido de Git. Los logs y mensajes no muestran la clave del dispositivo.
