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

## Research & Machine Learning Benchmark (Point 6)

The comprehensive research report, methodology, and 14-algorithm comparative study on **397,870 genuine respondents** from the **CDC BRFSS 2023** survey is documented in [RESEARCH_REPORT.md](RESEARCH_REPORT.md).

### Top Performing Algorithms Summary (Untouched 20% Test Dataset, N=6,000)

| Rank | Algorithm | Test ROC-AUC | Test Balanced Acc | Sensitivity (Recall) | Specificity | F1 Score | Weighted ROC-AUC |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | **Logistic Regression (Balanced)** | **0.8522** | **0.7697** | **0.8031** | **0.7363** | **0.3474** | **0.8920** |
| **2** | **CatBoost Classifier** | **0.8522** | **0.7638** | **0.7914** | **0.7361** | **0.3431** | **0.8886** |
| 3 | Calibrated Support Vector Machine | 0.8522 | 0.5598 | 0.1306 | 0.9891 | 0.2094 | 0.8922 |
| 4 | Stacking Classifier (Meta LR) | 0.8519 | 0.5412 | 0.0877 | 0.9947 | 0.1533 | 0.8896 |
| 5 | Gradient Boosting (GBDT) | 0.8515 | 0.5629 | 0.1345 | 0.9913 | 0.2190 | 0.8837 |
| 6 | XGBoost Classifier | 0.8506 | 0.7660 | 0.7953 | 0.7367 | 0.3449 | 0.8846 |
| 7 | LightGBM Classifier | 0.8493 | 0.7663 | 0.7778 | 0.7549 | 0.3536 | 0.8854 |
| 8 | Tree-Weighted Random Forest (TWRF) | 0.8431 | 0.5228 | 0.0468 | 0.9987 | 0.0882 | 0.8772 |
| 9 | Random Forest (Balanced) | 0.8420 | 0.7673 | 0.8012 | 0.7334 | 0.3444 | 0.8772 |
| 10 | Extra Trees Classifier | 0.8416 | 0.7631 | 0.7973 | 0.7290 | 0.3396 | 0.8769 |
| 11 | Enriched Random Forest (ERF) | 0.8404 | 0.5314 | 0.0702 | 0.9927 | 0.1222 | 0.8735 |
| 12 | CART Decision Tree (Gini) | 0.8214 | 0.7560 | 0.8304 | 0.6816 | 0.3172 | 0.8611 |
| 13 | AdaBoost Classifier | 0.8189 | 0.5000 | 0.0000 | 1.0000 | 0.0000 | 0.8600 |
| 14 | Entropy Decision Tree | 0.8152 | 0.7420 | 0.8051 | 0.6789 | 0.3073 | 0.8146 |

---

## Google Colab Research Notebooks Directory

The 13 dedicated, self-contained Google Colab notebooks are organized in [`notebooks/`](notebooks/):

| Notebook | Focus | Colab Launcher |
| :--- | :--- | :---: |
| **01. Dataset Collection** | Ingestion of raw CDC BRFSS 2023 SAS XPT data & codebook verification. | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/AbhinavYaduvanshi/HeartAI/blob/main/notebooks/01_dataset_collection.ipynb) |
| **02. Exploratory Data Analysis** | Physiological distributions, demographic risk stratification, correlation heatmaps. | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/AbhinavYaduvanshi/HeartAI/blob/main/notebooks/02_exploratory_data_analysis.ipynb) |
| **03. Data Preprocessing** | Zero-leakage ColumnTransformer, median imputation, physiological clipping, scaling. | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/AbhinavYaduvanshi/HeartAI/blob/main/notebooks/03_data_preprocessing.ipynb) |
| **04. Bagging Algorithms** | Comparative benchmarking of Random Forest and Extra Trees. | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/AbhinavYaduvanshi/HeartAI/blob/main/notebooks/04_bagging_algorithms.ipynb) |
| **05. Boosting Algorithms** | AdaBoost, Gradient Boosting (GBDT), XGBoost, LightGBM, and CatBoost. | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/AbhinavYaduvanshi/HeartAI/blob/main/notebooks/05_boosting_algorithms.ipynb) |
| **06. Decision Trees** | CART (Gini impurity) vs. Entropy-based Decision Trees. | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/AbhinavYaduvanshi/HeartAI/blob/main/notebooks/06_decision_tree_algorithms.ipynb) |
| **07. Stacking Ensemble** | Multi-model stacking combining linear, tree, and boosting base estimators. | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/AbhinavYaduvanshi/HeartAI/blob/main/notebooks/07_stacking_algorithms.ipynb) |
| **08. Custom Ensembles** | Implementation of Enriched Random Forest (ERF) & Tree-Weighted RF (TWRF). | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/AbhinavYaduvanshi/HeartAI/blob/main/notebooks/08_custom_ensemble_algorithms.ipynb) |
| **09. Hyperparameter Tuning** | 5-Fold Stratified Cross-Validation with RandomizedSearchCV. | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/AbhinavYaduvanshi/HeartAI/blob/main/notebooks/09_hyperparameter_tuning.ipynb) |
| **10. Model Evaluation** | ROC curves, PR-AUC, Brier score, and reliability calibration curves. | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/AbhinavYaduvanshi/HeartAI/blob/main/notebooks/10_model_evaluation.ipynb) |
| **11. Model Explainability** | SHAP TreeExplainer, feature importance rankings, demographic fairness parity checks. | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/AbhinavYaduvanshi/HeartAI/blob/main/notebooks/11_model_explainability.ipynb) |
| **12. Model Comparison** | Comprehensive multi-metric ranking and latency benchmarks. | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/AbhinavYaduvanshi/HeartAI/blob/main/notebooks/12_model_comparison.ipynb) |
| **13. Model Export** | SHA-256 verified artifact packaging and Google Drive export synchronization. | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/AbhinavYaduvanshi/HeartAI/blob/main/notebooks/13_model_export.ipynb) |

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
       repo="AbhinavYaduvanshi/HeartAI",
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

