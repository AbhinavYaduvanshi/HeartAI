# HeartAI Design System Specification (Point 10)

**Document ID:** HEARTAI-DS-001  
**Version:** 2.0.0 (Production Dual-Theme Edition)  
**Base Accepted Commit:** `d175201`  
**Date:** November 14, 2026  
**Status:** Approved & Implemented  
**Scope:** Complete design tokens, components, visual hierarchy, and accessibility rules.

---

## 1. Visual Hierarchy & Design Philosophy

HeartAI's design language unifies three distinct modern healthcare visual aesthetics:

```
+-----------------------------------------------------------------------------------+
|                        HEARTAI UNIFIED DESIGN LANGUAGE                            |
+-----------------------------------------------------------------------------------+
|  1. PRIMARY (70%): Teal Futuristic Healthcare Identity (Reference 3)              |
|     - Deep teal (#0d9488), vivid cyan glows, clean clinical layout, anatomical SVGs|
|                                                                                   |
|  2. SECONDARY (20%): Purple Glassmorphism (Reference 1)                           |
|     - Translucent lavender, violet accents (#7c3aed, #a855f7), floating orb       |
|                                                                                   |
|  3. ACCENT/DATA (10%): Premium High-Contrast Dark Dashboard (Reference 2)         |
|     - Deep charcoal (#090d16), emerald/coral status gauges, high-contrast metrics|
+-----------------------------------------------------------------------------------+
```

---

## 2. Design Tokens & CSS Variables

All tokens are defined in `static/css/heartai-motion.css` under `:root, [data-theme="light"]` and overridden for `[data-theme="dark"]`.

### 2.1. Color Tokens

| Token Name | Light Theme Value | Dark Theme Value | Purpose |
| :--- | :--- | :--- | :--- |
| `--heartai-teal-50` | `#f0fdfa` | `#042f2e` | Tinted background washes |
| `--heartai-teal-100` | `#ccfbf1` | `#115e59` | Subtle button borders |
| `--heartai-teal-400` | `#2dd4bf` | `#2dd4bf` | Interactive focus rings / glow |
| `--heartai-teal-500` | `#14b8a6` | `#14b8a6` | Vibrant brand teal |
| `--heartai-teal-600` | `#0d9488` | `#0d9488` | **Dominant Primary Brand** |
| `--heartai-teal-700` | `#0f766e` | `#2dd4bf` | Deep clinical teal / headers |
| `--heartai-teal-glow` | `rgba(13, 148, 136, 0.22)` | `rgba(45, 212, 191, 0.25)` | Elevated card hover glows |
| `--heartai-purple-500`| `#a855f7` | `#c084fc` | Aarogya Saathi AI badge |
| `--heartai-purple-600`| `#9333ea` | `#a855f7` | Aarogya Saathi AI accents |
| `--heartai-purple-glass-bg` | `rgba(147, 51, 234, 0.08)` | `rgba(147, 51, 234, 0.14)` | AI modal backdrop fill |
| `--heartai-purple-glow` | `rgba(168, 85, 247, 0.28)` | `rgba(192, 132, 252, 0.35)` | AI trigger orb pulse |
| `--bg-base` | `#f8fafc` | `#090d16` | Main viewport canvas |
| `--bg-surface` | `#ffffff` | `#0f172a` | Primary card & section surfaces |
| `--bg-surface-elevated`| `#ffffff` | `#1e293b` | Modals & dropdown flyouts |
| `--text-primary` | `#0f172a` | `#f8fafc` | Highest-priority headings |
| `--text-secondary` | `#334155` | `#cbd5e1` | Body and descriptive copy |
| `--text-muted` | `#64748b` | `#94a3b8` | Metadata, captions, timestamps |
| `--border-subtle` | `#e2e8f0` | `#1e293b` | Dividers and hairline strokes |
| `--border-card` | `rgba(226, 232, 240, 0.85)` | `rgba(51, 65, 85, 0.7)` | Card borders |

### 2.2. Elevation & Depth Tokens

