"""HeartAI Generative AI Prompt Templates & System Instructions — Aarogya Saathi.

Engineered system prompts for Aarogya Saathi (आरोग्य साथी):
Cardiovascular clinical education, metric interpretation, symptom analysis,
CDC BRFSS historical model limitations, and consented lifestyle guidance.
"""

from __future__ import annotations

from typing import Any

from app.schemas.ai import SymptomAssessmentInput

SYSTEM_INSTRUCTION_AAROGYA_SAATHI = """You are Aarogya Saathi (आरोग्य साथी), the dedicated cardiovascular health education and research companion for the HeartAI platform.

Meaning of your name: In Sanskrit and Hindi, "Aarogya" (आरोग्य) signifies holistic health and disease-free wellbeing, and "Saathi" (साथी) means a trusted companion or guide.

Your tone is warm, respectful, objective, culturally empathetic, and clinically grounded in international cardiovascular guidelines (American Heart Association [AHA], American College of Cardiology [ACC], European Society of Cardiology [ESC], and Indian Council of Medical Research [ICMR]).

==================================================
STRICT DOMAIN & SAFETY BOUNDARIES (MANDATORY)
==================================================
1. STRICT HEARTAI-ONLY SCOPE: You exclusively assist with HeartAI application features, cardiovascular health education, vital metric interpretation, symptom urgency guidance, and lifestyle wellness. Unrelated queries are strictly out of scope.
2. NEVER DIAGNOSE: You are strictly an educational companion. You cannot diagnose conditions or determine disease etiology. Never say "You have heart disease" or "You are experiencing an acute coronary event."
3. NEVER PRESCRIBE OR ALTER MEDICATIONS: You must never recommend starting, discontinuing, adjusting, or tapering any pharmaceutical medication or dosage. Always instruct users to consult their prescribing doctor.
4. NO FUTURE HEART ATTACK PREDICTIONS: HeartAI's machine learning model was trained on the CDC BRFSS 2023 survey and estimates similarity to individuals reporting historical cardiovascular disease (_MICHD). It DOES NOT predict future heart attacks, future event risk, or acute event timing. If asked about future risk, explicitly explain this scientific limitation.
5. SCREENING THRESHOLD TRANSPARENCY: Explain that the calibrated operating threshold (0.09) is designed for high sensitivity (~80%) in research screening to minimize missed patterns, meaning a positive screening flag is not a diagnostic confirmation.
6. EMERGENCY PROTOCOL: If any acute symptoms (chest pressure, pain radiating to arm/jaw, acute shortness of breath, slurred speech, syncope) are described, IMMEDIATELY prioritize calling emergency services (112 in India, 911 in US/Canada, 999 in UK).
7. ALWAYS RECOMMEND QUALIFIED CLINICAL CARE: Conclude discussions by reminding users that personal medical management requires a licensed healthcare professional.
"""

SYSTEM_INSTRUCTION_SYMPTOM_ANALYSIS = """You are Aarogya Saathi (आरोग्य साथी), HeartAI's clinical education companion.
Analyze the user's reported symptoms for educational purposes and output a structured JSON response conforming strictly to the required schema:
- symptom_summary: Objective, concise summary of the reported symptoms and onset.
- general_cardiovascular_relevance: Evidence-based explanation of how such symptoms relate to heart and vascular physiology.
- warning_signs_identified: Specific warning signs in the report that warrant professional evaluation.
- urgency_category: Choose conservatively from:
  * "EMERGENCY": Acute, life-threatening indicators (e.g. crushing chest pain, radiating arm/jaw pain, severe sudden dyspnea, syncope, facial droop).
  * "URGENT": Significant discomfort or new/worsening symptoms requiring prompt medical evaluation within hours.
  * "ROUTINE": Mild, chronic, or stable symptoms to discuss at the next regular doctor visit.
  * "NON_CARDIOVASCULAR_OR_UNCERTAIN": Non-specific symptoms that cannot be safely categorized.
- suggested_next_action: Clear, reassuring, safe recommendation (e.g. "Call emergency services immediately", "Consult a physician today").
- is_emergency: Boolean flag (True if EMERGENCY category, False otherwise).
- emergency_contacts: Official emergency telephone numbers (India: 112, US: 911, UK: 999).
- limitations_disclaimer: Mandatory disclaimer that automated analysis cannot rule out emergencies or diagnose illness.

CRITICAL: NO diagnoses. NO drug prescriptions. NO claims of medical certainty.
"""

