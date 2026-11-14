"""HeartAI Motion System Demonstration & Integration Sandbox.

Demonstrates all 6 animation categories implemented for HeartAI in NiceGUI.
Does not alter the website's core design — serves as an architectural example.
Integrates with the FastAPI backend (/predict) for calibrated inference.
"""

from __future__ import annotations

import random
from typing import Any

import httpx
from nicegui import app, ui

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

    # --- Assessment Modal Dialog for Backend Connection ---
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
                                ui.label(f"Threshold Classification: {flag_str}").classes("text-xs text-slate-700")
                                ui.label(data["educational_disclaimer"]).classes("text-xs text-slate-500 italic mt-1")
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

    # 1. NAVIGATION
    with ui.header().classes("heartai-navbar w-full bg-white/80 fixed top-0 left-0 z-50 px-8 py-4 flex justify-between items-center"):
        with ui.row().classes("items-center gap-2"):
            ui.icon("favorite", color="red-500").classes("text-2xl heartai-pulse")
            ui.label("HeartAI").classes("text-xl font-bold tracking-tight text-slate-900")

        with ui.row().classes("items-center gap-6"):
            ui.link("Home", "#hero").classes("heartai-nav-link active text-slate-700 font-medium no-underline")
            ui.link("Doctors", "#doctors").classes("heartai-nav-link text-slate-700 font-medium no-underline")
            ui.link("Analytics", "#analytics").classes("heartai-nav-link text-slate-700 font-medium no-underline")
            ui.link("Metrics", "#metrics").classes("heartai-nav-link text-slate-700 font-medium no-underline")
            ui.button("Sign In").classes("heartai-btn bg-teal-600 text-white rounded-lg px-4 py-2 font-medium")

    # 2. HERO SECTION
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

            with ui.row().classes("gap-4 items-center"):
                ui.button("Start Assessment", icon="arrow_forward", on_click=assessment_dialog.open).classes(
                    "heartai-btn bg-teal-600 text-white text-base px-6 py-3 rounded-xl shadow-lg"
                )
                ui.button("Explore Analytics", icon="insights").props("outline").classes(
                    "heartai-btn text-teal-700 border-teal-600 px-6 py-3 rounded-xl"
                )

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

    # 3. DOCTORS SECTION
    with ui.element("section").props('id="doctors"').classes("py-20 px-8 max-w-6xl mx-auto"):
        ui.label("Our Expert Cardiologists").classes("text-3xl font-bold text-slate-900 text-center mb-2")
        ui.label("Board-certified cardiac specialists guiding AI-driven clinical outcomes.").classes("text-slate-500 text-center mb-12")

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

    # 4. ANALYTICS SECTION
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

                    ui.button("Generate Detailed Diagnostic Report", icon="description", on_click=generate_diagnostic_report).classes(
                        "heartai-btn bg-teal-600 text-white text-sm px-4 py-2 rounded-lg"
                    )

    # 5. HEALTH METRICS SECTION
    with ui.element("section").props('id="metrics"').classes("py-20 px-8 max-w-6xl mx-auto"):
        ui.label("Real-Time Vital Metrics").classes("text-3xl font-bold text-slate-900 text-center mb-2")
        ui.label("Reactive circular gauges with dynamic client-side tweening.").classes("text-slate-500 text-center mb-10")

        with ui.row().classes("justify-center gap-8 w-full flex-wrap"):
            ui.html(render_circular_gauge_svg("hr", percent=72, display_value=72, unit="bpm", color="#ef4444", label="Heart Rate"))
            ui.html(render_circular_gauge_svg("spo2", percent=98, display_value=98, unit="%", color="#0d9488", label="SpO2"))
            ui.html(render_circular_gauge_svg("bp", percent=65, display_value=120, unit="mmHg", color="#3b82f6", label="Systolic BP"))
            ui.html(render_circular_gauge_svg("hrv", percent=82, display_value=58, unit="ms", color="#8b5cf6", label="HRV Score"))

        with ui.row().classes("justify-center mt-6"):
            def simulate_live_data():
                new_hr = random.randint(65, 88)
                new_spo2 = random.randint(96, 99)
                new_bp = random.randint(115, 130)
                ui.run_javascript(get_update_metric_js("hr", new_hr, 120))
                ui.run_javascript(get_update_metric_js("spo2", new_spo2, 100))
                ui.run_javascript(get_update_metric_js("bp", new_bp, 160))

            ui.button("Simulate Live Telemetry Update", icon="refresh", on_click=simulate_live_data).classes("heartai-btn bg-slate-900 text-white rounded-lg px-5 py-2.5 shadow")

    # 6. BOTTOM DOCTOR BANNER
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
    ui.run(title="HeartAI Advanced Motion Demo", port=8080, reload=False, show=False)
