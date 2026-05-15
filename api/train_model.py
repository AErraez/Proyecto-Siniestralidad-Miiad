"""
train_model.py — SPO-Bogotá: LightGBM Model Training
======================================================
Run this script to train the model and generate:
  - model.pkl          (LightGBM classifier)
  - kmeans.pkl         (KMeans spatial clustering)
  - feature_columns.pkl (ordered feature list)

Usage:
    python train_model.py --data base-anuario-de-siniestralidad-2024.xlsx

The Excel file must have sheets: Siniestros, Vehiculos
"""

import argparse
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import lightgbm as lgb
import joblib
import warnings
import os

warnings.filterwarnings("ignore")

# ── CLI ──────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--data", default="base-anuario-de-siniestralidad-2024.xlsx",
                    help="Path to the Excel file with Siniestros and Vehiculos sheets")
parser.add_argument("--output-dir", default=".", help="Where to write the .pkl files")
args = parser.parse_args()

# ── LOAD ─────────────────────────────────────────────────────────────────────
print(f"📂 Loading data from: {args.data}")
df_siniestros = pd.read_excel(args.data, sheet_name="Siniestros")
df_vehiculos  = pd.read_excel(args.data, sheet_name="Vehiculos")
print(f"   Siniestros: {df_siniestros.shape[0]:,} rows | Vehiculos: {df_vehiculos.shape[0]:,} rows")

# ── PREPROCESSING ─────────────────────────────────────────────────────────────
print("⚙️  Preprocessing...")

# 1. Vehicle count per incident
conteo_veh = (df_vehiculos.groupby("Codigo_Accidente")
              .size().reset_index(name="Num_Vehiculos_Involucrados"))
df_ml = df_siniestros.merge(conteo_veh, on="Codigo_Accidente", how="left")
df_ml["Num_Vehiculos_Involucrados"] = df_ml["Num_Vehiculos_Involucrados"].fillna(0)

# 2. Clean coordinates and hour
df_ml["Hora_Acc"] = pd.to_numeric(df_ml["Hora_Acc"], errors="coerce")
df_ml = df_ml.dropna(subset=["Hora_Acc", "Gravedad_Indicador_Tradicional",
                               "Latitud", "Longitud"])
# Bogotá bounding box
df_ml = df_ml[(df_ml["Latitud"]  > 4.4) & (df_ml["Latitud"]  < 4.9) &
              (df_ml["Longitud"] > -74.3) & (df_ml["Longitud"] < -73.9)]

# 3. Binarise Con_* columns (SI → 1, else → 0)
con_cols = [c for c in df_ml.columns if str(c).startswith("Con_")]
for col in con_cols:
    df_ml[col] = (df_ml[col] == "SI").astype(int)

# 4. Month as number
mapa_meses = {
    "Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4,
    "Mayo": 5, "Junio": 6, "Julio": 7, "Agosto": 8,
    "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12,
}
df_ml["Mes_Num"] = df_ml["MM_Acc"].map(mapa_meses)

print(f"   Clean dataset: {df_ml.shape[0]:,} rows")

# ── SPATIAL CLUSTERING ────────────────────────────────────────────────────────
print("🗺️  Fitting KMeans (15 clusters)...")
coords = df_ml[["Latitud", "Longitud"]]
kmeans = KMeans(n_clusters=15, random_state=42, n_init=10)
df_ml["Zona_Riesgo_Cluster"] = kmeans.fit_predict(coords)

# ── ONE-HOT ENCODING ──────────────────────────────────────────────────────────
df_final = df_ml.copy()
df_final = pd.get_dummies(df_final,
                          columns=["Dia_Semana_Acc", "Clase_Acc", "Zona_Riesgo_Cluster"],
                          drop_first=True)

# ── TARGET ────────────────────────────────────────────────────────────────────
mapa_target = {"Solo Daños": 0, "Con Heridos": 1, "Con Muertos": 2}
df_final["Target"] = df_final["Gravedad_Indicador_Tradicional"].map(mapa_target)

# ── FEATURE SELECTION ─────────────────────────────────────────────────────────
drop_cols = [
    "Gravedad_Indicador_Tradicional", "Gravedad_indicador_30d", "Target",
    "Codigo_Accidente", "Formulario", "Fecha_Acc", "Direccion",
    "Latitud", "Longitud", "MM_Acc", "Localidad",
    "Elemento_Choque", "Tipo_Objeto_Fijo", "AA_Acc", "DD_Mes_Acc", "Min_Acc",
]
X = df_final.drop(drop_cols, axis=1, errors="ignore")
X = X.select_dtypes(include=[np.number, bool])
y = df_final["Target"]

