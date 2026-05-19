# SPO-Bogotá — Predicción de Severidad de Siniestros Viales

---

## Problema

La Secretaría de Movilidad de Bogotá (SDM) registra miles de siniestros viales al año. El tiempo de respuesta ante un accidente depende en gran medida de la capacidad del operador para estimar la severidad del evento antes de que llegue la ambulancia.

Este proyecto proporciona un modelo de clasificación multiclase que, a partir de características del siniestro (ubicación, hora, actores involucrados, tipo de accidente), predice si el resultado será **solo daños materiales**, **con heridos** o **con muertos**, y emite una recomendación de acción operativa inmediata.

---

## Instalación

### Requisitos previos
- Python 3.9+
- pip

### Dependencias de la API

```bash
pip install -r api/requirements.txt
```

### Dependencias de desarrollo (DVC, entrenamiento)

```bash
pip install -r requirements-dev.txt
```

### Configurar remote de DVC (una sola vez por máquina)

```bash
# Apuntar al directorio local de OneDrive donde se almacenan los artefactos
dvc remote add -d onedrive "C:\Users\<tu-usuario>\OneDrive - Universidad de los Andes\Attachments\spo-bogota"
```

---

## Datos

El Excel de datos SDM **no está en git** — está versionado con [DVC](https://dvc.org) y almacenado en OneDrive. Los modelos `.pkl` y JSONs generados se producen localmente al entrenar.

### Obtener el Excel por primera vez

```bash
dvc pull
```

### Actualizar el dataset (nueva versión del Excel)

```bash
dvc add data/base-anuario-de-siniestralidad.xlsx
git add data/base-anuario-de-siniestralidad.xlsx.dvc
git commit -m "actualizar datos siniestralidad 2025"
dvc push  # copia al directorio OneDrive configurado
```

### Variables del modelo (49 features)

| Grupo | Variables |
|-------|-----------|
| Temporal | `Hora_Acc`, `Mes_Num` |
| Operacional | `Num_Vehiculos_Involucrados` |
| Actores (binario) | `Con_Moto`, `Con_Peaton`, `Con_Bicicleta`, `Con_Velocidad`, `Con_Embriaguez`, `Con_Carga`, `Con_Menores`, `Con_Persona_Mayor`, `Con_Rutas`, `Con_Tpi`, `Con_Tpp`, `Con_Sitp`, `Con_Troncal`, `Con_Alimentador`, `Con_Zonal`, `Con_Provisional`, `Con_Articulado`, `Con_Biarticulado`, `Con_Padron_Dual`, `Con_Servicio_Especial`, `Con_Taxi` |
| Día (one-hot) | `Dia_Semana_Acc_jueves/lunes/martes/miércoles/sábado/viernes` |
| Clase (one-hot) | `Clase_Acc_Caida de ocupante/Choque/Otro/Volcamiento` |
| Cluster (one-hot) | `Zona_Riesgo_Cluster_1` ... `Zona_Riesgo_Cluster_14` |

### Variable objetivo (target)

| Valor | Clase | Descripción |
|-------|-------|-------------|
| 0 | Solo Daños | Solo daños materiales |
| 1 | Con Heridos | Al menos un herido |
| 2 | Con Muertos | Al menos una fatalidad |

---

## Ejecución

### 1 — Entrenar el modelo

```bash
cd api
python train_model.py --data ../data/base-anuario-de-siniestralidad.xlsx
```

Genera localmente: `model.pkl` (LightGBM), `kmeans.pkl` (15 clústeres espaciales), `feature_columns.pkl`, `stats.json`, `map_data.json`, `cluster_stats.json`.

### 2 — Levantar la API

```bash
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

- API: http://localhost:8000
- Swagger: http://localhost:8000/docs

#### Ejemplo de llamada

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

### 3 — Abrir el dashboard

1. Abre `dashboard/dashboard.html` en el navegador
2. Verifica que la URL de la API apunta a `http://localhost:8000`
3. Ingresa los datos del siniestro y presiona **Calcular Riesgo**

---

## Despliegue en AWS EC2

### 1 — Crear y acceder a la instancia

**Crear instancia EC2**
- AWS Console → EC2 → Launch Instance
- AMI: Ubuntu | Tipo: t3.micro | Almacenamiento: 20 GB
- Crear o seleccionar una llave `.pem` para SSH
- Abrir puertos: `22` (SSH), `80` (Dashboard), `8001` (API)

**Conectarse vía SSH**

```bash
ssh -i /path/to/llave.pem ubuntu@IP_PUBLICA
```

---

### 2 — Instalar Docker

```bash
# Eliminar versiones antiguas
sudo apt-get remove docker docker-engine docker.io containerd runc -y

# Actualizar e instalar dependencias
sudo apt-get update
sudo apt-get install ca-certificates curl gnupg -y

# Agregar clave GPG y repositorio oficial de Docker
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Instalar Docker Engine
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -y
```

---

### 3 — Descargar el código y levantar los contenedores

```bash
# Clonar repositorio
git clone https://github.com/AErraez/Proyecto-Development
cd Proyecto-Development

# Construir y ejecutar
sudo docker compose up -d --build
```

Una vez levantados, acceder desde el navegador:

| Servicio | URL |
|----------|-----|
| Dashboard | `http://IP_PUBLICA:80` |
| API | `http://IP_PUBLICA:8001` |

---

## Resultados

El modelo devuelve una clasificación con probabilidades por clase y una recomendación operativa:

```json
{
  "clase_predicha": 1,
  "etiqueta": "Con Heridos",
  "prob_solo_danos": 0.2341,
  "prob_con_heridos": 0.6112,
  "prob_con_muertos": 0.1547,
  "zona_cluster": 7,
  "accion_recomendada": "PRIORIDAD ALTA — Despacho de Ambulancia de Soporte Vital Básico."
}
```

---

## Estructura

```
spo-bogota/
├── api/
│   ├── train_model.py           ← Entrena y guarda los .pkl
│   ├── api.py                   ← Servidor FastAPI
│   ├── requirements.txt         ← Dependencias Python de la API
│   ├── model.pkl                ← Modelo LightGBM (generado al entrenar)
│   ├── kmeans.pkl               ← Clustering espacial (generado al entrenar)
│   ├── feature_columns.pkl      ← Orden de columnas (generado al entrenar)
│   ├── stats.json               ← Estadísticas mensuales (generado al entrenar)
│   ├── map_data.json            ← Datos del mapa (generado al entrenar)
│   └── cluster_stats.json       ← Estadísticas por clúster (generado al entrenar)
├── data/
│   └── base-anuario-de-siniestralidad.xlsx  ← (DVC) Datos SDM
├── dashboard/
│   ├── dashboard.html           ← Interfaz web del simulador
│   ├── dashboard.js
│   └── dashboard.css
└── requirements-dev.txt         ← Dependencias de desarrollo (DVC)
```

---

## Equipo

| Nombre           |
|------------------|
|Ariel Erráez      |
|Delio Hoyos       |
|Leonardo Palencia |
|Edgar González    |
