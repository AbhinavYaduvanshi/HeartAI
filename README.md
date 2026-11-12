# HeartAI — AI-Powered Cardiovascular Risk Prediction & Analytics

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.133+-009688.svg)](https://fastapi.tiangolo.com/)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)]()

HeartAI is an enterprise-grade artificial intelligence platform for continuous cardiovascular disease risk stratification, telemetry analytics, and interactive healthcare insights.

This architecture decouples the training and serving lifecycle:
* **Training & Research Environment:** **Google Colab** (with T4/V100/A100 GPU acceleration and Google Drive integration).
* **Development & Serving Environment:** **Antigravity IDE** (FastAPI backend, multi-format model registry, NiceGUI UI, and GSAP/ScrollTrigger motion engine).
* **Model Transfer Pipeline:** Cryptographic SHA-256 verified model artifacts synchronized via **Google Drive** or **GitHub Releases**.

---

## Architecture Overview

```
 ┌────────────────────────────────────────────────────────┐
 │               GOOGLE COLAB (Cloud ML)                  │
 │  1. data_preprocessing.ipynb                           │
 │  2. exploratory_data_analysis.ipynb                    │
 │  3. heart_disease_model_training.ipynb (GPU Accelerated)│
 │  4. model_evaluation.ipynb                             │
 │  5. model_export.ipynb                                 │
 └──────────────────────────┬─────────────────────────────┘
                            │ Serializes: model.joblib / .pt
                            │ Generates: metadata.json + SHA-256
                            ▼
 ┌────────────────────────────────────────────────────────┐
 │          TRANSFER INFRASTRUCTURE                      │
 │    • Google Drive (MyDrive/HeartAI/models/<id>/)       │
 │    • GitHub Releases (`gh release download`)           │
 └──────────────────────────┬─────────────────────────────┘
                            │ transfer_sync.py
                            ▼
 ┌────────────────────────────────────────────────────────┐
 │           ANTIGRAVITY IDE (Serving & Web App)          │
 │  • app/ml/model_loader.py    (SHA-256 verification)   │
 │  • app/ml/model_registry.py  (Multi-version registry)  │
 │  • app/ml/predict.py         (Continuous risk engine)  │
 │  • main.py                   (FastAPI REST endpoints)  │
 │  • static/ (js/css)          (GSAP & Motion system)    │
 └────────────────────────────────────────────────────────┘
```

---

## Google Colab Training Notebooks

All training, exploration, and model serialization workflows are split into 5 modular, Colab-ready notebooks in [`notebooks/`](notebooks/):

| Notebook | Purpose | Colab Launcher |
| :--- | :--- | :---: |
| **1. Data Preprocessing** | Missing value imputation, standard scaling, and stratified train/val/test splits. | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/24abh/HeartAI/blob/main/notebooks/data_preprocessing.ipynb) |
| **2. Exploratory Data Analysis** | Physiological distributions (BP, cholesterol, max HR), KDE plots, correlation matrices. | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/24abh/HeartAI/blob/main/notebooks/exploratory_data_analysis.ipynb) |
| **3. Model Training** | Trains Random Forest, XGBoost (`XGBClassifier`), and PyTorch Deep MLP (`CardiacDeepNet`). | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/24abh/HeartAI/blob/main/notebooks/heart_disease_model_training.ipynb) |
| **4. Model Evaluation** | ROC-AUC, confusion matrices, sensitivity (recall), specificity, and Brier calibration curves. | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/24abh/HeartAI/blob/main/notebooks/model_evaluation.ipynb) |
| **5. Model Export & Integrity** | Computes SHA-256 digests and outputs `model.joblib` and canonical `metadata.json` to Drive. | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/24abh/HeartAI/blob/main/notebooks/model_export.ipynb) |

---

## Step-by-Step ML Training & Transfer Guide

### Step 1: Open Notebooks in Google Colab
1. Navigate to the desired notebook in GitHub or click any **"Open in Colab"** badge above.
2. Select **File $\to$ Save a copy in Drive** to preserve your training outputs.

### Step 2: Enable GPU Hardware Acceleration
For PyTorch neural network training or XGBoost GPU tree methods:
1. In Colab, click **Runtime $\to$ Change runtime type**.
2. Under **Hardware accelerator**, select **T4 GPU** (or A100 / V100 if available on Colab Pro).
3. Click **Save**.
4. The notebook verifies GPU availability automatically via `torch.cuda.is_available()`.

### Step 3: Train and Evaluate Models
1. Execute `notebooks/data_preprocessing.ipynb` to process the benchmark dataset into `/content/drive/MyDrive/HeartAI/data/`.
2. Run `notebooks/heart_disease_model_training.ipynb` to train models with 5-fold cross-validation.
3. Run `notebooks/model_evaluation.ipynb` to inspect ROC curves, sensitivity/specificity tradeoffs, and calibration metrics.

