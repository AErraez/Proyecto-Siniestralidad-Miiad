import argparse
import os
import warnings
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.model_selection import train_test_split
from sklearn.metrics import recall_score, f1_score, accuracy_score, roc_curve, auc
from sklearn.preprocessing import label_binarize
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
import lightgbm as lgb
import mlflow
import mlflow.sklearn
import mlflow.lightgbm

warnings.filterwarnings("ignore")

# ARGUMENTOS DE LÍNEA DE COMANDOS
parser = argparse.ArgumentParser()
parser.add_argument("--data",       default=os.path.join(os.path.dirname(__file__), "../data/base-anuario-de-siniestralidad.xlsx"),
                    help="Ruta al Excel con las hojas Siniestros y Vehiculos")
parser.add_argument("--experiment", default="siniestros-severidad",
                    help="Nombre del experimento en MLflow")
args = parser.parse_args()

# CARGA DE DATOS
print(f"Cargando datos desde: {args.data}")
df_siniestros = pd.read_excel(args.data, sheet_name="Siniestros")
df_vehiculos  = pd.read_excel(args.data, sheet_name="Vehiculos")
print(f"   Siniestros: {df_siniestros.shape[0]:,} filas | Vehículos: {df_vehiculos.shape[0]:,} filas")

# PREPROCESAMIENTO
print("Preprocesando datos...")

conteo_veh = (df_vehiculos.groupby("Codigo_Accidente")
              .size().reset_index(name="Num_Vehiculos_Involucrados"))
df_ml = df_siniestros.merge(conteo_veh, on="Codigo_Accidente", how="left")
df_ml["Num_Vehiculos_Involucrados"] = df_ml["Num_Vehiculos_Involucrados"].fillna(0)

df_ml["Hora_Acc"] = pd.to_numeric(df_ml["Hora_Acc"], errors="coerce")
df_ml = df_ml.dropna(subset=["Hora_Acc", "Gravedad_Indicador_Tradicional", "Latitud", "Longitud"])

# Filtramos solo puntos dentro del área geográfica de Bogotá
df_ml = df_ml[(df_ml["Latitud"]  > 4.4) & (df_ml["Latitud"]  < 4.9) &
              (df_ml["Longitud"] > -74.3) & (df_ml["Longitud"] < -73.9)]

# Convertimos las columnas Con_* a binario (SI → 1, cualquier otra cosa → 0)
for col in [c for c in df_ml.columns if str(c).startswith("Con_")]:
    df_ml[col] = (df_ml[col] == "SI").astype(int)

mapa_meses = {
    "Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4,
    "Mayo": 5, "Junio": 6, "Julio": 7, "Agosto": 8,
    "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12,
}
df_ml["Mes_Num"] = df_ml["MM_Acc"].map(mapa_meses)
print(f"   Dataset limpio: {df_ml.shape[0]:,} filas")

# CLUSTERING ESPACIAL
print("🗺️  Ajustando KMeans (15 clústeres)...")
coords = df_ml[["Latitud", "Longitud"]]
kmeans = KMeans(n_clusters=15, random_state=42, n_init=10)
df_ml["Zona_Riesgo_Cluster"] = kmeans.fit_predict(coords)

# CODIFICACIÓN ONE-HOT
df_final = pd.get_dummies(df_ml.copy(),
                          columns=["Dia_Semana_Acc", "Clase_Acc", "Zona_Riesgo_Cluster"],
                          drop_first=True)

# VARIABLE OBJETIVO
mapa_target = {"Solo Daños": 0, "Con Heridos": 1, "Con Muertos": 2}
df_final["Target"] = df_final["Gravedad_Indicador_Tradicional"].map(mapa_target)

# SELECCIÓN DE VARIABLES
drop_cols = [
    "Gravedad_Indicador_Tradicional", "Gravedad_indicador_30d", "Target",
    "Codigo_Accidente", "Formulario", "Fecha_Acc", "Direccion",
    "Latitud", "Longitud", "MM_Acc", "Localidad",
    "Elemento_Choque", "Tipo_Objeto_Fijo", "AA_Acc", "DD_Mes_Acc", "Min_Acc",
]
X = df_final.drop(drop_cols, axis=1, errors="ignore").select_dtypes(include=[np.number, bool])
y = df_final["Target"]