SYSTEM_INSTRUCTION_STRUCTURED_ADVICE = """You are Aarogya Saathi (आरोग्य साथी), HeartAI's clinical education companion.
Provide structured cardiovascular wellness education conforming strictly to the requested schema.
Include clear titles, summaries, evidence-based key points, lifestyle recommendations aligned with AHA Life's Essential 8,
and suggested questions for the patient's doctor.
Never diagnose, never prescribe, never claim medical certainty."""



def build_symptom_analysis_prompt(symptom_input: SymptomAssessmentInput) -> str:
    """Creates a structured symptom assessment prompt."""
    assoc_str = ", ".join(symptom_input.associated_symptoms) if symptom_input.associated_symptoms else "None reported"
    timing_str = "Ongoing" if symptom_input.is_ongoing else "Intermittent"

    return f"""Please provide conservative, non-diagnostic educational analysis for the following user-reported cardiovascular symptoms:

- Primary Symptoms: {symptom_input.symptoms_experienced}
- Onset Time: {symptom_input.onset_time}
- Timing Pattern: {timing_str}
- Self-Reported Severity: {symptom_input.severity.value}
- Associated Symptoms: {assoc_str}
- Progression Trend: {symptom_input.progression.value}

Analyze these symptoms safely according to AHA/ACC guidelines:
1. Summarize the symptoms concisely.
2. Explain general cardiovascular relevance.
3. Identify warning signs that may require urgent medical assessment.
4. Categorize urgency conservatively (EMERGENCY, URGENT, ROUTINE, or UNCERTAIN).
5. Suggest immediate safe next actions.
"""


def build_heart_health_education_prompt(topic: str) -> str:
    """Creates an educational prompt on a specific cardiovascular topic."""
    return f"""Please provide comprehensive, evidence-based cardiovascular health education regarding:
Topic: "{topic}"

Include:
1. Physiological explanation in plain terms.
2. Why this is relevant to cardiovascular wellness.
3. Standard clinical risk factors and preventative lifestyle measures.
4. When an individual should consult a cardiologist or primary doctor.
"""


def build_metric_explanation_prompt(
    metric_name: str,
    metric_value: float | None = None,
    unit: str | None = None,
) -> str:
    """Creates an explanation prompt for a vital health metric."""
    val_str = f" Value: {metric_value} {unit or ''}" if metric_value is not None else ""
    return f"""Explain the clinical and physiological significance of the cardiovascular health metric: "{metric_name}".{val_str}

Please address:
1. What this metric measures in the cardiovascular system.
2. Standard reference ranges (e.g. normal, elevated, high) according to ACC/AHA and international guidelines.
3. How lifestyle factors (diet, physical activity, sleep, stress) influence this metric.
4. Key questions a patient might discuss with their physician regarding this metric.
Remember: Do not diagnose the individual or recommend changing prescription medications.
"""


def build_model_limitations_prompt(
    estimated_probability: float,
    binary_classification: int,
    operating_threshold: float = 0.09,
    feature_context: dict[str, Any] | None = None,
) -> str:
    """Creates a prompt to transparently explain HeartAI model uncertainty, threshold, and survey limitations."""
    pct = estimated_probability * 100.0
    flag_str = (
        "Historical CVD Pattern Detected"
        if binary_classification == 1
        else "Baseline Survey Pattern"
    )

    context_str = ""
    if feature_context:
        safe_keys = [f"{k}: {v}" for k, v in feature_context.items() if k in {"BMI", "HighBP", "HighCholesterol", "SmokerStatus"}]
        if safe_keys:
            context_str = f"\nConsented Contextual Indicators: {', '.join(safe_keys)}"

    return f"""The HeartAI calibrated ensemble model produced the following educational risk output:
- Estimated Probability: {pct:.2f}% ({estimated_probability:.4f})
- Operating Threshold: {operating_threshold:.2f}
- Classification: {flag_str}{context_str}

Please generate a clear, transparent explanation addressing:
1. What this probability actually represents: an educational estimate of similarity to individuals reporting historical cardiovascular disease in the CDC BRFSS 2023 survey.
2. Why this is NOT a prediction of a future heart attack or a clinical diagnosis.
3. The meaning of the operating threshold ({operating_threshold:.2f}): explain how screening models use a lower threshold to maximize sensitivity (~80%) to avoid missing patterns, which means many individuals above the threshold do not have active heart disease.
4. Inherent research limitations: survey self-reporting bias, unweighted sampling, and population correlation vs. biological causality.
5. Reassuring, actionable next steps for discussing cardiovascular health with a doctor.
"""


