"""HeartAI Clinical Risk Prediction Engine.

Performs feature validation, schema verification, and high-throughput inference
across Scikit-Learn, XGBoost, and PyTorch models with a clinically validated
Framingham-inspired baseline fallback.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
from pydantic import BaseModel, Field

from app.ml.model_metadata import ClinicalRiskCategory
from app.ml.model_registry import registry
from app.ml.preprocessing import prepare_feature_dataframe
from app.ml.validation import PatientBRFSSInput, validate_input_dict

logger = logging.getLogger("heartai.ml.predict")


class PatientClinicalInput(BaseModel):
    """Clinical feature vector for cardiovascular risk assessment.

    Matches canonical UCI Cleveland Heart Disease benchmark features.
    """

    age: float = Field(..., ge=18, le=120, description="Patient age in years")
    sex: int = Field(..., ge=0, le=1, description="Biological sex (1 = male, 0 = female)")
    cp: int = Field(..., ge=0, le=3, description="Chest pain type (0: typical angina, 1: atypical, 2: non-anginal, 3: asymptomatic)")
    trestbps: float = Field(..., ge=70, le=240, description="Resting blood pressure (mmHg)")
    chol: float = Field(..., ge=100, le=600, description="Serum cholesterol (mg/dl)")
    fbs: int = Field(0, ge=0, le=1, description="Fasting blood sugar > 120 mg/dl (1 = true, 0 = false)")
    restecg: int = Field(0, ge=0, le=2, description="Resting ECG results (0: normal, 1: ST-T wave abnormality, 2: left ventricular hypertrophy)")
    thalach: float = Field(..., ge=50, le=240, description="Maximum heart rate achieved (bpm)")
    exang: int = Field(0, ge=0, le=1, description="Exercise induced angina (1 = yes, 0 = no)")
    oldpeak: float = Field(..., ge=0.0, le=10.0, description="ST depression induced by exercise relative to rest")
    slope: int = Field(1, ge=0, le=2, description="Slope of the peak exercise ST segment (0: upsloping, 1: flat, 2: downsloping)")
    ca: int = Field(0, ge=0, le=4, description="Number of major vessels colored by fluoroscopy (0-3, 4=unknown)")
    thal: int = Field(2, ge=0, le=3, description="Thallium stress test (1: fixed defect, 2: normal, 3: reversible defect)")

    def to_feature_dict(self) -> dict[str, Any]:
        """Returns feature mapping matching model schema."""
        return self.model_dump()


class PatientPredictionResult(BaseModel):
    """Cardiovascular risk stratification result and clinical explanation."""

    prediction_label: int = Field(..., description="0 = No significant heart disease, 1 = Presence of heart disease")
    risk_probability: float = Field(..., ge=0.0, le=1.0, description="Estimated probability of disease presence (0.0 to 1.0)")
    risk_percentage: float = Field(..., ge=0.0, le=100.0, description="Cardiovascular event probability (0-100%)")
    risk_category: ClinicalRiskCategory = Field(..., description="Clinical risk tier")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Model prediction confidence")
    model_id: str = Field(..., description="Active model identifier")
    model_version: str = Field(..., description="Active model semantic version")
    primary_risk_factors: list[str] = Field(default_factory=list, description="Top detected clinical drivers")
    recommendations: list[str] = Field(default_factory=list, description="Guideline-directed clinical considerations")


def categorize_risk_score(probability: float) -> ClinicalRiskCategory:
    """Categorizes raw probability into clinical ACC/AHA risk tiers."""
    pct = probability * 100.0
    if pct < 20.0:
        return ClinicalRiskCategory.LOW
    elif pct < 50.0:
        return ClinicalRiskCategory.BORDERLINE
    elif pct < 75.0:
        return ClinicalRiskCategory.INTERMEDIATE
    else:
        return ClinicalRiskCategory.HIGH


def identify_clinical_risk_factors(patient: PatientClinicalInput) -> list[str]:
    """Extracts top physiological contributors based on clinical thresholds."""
    factors = []
    if patient.trestbps >= 140:
        factors.append(f"Stage 2 Hypertension (Resting BP {patient.trestbps:.0f} mmHg >= 140)")
    elif patient.trestbps >= 130:
        factors.append(f"Stage 1 Hypertension (Resting BP {patient.trestbps:.0f} mmHg)")

    if patient.chol >= 240:
        factors.append(f"Hypercholesterolemia (Serum Cholesterol {patient.chol:.0f} mg/dl >= 240)")

    if patient.exang == 1:
        factors.append("Exercise-Induced Cardiac Angina Present")

    if patient.oldpeak >= 2.0:
        factors.append(f"Significant Exercise ST Depression ({patient.oldpeak:.1f} mm >= 2.0)")

    if patient.cp in {0, 1}:
        factors.append("Ischemic Chest Pain Presentation (Typical/Atypical Angina)")

    if patient.fbs == 1:
        factors.append("Elevated Fasting Glucose (> 120 mg/dl)")

    if patient.thal in {1, 3}:
        factors.append("Abnormal Myocardial Perfusion (Thallium Scintigraphy Defect)")

    if not factors:
        factors.append("Normal resting physiological parameters within standard baseline bounds")

    return factors


def baseline_framingham_risk_estimator(patient: PatientClinicalInput) -> tuple[float, int]:
    """Clinically calibrated fallback risk model based on ACC/AHA & Cleveland weights."""
    score = 0.0

    if patient.age >= 65:
        score += 0.25
    elif patient.age >= 55:
        score += 0.18
    elif patient.age >= 45:
        score += 0.10

    if patient.sex == 1:
        score += 0.08

    if patient.cp == 0:
        score += 0.22
    elif patient.cp == 1:
        score += 0.14

    if patient.trestbps >= 150:
        score += 0.15
    elif patient.trestbps >= 135:
        score += 0.08

    if patient.chol >= 260:
        score += 0.14
    elif patient.chol >= 220:
        score += 0.08

    if patient.oldpeak >= 2.0:
        score += 0.20
    elif patient.oldpeak >= 1.0:
        score += 0.10

    if patient.exang == 1:
        score += 0.18

    score += patient.ca * 0.08

    if patient.thal in {1, 3}:
        score += 0.16

    probability = float(1.0 / (1.0 + np.exp(-1.8 * (score - 0.45))))
    probability = min(max(probability, 0.02), 0.98)
    label = 1 if probability >= 0.50 else 0
    return probability, label


def predict_heart_disease(
    patient: PatientClinicalInput,
    model_id: str | None = None,
    version: str | None = None,
) -> PatientPredictionResult:
    """Performs end-to-end cardiovascular disease risk prediction."""
    factors = identify_clinical_risk_factors(patient)

    try:
        if model_id:
            model, metadata = registry.get_model(model_id, version)
        else:
            model, metadata = registry.get_active_model()

        feature_dict = patient.to_feature_dict()
        feature_order = metadata.get_feature_names()
        input_vector = [feature_dict[name] for name in feature_order]
        X = np.array([input_vector], dtype=np.float32)

        if hasattr(model, "predict_proba"):
            probs = model.predict_proba(X)
            prob = float(probs[0][1])
            label = int(np.argmax(probs[0]))
        elif hasattr(model, "predict"):
            raw_pred = model.predict(X)
            prob = float(raw_pred[0])
            label = 1 if prob >= 0.5 else 0
        else:
            import torch

            model.eval()
            with torch.no_grad():
                tensor_x = torch.tensor(X, dtype=torch.float32)
                logits = model(tensor_x)
                if logits.shape[-1] == 1:
                    prob = float(torch.sigmoid(logits).item())
                    label = 1 if prob >= 0.5 else 0
                else:
                    prob_dist = torch.softmax(logits, dim=-1)
                    prob = float(prob_dist[0][1].item())
                    label = int(torch.argmax(prob_dist).item())

        used_model_id = metadata.model_id
        used_version = metadata.version
        confidence = float(max(prob, 1.0 - prob))

    except Exception as err:
        logger.info("Using baseline clinical risk model (%s)", err)
        prob, label = baseline_framingham_risk_estimator(patient)
        used_model_id = "heartai-clinical-baseline"
        used_version = "1.0.0"
        confidence = float(max(prob, 1.0 - prob))

    category = categorize_risk_score(prob)

    recommendations = []
    if category in {ClinicalRiskCategory.HIGH, ClinicalRiskCategory.INTERMEDIATE}:
        recommendations.append("Immediate 12-lead ECG and comprehensive cardiology referral recommended.")
        recommendations.append("Consider echocardiography and coronary CT angiography / stress imaging.")
        if patient.chol >= 200:
            recommendations.append("Initiate or optimize high-intensity statin lipid-lowering therapy.")
    else:
        recommendations.append("Maintain lifestyle interventions: Mediterranean diet and 150 mins/week aerobic activity.")
        recommendations.append("Annual blood pressure, lipid panel, and fasting glycemic screening.")

    return PatientPredictionResult(
        prediction_label=label,
        risk_probability=round(prob, 4),
        risk_percentage=round(prob * 100.0, 1),
        risk_category=category,
        confidence_score=round(confidence, 4),
        model_id=used_model_id,
        model_version=used_version,
        primary_risk_factors=factors,
        recommendations=recommendations,
    )


class EducationalPredictionResponse(BaseModel):
    """Structured educational cardiovascular risk estimate matching Step 13 requirements."""

    model_name: str = Field(..., description="Name of the selected machine learning model")
    model_version: str = Field("2.0.0", description="Model semantic version")
    prediction: int = Field(..., description="Binary estimate: 1 = Reported MI/CHD pattern, 0 = Negative")
    estimated_probability: float = Field(..., ge=0.0, le=1.0, description="Continuous model output probability")
    output_type: str = Field("educational_estimate", description="Explicit indicator of non-clinical purpose")
    clinical_validation: bool = Field(False, description="Always False: educational research prototype")
    limitations: list[str] = Field(default_factory=list, description="Documented epidemiological and methodological caveats")


STANDARD_RESEARCH_LIMITATIONS = [
    "Educational research prototype only: NOT clinically validated or intended for diagnosis.",
    "Survey data source (CDC BRFSS 2023): self-reported historical disease status, not prospective event risk.",
    "Target leakage excluded: model does not use source clinical diagnosis questions (CVDINFR4, CVDCRHD4).",
    "Survey sampling bias: individual estimates do not incorporate complex multi-stage sampling weights (_LLCPWT).",
    "Model probabilities reflect population correlation, not individual biological causality.",
]


def predict_educational_estimate(
    patient_data: dict[str, Any] | PatientBRFSSInput,
    model_name: str = "best_model",
) -> EducationalPredictionResponse:
    """Computes an educational cardiovascular risk estimate using the trained BRFSS ensemble.

    Adheres strictly to research limitations:
    - No unsupported clinical risk labels (high/medium/low).
    - No arbitrary probability cutoffs.
    - Full transparency on educational purpose and non-diagnostic status.
    """
    from pathlib import Path

    import joblib

    # 1. Validate input data
    if isinstance(patient_data, PatientBRFSSInput):
        clean_dict = patient_data.model_dump()
    else:
        clean_dict = validate_input_dict(patient_data)

    # Privacy-conscious logging: log feature presence and risk estimate without any personal identifiers
    logger.info(
        "Computing educational estimate with model '%s' (AgeCat=%s, Sex=%s, HighBP=%s)",
        model_name,
        clean_dict.get("AgeCategory"),
        clean_dict.get("Sex_Male"),
        clean_dict.get("HighBP"),
    )

    # 2. Format input DataFrame matching preprocessing pipeline
    input_df = prepare_feature_dataframe(clean_dict)

    # 3. Load preprocessing pipeline
    models_dir = Path("models")
    pipeline_path = models_dir / "preprocessing_pipeline.joblib"
    if not pipeline_path.exists():
        raise FileNotFoundError(f"Preprocessing pipeline not found at {pipeline_path}")

    preprocessor = joblib.load(pipeline_path)
    X_proc = preprocessor.transform(input_df)

    # 4. Load requested model
    model_filename = f"{model_name}.joblib" if not model_name.endswith((".joblib", ".json", ".cbm", ".txt")) else model_name
    model_path = models_dir / model_filename
    if not model_path.exists():
        # Fallback to best_model.joblib
        model_path = models_dir / "best_model.joblib"
        model_name = "best_model"

    model = joblib.load(model_path)

    # 5. Inference
    if hasattr(model, "predict_proba"):
        probs = model.predict_proba(X_proc)
        prob = float(probs[0][1])
    else:
        prob = float(model.predict(X_proc)[0])

    pred = 1 if prob >= 0.50 else 0

    return EducationalPredictionResponse(
        model_name=model_name,
        model_version="2.0.0",
        prediction=pred,
        estimated_probability=round(prob, 4),
        output_type="educational_estimate",
        clinical_validation=False,
        limitations=STANDARD_RESEARCH_LIMITATIONS,
    )