print(f"   Features: {X.shape[1]} | Distribución del target:\n{y.value_counts().sort_index()}")

# DIVISIÓN ENTRENAMIENTO / PRUEBA
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42)

# MODELOS A COMPARAR
MODELOS = {
    "logistic_regression": LogisticRegression(class_weight="balanced", max_iter=2000, random_state=42),
    "decision_tree":       DecisionTreeClassifier(class_weight="balanced", max_depth=60, random_state=42),
    "random_forest":       RandomForestClassifier(class_weight="balanced", n_estimators=100,
                                                  max_depth=60, random_state=42),
    "lightgbm":            lgb.LGBMClassifier(class_weight="balanced", n_estimators=200,
                                              learning_rate=0.001, num_leaves=32,
                                              random_state=42, verbose=-1),
}

# EXPERIMENTOS MLFLOW
from pathlib import Path
mlflow.set_tracking_uri(Path(os.path.join(os.path.dirname(__file__), "mlruns")).resolve().as_uri())
mlflow.set_experiment(args.experiment)

y_test_bin  = label_binarize(y_test, classes=[0, 1, 2])
best_recall = -1
best_model  = None
best_name   = None

print(f"\nCorriendo experimentos MLflow (experimento: '{args.experiment}')...")
print(f"   {'Modelo':<30} {'recall_muertos':>14} {'auc_muertos':>12} {'accuracy':>10}")
print(f"   {'-'*70}")

for nombre, modelo in MODELOS.items():
    params = modelo.get_params()

    KEY_PARAMS = {
        "logistic_regression": ["C", "max_iter"],
        "decision_tree":       ["max_depth"],
        "random_forest":       ["n_estimators", "max_depth"],
        "lightgbm":            ["n_estimators", "learning_rate", "num_leaves"],
    }
    key_p = KEY_PARAMS.get(nombre, [])
    params_str = "_".join(f"{k}={params[k]}" for k in key_p if k in params)
    run_name = f"{nombre}__{params_str}" if params_str else nombre

    with mlflow.start_run(run_name=run_name):
        mlflow.set_tag("model_name", nombre)
        mlflow.set_tag("dataset", os.path.basename(args.data))
        mlflow.set_tag("target", "Gravedad_Indicador_Tradicional")

        mlflow.log_params(params)
        mlflow.log_param("model_type",  nombre)
        mlflow.log_param("test_size",   0.2)
        mlflow.log_param("n_features",  X_train.shape[1])
        mlflow.log_param("n_clusters",  15)
        mlflow.log_param("random_state", 42)

        modelo.fit(X_train, y_train)
        y_pred  = modelo.predict(X_test)
        y_proba = modelo.predict_proba(X_test)

        recalls     = recall_score(y_test, y_pred, average=None)
        f1s         = f1_score(y_test,    y_pred, average=None)
        acc         = accuracy_score(y_test, y_pred)
        fpr, tpr, _ = roc_curve(y_test_bin[:, 2], y_proba[:, 2])
        auc_muertos = auc(fpr, tpr)

        mlflow.log_metric("accuracy",       acc)
        mlflow.log_metric("recall_danos",   recalls[0])
        mlflow.log_metric("recall_heridos", recalls[1])
        mlflow.log_metric("recall_muertos", recalls[2])
        mlflow.log_metric("f1_danos",       f1s[0])
        mlflow.log_metric("f1_heridos",     f1s[1])
        mlflow.log_metric("f1_muertos",     f1s[2])
        mlflow.log_metric("auc_muertos",    auc_muertos)

        if nombre == "lightgbm":
            mlflow.lightgbm.log_model(modelo, nombre)
        else:
            mlflow.sklearn.log_model(modelo, nombre)

        print(f"   {nombre:<30} {recalls[2]:>14.3f} {auc_muertos:>12.3f} {acc:>10.3f}")

        if recalls[2] > best_recall:
            best_recall = recalls[2]
            best_model  = modelo
            best_name   = nombre

print(f"\nMejor modelo: {best_name} (recall_muertos={best_recall:.3f})")
print(f"\nPara ver los experimentos: mlflow ui")
print(f"   Para producción, corre: cd ../website/api && python train_model.py")
