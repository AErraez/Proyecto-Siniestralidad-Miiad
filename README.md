# SPO-Bogotá — Guía de Despliegue

## Archivos del Proyecto

```
spo-bogota/
├── train_model.py               ← Entrena y guarda los .pkl
├── api.py                       ← Servidor FastAPI
├── dashboard.html               ← Interfaz web del simulador
├── requirements.txt             ← Dependencias Python
├── model.pkl                    ← (generado) Modelo LightGBM
├── kmeans.pkl                   ← (generado) Clustering espacial
├── feature_columns.pkl          ← (generado) Orden de columnas
└── base-anuario-de-siniestralidad-2024.xlsx  ← Datos SDM
```

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
