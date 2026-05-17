# SPO-Bogotá — Guía de Despliegue

## Archivos del Proyecto

```
spo-bogota/
├── api/
│   ├── train_model.py           ← Entrena y guarda los .pkl
│   ├── api.py                   ← Servidor FastAPI
│   ├── requirements.txt         ← Dependencias Python de la API
│   ├── model.pkl                ← (DVC) Modelo LightGBM
│   ├── kmeans.pkl               ← (DVC) Clustering espacial
│   ├── feature_columns.pkl      ← (DVC) Orden de columnas
│   ├── stats.json               ← (DVC) Estadísticas mensuales
│   ├── map_data.json            ← (DVC) Datos del mapa
│   ├── cluster_stats.json       ← (DVC) Estadísticas por clúster
│   └── base-anuario-de-siniestralidad-2024.xlsx  ← (DVC) Datos SDM
├── dashboard/
│   ├── dashboard.html           ← Interfaz web del simulador
│   ├── dashboard.js
│   └── dashboard.css
├── dvc.yaml                     ← Pipeline de entrenamiento (DVC)
├── dvc.lock                     ← Estado actual del pipeline (DVC)
└── requirements-dev.txt         ← Dependencias de desarrollo (DVC)
```

---

## Gestión de datos con DVC

Los archivos grandes (Excel de datos, modelos `.pkl`, JSONs generados) **no están en git** — están versionados con [DVC](https://dvc.org) y almacenados en Google Drive.

### Primer uso — clonar el proyecto y obtener los datos

```bash
# 1. Instalar dependencias de desarrollo
pip install -r requirements-dev.txt

# 2. Bajar los datos y modelos desde Google Drive (te va a pedir login Google la primera vez)
dvc pull
```

### Actualizar los datos (nueva versión del Excel)

```bash
# Reemplazá el Excel en api/ y volvé a trackear
dvc add api/base-anuario-de-siniestralidad-2024.xlsx
git add api/base-anuario-de-siniestralidad-2024.xlsx.dvc
git commit -m "actualizar datos siniestralidad 2025"
dvc push
```

### Reentrenar el modelo

```bash
# Si los datos cambiaron, esto detecta qué pasos ejecutar
dvc repro

# Subir los nuevos modelos a Google Drive
dvc push

git add dvc.lock
git commit -m "reentrenar modelo con datos actualizados"
```

### Configurar el remote de Google Drive (solo una vez por máquina nueva)

```bash
# Reemplazá <FOLDER_ID> con el ID de la carpeta en Google Drive
# (está en la URL: drive.google.com/drive/folders/<FOLDER_ID>)
dvc remote add -d gdrive gdrive://<FOLDER_ID>
dvc remote modify gdrive gdrive_acknowledge_abuse true
```

---

---

## PASO 1 — Instalar dependencias

```bash
pip install -r requirements.txt
```

---

## PASO 2 — Entrenar el modelo y generar los .pkl

Coloca el archivo Excel en la misma carpeta y ejecuta:

```bash
python train_model.py --data base-anuario-de-siniestralidad-2024.xlsx
```

Esto genera:
- **model.pkl** — clasificador LightGBM entrenado
- **kmeans.pkl** — modelo KMeans de 15 clústeres espaciales
- **feature_columns.pkl** — lista ordenada de las 49 features

---

## PASO 3 — Levantar la API

```bash
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

Verifica que funciona abriendo: http://localhost:8000  
Documentación Swagger:        http://localhost:8000/docs

### Ejemplo de llamada directa (curl)

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "latitud": 4.609,
    "longitud": -74.082,
    "hora_acc": 8,
    "num_vehiculos": 2,
    "con_moto": 1,
    "con_peaton": 0,
    "con_bicicleta": 0,
    "con_velocidad": 0,
    "con_embriaguez": 0,
    "con_carga": 0,
    "con_menores": 0,
    "con_persona_mayor": 0,
    "dia_semana": "viernes",
    "clase_acc": "Atropello",
    "mes_num": 6
  }'
```

Respuesta esperada:
```json
{
  "clase_predicha": 1,
  "etiqueta": "Con Heridos",
  "prob_solo_danos": 0.2341,
  "prob_con_heridos": 0.6112,
  "prob_con_muertos": 0.1547,
  "zona_cluster": 7,
  "accion_recomendada": "🚨 PRIORIDAD ALTA — Despacho de Ambulancia de Soporte Vital Básico."
}
```

---

## PASO 4 — Abrir el dashboard

1. Abre **dashboard.html** en tu navegador
2. En el panel derecho, cambia la URL de la API si es necesario (por defecto `http://localhost:8000`)
3. Ingresa los datos del siniestro y presiona **⚡ Calcular Riesgo**

---

## Despliegue en la nube (opcional)

### Render / Railway / Fly.io
1. Sube todos los archivos incluyendo los `.pkl` ya generados
2. Comando de inicio: `uvicorn api:app --host 0.0.0.0 --port $PORT`
3. Actualiza la URL de la API en el dashboard

### Google Cloud Run / AWS Lambda
- Empaqueta en Docker con los `.pkl` incluidos
- La imagen base `python:3.11-slim` es suficiente

---

## Variables del Modelo (49 features)

| Grupo | Variables |
|-------|-----------|
| Temporal | `Hora_Acc`, `Mes_Num` |
| Operacional | `Num_Vehiculos_Involucrados` |
| Actores (binario) | `Con_Moto`, `Con_Peaton`, `Con_Bicicleta`, `Con_Velocidad`, `Con_Embriaguez`, `Con_Carga`, `Con_Menores`, `Con_Persona_Mayor`, `Con_Rutas`, `Con_Tpi`, `Con_Tpp`, `Con_Sitp`, `Con_Troncal`, `Con_Alimentador`, `Con_Zonal`, `Con_Provisional`, `Con_Articulado`, `Con_Biarticulado`, `Con_Padron_Dual`, `Con_Servicio_Especial`, `Con_Taxi` |
| Día (one-hot) | `Dia_Semana_Acc_jueves/lunes/martes/miércoles/sábado/viernes` |
| Clase (one-hot) | `Clase_Acc_Caida de ocupante/Choque/Otro/Volcamiento` |
| Cluster (one-hot) | `Zona_Riesgo_Cluster_1` ... `Zona_Riesgo_Cluster_14` |

---

## Target (variable a predecir)

| Valor | Clase | Descripción |
|-------|-------|-------------|
| 0 | Solo Daños | Solo daños materiales |
| 1 | Con Heridos | Al menos un herido |
| 2 | Con Muertos | Al menos una fatalidad |