def build_future_risk_explanation() -> str:
    """Static educational explanation of why HeartAI does not predict future heart attacks."""
    return (
        "HeartAI's current machine learning model is trained on cross-sectional survey data (CDC BRFSS 2023) "
        "and estimates statistical similarity to respondents with self-reported historical cardiovascular disease (_MICHD). "
        "It does NOT predict future heart attack probability, prospective cardiovascular event timing, or acute clinical outcomes. "
        "Predicting future cardiovascular events requires a prospective longitudinal cohort model (such as the Framingham "
        "or ACC/AHA ASCVD Risk Estimator) utilizing clinically measured laboratory biomarkers (e.g. serum cholesterol fractions, "
        "systolic blood pressure, HbA1c) validated across multi-year clinical follow-up cohorts."
    )


def build_lifestyle_education_prompt(lifestyle_factors: list[str] | None = None) -> str:
    """Creates an evidence-based lifestyle guidance prompt aligned with AHA Life's Essential 8."""
    factors_str = (
        ", ".join(lifestyle_factors)
        if lifestyle_factors
        else "Diet, Physical Activity, Sleep, Stress Management, Nicotine Avoidance"
    )
    return f"""Provide practical, evidence-based cardiovascular lifestyle guidance centered on AHA's Life's Essential 8, focusing on: {factors_str}.

Detail:
1. Daily actionable steps for cardiac wellness.
2. The physiological benefits for the vascular endothelium and heart muscle.
3. Realistic, sustainable incremental improvements.
"""


def build_personalized_education_prompt(
    survey_features: dict[str, Any],
    user_consent_verified: bool,
) -> str:
    """Creates an education prompt using verified server-side consented survey features."""
    if not user_consent_verified:
        return (
            "The user has NOT granted verified server-side informed consent (and has chosen NOT to share individual survey responses) "
            "for individual personalization. In strict accordance with Privacy by Default, provide general population-level "
            "cardiovascular wellness education covering balanced nutrition, daily physical activity, "
            "sleep hygiene, and routine checkups. Do not reference individual health parameters."
        )

    safe_profile_items = []
    if "BMI" in survey_features:
        safe_profile_items.append(f"BMI: {survey_features['BMI']:.1f}")
    if "HighBP" in survey_features:
        safe_profile_items.append(f"High Blood Pressure Reported: {'Yes' if survey_features['HighBP'] == 1 else 'No'}")
    if "HighCholesterol" in survey_features:
        safe_profile_items.append(f"High Cholesterol Reported: {'Yes' if survey_features['HighCholesterol'] == 1 else 'No'}")
    if "SmokerStatus" in survey_features:
        smoker_map = {1: "Daily smoker", 2: "Someday smoker", 3: "Former smoker", 4: "Never smoked"}
        safe_profile_items.append(f"Smoking History: {smoker_map.get(survey_features['SmokerStatus'], 'Unspecified')}")
    if "PhysicalActivity" in survey_features:
        safe_profile_items.append(f"Regular Exercise: {'Yes' if survey_features['PhysicalActivity'] == 1 else 'No'}")
    if "GeneralHealth" in survey_features:
        health_map = {1: "Excellent", 2: "Very Good", 3: "Good", 4: "Fair", 5: "Poor"}
        safe_profile_items.append(f"General Health Perception: {health_map.get(survey_features['GeneralHealth'], 'Unspecified')}")

    profile_text = "\n".join(f"- {item}" for item in safe_profile_items) or "- Baseline general survey entry"

    return f"""The user has granted verified informed consent to receive personalized educational guidance based on their reported survey lifestyle profile:
{profile_text}

Provide personalized, supportive, evidence-based cardiovascular education:
1. Highlight positive protective lifestyle habits.
2. Suggest actionable, low-risk lifestyle improvements tailored to the consented factors (e.g. nutrition tips if high BP is reported, cardiovascular exercise advice, or sleep routines).
3. Frame everything as educational lifestyle guidance, NEVER as diagnostic advice.
4. Suggest questions tailored to their profile for their next primary care checkup.
"""
