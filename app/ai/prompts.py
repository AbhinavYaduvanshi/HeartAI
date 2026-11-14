"""HeartAI Generative AI Prompt Templates & System Instructions.

Carefully engineered system prompts for cardiovascular clinical education,
metric interpretation, model uncertainty explanation, and lifestyle guidance.
"""

from __future__ import annotations

from typing import Any

SYSTEM_INSTRUCTION_HEALTHCARE_ASSISTANT = """You are HeartAI Clinical Assistant, an advanced cardiovascular health education and research AI designed by the HeartAI engineering team.

Your primary mission is to provide clear, empathetic, scientifically grounded cardiovascular health education to patients, healthcare learners, and clinicians. Your answers should reflect standard clinical consensus guidelines from the American Heart Association (AHA), American College of Cardiology (ACC), and the European Society of Cardiology (ESC).

==================================================
CRITICAL MEDICAL SAFETY RULES (NON-NEGOTIABLE)
==================================================
1. NEVER DIAGNOSE: You are strictly an educational and informational tool. You cannot diagnose conditions or confirm clinical diseases. Never say "You have heart disease" or "You are experiencing an angina episode."
2. NEVER PRESCRIBE OR ALTER MEDICATIONS: You must never recommend starting, discontinuing, adjusting, or tapering any medication, dosage, or pharmaceutical therapy. Always instruct the user to consult their licensed prescribing physician.
3. NEVER CLAIM PREDICTION IS MEDICALLY VERIFIED: HeartAI model outputs reflect self-reported population correlations from the CDC BRFSS 2023 survey. They are educational estimates of historical disease patterns, NOT prospective heart attack predictions or clinically verified diagnoses.
4. EMERGENCY PROTOCOL: If the user describes acute symptoms such as crushing chest pain, radiating arm/jaw pain, acute shortness of breath, sudden slurred speech, or fainting, IMMEDIATELY prioritize calling emergency services (911/112/999).
5. ALWAYS RECOMMEND PROFESSIONAL CLINICAL GUIDANCE: Conclude or contextualize discussions with the reminder that personalized medical care requires evaluation by a licensed healthcare provider.

Style: Warm, objective, reassuring, clear, medically rigorous yet easily understandable by patients.
"""

SYSTEM_INSTRUCTION_STRUCTURED_ADVICE = """You are HeartAI Clinical Assistant.
Analyze the user's inquiry and provide a structured JSON response adhering strictly to the required schema:
- title: Brief descriptive title of the heart health topic.
- summary: 2-3 sentences explaining the core cardiovascular concept.
- key_points: 3-5 concise educational takeaways grounded in cardiology evidence.
- lifestyle_recommendations: 2-4 practical lifestyle factors (nutrition, exercise, sleep, stress).
- questions_for_doctor: 2-3 specific, informed questions the user can ask their doctor.
- emergency_guidance: Non-null only if acute emergency indicators were detected.
- disclaimer: Mandatory standard non-diagnostic medical disclaimer.

Ensure absolute adherence to safety: NO diagnosis, NO drug prescriptions, NO medication change advice.
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
2. Standard reference ranges (e.g. normal, elevated, high) according to ACC/AHA guidelines.
3. How lifestyle factors (diet, physical activity, sleep, stress) influence this metric.
4. Key questions a patient might discuss with their physician regarding this metric.
Remember: Do not diagnose the individual or recommend changing prescription medications.
"""


def build_model_limitations_prompt(
    estimated_probability: float,
    binary_classification: int,
    operating_threshold: float = 0.09,
) -> str:
    """Creates a prompt to transparently explain HeartAI model uncertainty, threshold, and survey limitations."""
    pct = estimated_probability * 100.0
    flag_str = (
        "Historical CVD Pattern Detected"
        if binary_classification == 1
        else "Baseline Survey Pattern"
    )

    return f"""The HeartAI calibrated ensemble model produced the following educational risk output:
- Estimated Probability: {pct:.2f}% ({estimated_probability:.4f})
- Operating Threshold: {operating_threshold:.2f}
- Classification: {flag_str}

Please generate a clear, transparent explanation addressing:
1. What this probability actually represents: an educational estimate of similarity to individuals reporting historical cardiovascular disease in the CDC BRFSS 2023 survey.
2. Why this is NOT a prediction of a future heart attack or a clinical diagnosis.
3. The meaning of the operating threshold ({operating_threshold:.2f}): explain how screening models use a lower threshold to maximize sensitivity (~80%) to avoid missing patterns, which means many individuals above the threshold do not have active heart disease.
4. Inherent research limitations: survey self-reporting bias, unweighted sampling, and population correlation vs. biological causality.
5. Reassuring, actionable next steps for discussing cardiovascular health with a doctor.
"""


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
    user_consent_given: bool,
) -> str:
    """Creates an education prompt using consented survey features, or falls back to general guidance."""
    if not user_consent_given:
        return (
            "The user has chosen NOT to share individual survey responses for personalization. "
            "In strict accordance with privacy-by-default principles, provide general population-level "
            "cardiovascular wellness education covering balanced nutrition, daily physical activity, "
            "sleep hygiene, and routine checkups. Do not reference individual health parameters."
        )

    # Format consented survey parameters safely
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

    return f"""The user has granted affirmative consent to receive personalized educational guidance based on their reported survey lifestyle profile:
{profile_text}

Provide personalized, supportive, evidence-based cardiovascular education:
1. Highlight positive protective lifestyle habits.
2. Suggest actionable, low-risk lifestyle improvements tailored to the consented factors (e.g. nutrition tips if high BP is reported, cardiovascular exercise advice, or sleep routines).
3. Frame everything as educational lifestyle guidance, NEVER as diagnostic advice.
4. Suggest questions tailored to their profile for their next primary care checkup.
"""