### Step 4: Export Model to Google Drive
Run `notebooks/model_export.ipynb`:
1. It mounts your Google Drive securely via `google.colab.drive.mount('/content/drive')`.
2. Serializes the model artifact (`model.joblib` or `model.pt`).
3. Computes the cryptographic **SHA-256 checksum** of the serialized weights.
4. Generates a schema-validated `metadata.json` manifest specifying feature boundaries, performance metrics, and framework versions.
5. Files are written to `/content/drive/MyDrive/HeartAI/models/<model_id>/`.

---

## Transferring Models into Antigravity IDE

### Method A: Direct Google Drive Sync (Recommended for Local Dev)
If you have Google Drive for Desktop installed or have synced your Drive folder locally:

```python
from app.ml.transfer_sync import transfer_manager

# Sync from local Google Drive mount into Antigravity IDE
metadata = transfer_manager.import_from_drive(
    drive_model_folder="G:/My Drive/HeartAI/models/heartai-xgboost-v1",
    set_active=True
)
print(f"Loaded {metadata.model_name} (v{metadata.version})")
```

Alternatively, call the FastAPI sync endpoint:
```bash
curl -X POST "http://localhost:8000/api/v1/models/sync-drive" \
     -H "Content-Type: application/json" \
     -d '{"source_dir": "G:/My Drive/HeartAI/models/heartai-xgboost-v1", "set_active": true}'
```

### Method B: GitHub Releases (CI/CD Automated Sync)
For versioned team releases:
1. Tag and push a release on GitHub containing `model.joblib` and `metadata.json`:
   ```bash
   gh release create v1.0.0 ./export/* --title "HeartAI XGBoost v1.0.0" --notes "Clinical validation ROC-AUC 0.942"
   ```
2. In Antigravity IDE, trigger release synchronization:
   ```python
   from app.ml.transfer_sync import transfer_manager

   transfer_manager.import_from_github_release(
       repo="24abh/HeartAI",
       tag="v1.0.0",
       set_active=True
   )
   ```

---

## Local Development & Inference

### 1. Environment Setup
The development environment is configured with Python 3.12 in `.venv`:
```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1
```

### 2. Start the FastAPI API Server
```powershell
.\.venv\Scripts\python.exe main.py
```
* **Interactive API Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **Alternative ReDoc UI:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

### 3. Example Clinical Inference Request
```bash
curl -X POST "http://localhost:8000/api/v1/predict" \
     -H "Content-Type: application/json" \
     -d '{
       "age": 62,
       "sex": 1,
       "cp": 3,
       "trestbps": 158,
       "chol": 284,
       "fbs": 1,
       "restecg": 2,
       "thalach": 118,
       "exang": 1,
       "oldpeak": 2.8,
       "slope": 2,
       "ca": 2,
       "thal": 3
     }'
```

**Response:**
```json
{
  "risk_score": 0.865,
  "risk_category": "High Risk",
  "prediction": 1,
  "confidence": 0.865,
  "model_id": "heartai-rf-v1",
  "model_version": "1.0.0",
  "clinical_factors": [
    "Elevated Systolic Blood Pressure (158.0 mmHg)",
    "Hypercholesterolemia (284.0 mg/dl)",
    "Exercise-Induced Angina Present",
    "Significant ST-Segment Depression (2.8 mm)",
    "Fluoroscopy Visualized Fluoroscopy Calcification (2 vessels)"
  ],
  "recommendations": [
    "Urgent cardiology consultation recommended.",
    "Order comprehensive 12-lead diagnostic ECG and stress echocardiography.",
    "Evaluate coronary angiography suitability."
  ],
  "timestamp": "2026-11-12T11:30:00Z"
}
```

---

## Code Quality & Testing

HeartAI enforces strict test coverage and linting standards:

```powershell
# Run Ruff linting and formatting verification
.\.venv\Scripts\python.exe -m ruff check .

# Run complete pytest test suite (20 automated tests)
.\.venv\Scripts\python.exe -m pytest -v
```

---

## Data Privacy & Clinical Security Compliance

- **Zero Clinical Data in VCS:** All clinical benchmarks, CSV files, and DICOM imaging are barred by `.gitignore`.
- **Cryptographic Model Verification:** All imported model bundles require matching SHA-256 digests before execution.
- **Strict Boundary Checks:** The model loader rejects unrecognized architectures and ensures inputs conform to canonical physiological boundaries.
- **Safe Heuristic Fallbacks:** If a machine learning model is unavailable, the inference pipeline automatically engages a clinical Framingham-based baseline estimator to prevent silent server failure.
