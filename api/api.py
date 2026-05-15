"""
api.py — SPO-Bogotá: FastAPI REST endpoint for the LightGBM model
==================================================================
Start server:
    pip install fastapi uvicorn lightgbm scikit-learn pandas joblib
    uvicorn api:app --host 0.0.0.0 --port 8000 --reload

Endpoints:
    GET  /              → health check
    POST /predict       → return severity prediction + probabilities
    GET  /docs          → Swagger UI
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import pandas as pd
import numpy as np
import joblib
import json
import os

# ── LOAD ARTIFACTS ────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(__file__)

try:
    model           = joblib.load(os.path.join(BASE_DIR, "model.pkl"))
    kmeans          = joblib.load(os.path.join(BASE_DIR, "kmeans.pkl"))
    feature_columns = joblib.load(os.path.join(BASE_DIR, "feature_columns.pkl"))
except FileNotFoundError as e:
    raise RuntimeError(
        f"Model artifacts not found: {e}\n"
        "Run  python train_model.py  first to generate model.pkl, kmeans.pkl, feature_columns.pkl"
    )

# ── APP ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="SPO-Bogotá — API de Predicción de Siniestros Viales",
    description="LightGBM multiclass classifier: Solo Daños / Con Heridos / Con Muertos",
    version="1.0.0",
)

# Allow all origins (tighten in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── SCHEMA ────────────────────────────────────────────────────────────────────
class PredictRequest(BaseModel):
    latitud:                   float = Field(..., example=4.609,  description="GPS latitude (Bogotá: 4.4 – 4.9)")
    longitud:                  float = Field(..., example=-74.082, description="GPS longitude (Bogotá: -74.3 – -73.9)")
    hora_acc:                  int   = Field(..., ge=0, le=23,     description="Hour of the incident (0–23)")
    num_vehiculos:             int   = Field(..., ge=1, le=20,     description="Number of vehicles involved")
    # binary actor flags
    con_moto:                  int   = Field(0, ge=0, le=1)
    con_peaton:                int   = Field(0, ge=0, le=1)
    con_bicicleta:             int   = Field(0, ge=0, le=1)
    con_velocidad:             int   = Field(0, ge=0, le=1)
    con_embriaguez:            int   = Field(0, ge=0, le=1)
    con_carga:                 int   = Field(0, ge=0, le=1)
    con_menores:               int   = Field(0, ge=0, le=1)
    con_persona_mayor:         int   = Field(0, ge=0, le=1)
    # optional — day of week (spanish, lowercase) and accident class
    dia_semana:                str   = Field("lunes", description="lunes/martes/miércoles/jueves/viernes/sábado/domingo")
    clase_acc:                 str   = Field("Choque", description="Choque / Atropello / Caida de ocupante / Volcamiento / Otro")
    mes_num:                   int   = Field(1, ge=1, le=12, description="Month number 1–12")

class PredictResponse(BaseModel):
    clase_predicha:     int
    etiqueta:           str
    prob_solo_danos:    float
    prob_con_heridos:   float
    prob_con_muertos:   float
    zona_cluster:       int
    accion_recomendada: str

# ── HELPERS ───────────────────────────────────────────────────────────────────
LABEL_MAP = {0: "Solo Daños", 1: "Con Heridos", 2: "Con Muertos"}

def get_action(clase: int, prob_muertos: float) -> str:
    if prob_muertos >= 0.20:
        return "CÓDIGO ROJO — Despacho inmediato de Ambulancia Medicalizada (SVA)."
    if clase >= 1:
        return "PRIORIDAD ALTA — Despacho de Ambulancia de Soporte Vital Básico."
    return "DESPACHO ESTÁNDAR — Grúa y Policía de Tránsito."

# ── ENDPOINTS ─────────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def health():
    return {"status": "ok", "model": "LightGBM SPO-Bogotá v1.0"}


@app.get("/stats/monthly", tags=["Analytics"])
def stats_monthly():
    path = os.path.join(BASE_DIR, "stats.json")
    if not os.path.exists(path):
        raise HTTPException(
            status_code=503,
            detail="Estadísticas no disponibles. Ejecute train_model.py para generarlas."
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@app.get("/map/data", tags=["Analytics"])
def map_data():
    path = os.path.join(BASE_DIR, "map_data.json")
    if not os.path.exists(path):
        raise HTTPException(
            status_code=503,
            detail="Datos del mapa no disponibles. Ejecute train_model.py para generarlos."
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@app.get("/stats/clusters", tags=["Analytics"])
def stats_clusters():
    path = os.path.join(BASE_DIR, "cluster_stats.json")
    if not os.path.exists(path):
        raise HTTPException(
            status_code=503,
            detail="Estadísticas de clústeres no disponibles. Ejecute train_model.py para generarlas."
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@app.post("/predict", response_model=PredictResponse, tags=["Prediction"])
def predict(req: PredictRequest):
    # 1. Validate coordinates
    if not (4.4 < req.latitud < 4.9 and -74.3 < req.longitud < -73.9):
        raise HTTPException(
            status_code=422,
            detail="Coordinates out of Bogotá bounding box. "
                   "Latitude 4.4–4.9 | Longitude -74.3 – -73.9",
        )

    # 2. Assign spatial cluster
    coords_df = pd.DataFrame({"Latitud": [req.latitud], "Longitud": [req.longitud]})
    zona = int(kmeans.predict(coords_df)[0])

    # 3. Build feature vector (all zeros, then fill known fields)
    instance = pd.Series(0, index=feature_columns, dtype=float)

    # numeric
    instance["Hora_Acc"]                  = req.hora_acc
    instance["Num_Vehiculos_Involucrados"]= req.num_vehiculos
    instance["Mes_Num"]                   = req.mes_num

    # binary Con_* fields (map request field names to dataset column names)
    field_map = {
        "Con_Moto":          req.con_moto,
        "Con_Peaton":        req.con_peaton,
        "Con_Bicicleta":     req.con_bicicleta,
        "Con_Velocidad":     req.con_velocidad,
        "Con_Embriaguez":    req.con_embriaguez,
        "Con_Carga":         req.con_carga,
        "Con_Menores":       req.con_menores,
        "Con_Persona_Mayor": req.con_persona_mayor,
    }
    for col, val in field_map.items():
        if col in instance.index:
            instance[col] = val

    # one-hot day of week (drop_first removed "domingo")
    dia_col = f"Dia_Semana_Acc_{req.dia_semana.lower()}"
    if dia_col in instance.index:
        instance[dia_col] = 1

    # one-hot accident class (drop_first removed "Atropello")
    clase_col = f"Clase_Acc_{req.clase_acc}"
    if clase_col in instance.index:
        instance[clase_col] = 1

    # one-hot cluster (drop_first removed cluster 0)
    cluster_col = f"Zona_Riesgo_Cluster_{zona}"
    if cluster_col in instance.index:
        instance[cluster_col] = 1

    # 4. Predict
    X_input = instance.to_frame().T
    clase_pred  = int(model.predict(X_input)[0])
    probas      = model.predict_proba(X_input)[0]

    return PredictResponse(
        clase_predicha     = clase_pred,
        etiqueta           = LABEL_MAP[clase_pred],
        prob_solo_danos    = round(float(probas[0]), 4),
        prob_con_heridos   = round(float(probas[1]), 4),
        prob_con_muertos   = round(float(probas[2]), 4),
        zona_cluster       = zona,
        accion_recomendada = get_action(clase_pred, float(probas[2])),
    )