print(f"   Features: {X.shape[1]} | Target distribution:\n{y.value_counts().sort_index()}")

# ── TRAIN / TEST SPLIT ────────────────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42
)

# ── MODEL ─────────────────────────────────────────────────────────────────────
print("🚀 Training LightGBM...")
model = lgb.LGBMClassifier(
    class_weight="balanced",
    n_estimators=300,
    learning_rate=0.05,
    num_leaves=63,
    random_state=42,
    verbose=-1,
)
model.fit(X_train, y_train)

# ── EVALUATION ────────────────────────────────────────────────────────────────
y_pred = model.predict(X_test)
print("\n📊 Classification Report:")
print(classification_report(y_test, y_pred,
                             target_names=["Solo Daños", "Con Heridos", "Con Muertos"]))

# ── SAVE ARTIFACTS ────────────────────────────────────────────────────────────
os.makedirs(args.output_dir, exist_ok=True)
joblib.dump(model,                os.path.join(args.output_dir, "model.pkl"))
joblib.dump(kmeans,               os.path.join(args.output_dir, "kmeans.pkl"))
joblib.dump(X_train.columns.tolist(), os.path.join(args.output_dir, "feature_columns.pkl"))

print(f"\n✅ Saved to {args.output_dir}/")
print("   model.pkl, kmeans.pkl, feature_columns.pkl")

# ── STATS JSON ────────────────────────────────────────────────────────────────
import json

print("📊 Generating stats.json...")
meses_orden = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
               "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
monthly = []
for mes_name in meses_orden:
    mes_num = mapa_meses[mes_name]
    subset  = df_ml[df_ml["Mes_Num"] == mes_num]
    monthly.append({
        "mes":     mes_name[:3],
        "mes_num": mes_num,
        "fatales": int((subset["Gravedad_Indicador_Tradicional"] == "Con Muertos").sum()),
        "heridos": int((subset["Gravedad_Indicador_Tradicional"] == "Con Heridos").sum()),
        "danos":   int((subset["Gravedad_Indicador_Tradicional"] == "Solo Daños").sum()),
    })
with open(os.path.join(args.output_dir, "stats.json"), "w", encoding="utf-8") as f:
    json.dump({"monthly": monthly}, f, ensure_ascii=False)

# ── MAP DATA JSON ─────────────────────────────────────────────────────────────
print("🗺️  Generating map_data.json...")
SAMPLE_N = 3000
sev_map  = {"Solo Daños": 0, "Con Heridos": 1, "Con Muertos": 2}
df_map   = df_ml[["Latitud", "Longitud", "Gravedad_Indicador_Tradicional",
                   "Zona_Riesgo_Cluster"]].copy()
df_map["severity"] = df_map["Gravedad_Indicador_Tradicional"].map(sev_map)
df_map = df_map.dropna(subset=["severity"])

if len(df_map) > SAMPLE_N:
    df_map = (df_map.groupby("severity", group_keys=False)
              .apply(lambda x: x.sample(
                  min(len(x), max(1, int(SAMPLE_N * len(x) / len(df_map)))),
                  random_state=42)))

incidents = [
    {"lat": round(float(r.Latitud), 5),
     "lon": round(float(r.Longitud), 5),
     "severity": int(r.severity)}
    for r in df_map.itertuples()
]
clusters = [
    {"id": int(i), "lat": round(float(c[0]), 5), "lon": round(float(c[1]), 5)}
    for i, c in enumerate(kmeans.cluster_centers_)
]
with open(os.path.join(args.output_dir, "map_data.json"), "w", encoding="utf-8") as f:
    json.dump({"incidents": incidents, "clusters": clusters}, f)

print("✅ Generated stats.json and map_data.json")

# ── CLUSTER STATS JSON ────────────────────────────────────────────────────────
print("📊 Generating cluster_stats.json (last 6 months per cluster)...")
last6 = df_ml[df_ml["Mes_Num"] >= 7]
cluster_stats = {}
for cid in range(15):
    subset = last6[last6["Zona_Riesgo_Cluster"] == cid]
    cluster_stats[str(cid)] = {
        "fatales_6m": int((subset["Gravedad_Indicador_Tradicional"] == "Con Muertos").sum()),
        "heridos_6m": int((subset["Gravedad_Indicador_Tradicional"] == "Con Heridos").sum()),
        "total_6m":   int(len(subset)),
    }
with open(os.path.join(args.output_dir, "cluster_stats.json"), "w", encoding="utf-8") as f:
    json.dump(cluster_stats, f)
print("✅ Generated cluster_stats.json")
