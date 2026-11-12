"""HeartAI Frontend Animations Module (Compatibility & Integration Bridge).

Bridges existing functions to the unified HeartAI Motion System (`motion.py`).
"""

from __future__ import annotations

from motion import (
    CSS_DIR,
    GSAP_LOCAL_PATH,
    JS_DIR,
    LOTTIE_LOCAL_PATH,
    SCROLLTRIGGER_LOCAL_PATH,
    STATIC_DIR,
    get_cleanup_js,
    get_init_analytics_js,
    get_init_doctor_banner_js,
    get_init_doctor_images_js,
    get_init_health_metrics_js,
    get_init_hero_js,
    get_init_navbar_js,
    get_motion_head_html,
    get_update_metric_js,
    render_anatomical_heart_svg,
    render_circular_gauge_svg,
    render_ecg_svg,
    render_risk_gauge_svg,
)


def get_animation_head_scripts(use_cdn: bool = False) -> str:
    """Returns HTML script and stylesheet tags to inject into NiceGUI or FastAPI headers."""
    return get_motion_head_html(use_cdn=use_cdn)


def get_heartbeat_pulse_js(element_selector: str = ".heartai-pulse") -> str:
    """Generates a realistic clinical ECG heartbeat pulse animation using GSAP."""
    return f"""
    if (window.gsap && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {{
        gsap.to("{element_selector}", {{
            scale: 1.12,
            duration: 0.18,
            ease: "power2.out",
            repeat: -1,
            yoyo: true,
            repeatDelay: 0.85
        }});
    }}
    """.strip()


def get_ecg_scroll_reveal_js(trigger_selector: str = ".ecg-chart") -> str:
    """Configures GSAP ScrollTrigger to animate health data charts when scrolled into view."""
    return f"""
    if (window.gsap && window.ScrollTrigger && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {{
        gsap.registerPlugin(ScrollTrigger);
        gsap.from("{trigger_selector}", {{
            scrollTrigger: {{
                trigger: "{trigger_selector}",
                start: "top 80%",
                toggleActions: "play none none reverse"
            }},
            opacity: 0,
            y: 40,
            duration: 1.1,
            ease: "power3.out"
        }});
    }}
    """.strip()


def get_lottie_heart_loader_js(container_id: str, lottie_json_url: str) -> str:
    """Initializes a Lottie animated vector for heart diagnostics."""
    return f"""
    if (window.HeartAIMotion) {{
        window.HeartAIMotion.initLottiePlayer('{container_id}', '{lottie_json_url}');
    }} else if (typeof lottie !== 'undefined') {{
        lottie.loadAnimation({{
            container: document.getElementById('{container_id}'),
            renderer: 'svg',
            loop: !window.matchMedia('(prefers-reduced-motion: reduce)').matches,
            autoplay: !window.matchMedia('(prefers-reduced-motion: reduce)').matches,
            path: '{lottie_json_url}'
        }});
    }}
    """.strip()


__all__ = [
    "STATIC_DIR",
    "JS_DIR",
    "CSS_DIR",
    "GSAP_LOCAL_PATH",
    "SCROLLTRIGGER_LOCAL_PATH",
    "LOTTIE_LOCAL_PATH",
    "get_animation_head_scripts",
    "get_heartbeat_pulse_js",
    "get_ecg_scroll_reveal_js",
    "get_lottie_heart_loader_js",
    "get_motion_head_html",
    "get_init_hero_js",
    "get_init_navbar_js",
    "get_init_doctor_images_js",
    "get_init_analytics_js",
    "get_init_health_metrics_js",
    "get_init_doctor_banner_js",
    "get_update_metric_js",
    "get_cleanup_js",
    "render_ecg_svg",
    "render_anatomical_heart_svg",
    "render_circular_gauge_svg",
    "render_risk_gauge_svg",
]
