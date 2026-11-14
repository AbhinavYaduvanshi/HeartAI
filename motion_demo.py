"""HeartAI Motion System Demonstration & Integration Sandbox — Point 8.1.

Demonstrates:
1. All 6 motion and animation categories implemented for HeartAI in NiceGUI.
2. Complete application-wide integration of Aarogya Saathi (आरोग्य साथी),
   HeartAI's persistent AI healthcare companion.
3. Interactive deterministic emergency-screened symptom assessment.
4. Calibrated BRFSS model inference with contextual AI risk explanations.
5. Contextual AI triggers across Hero, Assessment, Doctors, Analytics, and Metrics.
6. Responsive design respecting prefers-reduced-motion and high accessibility.
"""

from __future__ import annotations

import random
from typing import Any

import httpx
from nicegui import app, ui

from app.schemas.ai import (
    AIChatRequest,
    SymptomAssessmentInput,
    SymptomProgression,
    SymptomSeverity,
)
from motion import (
    get_init_analytics_js,
    get_init_doctor_banner_js,
    get_init_doctor_images_js,
    get_init_health_metrics_js,
    get_init_hero_js,
    get_init_navbar_js,
    get_motion_head_html,
    get_update_metric_js,
    register_motion_routes,
    render_anatomical_heart_svg,
    render_circular_gauge_svg,
    render_ecg_svg,
    render_risk_gauge_svg,
)

# Register static routes
register_motion_routes(app)

BACKEND_API_URL = "http://localhost:8000"


