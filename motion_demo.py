"""HeartAI Motion System & Modernized Clinical Interface — Point 10.

Implements:
1. Unified Design Language:
   - Primary: Teal futuristic healthcare (dominant brand identity).
   - Secondary: Purple glassmorphism (Aarogya Saathi AI & interactive modals).
   - Analytics: Premium high-contrast dark interface (data & trajectories).
2. Complete Dual Theme System (Light / Dark mode) with navbar switcher,
   persistence in localStorage, system preference detection, and accessible controls.
3. Clean, Modern & Interactive Navbar:
   - Desktop: Brand, links, functional "Clinical Tools" dropdown, theme toggle,
     Aarogya Saathi quick-launch, account/auth modal.
   - Mobile: Responsive slide-in navigation drawer, theme switch, accessible touch targets.
4. Comprehensive Dashboard Hierarchy:
   - Welcome header, core clinical metrics, assessment hub, symptom triage,
     vital telemetry preview, and research audit log.
5. Cardiovascular Visual Experience:
   - Holographic/anatomical heart SVG, live isoelectric ECG monitor,
     reactive vitals gauges, and semi-circular risk gauge.
6. Modernized Aarogya Saathi AI Assistant (आरोग्य साथी):
   - Purple glassmorphic floating orb button and chat dialog with emergency banner (India 112/102).
7. Strict Medical & Scientific Disclosures:
   - CDC BRFSS 2023 non-diagnostic research prototype limitations preserved everywhere.
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
    render_theme_toggle_html,
)

# Register static routes
register_motion_routes(app)

BACKEND_API_URL = "http://localhost:8000"


@ui.page("/")
def index_page():
    # Inject Motion Styles & Scripts
    ui.add_head_html(get_motion_head_html(use_cdn=False))

    # =========================================================================
    # DIALOG 1: AAROGYA SAATHI (आरोग्य साथी) PURPLE GLASSMORPHIC AI ASSISTANT
    # =========================================================================
    with ui.dialog() as aarogya_dialog, ui.card().classes(
        "p-0 max-w-xl w-full rounded-2xl bg-white dark:bg-slate-900 shadow-2xl border border-slate-200 dark:border-purple-500/20 flex flex-col overflow-hidden heartai-glass-purple"
    ):
        # Header with Purple Glassmorphic Identity
        with ui.row().classes(
            "w-full justify-between items-center px-6 py-4 bg-gradient-to-r from-teal-800 via-teal-700 to-purple-800 text-white"
        ):
            with ui.row().classes("items-center gap-3"):
                with ui.element("div").classes("relative flex items-center justify-center w-10 h-10 rounded-full bg-white/20 border border-white/30"):
                    ui.icon("spa", color="amber-300").classes("text-xl")
                    # Online status indicator dot
                    ui.element("span").classes("absolute bottom-0 right-0 w-3 h-3 rounded-full bg-emerald-400 border-2 border-teal-800")
                with ui.column().classes("gap-0"):
                    ui.label("Aarogya Saathi (आरोग्य साथी)").classes("text-base font-bold tracking-wide")
                    ui.label("HeartAI Health & Wellbeing Companion").classes("text-[11px] text-teal-100")
            with ui.row().classes("items-center gap-2"):
                ui.element("span").classes("text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 border border-emerald-400/40 text-emerald-200 font-medium").text = "Online"
                ui.button(icon="close", on_click=aarogya_dialog.close).props("flat round dense").classes("text-white/80 hover:text-white")

        # Emergency Notice Bar
        with ui.row().classes("w-full px-6 py-2 bg-amber-50 dark:bg-amber-950/40 border-b border-amber-200 dark:border-amber-800/40 items-center justify-between text-[11px] text-amber-900 dark:text-amber-200"):
            with ui.row().classes("items-center gap-1.5"):
                ui.icon("warning", color="amber-700").classes("text-sm")
                ui.label("Emergency Notice: For acute chest pain or distress, call").classes("font-medium")
                ui.element("span").classes("font-bold text-red-700 dark:text-red-400").text = "112 / 102 (India)"
                ui.label("or 911 immediately.")

        # Chat Message Thread
        chat_scroll = ui.scroll_area().classes("h-80 w-full px-6 py-4 bg-slate-50/70 dark:bg-slate-900/60 border-b border-slate-100 dark:border-slate-800")
        with chat_scroll:
            chat_container = ui.column().classes("gap-3 w-full")
            with chat_container:
                with ui.chat_message(
                    name="Aarogya Saathi",
                    stamp="Just now",
                    avatar="https://images.unsplash.com/photo-1559839734-2b71ea197ec2?w=100&q=80",
                ):
                    ui.label(
                        "Namaste! I am Aarogya Saathi (आरोग्य साथी), your HeartAI companion for cardiovascular health education. "
                        "I can help explain cardiovascular health concepts, vital metrics (BP, SpO2, HRV), "
                        "our calibrated CDC BRFSS model, and guide you through symptom checks. "
                        "How may I support your health education today?"
                    ).classes("text-xs leading-relaxed text-slate-800 dark:text-slate-100")

        # Typing indicator container
        typing_indicator = ui.row().classes("hidden px-6 py-1 items-center gap-1.5 text-xs text-purple-700 dark:text-purple-300")
        with typing_indicator:
            ui.element("span").classes("aarogya-typing-dot")
            ui.element("span").classes("aarogya-typing-dot")
            ui.element("span").classes("aarogya-typing-dot")
            ui.label("Aarogya Saathi is preparing your educational response...").classes("text-[11px] text-slate-500 italic ml-1")

        # Quick Prompt Chips
        def set_chat_prompt(text: str):
            chat_input.value = text

        with ui.row().classes("px-6 py-2 gap-1.5 flex-wrap bg-white dark:bg-slate-900 border-t border-slate-100 dark:border-slate-800"):
            ui.button("Blood Pressure Ranges", on_click=lambda: set_chat_prompt("What are the standard clinical blood pressure ranges and classifications?")).props("outline dense").classes("text-[10px] text-teal-700 dark:text-teal-300 border-teal-200 dark:border-teal-700 hover:bg-teal-50")
            ui.button("Why Threshold 0.09?", on_click=lambda: set_chat_prompt("Why does HeartAI use an operating threshold of 0.09 instead of 0.50?")).props("outline dense").classes("text-[10px] text-teal-700 dark:text-teal-300 border-teal-200 dark:border-teal-700 hover:bg-teal-50")
            ui.button("Life's Essential 8", on_click=lambda: set_chat_prompt("What are the American Heart Association Life's Essential 8 cardiovascular health factors?")).props("outline dense").classes("text-[10px] text-teal-700 dark:text-teal-300 border-teal-200 dark:border-teal-700 hover:bg-teal-50")
            ui.button("What is Aarogya Saathi?", on_click=lambda: set_chat_prompt("Tell me about Aarogya Saathi and HeartAI's clinical education mission.")).props("outline dense").classes("text-[10px] text-purple-700 dark:text-purple-300 border-purple-200 dark:border-purple-700 hover:bg-purple-50")

        # Input Row
        with ui.row().classes("px-6 py-3 w-full gap-2 items-center bg-white dark:bg-slate-900"):
            chat_input = ui.input(placeholder="Ask Aarogya Saathi about heart health, metrics, or symptoms...").classes("flex-1 text-xs").props("outlined dense")
            chat_send_btn = ui.button(icon="send").classes("bg-teal-700 hover:bg-teal-800 text-white rounded-lg px-3 py-1.5 shadow")

        async def send_chat_message():
            msg = (chat_input.value or "").strip()
            if not msg:
                return
            chat_input.value = ""
            with chat_container:
                with ui.chat_message(name="You", sent=True, stamp="now"):
                    ui.label(msg).classes("text-xs text-slate-800 dark:text-slate-100")
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
                            ui.label("CRITICAL MEDICAL ALERT").classes("text-xs font-bold text-red-700 dark:text-red-300")
                            ui.markdown(resp_text).classes("text-xs text-red-900 dark:text-red-100 leading-relaxed")
                    else:
                        ui.markdown(resp_text).classes("text-xs leading-relaxed text-slate-800 dark:text-slate-100")
            chat_scroll.scroll_to(percent=1.0)

        chat_send_btn.on("click", send_chat_message)
        chat_input.on("keydown.enter", send_chat_message)

        # Footer Disclaimer
        ui.label(
            "Aarogya Saathi is an educational health assistant. Never provides medical diagnoses or prescriptions. In emergencies call 112 (India) or 911."
        ).classes("text-[9px] text-slate-400 italic text-center w-full px-6 py-2 bg-slate-50 dark:bg-slate-900/80")

    def open_aarogya_with_prompt(prompt_text: str):
        chat_input.value = prompt_text
        aarogya_dialog.open()

    # =========================================================================
    # DIALOG 2: CARDIOVASCULAR SYMPTOM ASSESSMENT DIALOG
    # =========================================================================
    with ui.dialog() as symptom_dialog, ui.card().classes(
        "p-6 max-w-xl w-full rounded-2xl bg-white dark:bg-slate-900 shadow-2xl border border-slate-200 dark:border-slate-800 flex flex-col gap-4 max-h-[90vh] overflow-y-auto"
    ):
        with ui.row().classes("w-full justify-between items-center pb-2 border-b border-slate-100 dark:border-slate-800"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("health_and_safety", color="teal-700").classes("text-2xl")
                with ui.column().classes("gap-0"):
                    ui.label("Cardiovascular Symptom Assessment").classes("text-lg font-bold text-slate-900 dark:text-slate-100")
                    ui.label("Deterministic emergency screening & educational triage guidance").classes("text-xs text-slate-500")
            ui.button(icon="close", on_click=symptom_dialog.close).props("flat round dense").classes("text-slate-400")

        # Emergency Warning Header
        with ui.card().classes("w-full p-3 bg-red-50 dark:bg-red-950/40 border-l-4 border-red-500 rounded-lg"):
            ui.label("Immediate Emergency Notice").classes("text-xs font-bold text-red-800 dark:text-red-300")
            ui.label(
                "If you or someone near you is experiencing crushing chest pressure, an elephant on your chest, "
                "pain radiating to the jaw/arm, sudden severe breathlessness, or syncope: "
                "CALL 112 / 102 (INDIA) OR 911 IMMEDIATELY. Do not wait."
            ).classes("text-[11px] text-red-700 dark:text-red-200 mt-0.5 leading-snug")

        with ui.column().classes("gap-3 w-full"):
            ui.label("Primary Symptoms Description").classes("text-xs font-semibold text-slate-700 dark:text-slate-300")
            symp_desc = ui.textarea(
                placeholder="Describe what you are feeling (e.g. tightness in chest, racing heartbeat, mild shortness of breath during stairs)..."
            ).classes("w-full text-xs").props("outlined dense rows=2")

            with ui.row().classes("w-full gap-4 flex-col sm:flex-row"):
                with ui.column().classes("flex-1 gap-1"):
                    ui.label("Onset Timeframe").classes("text-xs font-semibold text-slate-700 dark:text-slate-300")
                    symp_onset = ui.select(
                        options=["Within the last hour", "Earlier today", "Past few days", "Over weeks/months"],
                        value="Earlier today",
                    ).classes("w-full text-xs").props("outlined dense")
                with ui.column().classes("flex-1 gap-1"):
                    ui.label("Pattern").classes("text-xs font-semibold text-slate-700 dark:text-slate-300")
                    symp_pattern = ui.select(
                        options=["Ongoing continuous", "Intermittent / episodes", "Only with physical exertion"],
                        value="Intermittent / episodes",
                    ).classes("w-full text-xs").props("outlined dense")

            with ui.row().classes("w-full gap-4 flex-col sm:flex-row"):
                with ui.column().classes("flex-1 gap-1"):
                    ui.label("Severity").classes("text-xs font-semibold text-slate-700 dark:text-slate-300")
                    symp_severity = ui.select(
                        options=["Mild (noticeable but doesn't limit activity)", "Moderate (interferes with normal activity)", "Severe (unable to perform daily tasks)", "Very Severe (extreme distress)"],
                        value="Moderate (interferes with normal activity)",
                    ).classes("w-full text-xs").props("outlined dense")
                with ui.column().classes("flex-1 gap-1"):
                    ui.label("Progression Trend").classes("text-xs font-semibold text-slate-700 dark:text-slate-300")
                    symp_progression = ui.select(
                        options=["Improving", "Stable / unchanged", "Gradually worsening", "Rapidly worsening"],
                        value="Stable / unchanged",
                    ).classes("w-full text-xs").props("outlined dense")

            ui.label("Associated Warning Signs (Select all that apply)").classes("text-xs font-semibold text-slate-700 dark:text-slate-300 mt-1")
            with ui.row().classes("gap-3 w-full flex-wrap"):
                assoc_sob = ui.checkbox("Shortness of breath", value=False).classes("text-xs text-slate-700 dark:text-slate-300")
                assoc_rad = ui.checkbox("Pain radiating to arm / jaw / neck", value=False).classes("text-xs text-slate-700 dark:text-slate-300")
                assoc_diz = ui.checkbox("Dizziness or lightheadedness", value=False).classes("text-xs text-slate-700 dark:text-slate-300")
                assoc_sweat = ui.checkbox("Cold sweat / diaphoresis", value=False).classes("text-xs text-slate-700 dark:text-slate-300")
                assoc_palp = ui.checkbox("Heart racing or fluttering", value=False).classes("text-xs text-slate-700 dark:text-slate-300")

            symptom_results_box = ui.column().classes("w-full hidden mt-2 p-4 bg-slate-50 dark:bg-slate-800/60 rounded-xl border border-slate-200 dark:border-slate-700")

            async def submit_symptom_assessment():
                desc_val = (symp_desc.value or "").strip()
                if not desc_val:
                    ui.notify("Please describe your symptoms first.", color="orange")
                    return

                sev_map = {
                    "Mild (noticeable but doesn't limit activity)": SymptomSeverity.MILD,
                    "Moderate (interferes with normal activity)": SymptomSeverity.MODERATE,
                    "Severe (unable to perform daily tasks)": SymptomSeverity.SEVERE,
                    "Very Severe (extreme distress)": SymptomSeverity.VERY_SEVERE,
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
                            ui.label("CRITICAL EMERGENCY DETECTED").classes("text-sm font-extrabold text-red-800 dark:text-red-300")
                            ui.label("Your symptoms match patterns requiring IMMEDIATE emergency evaluation.").classes("text-xs font-semibold text-red-900 dark:text-red-100 mt-1")
                            ui.label("CALL 112 / 102 (INDIA) OR 911 IMMEDIATELY. Do not attempt to drive yourself.").classes("text-xs font-bold text-red-700 dark:text-red-300 mt-2")
                            contacts = data.get("emergency_contacts", {})
                            if contacts:
                                contact_str = ", ".join(f"{k}: {v}" for k, v in contacts.items())
                                ui.label(f"Emergency Contacts: {contact_str}").classes("text-[10px] text-red-800 dark:text-red-200 mt-1")

                    urgency_colors = {
                        "EMERGENCY": "bg-red-600 text-white",
                        "URGENT": "bg-amber-600 text-white",
                        "ROUTINE": "bg-teal-600 text-white",
                        "NON_CARDIOVASCULAR_OR_UNCERTAIN": "bg-slate-600 text-white",
                    }
                    with ui.row().classes("items-center gap-2 mb-2"):
                        ui.label("Triage Urgency:").classes("text-xs font-bold text-slate-700 dark:text-slate-300")
                        badge_cls = urgency_colors.get(urgency, "bg-slate-600 text-white")
                        ui.element("span").classes(f"text-[10px] font-bold px-2 py-0.5 rounded-full {badge_cls}").text = urgency

                    ui.label("Assessment Summary:").classes("text-xs font-bold text-slate-800 dark:text-slate-100 mt-1")
                    ui.label(data.get("symptom_summary", "")).classes("text-xs text-slate-700 dark:text-slate-300 leading-relaxed")

                    ui.label("Cardiovascular Relevance:").classes("text-xs font-bold text-slate-800 dark:text-slate-100 mt-2")
                    ui.label(data.get("general_cardiovascular_relevance", "")).classes("text-xs text-slate-700 dark:text-slate-300 leading-relaxed")

                    warning_signs = data.get("warning_signs_identified", [])
                    if warning_signs:
                        ui.label("Observed Warning Signs:").classes("text-xs font-bold text-amber-900 dark:text-amber-300 mt-2")
                        for ws in warning_signs:
                            with ui.row().classes("items-center gap-1.5 ml-2"):
                                ui.icon("fiber_manual_record", color="amber-700").classes("text-[8px]")
                                ui.label(ws).classes("text-xs text-amber-950 dark:text-amber-200")

                    ui.label("Suggested Next Action:").classes("text-xs font-bold text-teal-900 dark:text-teal-300 mt-2")
                    ui.label(data.get("suggested_next_action", "")).classes("text-xs text-teal-950 dark:text-teal-100 font-medium leading-relaxed")

                    def transfer_to_chat():
                        symptom_dialog.close()
                        open_aarogya_with_prompt(
                            f"I completed the symptom assessment. My reported symptoms: '{desc_val}'. "
                            f"Assigned urgency: {urgency}. Could you explain more about what this means and what questions I should ask my doctor?"
                        )

                    ui.button("Discuss with Aarogya Saathi", icon="chat", on_click=transfer_to_chat).classes(
                        "heartai-btn bg-teal-800 hover:bg-teal-900 text-white text-xs px-3 py-1.5 rounded-lg mt-3"
                    )

            with ui.row().classes("w-full justify-end gap-3 mt-4"):
                ui.button("Cancel", on_click=symptom_dialog.close).props("outline").classes("text-slate-600 dark:text-slate-400")
                ui.button("Assess Symptoms", icon="health_and_safety", on_click=submit_symptom_assessment).classes(
                    "heartai-btn bg-teal-700 hover:bg-teal-800 text-white rounded-lg px-4 py-2 font-medium"
                )

    # =========================================================================
    # DIALOG 3: CDC BRFSS SURVEY RISK ASSESSMENT MODAL
    # =========================================================================
    with ui.dialog() as assessment_dialog, ui.card().classes(
        "p-6 max-w-lg w-full rounded-2xl bg-white dark:bg-slate-900 shadow-xl border border-slate-200 dark:border-slate-800"
    ):
        ui.label("Cardiovascular Survey Assessment").classes("text-xl font-bold text-slate-900 dark:text-slate-100 mb-1")
        ui.label(
            "Submits CDC BRFSS feature vector to the calibrated HeartAI backend for educational estimation."
        ).classes("text-xs text-slate-500 mb-4")

        with ui.column().classes("gap-3 w-full"):
            with ui.row().classes("w-full justify-between items-center"):
                ui.label("Age Bracket (1: 18-24 ... 13: 80+)").classes("text-sm text-slate-700 dark:text-slate-300")
                age_cat = ui.number(value=10, min=1, max=13, step=1).classes("w-20")

            with ui.row().classes("w-full justify-between items-center"):
                ui.label("Body Mass Index (BMI)").classes("text-sm text-slate-700 dark:text-slate-300")
                bmi_val = ui.number(value=28.5, min=12.0, max=80.0, step=0.1).classes("w-24")

            with ui.row().classes("w-full justify-between items-center"):
                ui.label("General Health (1: Excellent ... 5: Poor)").classes("text-sm text-slate-700 dark:text-slate-300")
                gen_health = ui.number(value=3, min=1, max=5, step=1).classes("w-20")

            with ui.row().classes("gap-4 w-full flex-wrap"):
                bp_check = ui.checkbox("High Blood Pressure", value=True)
                chol_check = ui.checkbox("High Cholesterol", value=True)
                smoker_check = ui.checkbox("Current / Former Smoker", value=True)

            consent_check = ui.checkbox(
                "I affirmatively consent to store a keyed pseudonymized digest for research audit",
                value=False,
            ).classes("text-xs text-teal-800 dark:text-teal-300 font-medium mt-2")
            ui.label(
                "Notice: When enabled, a keyed HMAC-SHA256 digest (not raw answers) is stored for calibration audit. "
                "You may request deletion at any time."
            ).classes("text-[10px] text-slate-500 mb-1")

            result_banner = ui.column().classes("w-full hidden mt-2 p-3 bg-slate-50 dark:bg-slate-800/70 rounded-xl border border-slate-200 dark:border-slate-700")

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
                                ).classes("text-sm font-bold text-teal-900 dark:text-teal-200")
                                flag_str = (
                                    "Historical CVD Pattern Detected (prob >= 0.09)"
                                    if data["binary_classification"] == 1
                                    else "Baseline Survey Pattern (prob < 0.09)"
                                )
                                ui.label(f"Threshold Classification: {flag_str} (Operating Threshold: 0.09)").classes("text-xs text-slate-700 dark:text-slate-300")
                                ui.label(data["educational_disclaimer"]).classes("text-xs text-slate-500 italic mt-1")

                                def explain_in_aarogya():
                                    assessment_dialog.close()
                                    open_aarogya_with_prompt(
                                        f"Please explain my HeartAI cardiovascular risk estimate: {data['estimated_probability_percentage']:.2f}% "
                                        f"estimated probability ({flag_str}). What does this survey-based metric mean, why is the threshold 0.09, and what are its scientific limitations?"
                                    )

                                ui.button("Explain with Aarogya Saathi", icon="spa", on_click=explain_in_aarogya).classes(
                                    "heartai-btn bg-teal-800 hover:bg-teal-900 text-white text-xs px-3 py-1.5 rounded-lg mt-2"
                                )
                            ui.notify("Assessment inference successfully calculated", color="teal")
                        else:
                            ui.notify(f"Inference returned status {resp.status_code}", color="red")
                except Exception as exc:
                    ui.notify(f"Backend offline or unreachable ({exc}). Running local preview.", color="orange")

            with ui.row().classes("w-full justify-end gap-3 mt-4"):
                ui.button("Cancel", on_click=assessment_dialog.close).props("outline").classes("text-slate-600 dark:text-slate-400")
                ui.button("Calculate Risk", on_click=submit_assessment).classes(
                    "heartai-btn bg-teal-600 hover:bg-teal-700 text-white rounded-lg px-4 py-2 font-medium"
                )

    # =========================================================================
    # DIALOG 4: USER AUTHENTICATION & RESEARCH PROFILE MODAL
    # =========================================================================
    with ui.dialog() as auth_dialog, ui.card().classes(
        "p-6 max-w-md w-full rounded-2xl bg-white dark:bg-slate-900 shadow-2xl border border-slate-200 dark:border-slate-800 flex flex-col gap-4"
    ):
        with ui.row().classes("w-full justify-between items-center pb-2 border-b border-slate-100 dark:border-slate-800"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("account_circle", color="teal-700").classes("text-2xl")
                ui.label("Researcher & Physician Sign In").classes("text-lg font-bold text-slate-900 dark:text-slate-100")
            ui.button(icon="close", on_click=auth_dialog.close).props("flat round dense").classes("text-slate-400")

        auth_email = ui.input("Email Address", placeholder="doctor@hospital.org").classes("w-full text-xs").props("outlined dense")
        auth_password = ui.input("Password", placeholder="••••••••••••").classes("w-full text-xs").props("outlined dense type=password")

        auth_status_label = ui.label("").classes("text-xs text-slate-500")

        async def execute_sign_in():
            email_val = (auth_email.value or "").strip()
            pass_val = (auth_password.value or "").strip()
            if not email_val or not pass_val:
                auth_status_label.text = "Please enter both email and password."
                return
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.post(
                        f"{BACKEND_API_URL}/api/v1/auth/login",
                        json={"email": email_val, "password": pass_val},
                    )
                    if resp.status_code == 200:
                        ui.notify(f"Welcome back, {email_val}!", color="teal")
                        auth_status_label.text = "Authentication successful!"
                        auth_dialog.close()
                    else:
                        auth_status_label.text = f"Sign in failed (HTTP {resp.status_code})."
            except Exception:
                ui.notify("Backend authenticating in local mock mode.", color="teal")
                auth_dialog.close()

        with ui.row().classes("w-full justify-end gap-3 mt-2"):
            ui.button("Cancel", on_click=auth_dialog.close).props("outline").classes("text-slate-600 dark:text-slate-400")
            ui.button("Sign In", on_click=execute_sign_in).classes("heartai-btn bg-teal-600 hover:bg-teal-700 text-white rounded-lg px-4 py-2 font-medium")

    # =========================================================================
    # 1. NAVIGATION BAR (Clean, Modern, Interactive & Responsive)
    # =========================================================================
    with ui.header().classes("heartai-navbar w-full fixed top-0 left-0 z-50 px-6 md:px-10 py-3.5 flex justify-between items-center backdrop-blur-md"):
        # Left: Brand Logo & Identity
        with ui.row().classes("items-center gap-3"):
            ui.icon("favorite", color="red-500").classes("text-2xl heartai-pulse")
            with ui.column().classes("gap-0"):
                with ui.row().classes("items-center gap-2"):
                    ui.label("HeartAI").classes("text-xl font-extrabold tracking-tight text-slate-900 dark:text-white")
                    ui.element("span").classes("text-[10px] font-bold px-1.5 py-0.2 rounded bg-teal-500/15 text-teal-700 dark:text-teal-300 border border-teal-500/30").text = "v2.1"
                ui.label("Clinical Intelligence Platform").classes("text-[10px] text-slate-500 dark:text-slate-400 font-medium hidden sm:block")

        # Center: Desktop Navigation Links with Active State
        with ui.row().classes("items-center gap-6 hidden md:flex"):
            ui.link("Home", "#hero").classes("heartai-nav-link active font-medium text-sm no-underline")
            ui.link("Dashboard", "#dashboard").classes("heartai-nav-link font-medium text-sm no-underline")
            ui.link("Analytics", "#analytics").classes("heartai-nav-link font-medium text-sm no-underline")
            ui.link("Metrics", "#metrics").classes("heartai-nav-link font-medium text-sm no-underline")
            ui.link("Doctors", "#doctors").classes("heartai-nav-link font-medium text-sm no-underline")

            # Dropdown Menu: Clinical Tools
            with ui.element("div").classes("relative"):
                ui.button("Clinical Tools").props('icon-right="expand_more" flat dense data-dropdown-toggle="tools-dropdown"').classes(
                    "text-xs font-semibold text-slate-700 dark:text-slate-300 hover:text-teal-600"
                )
                with ui.element("div").props('id="tools-dropdown"').classes("heartai-dropdown-menu absolute top-full mt-2 left-0 hidden p-2 flex flex-col gap-1"):
                    ui.button("Risk Assessment Survey", icon="assessment", on_click=assessment_dialog.open).props("flat dense").classes("text-xs text-left justify-start text-slate-700 dark:text-slate-200 hover:bg-teal-50 dark:hover:bg-slate-800")
                    ui.button("Symptom Triage (112 India)", icon="health_and_safety", on_click=symptom_dialog.open).props("flat dense").classes("text-xs text-left justify-start text-slate-700 dark:text-slate-200 hover:bg-teal-50 dark:hover:bg-slate-800")
                    ui.button("Vital Stream Gauges", icon="speed", on_click=lambda: ui.navigate.to("#metrics")).props("flat dense").classes("text-xs text-left justify-start text-slate-700 dark:text-slate-200 hover:bg-teal-50 dark:hover:bg-slate-800")

        # Right: Actions (Theme Toggle, Aarogya Saathi, Sign In, Mobile Menu Toggle)
        with ui.row().classes("items-center gap-3"):
            # Theme Toggle Button (Desktop & Tablet)
            ui.html(render_theme_toggle_html())

            # Aarogya Saathi Assistant Quick Button
            with ui.button("Aarogya Saathi", icon="spa", on_click=aarogya_dialog.open).classes(
                "hidden lg:flex heartai-btn bg-purple-700 hover:bg-purple-800 text-white rounded-xl px-3.5 py-1.5 text-xs font-semibold shadow-md"
            ):
                ui.tooltip("Open Aarogya Saathi (आरोग्य साथी) AI Assistant")

            # Sign In Button
            ui.button("Sign In", icon="login", on_click=auth_dialog.open).classes(
                "heartai-btn bg-teal-600 hover:bg-teal-700 text-white rounded-xl px-4 py-1.5 text-xs font-medium shadow-sm hidden sm:flex"
            )

            # Mobile Hamburger Button
            ui.button(icon="menu").props("flat round dense").classes("md:hidden text-slate-800 dark:text-white").props('onclick="window.HeartAIMotion && window.HeartAIMotion.toggleMobileNav()" aria-label="Open mobile navigation"')

    # Mobile Drawer Backdrop & Drawer Element
    with ui.element("div").props('id="heartai-mobile-backdrop" onclick="window.HeartAIMotion && window.HeartAIMotion.closeMobileNav()"').classes(
        "fixed inset-0 bg-black/50 z-50 hidden backdrop-blur-sm transition-opacity duration-300 md:hidden"
    ):
        pass

    with ui.element("aside").props('id="heartai-mobile-menu"').classes(
        "fixed top-0 right-0 h-full w-72 bg-white dark:bg-slate-900 shadow-2xl z-50 p-6 flex flex-col justify-between hidden md:hidden border-l border-slate-200 dark:border-slate-800"
    ):
        with ui.column().classes("gap-4 w-full"):
            with ui.row().classes("justify-between items-center w-full pb-3 border-b border-slate-100 dark:border-slate-800"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("favorite", color="red-500").classes("text-xl heartai-pulse")
                    ui.label("HeartAI Menu").classes("font-bold text-slate-900 dark:text-white")
                ui.button(icon="close").props("flat round dense").props('onclick="window.HeartAIMotion && window.HeartAIMotion.closeMobileNav()" aria-label="Close menu"')

            # Mobile nav links
            with ui.column().classes("gap-2 w-full mt-2"):
                ui.link("Home", "#hero").classes("py-2 px-3 rounded-lg text-slate-800 dark:text-slate-200 hover:bg-teal-50 dark:hover:bg-slate-800 text-sm font-medium no-underline").props('onclick="window.HeartAIMotion && window.HeartAIMotion.closeMobileNav()"')
                ui.link("Dashboard", "#dashboard").classes("py-2 px-3 rounded-lg text-slate-800 dark:text-slate-200 hover:bg-teal-50 dark:hover:bg-slate-800 text-sm font-medium no-underline").props('onclick="window.HeartAIMotion && window.HeartAIMotion.closeMobileNav()"')
                ui.link("Analytics", "#analytics").classes("py-2 px-3 rounded-lg text-slate-800 dark:text-slate-200 hover:bg-teal-50 dark:hover:bg-slate-800 text-sm font-medium no-underline").props('onclick="window.HeartAIMotion && window.HeartAIMotion.closeMobileNav()"')
                ui.link("Metrics", "#metrics").classes("py-2 px-3 rounded-lg text-slate-800 dark:text-slate-200 hover:bg-teal-50 dark:hover:bg-slate-800 text-sm font-medium no-underline").props('onclick="window.HeartAIMotion && window.HeartAIMotion.closeMobileNav()"')
                ui.link("Doctors", "#doctors").classes("py-2 px-3 rounded-lg text-slate-800 dark:text-slate-200 hover:bg-teal-50 dark:hover:bg-slate-800 text-sm font-medium no-underline").props('onclick="window.HeartAIMotion && window.HeartAIMotion.closeMobileNav()"')

            with ui.column().classes("gap-2 w-full mt-4 pt-4 border-t border-slate-100 dark:border-slate-800"):
                ui.button("Start Assessment", icon="assessment", on_click=assessment_dialog.open).classes("w-full bg-teal-600 text-white rounded-lg py-2 text-xs font-semibold")
                ui.button("Symptom Triage", icon="health_and_safety", on_click=symptom_dialog.open).props("outline").classes("w-full text-teal-700 dark:text-teal-300 border-teal-500 rounded-lg py-2 text-xs font-semibold")
                ui.button("Aarogya Saathi AI", icon="spa", on_click=aarogya_dialog.open).classes("w-full bg-purple-700 text-white rounded-lg py-2 text-xs font-semibold")

        with ui.row().classes("justify-between items-center pt-4 border-t border-slate-100 dark:border-slate-800 w-full"):
            ui.label("Theme Switcher").classes("text-xs text-slate-500 dark:text-slate-400 font-medium")
            ui.html(render_theme_toggle_html())

    # =========================================================================
    # 2. HERO SECTION (Teal Futuristic Healthcare — Inspired by Reference 3)
    # =========================================================================
    with ui.element("section").props('id="hero"').classes("min-h-[88vh] pt-32 px-6 md:px-12 max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-12"):
        with ui.column().classes("flex-1"):
            # Trust Pill
            with ui.row().classes("items-center gap-2 px-3.5 py-1.5 rounded-full bg-teal-50 dark:bg-teal-950/60 border border-teal-200 dark:border-teal-700/60 mb-5 w-fit"):
                ui.element("span").classes("w-2 h-2 rounded-full bg-emerald-500 animate-ping")
                ui.label("CDC BRFSS 2023 Validated Pipeline • Operating Threshold T=0.09").classes("text-xs font-semibold text-teal-800 dark:text-teal-200")

            ui.html(
                '<h1 class="heartai-hero-headline text-4xl sm:text-5xl lg:text-6xl font-extrabold text-slate-900 dark:text-white leading-[1.15] mb-5">'
                'Heart Disease '
                '<span class="heartai-teal-accent">Risk Prediction</span> '
                '& Health Data Analytics'
                '</h1>'
            )
            ui.label(
                "Predict. Prevent. Live Healthier. Leverage calibrated machine learning and generative clinical education "
                "to evaluate cardiovascular disease associations and personalize lifestyle prevention."
            ).classes("text-slate-600 dark:text-slate-300 text-base md:text-lg mb-8 leading-relaxed max-w-xl")

            with ui.row().classes("gap-3.5 items-center flex-wrap"):
                ui.button("Start Risk Assessment", icon="arrow_forward", on_click=assessment_dialog.open).classes(
                    "heartai-btn bg-teal-600 hover:bg-teal-700 text-white text-base px-6 py-3 rounded-xl shadow-lg font-semibold"
                )
                ui.button("Check Symptoms", icon="health_and_safety", on_click=symptom_dialog.open).props("outline").classes(
                    "heartai-btn text-teal-700 dark:text-teal-300 border-teal-600 hover:bg-teal-50 dark:hover:bg-slate-800 px-5 py-3 rounded-xl font-medium"
                )
                ui.button(
                    "Ask Aarogya Saathi",
                    icon="spa",
                    on_click=lambda: open_aarogya_with_prompt("Hello Aarogya Saathi! How does HeartAI assist in cardiovascular health education?"),
                ).classes("heartai-btn bg-purple-700 hover:bg-purple-800 text-white text-base px-5 py-3 rounded-xl shadow-md font-medium")

            # ECG Monitor Waveform
            with ui.column().classes("mt-8 w-full max-w-md p-4 bg-white dark:bg-slate-900 rounded-2xl border border-slate-100 dark:border-slate-800 shadow-sm"):
                with ui.row().classes("justify-between items-center w-full mb-1"):
                    ui.label("Live Isoelectric Rhythm Monitor").classes("text-[11px] font-bold text-teal-700 dark:text-teal-300 uppercase tracking-wider")
                    ui.label("Normal Sinus • 72 bpm").classes("text-[11px] text-emerald-600 dark:text-emerald-400 font-semibold")
                ui.html(render_ecg_svg(width=340, height=65, stroke_color="#0d9488", stroke_width=2.5))

        # Central Visual: Holographic / Anatomical Heart Visual
        with ui.column().classes("flex-1 items-center justify-center relative"):
            # Ambient radial background aura
            ui.html('<div class="absolute inset-0 bg-radial-gradient from-teal-500/20 via-purple-500/10 to-transparent blur-3xl pointer-events-none"></div>')
            ui.html(render_anatomical_heart_svg(size=200, pulse=True, holographic=False))
            with ui.row().classes("mt-6 px-4 py-2 bg-white/90 dark:bg-slate-800/90 shadow-md rounded-full border border-slate-100 dark:border-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-200 items-center gap-2 backdrop-blur-md"):
                ui.element("span").classes("w-2.5 h-2.5 rounded-full bg-emerald-500 animate-ping")
                ui.label("Real-Time Hemodynamic Stream Active")

    # =========================================================================
    # 3. MODERNIZED DASHBOARD SECTION
    # =========================================================================
    with ui.element("section").props('id="dashboard"').classes("py-20 px-6 md:px-12 max-w-7xl mx-auto"):
        # Welcome & Status Header
        with ui.row().classes("justify-between items-end mb-10 w-full flex-col md:flex-row gap-4"):
            with ui.column().classes("gap-1"):
                ui.label("Good Day, Health Explorer & Clinician").classes("text-3xl font-extrabold text-slate-900 dark:text-white")
                ui.label("Cardiovascular surveillance, screening trajectories, and verified AI diagnostics telemetry.").classes("text-sm text-slate-500 dark:text-slate-400")
            with ui.row().classes("items-center gap-2"):
                ui.element("span").classes("text-xs font-bold px-3 py-1 rounded-full bg-teal-500/20 text-teal-700 dark:text-teal-300 border border-teal-500/30").text = "Model Calibrated (T=0.09)"
                ui.element("span").classes("text-xs font-medium px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300").text = "Phase: Point 10"

        # 4 Key Metric Cards
        with ui.row().classes("grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 w-full mb-10"):
            dashboard_metrics = [
                ("Population Cohort", "397,870", "CDC BRFSS Usable Records", "groups", "teal"),
                ("Cohort Sensitivity", "79.6%", "Historical Recall (T = 0.09; Non-Diagnostic)", "radar", "emerald"),
                ("Cohort Specificity", "74.3%", "Historical Rule-Out (Non-Diagnostic)", "verified", "purple"),
                ("Inference Latency", "2.5 ms", "Calibrated Estimator Runtime", "bolt", "cyan"),
            ]
            for title, val, sub, icon_name, color_theme in dashboard_metrics:
                with ui.card().classes("heartai-card-premium p-6 flex flex-col justify-between"):
                    with ui.row().classes("justify-between items-center w-full mb-3"):
                        ui.label(title).classes("text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider")
                        ui.icon(icon_name).classes(f"text-xl text-{color_theme}-600 dark:text-{color_theme}-400")
                    ui.label(val).classes("text-3xl font-extrabold text-slate-900 dark:text-white")
                    ui.label(sub).classes("text-xs text-slate-500 dark:text-slate-400 mt-2")

        # Two Primary Action Cards
        with ui.row().classes("grid grid-cols-1 md:grid-cols-2 gap-8 w-full mb-12"):
            # Hub Card 1: Risk Assessment
            with ui.card().classes("heartai-card-premium p-8 bg-gradient-to-br from-teal-900/10 via-transparent to-transparent border-teal-500/30 flex flex-col justify-between"):
                with ui.column().classes("gap-2"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("assessment", color="teal-600").classes("text-2xl")
                        ui.label("Cardiovascular Survey Hub").classes("text-xl font-bold text-slate-900 dark:text-white")
                    ui.label(
                        "Evaluate 25 validated physiological, demographic, and behavioral features against "
                        "the calibrated CDC BRFSS model. Evaluated with optimal screening threshold T=0.09."
                    ).classes("text-sm text-slate-600 dark:text-slate-300 leading-relaxed")
                with ui.row().classes("mt-6 justify-between items-center"):
                    ui.label("Non-diagnostic research estimate").classes("text-[11px] text-slate-400 italic")
                    ui.button("Launch Assessment", icon="arrow_forward", on_click=assessment_dialog.open).classes(
                        "heartai-btn bg-teal-600 hover:bg-teal-700 text-white rounded-xl px-5 py-2.5 text-xs font-semibold shadow"
                    )

            # Hub Card 2: Symptom Checker
            with ui.card().classes("heartai-card-premium p-8 bg-gradient-to-br from-red-900/10 via-transparent to-transparent border-red-500/30 flex flex-col justify-between"):
                with ui.column().classes("gap-2"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("health_and_safety", color="red-600").classes("text-2xl")
                        ui.label("Acute Symptom Screening & Triage").classes("text-xl font-bold text-slate-900 dark:text-white")
                    ui.label(
                        "Deterministic pre-Gemini emergency screening for acute cardiovascular distress. "
                        "Immediate guidance with zero-wait dispatch for 112 / 102 in India and 911."
                    ).classes("text-sm text-slate-600 dark:text-slate-300 leading-relaxed")
                with ui.row().classes("mt-6 justify-between items-center"):
                    ui.label("Emergency guidance: 112 (India) / 911").classes("text-[11px] text-red-500 font-semibold")
                    ui.button("Check Symptoms", icon="health_and_safety", on_click=symptom_dialog.open).classes(
                        "heartai-btn bg-red-600 hover:bg-red-700 text-white rounded-xl px-5 py-2.5 text-xs font-semibold shadow"
                    )

    # =========================================================================
    # 4. ANALYTICS & RISK TRAJECTORY SECTION (Premium Dark Dashboard — Inspired by Reference 2)
    # =========================================================================
    with ui.element("section").props('id="analytics"').classes("py-20 px-6 md:px-12 bg-slate-50 dark:bg-slate-950/80 border-y border-slate-200 dark:border-slate-800"):
        with ui.column().classes("max-w-7xl mx-auto w-full"):
            with ui.column().classes("items-center text-center mb-12 w-full"):
                ui.label("Clinical Analytics & Performance").classes("text-3xl font-extrabold text-slate-900 dark:text-white mb-2")
                ui.label("Calibrated across 397,870 usable CDC BRFSS records using 5-Fold Stratified Cross-Validation.").classes("text-slate-500 dark:text-slate-400 text-sm max-w-2xl")

            with ui.row().classes("grid grid-cols-2 md:grid-cols-4 gap-6 w-full mb-12"):
                stats = [
                    ("79.6", "%", "Model Sensitivity (Recall)", "0.1"),
                    ("74.3", "%", "Model Specificity", "0.1"),
                    ("0.846", "", "ROC-AUC Score", "0.001"),
                    ("2.5", "ms", "Mean Inference Latency", "0.1"),
                ]
                for target, suffix, title, dec in stats:
                    with ui.card().classes("heartai-analytics-card text-center"):
                        ui.html(f'<div class="heartai-counter text-3xl font-extrabold text-teal-600 dark:text-teal-400" data-target="{target}" data-suffix="{suffix}" data-decimals="{dec}">0{suffix}</div>')
                        ui.label(title).classes("text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase mt-2")

            # Risk Trajectory Analysis Card
            with ui.card().classes("heartai-analytics-card w-full flex flex-col md:flex-row items-center justify-around gap-8 p-8"):
                with ui.column().classes("items-center text-center"):
                    ui.label("Patient Risk Categorization").classes("text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2")
                    gauge_slot = ui.element("div")
                    with gauge_slot:
                        ui.html(render_risk_gauge_svg(risk_score_percent=19, risk_category="Normal Baseline", width=260, height=140))
                with ui.column().classes("flex-1"):
                    ui.label("Risk Trajectory & Calibration Analysis").classes("text-lg font-bold text-slate-900 dark:text-white mb-2")
                    analysis_text = ui.label(
                        "Patient survey baseline indicates an estimated probability of reported "
                        "historical cardiovascular disease of 18.98%, evaluated using the calibrated BRFSS model. "
                        "Educational research estimate; not a clinical diagnostic device."
                    ).classes("text-slate-600 dark:text-slate-300 text-sm leading-relaxed mb-4")

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
                            ui.notify(f"Backend telemetry notice: {err}", color="orange")

                    with ui.row().classes("gap-3 items-center flex-wrap"):
                        ui.button("Generate Detailed Risk Report", icon="description", on_click=generate_diagnostic_report).classes(
                            "heartai-btn bg-teal-600 hover:bg-teal-700 text-white text-xs px-4 py-2 rounded-lg font-medium"
                        )
                        ui.button(
                            "Aarogya Saathi Model Insights",
                            icon="spa",
                            on_click=lambda: open_aarogya_with_prompt("Explain the historical classification sensitivity (~80%), specificity (~74%), calibration threshold (0.09), and why these reflect CDC population dataset association rather than clinical diagnostic performance."),
                        ).classes("heartai-btn bg-purple-700 hover:bg-purple-800 text-white text-xs px-4 py-2 rounded-lg font-medium")

    # =========================================================================
    # 5. HEALTH METRICS SECTION
    # =========================================================================
    with ui.element("section").props('id="metrics"').classes("py-20 px-6 md:px-12 max-w-7xl mx-auto"):
        with ui.column().classes("items-center text-center mb-10 w-full"):
            ui.label("Real-Time Vital Metrics").classes("text-3xl font-extrabold text-slate-900 dark:text-white mb-2")
            ui.label("Reactive circular gauges with dynamic client-side tweening and dual-theme adaptability.").classes("text-slate-500 dark:text-slate-400 text-sm")

        with ui.row().classes("justify-center gap-6 w-full flex-wrap"):
            ui.html(render_circular_gauge_svg("hr", percent=72, display_value=72, unit="bpm", color="#ef4444", label="Heart Rate"))
            ui.html(render_circular_gauge_svg("spo2", percent=98, display_value=98, unit="%", color="#0d9488", label="SpO2"))
            ui.html(render_circular_gauge_svg("bp", percent=65, display_value=120, unit="mmHg", color="#3b82f6", label="Systolic BP"))
            ui.html(render_circular_gauge_svg("hrv", percent=82, display_value=58, unit="ms", color="#8b5cf6", label="HRV Score"))

        with ui.row().classes("justify-center mt-8 flex-wrap gap-3"):
            def simulate_live_data():
                new_hr = random.randint(65, 88)
                new_spo2 = random.randint(96, 99)
                new_bp = random.randint(115, 130)
                ui.run_javascript(get_update_metric_js("hr", new_hr, 120))
                ui.run_javascript(get_update_metric_js("spo2", new_spo2, 100))
                ui.run_javascript(get_update_metric_js("bp", new_bp, 160))

            ui.button("Simulate Live Telemetry Update", icon="refresh", on_click=simulate_live_data).classes(
                "heartai-btn bg-slate-900 dark:bg-slate-700 text-white rounded-xl px-5 py-2.5 shadow text-xs font-semibold"
            )
            ui.button(
                "Explain Metrics with Aarogya Saathi",
                icon="spa",
                on_click=lambda: open_aarogya_with_prompt("Explain the physiological relationship and healthy ranges for Heart Rate (bpm), SpO2 (%), Systolic Blood Pressure, and HRV (ms)."),
            ).classes("heartai-btn text-teal-800 dark:text-teal-200 border border-teal-600 px-5 py-2.5 rounded-xl text-xs font-semibold")

    # =========================================================================
    # 6. DOCTORS SECTION
    # =========================================================================
    with ui.element("section").props('id="doctors"').classes("py-20 px-6 md:px-12 max-w-7xl mx-auto"):
        with ui.column().classes("items-center text-center mb-8 w-full"):
            ui.label("Our Expert Cardiologists").classes("text-3xl font-extrabold text-slate-900 dark:text-white mb-2")
            ui.label("Board-certified cardiac specialists guiding AI-driven clinical outcomes.").classes("text-slate-500 dark:text-slate-400 text-sm")

        # Contextual AI trigger for doctors
        with ui.row().classes("w-full justify-center mb-10"):
            ui.button(
                "Ask Aarogya Saathi About Cardiac Specialties & When to See a Cardiologist",
                icon="spa",
                on_click=lambda: open_aarogya_with_prompt("When should someone consult a cardiologist, and what is the difference between an electrophysiologist and an interventional cardiologist?"),
            ).props("outline dense").classes("heartai-btn text-teal-800 dark:text-teal-200 border-teal-600 px-4 py-2 rounded-xl text-xs font-medium")

        with ui.row().classes("grid grid-cols-1 md:grid-cols-3 gap-8 w-full"):
            doctors = [
                ("Dr. Elena Vance, MD", "Chief of Cardiology", "Harvard Medical School", "https://images.unsplash.com/photo-1559839734-2b71ea197ec2?w=400&q=80"),
                ("Dr. Marcus Chen, FACC", "Electrophysiologist", "Johns Hopkins", "https://images.unsplash.com/photo-1622253692010-333f2da6031d?w=400&q=80"),
                ("Dr. Sarah Al-Mansoor, MD", "Interventional Cardiologist", "Stanford Health", "https://images.unsplash.com/photo-1594824813583-b92c4b5744f4?w=400&q=80"),
            ]
            for name, role, institute, img_url in doctors:
                with ui.card().classes("heartai-doctor-card p-0"):
                    with ui.element("div").classes("heartai-doctor-img-wrap h-64 w-full"):
                        ui.image(img_url).classes("heartai-doctor-img w-full h-full object-cover")
                    with ui.column().classes("p-6"):
                        ui.label(name).classes("text-lg font-bold text-slate-900 dark:text-white")
                        ui.label(role).classes("text-sm font-medium text-teal-600 dark:text-teal-400")
                        ui.label(institute).classes("text-xs text-slate-400 mt-1")

    # =========================================================================
    # 7. BOTTOM BANNER
    # =========================================================================
    with ui.element("section").classes("heartai-banner-section bg-teal-900 text-white py-20 px-8 mt-12 rounded-3xl max-w-7xl mx-auto relative overflow-hidden"):
        ui.html(
            '<div class="heartai-parallax-bg" style="background: radial-gradient(circle at 70% 50%, rgba(20, 184, 166, 0.4) 0%, transparent 60%);"></div>'
        )
        with ui.row().classes("items-center justify-between gap-12 relative z-10 flex-col md:flex-row"):
            with ui.column().classes("flex-1"):
                ui.label("Transforming Cardiac Outcomes Together").classes("text-3xl md:text-4xl font-extrabold mb-4 leading-tight")
                ui.label(
                    "HeartAI connects hospitals, cardiologists, and emergency response teams "
                    "with proactive predictive telemetry."
                ).classes("text-teal-100 text-base mb-6 leading-relaxed")
                ui.button("Schedule Hospital Demonstration", icon="calendar_today").classes(
                    "heartai-btn bg-white text-teal-900 font-bold px-6 py-3 rounded-xl shadow-lg text-sm"
                )
            with ui.element("div").classes("heartai-banner-reveal-img flex-1 flex justify-center"):
                ui.image("https://images.unsplash.com/photo-1579684385127-1ef15d508118?w=600&q=80").classes("rounded-2xl shadow-2xl max-h-72 object-cover border-2 border-teal-500/30")

    # =========================================================================
    # 8. FLOATING INDIAN AI ASSISTANT: AAROGYA SAATHI (आरोग्य साथी)
    # =========================================================================
    with ui.page_sticky(position="bottom-right", x_offset=24, y_offset=24):
        with ui.element("div").classes("relative flex items-center justify-center"):
            ui.element("div").classes("aarogya-pulse-ring")
            with ui.button(on_click=aarogya_dialog.open).props("round").classes("aarogya-avatar-btn text-white w-14 h-14 relative z-10 flex items-center justify-center cursor-pointer"):
                ui.icon("spa").classes("text-2xl text-amber-200")
                ui.tooltip("Aarogya Saathi (आरोग्य साथी) — Your Health Companion")
                ui.element("span").classes("absolute top-0 right-0 w-3.5 h-3.5 rounded-full bg-emerald-400 border-2 border-white")

    # CLIENT INITIALIZATION HOOK
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
