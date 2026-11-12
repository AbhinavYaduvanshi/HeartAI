"""Tests for HeartAI Advanced Motion & Animation System."""

from pathlib import Path

import frontend_animations
import motion


def test_motion_assets_exist():
    """Verify all motion CSS and JS files exist on disk with valid file sizes."""
    css_path = Path("static/css/heartai-motion.css")
    js_motion_path = Path("static/js/heartai-motion.js")
    gsap_path = Path("static/js/gsap.min.js")
    scrolltrigger_path = Path("static/js/ScrollTrigger.min.js")
    lottie_path = Path("static/js/lottie.min.js")

    assert css_path.exists(), "heartai-motion.css missing"
    assert js_motion_path.exists(), "heartai-motion.js missing"
    assert gsap_path.exists(), "gsap.min.js missing"
    assert scrolltrigger_path.exists(), "ScrollTrigger.min.js missing"
    assert lottie_path.exists(), "lottie.min.js missing"

    assert css_path.stat().st_size > 1000
    assert js_motion_path.stat().st_size > 2000
    assert gsap_path.stat().st_size > 50000


def test_get_motion_head_html():
    """Verify generated head HTML links to all required scripts and styles."""
    html_local = motion.get_motion_head_html(use_cdn=False)
    assert "/static/css/heartai-motion.css" in html_local
    assert "/static/js/gsap.min.js" in html_local
    assert "/static/js/ScrollTrigger.min.js" in html_local
    assert "/static/js/heartai-motion.js" in html_local

    html_cdn = motion.get_motion_head_html(use_cdn=True)
    assert "cdnjs.cloudflare.com" in html_cdn
    assert "/static/css/heartai-motion.css" in html_cdn


def test_javascript_generator_helpers():
    """Verify JavaScript emitter helpers return valid JS calls."""
    hero_js = motion.get_init_hero_js({"container": "#hero"})
    assert "window.HeartAIMotion.initHero" in hero_js
    assert '"container": "#hero"' in hero_js

    nav_js = motion.get_init_navbar_js()
    assert "window.HeartAIMotion.initNavbar" in nav_js

    doc_js = motion.get_init_doctor_images_js()
    assert "window.HeartAIMotion.initDoctorImages" in doc_js

    analytics_js = motion.get_init_analytics_js()
    assert "window.HeartAIMotion.initAnalytics" in analytics_js

    metrics_js = motion.get_init_health_metrics_js()
    assert "window.HeartAIMotion.initHealthMetrics" in metrics_js

    banner_js = motion.get_init_doctor_banner_js()
    assert "window.HeartAIMotion.initBottomDoctorBanner" in banner_js

    update_js = motion.get_update_metric_js("hr", 75, 100)
    assert "window.HeartAIMotion.updateMetric('hr', 75, 100)" in update_js

    cleanup_js = motion.get_cleanup_js()
    assert "window.HeartAIMotion.cleanup()" in cleanup_js


def test_render_ecg_svg():
    """Verify ECG SVG rendering and stroke path parameters."""
    svg = motion.render_ecg_svg(width=340, height=70, stroke_color="#0d9488")
    assert "<svg" in svg
    assert 'class="heartai-ecg-svg"' in svg
    assert 'class="heartai-ecg-path"' in svg
    assert 'stroke="#0d9488"' in svg
    assert "M 0 35 L 50 35" in svg


def test_render_anatomical_heart_svg():
    """Verify anatomical heart rendering and cardiac pulse class."""
    svg_pulse = motion.render_anatomical_heart_svg(size=140, pulse=True)
    assert 'class="heartai-heart-visual heartai-pulse"' in svg_pulse
    assert "heartGrad" in svg_pulse

    svg_static = motion.render_anatomical_heart_svg(size=100, pulse=False)
    assert "heartai-pulse" not in svg_static


def test_render_circular_gauge_svg():
    """Verify circular gauge SVG metrics and percent attributes."""
    gauge_html = motion.render_circular_gauge_svg("hr", percent=75, display_value=75, unit="bpm")
    assert 'id="hr-ring"' in gauge_html
    assert 'id="hr-val"' in gauge_html
    assert 'data-percent="75"' in gauge_html
    assert "bpm" in gauge_html


def test_render_risk_gauge_svg():
    """Verify semi-circular risk gauge angle calculation."""
    # 0% risk -> -90 deg needle
    gauge_0 = motion.render_risk_gauge_svg(0, "Minimal")
    assert 'data-angle="-90.0"' in gauge_0

    # 50% risk -> 0 deg needle (vertical)
    gauge_50 = motion.render_risk_gauge_svg(50, "Moderate")
    assert 'data-angle="0.0"' in gauge_50

    # 100% risk -> +90 deg needle
    gauge_100 = motion.render_risk_gauge_svg(100, "High Risk")
    assert 'data-angle="90.0"' in gauge_100


def test_frontend_animations_backwards_compatibility():
    """Verify backwards compatibility functions in frontend_animations.py."""
    pulse_js = frontend_animations.get_heartbeat_pulse_js()
    assert "scale: 1.12" in pulse_js

    scroll_js = frontend_animations.get_ecg_scroll_reveal_js()
    assert "ScrollTrigger" in scroll_js

    lottie_js = frontend_animations.get_lottie_heart_loader_js("loader-box", "/path/to/heart.json")
    assert "loader-box" in lottie_js
    assert "/path/to/heart.json" in lottie_js