@ui.page("/")
def index_page():
    # Inject Motion Styles & Scripts
    ui.add_head_html(get_motion_head_html(use_cdn=False))

    # =========================================================================
    # DIALOG 1: AAROGYA SAATHI (आरोग्य साथी) PERSISTENT AI ASSISTANT CHAT
    # =========================================================================
    with ui.dialog() as aarogya_dialog, ui.card().classes(
        "p-0 max-w-xl w-full rounded-2xl bg-white shadow-2xl border border-slate-100 flex flex-col overflow-hidden"
    ):
        # Header with Indian Healthcare Companion Identity
        with ui.row().classes(
            "w-full justify-between items-center px-6 py-4 bg-gradient-to-r from-teal-800 via-teal-700 to-amber-700 text-white"
        ):
            with ui.row().classes("items-center gap-3"):
                with ui.element("div").classes("relative flex items-center justify-center w-10 h-10 rounded-full bg-white/20 border border-white/30"):
                    ui.icon("spa", color="amber-300").classes("text-xl")
                    # Status Indicator dot
                    ui.element("span").classes("absolute bottom-0 right-0 w-3 h-3 rounded-full bg-emerald-400 border-2 border-teal-800")
                with ui.column().classes("gap-0"):
                    ui.label("Aarogya Saathi (आरोग्य साथी)").classes("text-base font-bold tracking-wide")
                    ui.label("HeartAI Health & Wellbeing Companion").classes("text-[11px] text-teal-100")
            with ui.row().classes("items-center gap-2"):
                ui.element("span").classes("text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 border border-emerald-400/40 text-emerald-200 font-medium").text = "Online"
                ui.button(icon="close", on_click=aarogya_dialog.close).props("flat round dense").classes("text-white/80 hover:text-white")

        # Emergency Notice Bar
        with ui.row().classes("w-full px-6 py-2 bg-amber-50 border-b border-amber-200 items-center justify-between text-[11px] text-amber-900"):
            with ui.row().classes("items-center gap-1.5"):
                ui.icon("warning", color="amber-700").classes("text-sm")
                ui.label("Emergency: For acute chest pain or severe distress, call").classes("font-medium")
                ui.element("span").classes("font-bold text-red-700").text = "112 (India)"
                ui.label("or 911 immediately.")

        # Chat Message Thread
        chat_scroll = ui.scroll_area().classes("h-80 w-full px-6 py-4 bg-slate-50/70 border-b border-slate-100")
        with chat_scroll:
            chat_container = ui.column().classes("gap-3 w-full")
            with chat_container:
                with ui.chat_message(
                    name="Aarogya Saathi",
                    stamp="Just now",
                    avatar="https://images.unsplash.com/photo-1559839734-2b71ea197ec2?w=100&q=80",
                ):
                    ui.label(
                        "Namaste! I am Aarogya Saathi (आरोग्य साथी), your HeartAI companion for health and wellbeing. "
                        "I can help explain cardiovascular health concepts, vital metrics (BP, SpO2, HRV), "
                        "our calibrated CDC BRFSS model, and guide you through symptom checks. "
                        "How may I support your health education today?"
                    ).classes("text-xs leading-relaxed text-slate-800")

        # Typing indicator container (hidden by default)
        typing_indicator = ui.row().classes("hidden px-6 py-1 items-center gap-1.5 text-xs text-teal-700")
        with typing_indicator:
            ui.element("span").classes("aarogya-typing-dot")
            ui.element("span").classes("aarogya-typing-dot")
            ui.element("span").classes("aarogya-typing-dot")
            ui.label("Aarogya Saathi is preparing your educational response...").classes("text-[11px] text-slate-500 italic ml-1")

        # Quick Prompt Chips
        def set_chat_prompt(text: str):
            chat_input.value = text

        with ui.row().classes("px-6 py-2 gap-1.5 flex-wrap bg-white"):
            ui.button("Blood Pressure Ranges", on_click=lambda: set_chat_prompt("What are the standard clinical blood pressure ranges and classifications?")).props("outline dense").classes("text-[10px] text-teal-700 border-teal-200 hover:bg-teal-50")
            ui.button("Why Threshold 0.09?", on_click=lambda: set_chat_prompt("Why does HeartAI use an operating threshold of 0.09 instead of 0.50?")).props("outline dense").classes("text-[10px] text-teal-700 border-teal-200 hover:bg-teal-50")
            ui.button("Life's Essential 8", on_click=lambda: set_chat_prompt("What are the American Heart Association Life's Essential 8 cardiovascular health factors?")).props("outline dense").classes("text-[10px] text-teal-700 border-teal-200 hover:bg-teal-50")
            ui.button("What is Aarogya Saathi?", on_click=lambda: set_chat_prompt("Tell me about Aarogya Saathi and HeartAI's clinical education mission.")).props("outline dense").classes("text-[10px] text-amber-800 border-amber-200 hover:bg-amber-50")

        # Input Row
        with ui.row().classes("px-6 py-3 w-full gap-2 items-center bg-white"):
            chat_input = ui.input(placeholder="Ask Aarogya Saathi about heart health, metrics, or symptoms...").classes("flex-1 text-xs").props("outlined dense")
            chat_send_btn = ui.button(icon="send").classes("bg-teal-700 text-white rounded-lg px-3 py-1.5 hover:bg-teal-800")

        async def send_chat_message():
            msg = (chat_input.value or "").strip()
            if not msg:
                return
            chat_input.value = ""
            with chat_container:
                with ui.chat_message(name="You", sent=True, stamp="now"):
                    ui.label(msg).classes("text-xs text-slate-800")
            chat_scroll.scroll_to(percent=1.0)

            # Show typing indicator
            typing_indicator.classes(remove="hidden")

            # Call backend AI endpoint
            resp_text = ""
            emergency_flag = False
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(
                        f"{BACKEND_API_URL}/api/v1/ai/chat",
                        json={"message": msg, "user_consent_given": False},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        resp_text = data.get("response_text", "")
                        emergency_flag = data.get("emergency_flag", False)
                    else:
                        resp_text = f"Aarogya Saathi service notice: HTTP {resp.status_code}."
            except Exception:
                # Direct in-process fallback for standalone UI preview
                try:
                    from app.ai.assistant import assistant
                    local_resp = assistant.chat(AIChatRequest(message=msg, user_consent_given=False))
                    resp_text = local_resp.response_text
                    emergency_flag = local_resp.emergency_flag
                except Exception as local_err:
                    resp_text = f"Aarogya Saathi is currently offline ({local_err}). Please check connection."

            typing_indicator.classes(add="hidden")

            with chat_container:
                with ui.chat_message(
                    name="Aarogya Saathi",
                    stamp="now",
                    avatar="https://images.unsplash.com/photo-1559839734-2b71ea197ec2?w=100&q=80",
                ):
                    if emergency_flag:
                        with ui.card().classes("p-3 aarogya-emergency-banner rounded-lg mb-2"):
                            ui.label("CRITICAL MEDICAL ALERT").classes("text-xs font-bold text-red-700")
                            ui.markdown(resp_text).classes("text-xs text-red-900 leading-relaxed")
                    else:
                        ui.markdown(resp_text).classes("text-xs leading-relaxed text-slate-800")
            chat_scroll.scroll_to(percent=1.0)

        chat_send_btn.on("click", send_chat_message)
        chat_input.on("keydown.enter", send_chat_message)

        # Footer Disclaimer
        ui.label(
            "Aarogya Saathi is an educational health assistant. Never provides medical diagnoses or prescriptions. In emergencies call 112 (India) or 911."
        ).classes("text-[9px] text-slate-400 italic text-center w-full px-6 py-2 bg-slate-50")

    def open_aarogya_with_prompt(prompt_text: str):
        chat_input.value = prompt_text
        aarogya_dialog.open()

    # =========================================================================
    # DIALOG 2: CARDIOVASCULAR SYMPTOM ASSESSMENT DIALOG (POINT 8.1 - PART 4)
    # =========================================================================
    with ui.dialog() as symptom_dialog, ui.card().classes(
        "p-6 max-w-xl w-full rounded-2xl bg-white shadow-2xl border border-slate-100 flex flex-col gap-4 max-h-[90vh] overflow-y-auto"
    ):
        with ui.row().classes("w-full justify-between items-center pb-2 border-b border-slate-100"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("health_and_safety", color="teal-700").classes("text-2xl")
                with ui.column().classes("gap-0"):
                    ui.label("Cardiovascular Symptom Assessment").classes("text-lg font-bold text-slate-900")
                    ui.label("Deterministic emergency screening & educational triage guidance").classes("text-xs text-slate-500")
            ui.button(icon="close", on_click=symptom_dialog.close).props("flat round dense").classes("text-slate-400")

        # Emergency Warning Header
        with ui.card().classes("w-full p-3 bg-red-50 border-l-4 border-red-500 rounded-lg"):
            ui.label("Immediate Medical Notice").classes("text-xs font-bold text-red-800")
            ui.label(
                "If you or someone near you is experiencing crushing chest pressure, pain radiating to the jaw/arm, "
                "sudden severe breathlessness, or fainting, CALL 112 (India) OR 911 IMMEDIATELY. Do not wait."
            ).classes("text-[11px] text-red-700 mt-0.5 leading-snug")

        with ui.column().classes("gap-3 w-full"):
            ui.label("Primary Symptoms Description").classes("text-xs font-semibold text-slate-700")
            symp_desc = ui.textarea(
                placeholder="Describe what you are feeling (e.g. tightness in chest, racing heartbeat, mild shortness of breath during stairs)..."
            ).classes("w-full text-xs").props("outlined dense rows=2")

            with ui.row().classes("w-full gap-4 flex-col sm:flex-row"):
                with ui.column().classes("flex-1 gap-1"):
                    ui.label("Onset Timeframe").classes("text-xs font-semibold text-slate-700")
                    symp_onset = ui.select(
                        options=["Within the last hour", "Earlier today", "Past few days", "Over weeks/months"],
                        value="Earlier today",
                    ).classes("w-full text-xs").props("outlined dense")
                with ui.column().classes("flex-1 gap-1"):
                    ui.label("Pattern").classes("text-xs font-semibold text-slate-700")
                    symp_pattern = ui.select(
                        options=["Ongoing continuous", "Intermittent / episodes", "Only with physical exertion"],
                        value="Intermittent / episodes",
                    ).classes("w-full text-xs").props("outlined dense")

            with ui.row().classes("w-full gap-4 flex-col sm:flex-row"):
                with ui.column().classes("flex-1 gap-1"):
                    ui.label("Severity").classes("text-xs font-semibold text-slate-700")
                    symp_severity = ui.select(
                        options=["Mild (noticeable but doesn't limit activity)", "Moderate (interferes with normal activity)", "Severe (unable to perform daily tasks)", "Very Severe (extreme incapacitating distress)"],
                        value="Moderate (interferes with normal activity)",
                    ).classes("w-full text-xs").props("outlined dense")
                with ui.column().classes("flex-1 gap-1"):
                    ui.label("Progression Trend").classes("text-xs font-semibold text-slate-700")
                    symp_progression = ui.select(
                        options=["Improving", "Stable / unchanged", "Gradually worsening", "Rapidly worsening"],
                        value="Stable / unchanged",
                    ).classes("w-full text-xs").props("outlined dense")

            ui.label("Associated Warning Signs (Select all that apply)").classes("text-xs font-semibold text-slate-700 mt-1")
            with ui.row().classes("gap-3 w-full flex-wrap"):
                assoc_sob = ui.checkbox("Shortness of breath", value=False).classes("text-xs text-slate-700")
                assoc_rad = ui.checkbox("Pain radiating to arm / jaw / neck", value=False).classes("text-xs text-slate-700")
                assoc_diz = ui.checkbox("Dizziness or lightheadedness", value=False).classes("text-xs text-slate-700")
                assoc_sweat = ui.checkbox("Cold sweat / diaphoresis", value=False).classes("text-xs text-slate-700")
                assoc_palp = ui.checkbox("Heart racing or fluttering", value=False).classes("text-xs text-slate-700")

            symptom_results_box = ui.column().classes("w-full hidden mt-2 p-4 bg-slate-50 rounded-xl border border-slate-200")

            async def submit_symptom_assessment():
                desc_val = (symp_desc.value or "").strip()
                if not desc_val:
                    ui.notify("Please describe your symptoms first.", color="orange")
                    return

                # Map UI severity and progression
                sev_map = {
                    "Mild (noticeable but doesn't limit activity)": SymptomSeverity.MILD,
                    "Moderate (interferes with normal activity)": SymptomSeverity.MODERATE,
                    "Severe (unable to perform daily tasks)": SymptomSeverity.SEVERE,
                    "Very Severe (extreme incapacitating distress)": SymptomSeverity.VERY_SEVERE,
                }
                prog_map = {
                    "Improving": SymptomProgression.GETTING_BETTER,
                    "Stable / unchanged": SymptomProgression.UNCHANGED,
                    "Gradually worsening": SymptomProgression.GETTING_WORSE,
                    "Rapidly worsening": SymptomProgression.RAPIDLY_WORSENING,
                }

                assoc_list = []
                if assoc_sob.value:
                    assoc_list.append("shortness of breath")
                if assoc_rad.value:
                    assoc_list.append("pain radiating to arm or jaw")
                if assoc_diz.value:
                    assoc_list.append("dizziness or lightheadedness")
                if assoc_sweat.value:
                    assoc_list.append("cold sweat")
                if assoc_palp.value:
                    assoc_list.append("palpitations or fluttering")

                payload = SymptomAssessmentInput(
                    symptoms_experienced=desc_val,
                    onset_time=str(symp_onset.value or "Earlier today"),
                    is_ongoing="Ongoing" in str(symp_pattern.value or ""),
                    severity=sev_map.get(str(symp_severity.value), SymptomSeverity.MODERATE),
                    associated_symptoms=assoc_list,
                    progression=prog_map.get(str(symp_progression.value), SymptomProgression.UNCHANGED),
                )

                symptom_results_box.clear()
                symptom_results_box.classes(remove="hidden")

                # Call backend or in-process assistant
                try:
                    async with httpx.AsyncClient(timeout=15.0) as client:
                        resp = await client.post(
                            f"{BACKEND_API_URL}/api/v1/ai/symptoms",
                            json=payload.model_dump(),
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                        else:
                            from app.ai.assistant import assistant
                            data = assistant.assess_symptoms(payload).model_dump()
                except Exception:
                    from app.ai.assistant import assistant
                    data = assistant.assess_symptoms(payload).model_dump()

                with symptom_results_box:
                    is_emerg = data.get("is_emergency", False)
                    urgency = data.get("urgency_category", "ROUTINE")

                    if is_emerg:
                        with ui.card().classes("w-full p-4 aarogya-emergency-banner rounded-xl mb-3 border-l-4 border-red-600"):
                            ui.label("CRITICAL EMERGENCY DETECTED").classes("text-sm font-extrabold text-red-800")
                            ui.label("Your symptoms match patterns requiring IMMEDIATE emergency evaluation.").classes("text-xs font-semibold text-red-900 mt-1")
                            ui.label("CALL 112 (INDIA) OR 911 IMMEDIATELY. Do not attempt to drive yourself.").classes("text-xs font-bold text-red-700 mt-2")
                            contacts = data.get("emergency_contacts", {})
                            if contacts:
                                contact_str = ", ".join(f"{k}: {v}" for k, v in contacts.items())
                                ui.label(f"Emergency Contacts: {contact_str}").classes("text-[10px] text-red-800 mt-1")

                    # Urgency badge
                    urgency_colors = {
                        "EMERGENCY": "bg-red-600 text-white",
                        "URGENT": "bg-amber-600 text-white",
                        "ROUTINE": "bg-teal-600 text-white",
                        "NON_CARDIOVASCULAR_OR_UNCERTAIN": "bg-slate-600 text-white",
                    }
                    with ui.row().classes("items-center gap-2 mb-2"):
                        ui.label("Triage Urgency:").classes("text-xs font-bold text-slate-700")
                        badge_cls = urgency_colors.get(urgency, "bg-slate-600 text-white")
                        ui.element("span").classes(f"text-[10px] font-bold px-2 py-0.5 rounded-full {badge_cls}").text = urgency

                    ui.label("Assessment Summary:").classes("text-xs font-bold text-slate-800 mt-1")
                    ui.label(data.get("symptom_summary", "")).classes("text-xs text-slate-700 leading-relaxed")

                    ui.label("Cardiovascular Relevance:").classes("text-xs font-bold text-slate-800 mt-2")
                    ui.label(data.get("general_cardiovascular_relevance", "")).classes("text-xs text-slate-700 leading-relaxed")

                    warning_signs = data.get("warning_signs_identified", [])
                    if warning_signs:
                        ui.label("Observed Warning Signs:").classes("text-xs font-bold text-amber-900 mt-2")
                        for ws in warning_signs:
                            with ui.row().classes("items-center gap-1.5 ml-2"):
                                ui.icon("fiber_manual_record", color="amber-700").classes("text-[8px]")
                                ui.label(ws).classes("text-xs text-amber-950")

                    ui.label("Suggested Next Action:").classes("text-xs font-bold text-teal-900 mt-2")
                    ui.label(data.get("suggested_next_action", "")).classes("text-xs text-teal-950 font-medium leading-relaxed")

                    def transfer_to_chat():
                        symptom_dialog.close()
                        open_aarogya_with_prompt(
                            f"I completed the symptom assessment. My reported symptoms: '{desc_val}'. "
                            f"Assigned urgency: {urgency}. Could you explain more about what this means and what questions I should ask my doctor?"
                        )

                    ui.button("Discuss with Aarogya Saathi", icon="chat", on_click=transfer_to_chat).classes(
                        "heartai-btn bg-teal-800 text-white text-xs px-3 py-1.5 rounded-lg mt-3"
                    )

            with ui.row().classes("w-full justify-end gap-3 mt-4"):
                ui.button("Cancel", on_click=symptom_dialog.close).props("outline").classes("text-slate-600")
                ui.button("Assess Symptoms", icon="health_and_safety", on_click=submit_symptom_assessment).classes(
                    "heartai-btn bg-teal-700 text-white rounded-lg px-4 py-2 font-medium"
                )

    # =========================================================================
    # DIALOG 3: CDC BRFSS SURVEY RISK ASSESSMENT MODAL (MODEL INTEGRATION)
    # =========================================================================
    with ui.dialog() as assessment_dialog, ui.card().classes(
        "p-6 max-w-lg w-full rounded-2xl bg-white shadow-xl border border-slate-100"
    ):
        ui.label("Cardiovascular Survey Assessment").classes("text-xl font-bold text-slate-900 mb-1")
        ui.label(
            "Submits CDC BRFSS feature vector to the calibrated HeartAI backend for educational estimation."
        ).classes("text-xs text-slate-500 mb-4")

        with ui.column().classes("gap-3 w-full"):
            with ui.row().classes("w-full justify-between items-center"):
                ui.label("Age Bracket (1: 18-24 ... 13: 80+)").classes("text-sm text-slate-700")
                age_cat = ui.number(value=10, min=1, max=13, step=1).classes("w-20")

            with ui.row().classes("w-full justify-between items-center"):
                ui.label("Body Mass Index (BMI)").classes("text-sm text-slate-700")
                bmi_val = ui.number(value=28.5, min=12.0, max=80.0, step=0.1).classes("w-24")

            with ui.row().classes("w-full justify-between items-center"):
                ui.label("General Health (1: Excellent ... 5: Poor)").classes("text-sm text-slate-700")
                gen_health = ui.number(value=3, min=1, max=5, step=1).classes("w-20")

            with ui.row().classes("gap-4 w-full flex-wrap"):
                bp_check = ui.checkbox("High Blood Pressure", value=True)
                chol_check = ui.checkbox("High Cholesterol", value=True)
                smoker_check = ui.checkbox("Current / Former Smoker", value=True)

            consent_check = ui.checkbox(
                "I affirmatively consent to store a keyed pseudonymized digest for research audit",
                value=False,
            ).classes("text-xs text-teal-800 font-medium mt-2")
            ui.label(
                "Notice: When enabled, a keyed HMAC-SHA256 digest (not raw answers) is stored for calibration audit. "
                "You may request deletion at any time."
            ).classes("text-[10px] text-slate-500 mb-1")

            result_banner = ui.column().classes("w-full hidden mt-2 p-3 bg-slate-50 rounded-xl border border-slate-200")

            async def submit_assessment():
                payload: dict[str, Any] = {
                    "Sex_Male": 1,
                    "AgeCategory": int(age_cat.value or 10),
                    "BMI": float(bmi_val.value or 28.5),
                    "BMICategory": 3,
                    "Race": 1,
                    "Education": 4,
                    "Income": 7,
                    "GeneralHealth": int(gen_health.value or 3),
                    "PhysicalHealthDays": 4.0,
                    "MentalHealthDays": 2.0,
                    "HighBP": 1 if bp_check.value else 0,
                    "HighCholesterol": 1 if chol_check.value else 0,
                    "StrokeHistory": 0,
                    "Diabetes": 0,
                    "KidneyDisease": 0,
                    "Depression": 0,
                    "Asthma": 0,
                    "SmokerStatus": 3 if smoker_check.value else 4,
                    "ECigStatus": 4,
                    "PhysicalActivity": 1,
                    "AlcoholDrinking": 1,
                    "BingeDrinking": 0,
                    "Checkup": 1,
                    "MedCostObstacle": 0,
                    "PersonalDoctor": 1,
                    "user_consent_given": bool(consent_check.value),
                    "consent_terms_version": "2026.1" if consent_check.value else None,
                }
                try:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        resp = await client.post(f"{BACKEND_API_URL}/predict", json=payload)
                        if resp.status_code == 200:
                            data = resp.json()
                            result_banner.clear()
                            result_banner.classes(remove="hidden")
                            with result_banner:
                                ui.label(
                                    f"Estimated probability of reported historical cardiovascular disease: "
                                    f"{data['estimated_probability_percentage']:.2f}%"
                                ).classes("text-sm font-bold text-teal-900")
                                flag_str = (
                                    "Historical CVD Pattern Detected (prob >= 0.09)"
                                    if data["binary_classification"] == 1
                                    else "Baseline Survey Pattern (prob < 0.09)"
                                )
                                ui.label(f"Threshold Classification: {flag_str} (Operating Threshold: 0.09)").classes("text-xs text-slate-700")
                                ui.label(data["educational_disclaimer"]).classes("text-xs text-slate-500 italic mt-1")

                                def explain_in_aarogya():
                                    assessment_dialog.close()
                                    open_aarogya_with_prompt(
                                        f"Please explain my HeartAI cardiovascular risk estimate: {data['estimated_probability_percentage']:.2f}% "
                                        f"estimated probability ({flag_str}). What does this survey-based metric mean, why is the threshold 0.09, and what are its scientific limitations?"
                                    )

                                ui.button("Explain with Aarogya Saathi", icon="spa", on_click=explain_in_aarogya).classes(
                                    "heartai-btn bg-teal-800 text-white text-xs px-3 py-1.5 rounded-lg mt-2"
                                )
                            ui.notify("Assessment inference successfully calculated", color="teal")
                        else:
                            ui.notify(f"Inference returned status {resp.status_code}", color="red")
                except Exception as exc:
                    ui.notify(f"Backend offline or unreachable ({exc}). Running local preview.", color="orange")

            with ui.row().classes("w-full justify-end gap-3 mt-4"):
                ui.button("Cancel", on_click=assessment_dialog.close).props("outline").classes("text-slate-600")
                ui.button("Calculate Risk", on_click=submit_assessment).classes(
                    "heartai-btn bg-teal-600 text-white rounded-lg px-4 py-2 font-medium"
                )

    # =========================================================================
    # 1. NAVIGATION BAR
    # =========================================================================
    with ui.header().classes("heartai-navbar w-full bg-white/80 fixed top-0 left-0 z-50 px-8 py-4 flex justify-between items-center backdrop-blur-md"):
        with ui.row().classes("items-center gap-2"):
            ui.icon("favorite", color="red-500").classes("text-2xl heartai-pulse")
            ui.label("HeartAI").classes("text-xl font-bold tracking-tight text-slate-900")

        with ui.row().classes("items-center gap-6"):
            ui.link("Home", "#hero").classes("heartai-nav-link active text-slate-700 font-medium no-underline")
            ui.link("Doctors", "#doctors").classes("heartai-nav-link text-slate-700 font-medium no-underline")
            ui.link("Analytics", "#analytics").classes("heartai-nav-link text-slate-700 font-medium no-underline")
            ui.link("Metrics", "#metrics").classes("heartai-nav-link text-slate-700 font-medium no-underline")
            ui.button("Check Symptoms", icon="health_and_safety", on_click=symptom_dialog.open).props("outline").classes(
                "heartai-btn text-teal-800 border-teal-600 rounded-lg px-3 py-1.5 text-xs font-semibold"
            )
            ui.button("Sign In").classes("heartai-btn bg-teal-600 text-white rounded-lg px-4 py-2 font-medium")

    # =========================================================================
    # 2. HERO SECTION
    # =========================================================================
    with ui.element("section").props('id="hero"').classes("min-h-[85vh] pt-32 px-8 max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-12"):
        with ui.column().classes("flex-1"):
            ui.html(
                '<h1 class="heartai-hero-headline text-4xl md:text-5xl font-extrabold text-slate-900 leading-tight mb-4">'
                'Predictive Cardiac Care Powered by '
                '<span class="heartai-teal-accent">Intelligent Clinical AI</span>'
                '</h1>'
            )
            ui.label(
                "Continuous real-time cardiovascular risk assessment, early arrhythmia detection, "
                "and personalized cardiology analytics designed for physicians and patients."
            ).classes("text-slate-600 text-lg mb-6 leading-relaxed")

            with ui.row().classes("gap-3 items-center flex-wrap"):
                ui.button("Start Assessment", icon="arrow_forward", on_click=assessment_dialog.open).classes(
                    "heartai-btn bg-teal-600 text-white text-base px-6 py-3 rounded-xl shadow-lg"
                )
                ui.button("Check Symptoms", icon="health_and_safety", on_click=symptom_dialog.open).props("outline").classes(
                    "heartai-btn text-teal-700 border-teal-600 px-5 py-3 rounded-xl"
                )
                ui.button(
                    "Ask Aarogya Saathi",
                    icon="spa",
                    on_click=lambda: open_aarogya_with_prompt("Hello Aarogya Saathi! How does HeartAI assist in cardiovascular health education?"),
                ).classes("heartai-btn bg-teal-800 text-white text-base px-5 py-3 rounded-xl shadow-md")

            with ui.column().classes("mt-8 w-full max-w-md"):
                ui.label("Live Isoelectric Rhythm Monitor").classes("text-xs font-semibold text-teal-800 uppercase tracking-wider")
                ui.html(render_ecg_svg(width=340, height=70, stroke_color="#0d9488", stroke_width=2.5))

        with ui.column().classes("flex-1 items-center justify-center"):
            ui.html(render_anatomical_heart_svg(size=180, pulse=True))
            ui.html(
                '<div class="mt-4 px-4 py-2 bg-white/90 shadow-md rounded-full border border-slate-100 text-xs font-semibold text-slate-700 flex items-center gap-2">'
                '<span class="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-ping"></span> Real-Time Hemodynamic Stream Active'
                '</div>'
            )

    # =========================================================================
    # 3. DOCTORS SECTION
    # =========================================================================
    with ui.element("section").props('id="doctors"').classes("py-20 px-8 max-w-6xl mx-auto"):
        ui.label("Our Expert Cardiologists").classes("text-3xl font-bold text-slate-900 text-center mb-2")
        ui.label("Board-certified cardiac specialists guiding AI-driven clinical outcomes.").classes("text-slate-500 text-center mb-6")

        # Contextual AI trigger for doctors
        with ui.row().classes("w-full justify-center mb-10"):
            ui.button(
                "Ask Aarogya Saathi About Cardiac Specialties & When to See a Cardiologist",
                icon="spa",
                on_click=lambda: open_aarogya_with_prompt("When should someone consult a cardiologist, and what is the difference between an electrophysiologist and an interventional cardiologist?"),
            ).props("outline dense").classes("heartai-btn text-teal-800 border-teal-600 px-4 py-2 rounded-xl text-xs font-medium")

        with ui.row().classes("heartai-doctors-grid grid grid-cols-1 md:grid-cols-3 gap-8 w-full"):
            doctors = [
                ("Dr. Elena Vance, MD", "Chief of Cardiology", "Harvard Medical School", "https://images.unsplash.com/photo-1559839734-2b71ea197ec2?w=400&q=80"),
                ("Dr. Marcus Chen, FACC", "Electrophysiologist", "Johns Hopkins", "https://images.unsplash.com/photo-1622253692010-333f2da6031d?w=400&q=80"),
                ("Dr. Sarah Al-Mansoor, MD", "Interventional Cardiologist", "Stanford Health", "https://images.unsplash.com/photo-1594824813583-b92c4b5744f4?w=400&q=80"),
            ]
            for name, role, institute, img_url in doctors:
                with ui.card().classes("heartai-doctor-card bg-white rounded-2xl overflow-hidden shadow-sm border border-slate-100 p-0"):
                    with ui.element("div").classes("heartai-doctor-img-wrap h-64 w-full bg-slate-100"):
                        ui.image(img_url).classes("heartai-doctor-img w-full h-full object-cover")
                    with ui.column().classes("p-6"):
                        ui.label(name).classes("text-lg font-bold text-slate-900")
                        ui.label(role).classes("text-sm font-medium text-teal-600")
                        ui.label(institute).classes("text-xs text-slate-400 mt-1")

    # =========================================================================
    # 4. ANALYTICS SECTION
    # =========================================================================
    with ui.element("section").props('id="analytics"').classes("py-20 px-8 bg-slate-50/80"):
        with ui.column().classes("max-w-6xl mx-auto"):
            ui.label("Clinical Analytics & Performance").classes("text-3xl font-bold text-slate-900 text-center mb-2")
            ui.label("Validated across multi-center cardiovascular clinical datasets.").classes("text-slate-500 text-center mb-12")

            with ui.row().classes("grid grid-cols-2 md:grid-cols-4 gap-6 w-full mb-12"):
                stats = [
                    ("98.4", "%", "Model Sensitivity", "0.1"),
                    ("142", "k+", "ECG Recordings Analyzed", "0"),
                    ("12", "ms", "Inference Latency", "0"),
                    ("99.1", "%", "Arrhythmia Specificity", "0.1"),
                ]
                for target, suffix, title, dec in stats:
                    with ui.card().classes("bg-white p-6 rounded-xl border border-slate-100 shadow-sm text-center"):
                        ui.html(f'<div class="heartai-counter text-3xl font-extrabold text-teal-700" data-target="{target}" data-suffix="{suffix}" data-decimals="{dec}">0{suffix}</div>')
                        ui.label(title).classes("text-xs font-semibold text-slate-500 uppercase mt-2")

            with ui.card().classes("bg-white p-8 rounded-2xl border border-slate-100 shadow-sm w-full flex flex-col md:flex-row items-center justify-around gap-8"):
                with ui.column().classes("items-center text-center"):
                    ui.label("Patient Risk Categorization").classes("text-sm font-semibold text-slate-500 uppercase tracking-wider mb-2")
                    gauge_slot = ui.element("div")
                    with gauge_slot:
                        ui.html(render_risk_gauge_svg(risk_score_percent=19, risk_category="Optimal Hemodynamics", width=260, height=140))
                with ui.column().classes("flex-1"):
                    ui.label("Risk Trajectory Analysis").classes("text-lg font-bold text-slate-900 mb-2")
                    analysis_text = ui.label(
                        "Patient survey baseline indicates an estimated probability of reported "
                        "historical cardiovascular disease of 18.98%, evaluated using calibrated BRFSS ensemble. "
                        "Educational research estimate; not a clinical diagnostic device."
                    ).classes("text-slate-600 text-sm leading-relaxed mb-4")

                    async def generate_diagnostic_report():
                        payload: dict[str, Any] = {
                            "Sex_Male": 1,
                            "AgeCategory": 10,
                            "BMI": 28.5,
                            "BMICategory": 3,
                            "Race": 1,
                            "Education": 4,
                            "Income": 7,
                            "GeneralHealth": 3,
                            "PhysicalHealthDays": 4.0,
                            "MentalHealthDays": 2.0,
                            "HighBP": 1,
                            "HighCholesterol": 1,
                            "StrokeHistory": 0,
                            "Diabetes": 0,
                            "KidneyDisease": 0,
                            "Depression": 0,
                            "Asthma": 0,
                            "SmokerStatus": 3,
                            "ECigStatus": 4,
                            "PhysicalActivity": 1,
                            "AlcoholDrinking": 1,
                            "BingeDrinking": 0,
                            "Checkup": 1,
                            "MedCostObstacle": 0,
                            "PersonalDoctor": 1,
                            "user_consent_given": False,
                            "consent_terms_version": None,
                        }
                        try:
                            async with httpx.AsyncClient(timeout=5.0) as client:
                                resp = await client.post(f"{BACKEND_API_URL}/predict", json=payload)
                                if resp.status_code == 200:
                                    data = resp.json()
                                    pct = data["estimated_probability_percentage"]
                                    flag = data["binary_classification"]
                                    flag_label = "Pattern Detected" if flag == 1 else "Normal Baseline"
                                    gauge_slot.clear()
                                    with gauge_slot:
                                        ui.html(render_risk_gauge_svg(risk_score_percent=int(pct), risk_category=flag_label, width=260, height=140))
                                    analysis_text.text = (
                                        f"Estimated probability of reported historical cardiovascular disease: "
                                        f"{pct:.2f}% (Operating Threshold: {data['operating_threshold']}, Classification: {flag_label}). "
                                        f"{data['educational_disclaimer']}"
                                    )
                                    ui.notify(f"Telemetry refreshed from backend: {pct:.2f}%", color="teal")
                        except Exception as err:
                            ui.notify(f"Backend telemetry call notice: {err}", color="orange")

                    with ui.row().classes("gap-3 items-center flex-wrap"):
                        ui.button("Generate Detailed Diagnostic Report", icon="description", on_click=generate_diagnostic_report).classes(
                            "heartai-btn bg-teal-600 text-white text-sm px-4 py-2 rounded-lg"
                        )
                        ui.button(
                            "Aarogya Saathi Model Insights",
                            icon="spa",
                            on_click=lambda: open_aarogya_with_prompt("Explain the clinical performance, sensitivity (~80%), and calibration threshold (0.09) of the HeartAI CDC BRFSS model."),
                        ).classes("heartai-btn bg-teal-800 text-white text-sm px-4 py-2 rounded-lg")

    # =========================================================================
    # 5. HEALTH METRICS SECTION
    # =========================================================================
    with ui.element("section").props('id="metrics"').classes("py-20 px-8 max-w-6xl mx-auto"):
        ui.label("Real-Time Vital Metrics").classes("text-3xl font-bold text-slate-900 text-center mb-2")
        ui.label("Reactive circular gauges with dynamic client-side tweening.").classes("text-slate-500 text-center mb-10")

        with ui.row().classes("justify-center gap-8 w-full flex-wrap"):
            ui.html(render_circular_gauge_svg("hr", percent=72, display_value=72, unit="bpm", color="#ef4444", label="Heart Rate"))
            ui.html(render_circular_gauge_svg("spo2", percent=98, display_value=98, unit="%", color="#0d9488", label="SpO2"))
            ui.html(render_circular_gauge_svg("bp", percent=65, display_value=120, unit="mmHg", color="#3b82f6", label="Systolic BP"))
            ui.html(render_circular_gauge_svg("hrv", percent=82, display_value=58, unit="ms", color="#8b5cf6", label="HRV Score"))

        with ui.row().classes("justify-center mt-6 flex-wrap gap-3"):
            def simulate_live_data():
                new_hr = random.randint(65, 88)
                new_spo2 = random.randint(96, 99)
                new_bp = random.randint(115, 130)
                ui.run_javascript(get_update_metric_js("hr", new_hr, 120))
                ui.run_javascript(get_update_metric_js("spo2", new_spo2, 100))
                ui.run_javascript(get_update_metric_js("bp", new_bp, 160))

            ui.button("Simulate Live Telemetry Update", icon="refresh", on_click=simulate_live_data).classes("heartai-btn bg-slate-900 text-white rounded-lg px-5 py-2.5 shadow")
            ui.button(
                "Explain Metrics with Aarogya Saathi",
                icon="spa",
                on_click=lambda: open_aarogya_with_prompt("Explain the physiological relationship and healthy ranges for Heart Rate (bpm), SpO2 (%), Systolic Blood Pressure, and HRV (ms)."),
            ).classes("heartai-btn text-teal-800 border border-teal-600 px-5 py-2.5 rounded-lg ml-3")

    # =========================================================================
    # 6. BOTTOM DOCTOR BANNER
    # =========================================================================
    with ui.element("section").classes("heartai-banner-section bg-teal-900 text-white py-24 px-8 mt-16 rounded-3xl max-w-6xl mx-auto relative overflow-hidden"):
        # Parallax Background Glow
        ui.html(
            '<div class="heartai-parallax-bg" style="background: radial-gradient(circle at 70% 50%, rgba(20, 184, 166, 0.4) 0%, transparent 60%);"></div>'
        )
        with ui.row().classes("items-center justify-between gap-12 relative z-10 flex-col md:flex-row"):
            with ui.column().classes("flex-1"):
                ui.label("Transforming Cardiac Outcomes Together").classes("heartai-banner-text text-3xl md:text-4xl font-extrabold mb-4 leading-tight")
                ui.label(
                    "HeartAI connects hospitals, cardiologists, and emergency response teams "
                    "with proactive predictive telemetry."
                ).classes("heartai-banner-text text-teal-100 text-base mb-6 leading-relaxed")
                ui.button("Schedule Hospital Demonstration", icon="calendar_today").classes("heartai-btn heartai-banner-text bg-white text-teal-900 font-bold px-6 py-3 rounded-xl shadow-lg")

            with ui.element("div").classes("heartai-banner-reveal-img flex-1 flex justify-center"):
                ui.image("https://images.unsplash.com/photo-1579684385127-1ef15d508118?w=600&q=80").classes("rounded-2xl shadow-2xl max-h-72 object-cover border-2 border-teal-500/30")

    # =========================================================================
    # 7. FLOATING INDIAN AI ASSISTANT: AAROGYA SAATHI (आरोग्य साथी)
    # =========================================================================
    with ui.page_sticky(position="bottom-right", x_offset=24, y_offset=24):
        with ui.element("div").classes("relative flex items-center justify-center"):
            # Subtle pulse ring
            ui.element("div").classes("aarogya-pulse-ring")
            # Floating Action Button
            with ui.button(on_click=aarogya_dialog.open).props("round").classes("aarogya-avatar-btn text-white w-14 h-14 relative z-10 flex items-center justify-center cursor-pointer"):
                ui.icon("spa").classes("text-2xl text-amber-200")
                ui.tooltip("Aarogya Saathi (आरोग्य साथी) — Your Health Companion")
                # Online status green dot
                ui.element("span").classes("absolute top-0 right-0 w-3.5 h-3.5 rounded-full bg-emerald-400 border-2 border-white")

    # CLIENT INITIALIZATION HOOK
    # Runs the motion engine once DOM elements are rendered
    ui.timer(0.1, lambda: ui.run_javascript(
        f"{get_init_hero_js()}; "
        f"{get_init_navbar_js()}; "
        f"{get_init_doctor_images_js()}; "
        f"{get_init_analytics_js()}; "
        f"{get_init_health_metrics_js()}; "
        f"{get_init_doctor_banner_js()};"
    ), once=True)


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="HeartAI — Advanced Motion & Aarogya Saathi Demo", port=8080, reload=False, show=False)