| Token Name | Light Theme Definition | Dark Theme Definition |
| :--- | :--- | :--- |
| `--shadow-sm` | `0 1px 2px 0 rgba(15, 23, 42, 0.05)` | `0 1px 2px 0 rgba(0, 0, 0, 0.35)` |
| `--shadow-card` | `0 10px 25px -3px rgba(15, 23, 42, 0.05)` | `0 10px 25px -3px rgba(0, 0, 0, 0.55)` |
| `--shadow-elevated` | `0 20px 25px -5px rgba(15, 23, 42, 0.08)` | `0 20px 25px -5px rgba(0, 0, 0, 0.65)` |
| `--nav-bg` | `rgba(255, 255, 255, 0.85)` | `rgba(9, 13, 22, 0.88)` |
| `--glass-bg` | `rgba(255, 255, 255, 0.8)` | `rgba(15, 23, 42, 0.82)` |

---

## 3. Typography Scale & Standards

HeartAI uses system-native clean sans-serif typography (`Inter`, `system-ui`, `-apple-system`, `Segoe UI`, `Roboto`) optimized for medical readability:

```css
/* Typography Scale */
--text-xs:   0.75rem  /* 12px - Badges, disclaimers, microcopy */
--text-sm:   0.875rem /* 14px - Field labels, subtext, captions */
--text-base: 1.00rem  /* 16px - Standard body text, inputs */
--text-lg:   1.125rem /* 18px - Card subheadings, lead text */
--text-xl:   1.25rem  /* 20px - Section subheadings */
--text-2xl:  1.50rem  /* 24px - Section headings */
--text-3xl:  1.875rem /* 30px - Major feature titles */
--text-4xl:  2.25rem  /* 36px - Hero headline secondary */
--text-5xl:  3.00rem  /* 48px - Primary hero headline */
```

### Numerical Readability
All clinical counters, heart rates, percentages, and laboratory values use `font-variant-numeric: tabular-nums;` to prevent character width jitter during GSAP live counter animations.

---

## 4. Component Catalog

### 4.1. Navigation Bar (`.heartai-navbar`)
- **Container:** `sticky top-0 z-50 backdrop-blur-md`
- **Background:** `var(--nav-bg)` with `border-b: 1px solid var(--nav-border)`
- **Interactions:**
  - Active nav pills with teal wash and text brand color.
  - Dropdown menu `.heartai-dropdown-menu` with animated enter/exit opacity and subtle slide.
  - Theme toggle button `.heartai-theme-toggle` featuring 40x40px touch target with smooth hover rotation.

### 4.2. Metric & Analytics Cards (`.heartai-analytics-card`)
- **Structure:** Rounded container (`rounded-2xl`, `p-6`) with `var(--border-card)`.
- **Hover Physics:** `transform: translateY(-3px)` with `var(--shadow-elevated)` and border color shift to teal-400.
- **Dark Mode Appearance:** Seamless dark-slate tile with 18% cyan glowing border.

### 4.3. Aarogya Saathi AI Glass Dialog (`.heartai-glass-purple`)
- **Background:** `var(--heartai-purple-glass-bg)` with `backdrop-filter: blur(16px)`.
- **Border:** `1px solid var(--heartai-purple-glass-border)`.
- **Orb Trigger:** 56x56px circular button with multi-stop gradient (`#0d9488` to `#7c3aed`), glowing box-shadow, and expanding pulse ring (`aarogya-pulse-ring`).
- **Emergency Alert:** Distinct high-visibility red-bordered box with 112 / 102 hotlines.

---

## 5. Animation & Motion Design Tokens

```css
/* Motion Curves */
--heartai-ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1);
--heartai-ease-in-out-smooth: cubic-bezier(0.4, 0, 0.2, 1);

/* Durations */
--duration-fast:   150ms /* Button clicks, hover tints */
--duration-normal: 280ms /* Dropdowns, card transforms */
--duration-smooth: 600ms /* Image hover scales, accordion expansions */
--duration-hero:   1200ms /* Staggered hero load, gauge sweeps */
```

### Accessibility Fallback
Under `@media (prefers-reduced-motion: reduce)`, all transforms, pulses, counter animations, and infinite keyframes are disabled (`animation: none !important; transition: none !important;`).
