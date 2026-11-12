/**
 * HeartAI Advanced Motion & Animation Controller
 * High-performance GSAP 3 + ScrollTrigger bridge for NiceGUI and Web Apps
 */

(function (window, document) {
  'use strict';

  // Ensure singleton instance
  if (window.HeartAIMotion) {
    return;
  }

  const MotionController = {
    initialized: false,
    scrollTriggers: [],
    timelines: [],

    // Detect accessibility preferences
    prefersReducedMotion() {
      return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    },

    // Detect mobile viewport
    isMobile() {
      return window.innerWidth < 768;
    },

    /**
     * Initializes GSAP & ScrollTrigger plugins safely
     */
    init() {
      if (this.initialized) return true;

      if (typeof window.gsap === 'undefined') {
        console.warn('[HeartAI Motion] GSAP library not found. Motion system running in CSS fallback mode.');
        return false;
      }

      if (typeof window.ScrollTrigger !== 'undefined') {
        window.gsap.registerPlugin(window.ScrollTrigger);
      }

      this.initialized = true;
      console.log('[HeartAI Motion] Motion engine initialized successfully.');
      return true;
    },

    /**
     * 1. HERO ANIMATIONS
     * Headline entrance, teal accent text reveal, anatomical heart entrance,
     * ECG waveform animation, and button hover dynamics.
     */
    initHero(options = {}) {
      if (!this.init()) return null;

      const opts = Object.assign({
        headline: '.heartai-hero-headline',
        accent: '.heartai-teal-accent',
        heartVisual: '.heartai-heart-visual',
        ecgPath: '.heartai-ecg-path',
        ctaButton: '.heartai-btn',
        container: '#hero-section'
      }, options);

      if (this.prefersReducedMotion()) {
        window.gsap.set([opts.headline, opts.accent, opts.heartVisual, opts.ctaButton], { opacity: 1, y: 0 });
        const ecg = document.querySelector(opts.ecgPath);
        if (ecg) ecg.style.strokeDashoffset = '0';
        return null;
      }

      const tl = window.gsap.timeline({
        defaults: { ease: 'power3.out', duration: 1.0 }
      });
      this.timelines.push(tl);

      // Headline Entrance
      const headlineEl = document.querySelector(opts.headline);
      if (headlineEl) {
        tl.fromTo(headlineEl, 
          { opacity: 0, y: 35, filter: 'blur(8px)' },
          { opacity: 1, y: 0, filter: 'blur(0px)', duration: 1.1 }
        );
      }

      // Teal Accent Text Reveal (gradient wipe / scale effect)
      const accentEl = document.querySelector(opts.accent);
      if (accentEl) {
        tl.fromTo(accentEl,
          { opacity: 0, scale: 0.94, y: 15 },
          { opacity: 1, scale: 1, y: 0, duration: 0.9, ease: 'back.out(1.4)' },
          '-=0.7'
        );
      }

      // Anatomical Heart Visual Entrance
      const heartEl = document.querySelector(opts.heartVisual);
      if (heartEl) {
        tl.fromTo(heartEl,
          { opacity: 0, scale: 0.75, rotation: -6 },
          { 
            opacity: 1, 
            scale: 1, 
            rotation: 0, 
            duration: 1.3, 
            ease: 'elastic.out(1, 0.75)',
            onComplete: () => {
              heartEl.classList.add('heartai-pulse');
            }
          },
          '-=0.8'
        );
      }

      // ECG Waveform Path Drawing
      const ecgEl = document.querySelector(opts.ecgPath);
      if (ecgEl) {
        const pathLength = ecgEl.getTotalLength ? ecgEl.getTotalLength() : 1000;
        ecgEl.style.strokeDasharray = pathLength;
        ecgEl.style.strokeDashoffset = pathLength;

        tl.to(ecgEl, {
          strokeDashoffset: 0,
          duration: 1.8,
          ease: 'power2.inOut',
          onComplete: () => {
            // Continuous subtle cardiac sweep
            this.startContinuousECG(ecgEl, pathLength);
          }
        }, '-=1.0');
      }

      // CTA Button Entrance
      const btnEl = document.querySelector(opts.ctaButton);
      if (btnEl) {
        tl.fromTo(btnEl,
          { opacity: 0, y: 20 },
          { opacity: 1, y: 0, duration: 0.7 },
          '-=0.9'
        );
      }

      return tl;
    },

    /**
     * Helper: Continuous realistic ECG pulse line
     */
    startContinuousECG(pathElement, length) {
      if (this.prefersReducedMotion() || !pathElement) return;

      const loopTl = window.gsap.timeline({ repeat: -1, repeatDelay: 1.2 });
      loopTl.fromTo(pathElement,
        { strokeDashoffset: length },
        { strokeDashoffset: -length, duration: 2.4, ease: 'none' }
      );
      this.timelines.push(loopTl);
    },

    /**
     * 2. NAVIGATION ANIMATIONS
     * Sticky navbar blur on scroll and active link sliding underline indicator.
     */
    initNavbar(options = {}) {
      const opts = Object.assign({
        navSelector: '.heartai-navbar',
        linkSelector: '.heartai-nav-link',
        scrollThreshold: 40
      }, options);

      const nav = document.querySelector(opts.navSelector);
      if (!nav) return;

      // Sticky backdrop blur scroll listener
      const handleScroll = () => {
        if (window.scrollY > opts.scrollThreshold) {
          nav.classList.add('heartai-nav-scrolled');
        } else {
          nav.classList.remove('heartai-nav-scrolled');
        }
      };

      window.addEventListener('scroll', handleScroll, { passive: true });
      handleScroll(); // Initial check

      // Active-link indicator
      const links = document.querySelectorAll(opts.linkSelector);
      links.forEach(link => {
        link.addEventListener('click', function() {
          links.forEach(l => l.classList.remove('active'));
          this.classList.add('active');
        });
      });
    },

    /**
     * 3. DOCTOR IMAGES & CARDS
     * Smooth entrance, subtle movement, and 3D hover interaction.
     */
    initDoctorImages(options = {}) {
      if (!this.init()) return;

      const opts = Object.assign({
        container: '.heartai-doctors-grid',
        cards: '.heartai-doctor-card'
      }, options);

      const cards = document.querySelectorAll(opts.cards);
      if (!cards.length) return;

      if (this.prefersReducedMotion()) {
        window.gsap.set(cards, { opacity: 1, y: 0 });
        return;
      }

      if (window.ScrollTrigger) {
        const trigger = window.ScrollTrigger.batch(cards, {
          start: 'top 85%',
          onEnter: batch => {
            window.gsap.fromTo(batch, 
              { opacity: 0, y: 40, scale: 0.95 },
              { opacity: 1, y: 0, scale: 1, stagger: 0.15, duration: 0.85, ease: 'power3.out' }
            );
          },
          once: true
        });
        if (trigger) this.scrollTriggers.push(...(Array.isArray(trigger) ? trigger : [trigger]));
      }

      // Add gentle 3D mouse parallax on desktop hover
      if (!this.isMobile() && !this.prefersReducedMotion()) {
        cards.forEach(card => {
          card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left - rect.width / 2;
            const y = e.clientY - rect.top - rect.height / 2;
            window.gsap.to(card, {
              rotationY: x * 0.04,
              rotationX: -y * 0.04,
              transformPerspective: 800,
              ease: 'power1.out',
              duration: 0.4
            });
          });

          card.addEventListener('mouseleave', () => {
            window.gsap.to(card, {
              rotationY: 0,
              rotationX: 0,
              ease: 'power2.out',
              duration: 0.6
            });
          });
        });
      }
    },

    /**
     * 4. ANALYTICS ANIMATIONS
     * Statistics counters (number roll-up), animated charts, and risk gauge.
     */
    initAnalytics(options = {}) {
      if (!this.init()) return;

      const opts = Object.assign({
        counters: '.heartai-counter',
        chartBars: '.heartai-chart-bar',
        chartLines: '.heartai-chart-line',
        gaugeNeedle: '.heartai-gauge-needle'
      }, options);

      // A. Numerical Statistics Count-up
      const counterElements = document.querySelectorAll(opts.counters);
      counterElements.forEach(counter => {
        const target = parseFloat(counter.getAttribute('data-target') || counter.innerText || '0');
        const prefix = counter.getAttribute('data-prefix') || '';
        const suffix = counter.getAttribute('data-suffix') || '';
        const decimals = parseInt(counter.getAttribute('data-decimals') || '0', 10);

        if (this.prefersReducedMotion()) {
          counter.innerText = prefix + target.toFixed(decimals) + suffix;
          return;
        }

        const countObj = { val: 0 };
        const trigger = window.ScrollTrigger ? {
          trigger: counter,
          start: 'top 90%',
          once: true
        } : null;

        const tween = window.gsap.to(countObj, {
          val: target,
          duration: 1.8,
          ease: 'power2.out',
          scrollTrigger: trigger,
          onUpdate: () => {
            counter.innerText = prefix + countObj.val.toFixed(decimals) + suffix;
          }
        });
        if (tween.scrollTrigger) this.scrollTriggers.push(tween.scrollTrigger);
      });

      // B. Animated Chart Bars / Lines
      const bars = document.querySelectorAll(opts.chartBars);
      if (bars.length && window.ScrollTrigger && !this.prefersReducedMotion()) {
        const barTrigger = window.ScrollTrigger.batch(bars, {
          start: 'top 85%',
          onEnter: batch => {
            window.gsap.fromTo(batch,
              { scaleY: 0, transformOrigin: 'bottom center' },
              { scaleY: 1, stagger: 0.08, duration: 1.0, ease: 'power3.out' }
            );
          },
          once: true
        });
        if (barTrigger) this.scrollTriggers.push(...(Array.isArray(barTrigger) ? barTrigger : [barTrigger]));
      }

      // C. Risk Gauge Animation
      const needles = document.querySelectorAll(opts.gaugeNeedle);
      needles.forEach(needle => {
        const angle = parseFloat(needle.getAttribute('data-angle') || '0'); // -90 deg to +90 deg
        if (this.prefersReducedMotion()) {
          needle.style.transform = `rotate(${angle}deg)`;
          return;
        }

        const tween = window.gsap.fromTo(needle,
          { rotation: -90, transformOrigin: '50% 100%' },
          {
            rotation: angle,
            duration: 1.6,
            ease: 'elastic.out(1, 0.65)',
            scrollTrigger: window.ScrollTrigger ? {
              trigger: needle,
              start: 'top 85%',
              once: true
            } : null
          }
        );
        if (tween.scrollTrigger) this.scrollTriggers.push(tween.scrollTrigger);
      });
    },

    /**
     * 5. HEALTH METRICS & CIRCULAR PROGRESS
     * Circular progress sweep, smooth gauge updates, and metric cards entrance.
     */
    initHealthMetrics(options = {}) {
      if (!this.init()) return;

      const opts = Object.assign({
        cards: '.heartai-metric-card',
        rings: '.heartai-ring-circle'
      }, options);

      // Staggered Cards Entrance
      const cards = document.querySelectorAll(opts.cards);
      if (cards.length && window.ScrollTrigger && !this.prefersReducedMotion()) {
        const trigger = window.ScrollTrigger.batch(cards, {
          start: 'top 88%',
          onEnter: batch => {
            window.gsap.fromTo(batch,
              { opacity: 0, y: 30 },
              { opacity: 1, y: 0, stagger: 0.12, duration: 0.75, ease: 'power2.out' }
            );
          },
          once: true
        });
        if (trigger) this.scrollTriggers.push(...(Array.isArray(trigger) ? trigger : [trigger]));
      }

      // Circular Progress Sweep
      const rings = document.querySelectorAll(opts.rings);
      rings.forEach(ring => {
        const radius = parseFloat(ring.getAttribute('r') || '45');
        const circumference = 2 * Math.PI * radius;
        const percent = Math.min(Math.max(parseFloat(ring.getAttribute('data-percent') || '0'), 0), 100);
        const targetOffset = circumference - (percent / 100) * circumference;

        ring.style.strokeDasharray = `${circumference} ${circumference}`;

        if (this.prefersReducedMotion()) {
          ring.style.strokeDashoffset = targetOffset;
          return;
        }

        ring.style.strokeDashoffset = circumference;
        const tween = window.gsap.to(ring, {
          strokeDashoffset: targetOffset,
          duration: 1.5,
          ease: 'power3.out',
          scrollTrigger: window.ScrollTrigger ? {
            trigger: ring,
            start: 'top 85%',
            once: true
          } : null
        });
        if (tween.scrollTrigger) this.scrollTriggers.push(tween.scrollTrigger);
      });
    },

    /**
     * Dynamic Runtime Update for Health Metrics (Called from Python / NiceGUI)
     */
    updateMetric(metricId, newValue, maxValue = 100) {
      const ring = document.getElementById(`${metricId}-ring`);
      const text = document.getElementById(`${metricId}-val`);

      if (ring) {
        const radius = parseFloat(ring.getAttribute('r') || '45');
        const circumference = 2 * Math.PI * radius;
        const percent = Math.min(Math.max((newValue / maxValue) * 100, 0), 100);
        const targetOffset = circumference - (percent / 100) * circumference;

        if (this.prefersReducedMotion()) {
          ring.style.strokeDashoffset = targetOffset;
        } else if (window.gsap) {
          window.gsap.to(ring, { strokeDashoffset: targetOffset, duration: 0.8, ease: 'power2.out' });
        } else {
          ring.style.strokeDashoffset = targetOffset;
        }
      }

      if (text) {
        if (this.prefersReducedMotion() || !window.gsap) {
          text.innerText = newValue;
        } else {
          const currentVal = parseFloat(text.innerText) || 0;
          const valObj = { val: currentVal };
          window.gsap.to(valObj, {
            val: newValue,
            duration: 0.8,
            ease: 'power2.out',
            onUpdate: () => {
              text.innerText = Math.round(valObj.val);
            }
          });
        }
      }
    },

    /**
     * 6. BOTTOM DOCTOR BANNER
     * Scrubbed background parallax, smooth image reveal, and text entrance.
     */
    initBottomDoctorBanner(options = {}) {
      if (!this.init()) return;

      const opts = Object.assign({
        banner: '.heartai-banner-section',
        parallaxBg: '.heartai-parallax-bg',
        revealImg: '.heartai-banner-reveal-img',
        bannerText: '.heartai-banner-text'
      }, options);

      const banner = document.querySelector(opts.banner);
      if (!banner) return;

      if (this.prefersReducedMotion()) {
        window.gsap.set([opts.revealImg, opts.bannerText], { opacity: 1, x: 0, y: 0 });
        return;
      }

      // Scrubbed Background Parallax (Disabled on Mobile for Battery/Performance)
      const bg = banner.querySelector(opts.parallaxBg);
      if (bg && window.ScrollTrigger && !this.isMobile()) {
        const st = window.ScrollTrigger.create({
          trigger: banner,
          start: 'top bottom',
          end: 'bottom top',
          scrub: 1.2,
          animation: window.gsap.fromTo(bg, { yPercent: -15 }, { yPercent: 15, ease: 'none' })
        });
        this.scrollTriggers.push(st);
      }

      // Smooth Image Diagonal / Scale Reveal
      const img = banner.querySelector(opts.revealImg);
      if (img && window.ScrollTrigger) {
        const tween = window.gsap.fromTo(img,
          { opacity: 0, x: -40, scale: 0.92 },
          {
            opacity: 1,
            x: 0,
            scale: 1,
            duration: 1.1,
            ease: 'power3.out',
            scrollTrigger: {
              trigger: banner,
              start: 'top 75%',
              once: true
            }
          }
        );
        if (tween.scrollTrigger) this.scrollTriggers.push(tween.scrollTrigger);
      }

      // Text Staggered Reveal
      const textGroup = banner.querySelectorAll(opts.bannerText);
      if (textGroup.length && window.ScrollTrigger) {
        const tween = window.gsap.fromTo(textGroup,
          { opacity: 0, y: 25 },
          {
            opacity: 1,
            y: 0,
            stagger: 0.18,
            duration: 0.9,
            ease: 'power2.out',
            scrollTrigger: {
              trigger: banner,
              start: 'top 75%',
              once: true
            }
          }
        );
        if (tween.scrollTrigger) this.scrollTriggers.push(tween.scrollTrigger);
      }
    },

    /**
     * 7. LOTTIE ANIMATION INTEGRATION
     */
    initLottiePlayer(containerId, animationPathOrData, options = {}) {
      if (typeof window.lottie === 'undefined') {
        console.warn('[HeartAI Motion] Lottie Web library not found.');
        return null;
      }

      const container = document.getElementById(containerId);
      if (!container) return null;

      const opts = Object.assign({
        container: container,
        renderer: 'svg',
        loop: !this.prefersReducedMotion(),
        autoplay: !this.prefersReducedMotion()
      }, options);

      if (typeof animationPathOrData === 'string') {
        opts.path = animationPathOrData;
      } else {
        opts.animationData = animationPathOrData;
      }

      try {
        return window.lottie.loadAnimation(opts);
      } catch (err) {
        console.error('[HeartAI Motion] Lottie failed to load animation:', err);
        return null;
      }
    },

    /**
     * Clean up all active GSAP instances and ScrollTriggers
     * Call before single-page transitions or component destruction to prevent leaks.
     */
    cleanup() {
      this.scrollTriggers.forEach(st => {
        try { st.kill(); } catch (e) {}
      });
      this.scrollTriggers = [];

      this.timelines.forEach(tl => {
        try { tl.kill(); } catch (e) {}
      });
      this.timelines = [];

      if (window.ScrollTrigger) {
        window.ScrollTrigger.getAll().forEach(t => t.kill());
      }
      console.log('[HeartAI Motion] Motion instances cleaned up.');
    }
  };

  // Expose to window
  window.HeartAIMotion = MotionController;

  // Auto-init on DOMContentLoaded if not loaded dynamically
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => MotionController.init());
  } else {
    MotionController.init();
  }

})(window, document);

