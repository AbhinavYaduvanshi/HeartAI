"""HeartAI Motion System — Python Integration for NiceGUI & FastAPI.

Provides high-performance, accessible, and reactive motion bindings.
Bridges Python UI components with the client-side GSAP 3 and ScrollTrigger engine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Directory paths
STATIC_DIR = Path(__file__).parent / "static"
CSS_DIR = STATIC_DIR / "css"
JS_DIR = STATIC_DIR / "js"

MOTION_CSS_PATH = "/static/css/heartai-motion.css"
GSAP_JS_PATH = "/static/js/gsap.min.js"
SCROLLTRIGGER_JS_PATH = "/static/js/ScrollTrigger.min.js"
LOTTIE_JS_PATH = "/static/js/lottie.min.js"
MOTION_JS_PATH = "/static/js/heartai-motion.js"

# Backward-compatible path aliases
GSAP_LOCAL_PATH = GSAP_JS_PATH
SCROLLTRIGGER_LOCAL_PATH = SCROLLTRIGGER_JS_PATH
LOTTIE_LOCAL_PATH = LOTTIE_JS_PATH


def get_motion_head_html(use_cdn: bool = False) -> str:
    """Returns HTML `<head>` tags to inject into NiceGUI pages or FastAPI templates."""
    if use_cdn:
        return """
        <!-- HeartAI Motion Assets (CDN Fallback) -->
        <link rel="stylesheet" href="/static/css/heartai-motion.css">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/ScrollTrigger.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/lottie-web/5.12.2/lottie.min.js"></script>
        <script src="/static/js/heartai-motion.js"></script>
        """

    return f"""
    <!-- HeartAI Motion Assets (High-Performance Local Bundles) -->
    <link rel="stylesheet" href="{MOTION_CSS_PATH}">
    <script src="{GSAP_JS_PATH}"></script>
    <script src="{SCROLLTRIGGER_JS_PATH}"></script>
    <script src="{LOTTIE_JS_PATH}"></script>
    <script src="{MOTION_JS_PATH}"></script>
    """


def register_motion_routes(app: Any) -> None:
    """Mounts static files in FastAPI or NiceGUI app if not already mounted."""
    if hasattr(app, "add_static_files"):
        try:
            app.add_static_files("/static", str(STATIC_DIR))
        except Exception:
            pass  # Route may already be mounted
    elif hasattr(app, "mount"):
        try:
            from fastapi.staticfiles import StaticFiles

            app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
        except Exception:
            pass


# ==============================================================================
# JAVASCRIPT EMITTER HELPERS FOR NICEGUI
# ==============================================================================


def get_init_hero_js(options: dict[str, Any] | None = None) -> str:
    """Generates JS to initialize Hero animations."""
    opts = json.dumps(options or {})
    return f"if (window.HeartAIMotion) {{ window.HeartAIMotion.initHero({opts}); }}"


def get_init_navbar_js(options: dict[str, Any] | None = None) -> str:
    """Generates JS to initialize Sticky Navbar and link indicators."""
    opts = json.dumps(options or {})
    return f"if (window.HeartAIMotion) {{ window.HeartAIMotion.initNavbar({opts}); }}"


def get_init_doctor_images_js(options: dict[str, Any] | None = None) -> str:
    """Generates JS to initialize Doctor card stagger and 3D hover effects."""
    opts = json.dumps(options or {})
    return f"if (window.HeartAIMotion) {{ window.HeartAIMotion.initDoctorImages({opts}); }}"


def get_init_analytics_js(options: dict[str, Any] | None = None) -> str:
    """Generates JS to initialize count-up statistics, chart reveals, and risk gauges."""
    opts = json.dumps(options or {})
    return f"if (window.HeartAIMotion) {{ window.HeartAIMotion.initAnalytics({opts}); }}"


def get_init_health_metrics_js(options: dict[str, Any] | None = None) -> str:
    """Generates JS to initialize Circular Progress sweep and card entrance."""
    opts = json.dumps(options or {})
    return f"if (window.HeartAIMotion) {{ window.HeartAIMotion.initHealthMetrics({opts}); }}"


def get_init_doctor_banner_js(options: dict[str, Any] | None = None) -> str:
    """Generates JS to initialize bottom banner parallax, image reveal, and text."""
    opts = json.dumps(options or {})
    return f"if (window.HeartAIMotion) {{ window.HeartAIMotion.initBottomDoctorBanner({opts}); }}"


def get_update_metric_js(metric_id: str, new_value: float | int, max_value: float | int = 100) -> str:
    """Generates JS to smoothly animate a live metric update."""
    return f"if (window.HeartAIMotion) {{ window.HeartAIMotion.updateMetric('{metric_id}', {new_value}, {max_value}); }}"


def get_cleanup_js() -> str:
    """Generates JS to clean up ScrollTriggers and timelines on page transition."""
    return "if (window.HeartAIMotion) { window.HeartAIMotion.cleanup(); }"


# ==============================================================================
# HIGH-PERFORMANCE SVG VISUAL BUILDERS (Clean, Accessible, Theme-Aware)
# ==============================================================================


def render_ecg_svg(
    width: int = 340,
    height: int = 70,
    stroke_color: str = "#0d9488",
    stroke_width: float = 2.5,
    css_class: str = "heartai-ecg-svg",
) -> str:
    """Generates a clinical P-Q-R-S-T ECG waveform SVG."""
    # Clinical ECG path coordinates (isoelectric baseline, P wave, Q dip, R spike, S dip, T wave)
    path_data = (
        "M 0 35 L 50 35 "
        "Q 65 24, 75 35 "  # P wave
        "L 95 35 "
        "L 105 45 "  # Q dip
        "L 120 4 "  # R peak
        "L 135 62 "  # S dip
        "L 145 35 "
        "L 165 35 "
        "Q 185 18, 205 35 "  # T wave
        "L 235 35 "
        "Q 250 24, 260 35 "  # Secondary P
        "L 280 35 "
        "L 290 45 L 305 4 L 320 62 L 330 35 L 340 35"
    )
    return f"""
    <svg class="{css_class}" viewBox="0 0 {width} {height}" width="100%" height="{height}" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path class="heartai-ecg-path" d="{path_data}" stroke="{stroke_color}" stroke-width="{stroke_width}" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    """.strip()


def render_anatomical_heart_svg(
    size: int = 120,
    pulse: bool = True,
    css_class: str = "heartai-heart-visual",
    holographic: bool = False,
) -> str:
    """Generates a modern anatomical heart icon with gradient lighting, optional holographic glow, and cardiac pulse."""
    pulse_class = "heartai-pulse" if pulse else ""
    glow_filter = 'filter: drop-shadow(0 0 18px rgba(45, 212, 191, 0.45));' if holographic else ''
    return f"""
    <div class="{css_class} {pulse_class}" style="display:inline-block; width:{size}px; height:{size}px; {glow_filter}">
        <svg viewBox="0 0 100 100" width="{size}" height="{size}" fill="none" xmlns="http://www.w3.org/2000/svg">
            <defs>
                <linearGradient id="heartGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stop-color="#ef4444" />
                    <stop offset="50%" stop-color="#dc2626" />
                    <stop offset="100%" stop-color="#991b1b" />
                </linearGradient>
                <linearGradient id="hologramGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stop-color="#2dd4bf" />
                    <stop offset="50%" stop-color="#0d9488" />
                    <stop offset="100%" stop-color="#042f2e" />
                </linearGradient>
                <filter id="heartShadow" x="-20%" y="-20%" width="140%" height="140%">
                    <feDropShadow dx="0" dy="8" stdDeviation="6" flood-color="rgba(239, 68, 68, 0.35)" />
                </filter>
            </defs>
            <path d="M 50 88 C 22 70 8 50 8 32 C 8 16 22 6 36 6 C 43 6 48 10 50 14 C 52 10 57 6 64 6 C 78 6 92 16 92 32 C 92 50 78 70 50 88 Z"
                  fill="url(#{'hologramGrad' if holographic else 'heartGrad'})" filter="url(#heartShadow)" />
            <!-- Interior vascular anatomical accents -->
            <path d="M 46 22 Q 42 34 35 48" stroke="rgba(255,255,255,0.45)" stroke-width="3" stroke-linecap="round" />
            <path d="M 54 20 Q 58 36 65 46" stroke="rgba(255,255,255,0.3)" stroke-width="2.5" stroke-linecap="round" />
            <!-- Cyan/Emerald glowing data nodes (Ref 2 & Ref 3) -->
            <circle cx="35" cy="48" r="2.5" fill="#2dd4bf" />
            <circle cx="65" cy="46" r="2.5" fill="#38bdf8" />
            <circle cx="50" cy="35" r="3" fill="#a855f7" />
        </svg>
    </div>
    """.strip()


def render_circular_gauge_svg(
    metric_id: str,
    percent: float | int,
    display_value: str | int | float,
    unit: str = "%",
    radius: float = 42.0,
    stroke_width: float = 8.0,
    color: str = "#0d9488",
    label: str = "Metric",
) -> str:
    """Generates an animated circular health gauge SVG for NiceGUI cards."""
    size = int((radius + stroke_width) * 2 + 10)
    center = size / 2
    return f"""
    <div class="heartai-metric-card heartai-card-premium" style="text-align:center; display:inline-block; margin:8px; padding:16px;">
        <svg class="heartai-ring-svg" width="{size}" height="{size}">
            <circle class="heartai-ring-bg" stroke-width="{stroke_width}" fill="transparent" r="{radius}" cx="{center}" cy="{center}"/>
            <circle id="{metric_id}-ring" class="heartai-ring-circle" stroke="{color}" stroke-width="{stroke_width}"
                    fill="transparent" r="{radius}" cx="{center}" cy="{center}" data-percent="{percent}"/>
        </svg>
        <div style="margin-top:-{size * 0.65}px; height:{size * 0.65}px; display:flex; flex-direction:column; justify-content:center; align-items:center;">
            <div style="font-weight:700; font-size:1.25rem; color:var(--text-primary);">
                <span id="{metric_id}-val">{display_value}</span><span style="font-size:0.85rem; font-weight:500; color:var(--text-muted);">{unit}</span>
            </div>
            <div style="font-size:0.75rem; color:var(--text-muted); font-weight:600; text-transform:uppercase; letter-spacing:0.04em;">{label}</div>
        </div>
    </div>
    """.strip()


def render_risk_gauge_svg(
    risk_score_percent: float | int,
    risk_category: str = "Low Risk",
    width: int = 240,
    height: int = 135,
) -> str:
    """Generates a semi-circular cardiac risk meter SVG with an animated needle."""
    # Convert percentage (0 to 100) to rotation angle (-90 to +90 degrees)
    angle = -90 + (float(risk_score_percent) / 100.0) * 180.0

    return f"""
    <div style="text-align:center; display:inline-block;">
        <svg class="heartai-gauge-svg" width="{width}" height="{height}" viewBox="0 0 200 115">
            <defs>
                <linearGradient id="riskArcGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stop-color="#10b981" />
                    <stop offset="50%" stop-color="#f59e0b" />
                    <stop offset="100%" stop-color="#ef4444" />
                </linearGradient>
            </defs>
            <!-- Gauge Track Arc -->
            <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke="url(#riskArcGrad)" stroke-width="16" stroke-linecap="round"/>
            <!-- Gauge Needle -->
            <g class="heartai-gauge-needle" data-angle="{angle:.1f}" style="transform-origin: 100px 100px;">
                <polygon points="98,100 102,100 100,28" fill="var(--text-primary, #0f172a)"/>
                <circle cx="100" cy="100" r="7" fill="var(--text-primary, #0f172a)"/>
                <circle cx="100" cy="100" r="3" fill="var(--bg-surface, #ffffff)"/>
            </g>
        </svg>
        <div style="margin-top:6px; font-weight:700; font-size:1.1rem; color:var(--text-primary, #0f172a);">
            {risk_score_percent}% <span style="font-size:0.9rem; font-weight:600; color:var(--text-brand, #0d9488);">— {risk_category}</span>
        </div>
    </div>
    """.strip()


def render_theme_toggle_html(css_class: str = "heartai-theme-toggle") -> str:
    """Generates an accessible theme toggle button."""
    return f"""
    <button class="{css_class}" onclick="window.HeartAIMotion && window.HeartAIMotion.toggleTheme()"
            aria-label="Toggle light and dark theme" title="Toggle theme" type="button">
        <span class="material-icons text-slate-700 text-lg">dark_mode</span>
    </button>
    """.strip()
