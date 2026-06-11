"""Inject global CSS theme based on Stateless Authority design tokens."""

from __future__ import annotations

import streamlit as st


_FONT_LINKS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=swap" rel="stylesheet">
"""


_CSS = """
<style>
:root {
  --rp-surface: #f7f9fb;
  --rp-surface-dim: #d8dadc;
  --rp-surface-bright: #f7f9fb;
  --rp-surface-container-lowest: #ffffff;
  --rp-surface-container-low: #f2f4f6;
  --rp-surface-container: #eceef0;
  --rp-surface-container-high: #e6e8ea;
  --rp-surface-container-highest: #e0e3e5;
  --rp-on-surface: #191c1e;
  --rp-on-surface-variant: #434655;
  --rp-inverse-surface: #2d3133;
  --rp-inverse-on-surface: #eff1f3;
  --rp-outline: #737686;
  --rp-outline-variant: #c3c6d7;
  --rp-primary: #2563eb;
  --rp-primary-deep: #004ac6;
  --rp-on-primary: #ffffff;
  --rp-primary-container: #eeefff;
  --rp-on-primary-container: #003ea8;
  --rp-secondary-container: #dae2fd;
  --rp-on-secondary-container: #5c647a;
  --rp-tertiary: #006242;
  --rp-error: #ba1a1a;
  --rp-error-container: #ffdad6;

  --rp-text-main: #111827;
  --rp-text-sub: #4b5563;

  --rp-radius-sm: 8px;
  --rp-radius-md: 12px;
  --rp-radius-lg: 16px;
  --rp-radius-xl: 24px;
  --rp-radius-2xl: 28px;
  --rp-radius-full: 9999px;

  --rp-shadow-1: 0 4px 12px rgba(15, 23, 42, 0.03);
  --rp-shadow-2: 0 12px 24px rgba(15, 23, 42, 0.08);
  --rp-shadow-3: 0 24px 48px rgba(15, 23, 42, 0.12);

  --rp-font: 'Public Sans', -apple-system, BlinkMacSystemFont, 'Pretendard',
             'Noto Sans KR', '맑은 고딕', sans-serif;
}

html, body {
  font-family: var(--rp-font);
}
/* Apply Public Sans to text nodes only. Icon spans excluded via :not() */
body, p, div, label, button, input, textarea, select,
h1, h2, h3, h4, h5, h6, a {
  font-family: var(--rp-font);
}
span:not([data-testid="stIconMaterial"]):not([class*="material-symbols"]):not([class*="MaterialIcon"]) {
  font-family: var(--rp-font);
}

/* ============================================================
   FORCE Material Symbols Rounded on streamlit icon spans.
   Streamlit uses data-testid="stIconMaterial" with the icon
   name as text content; ligatures convert to glyphs.
   ============================================================ */
[data-testid="stIconMaterial"],
[data-testid="stIconMaterial"] * {
  font-family: 'Material Symbols Rounded', 'Material Symbols Outlined' !important;
  font-weight: normal !important;
  font-style: normal !important;
  font-size: 24px;
  line-height: 1;
  letter-spacing: normal !important;
  text-transform: none !important;
  display: inline-block;
  white-space: nowrap;
  word-wrap: normal;
  direction: ltr;
  font-feature-settings: 'liga' !important;
  -webkit-font-feature-settings: 'liga' !important;
  -webkit-font-smoothing: antialiased;
  font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
}

[data-testid="stAppViewContainer"] {
  background: var(--rp-surface);
}

[data-testid="stHeader"] {
  background: transparent;
  height: 0;
}

[data-testid="stToolbar"] { display: none; }

[data-testid="stSidebar"] {
  background: var(--rp-surface-container-low);
  border-right: 1px solid var(--rp-outline-variant);
}

.block-container {
  padding-top: 0.5rem !important;
  padding-bottom: 3rem !important;
  max-width: 1280px !important;
}

h1, h2, h3, h4, h5, h6, p, span, label, div, button, input, textarea, select {
  font-family: var(--rp-font) !important;
}

h1 {
  font-weight: 700;
  letter-spacing: -0.01em;
  color: var(--rp-on-surface);
}
h2 { font-weight: 700; color: var(--rp-on-surface); }
h3 { font-weight: 600; color: var(--rp-on-surface); }

p, label, span { color: var(--rp-on-surface-variant); }

.material-symbols-outlined {
  font-family: 'Material Symbols Outlined' !important;
  font-weight: normal;
  font-style: normal;
  font-size: 24px;
  line-height: 1;
  letter-spacing: normal;
  text-transform: none;
  display: inline-block;
  white-space: nowrap;
  word-wrap: normal;
  direction: ltr;
  -webkit-font-feature-settings: 'liga';
  -webkit-font-smoothing: antialiased;
  font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
  vertical-align: middle;
}

/* --- Buttons --- */
div.stButton > button, div.stDownloadButton > button {
  border-radius: var(--rp-radius-md) !important;
  font-weight: 600 !important;
  font-family: var(--rp-font) !important;
  border: 1px solid var(--rp-outline-variant);
  background: var(--rp-surface-container-lowest);
  color: var(--rp-on-surface);
  box-shadow: none;
  transition: transform 0.12s ease, box-shadow 0.12s ease, background 0.12s ease;
  padding: 0.55rem 1.1rem;
}
div.stButton > button:hover, div.stDownloadButton > button:hover {
  background: var(--rp-surface-container-low);
  border-color: var(--rp-outline);
}
div.stButton > button:active, div.stDownloadButton > button:active {
  transform: scale(0.98);
}

div.stButton > button[kind="primary"], div.stDownloadButton > button[kind="primary"] {
  background: var(--rp-primary) !important;
  color: #ffffff !important;
  border: 1px solid var(--rp-primary) !important;
  box-shadow: var(--rp-shadow-1);
}
div.stButton > button[kind="primary"] *,
div.stDownloadButton > button[kind="primary"] * {
  color: #ffffff !important;
  fill: #ffffff !important;
}
div.stButton > button[kind="primary"]:hover, div.stDownloadButton > button[kind="primary"]:hover {
  background: #3b82f6 !important;
  border-color: #3b82f6 !important;
  color: #ffffff !important;
  box-shadow: var(--rp-shadow-1);
  transform: none;
}

div.stButton > button:disabled, div.stDownloadButton > button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

/* --- Inputs --- */
div[data-baseweb="input"] > div,
div[data-baseweb="textarea"] > div,
div[data-baseweb="select"] > div {
  border-radius: var(--rp-radius-md) !important;
  border-color: var(--rp-outline-variant) !important;
  background: var(--rp-surface-container-lowest) !important;
}
div[data-baseweb="input"]:focus-within > div,
div[data-baseweb="textarea"]:focus-within > div,
div[data-baseweb="select"]:focus-within > div {
  border-color: var(--rp-primary) !important;
  box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.12) !important;
}

.stTextInput input, .stTextArea textarea, .stNumberInput input {
  color: var(--rp-on-surface) !important;
}

/* --- File uploader --- */
[data-testid="stFileUploaderDropzone"] {
  border: 2px dashed var(--rp-outline-variant) !important;
  border-radius: var(--rp-radius-xl) !important;
  background: var(--rp-surface-container-lowest) !important;
  padding: 2.5rem 1.5rem !important;
  transition: border-color 0.15s ease, background 0.15s ease;
}
[data-testid="stFileUploaderDropzone"]:hover {
  border-color: var(--rp-primary) !important;
  background: var(--rp-primary-container) !important;
}

/* --- Containers w/ border --- */
[data-testid="stVerticalBlockBorderWrapper"] {
  border-radius: var(--rp-radius-xl) !important;
  border-color: var(--rp-outline-variant) !important;
  background: var(--rp-surface-container-lowest);
  box-shadow: var(--rp-shadow-1);
}

/* --- Metrics --- */
[data-testid="stMetric"] {
  background: var(--rp-surface-container-lowest);
  border: 1px solid var(--rp-outline-variant);
  border-radius: var(--rp-radius-lg);
  padding: 1rem 1.25rem;
  box-shadow: var(--rp-shadow-1);
}

/* --- Alerts --- */
[data-testid="stAlert"] {
  border-radius: var(--rp-radius-lg) !important;
}

/* --- Divider --- */
hr {
  border-color: var(--rp-outline-variant) !important;
  opacity: 0.6;
}

/* --- Tabs --- */
.stTabs [data-baseweb="tab-list"] {
  gap: 0.25rem;
  border-bottom: 1px solid var(--rp-outline-variant);
}
.stTabs [data-baseweb="tab"] {
  height: 44px;
  padding: 0 1.1rem;
  border-radius: var(--rp-radius-md) var(--rp-radius-md) 0 0;
  background: transparent;
  color: var(--rp-on-surface-variant);
  font-weight: 600;
}
.stTabs [aria-selected="true"] {
  background: var(--rp-surface-container-lowest);
  color: var(--rp-primary) !important;
  border-bottom: 2px solid var(--rp-primary);
}

/* --- Radio horizontal as segmented --- */
[data-testid="stRadio"] [role="radiogroup"] {
  gap: 0.5rem;
}

/* --- Top App Bar (st.columns row with marker) --- */
.rp-topbar-marker { display: none; }

[data-testid="stHorizontalBlock"]:has(.rp-topbar-marker) {
  background: var(--rp-surface-container-lowest);
  border-bottom: 1px solid var(--rp-outline-variant);
  margin: -1rem -1rem 1.5rem -1rem !important;
  padding: 0.75rem 2rem !important;
  box-shadow: var(--rp-shadow-1);
  align-items: center;
  min-height: 64px;
}
.rp-topbar__brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.rp-topbar__brand img {
  height: 32px;
  width: auto;
  object-fit: contain;
}
.rp-topbar__brand .rp-brand-text {
  font-size: 16px;
  font-weight: 700;
  color: var(--rp-on-surface);
  letter-spacing: -0.01em;
}

/* Nav buttons inside topbar */
[class*="st-key-nav_home_"] div.stButton > button,
[class*="st-key-nav_editor_"] div.stButton > button {
  font-size: 14px !important;
  font-weight: 600 !important;
  padding: 0.5rem 0.85rem !important;
  border-radius: var(--rp-radius-md) !important;
  background: transparent !important;
  border: 1px solid transparent !important;
  color: var(--rp-on-surface-variant) !important;
  box-shadow: none !important;
  white-space: nowrap;
}
[class*="st-key-nav_home_"] div.stButton > button:hover,
[class*="st-key-nav_editor_"] div.stButton > button:hover {
  background: var(--rp-surface-container) !important;
  color: var(--rp-on-surface) !important;
}
[class*="st-key-nav_home_"] div.stButton > button[kind="primary"],
[class*="st-key-nav_editor_"] div.stButton > button[kind="primary"] {
  background: transparent !important;
  color: var(--rp-primary) !important;
  border: 1px solid transparent !important;
  border-bottom: 2px solid var(--rp-primary) !important;
  border-radius: 0 !important;
  box-shadow: none !important;
}
[class*="st-key-nav_home_"] div.stButton > button[kind="primary"] *,
[class*="st-key-nav_editor_"] div.stButton > button[kind="primary"] * {
  color: var(--rp-primary) !important;
  fill: var(--rp-primary) !important;
}
[class*="st-key-nav_home_"] div.stButton > button[kind="primary"]:hover,
[class*="st-key-nav_editor_"] div.stButton > button[kind="primary"]:hover {
  background: var(--rp-surface-container-low) !important;
  color: var(--rp-primary) !important;
  border-bottom: 2px solid var(--rp-primary) !important;
}

/* --- Hero (built from st.columns + marker, styled via :has) --- */
.rp-hero-marker { display: none; }

[data-testid="stHorizontalBlock"]:has(.rp-hero-marker) {
  position: relative;
  isolation: isolate;
  overflow: hidden;
  padding: 4rem 2.5rem 3.5rem 2.5rem;
  border-radius: var(--rp-radius-2xl);
  background:
    radial-gradient(circle at 0% 0%, #eeefff 0%, transparent 55%),
    radial-gradient(circle at 100% 100%, #dae2fd 0%, transparent 55%),
    var(--rp-surface-container-lowest);
  border: 1px solid var(--rp-outline-variant);
  margin-bottom: 1rem;
  align-items: center;
}
[data-testid="stHorizontalBlock"]:has(.rp-hero-marker)::before {
  content: '';
  position: absolute;
  inset: -20%;
  z-index: -1;
  background:
    radial-gradient(circle at 20% 30%, rgba(180, 197, 255, 0.55) 0%, transparent 35%),
    radial-gradient(circle at 80% 70%, rgba(218, 226, 253, 0.65) 0%, transparent 40%),
    radial-gradient(circle at 60% 20%, rgba(238, 239, 255, 0.5) 0%, transparent 45%);
  animation: rp-orb-drift 18s ease-in-out infinite;
}
.rp-hero-left {
  display: flex;
  flex-direction: column;
  gap: 0;
}
.rp-hero__badge {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.35rem 0.85rem;
  background: var(--rp-primary-container);
  color: var(--rp-on-primary-container);
  border-radius: var(--rp-radius-full);
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 1.25rem;
}
.rp-hero__title {
  font-size: 36px;
  line-height: 1.2;
  font-weight: 700;
  color: var(--rp-on-surface);
  letter-spacing: -0.01em;
  margin-bottom: 1rem;
}
.rp-hero__desc {
  font-size: 15px;
  line-height: 1.55;
  color: var(--rp-on-surface-variant);
  margin-bottom: 1.75rem;
  max-width: 32rem;
}
.rp-hero__mockwrap {
  position: relative;
  height: 380px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.rp-mock-card {
  position: absolute;
  width: 210px;
  aspect-ratio: 4 / 5;
  border-radius: var(--rp-radius-xl);
  background: linear-gradient(135deg, #ffffff 0%, #f2f4f6 100%);
  border: 1px solid rgba(15, 23, 42, 0.05);
  box-shadow: var(--rp-shadow-3);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
}
.rp-mock-card img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.rp-mock-card.left {
  transform: rotate(-7deg) translate(-110px, 10px);
  background: linear-gradient(135deg, #eeefff 0%, #dae2fd 100%);
}
.rp-mock-card.right {
  transform: rotate(5deg) translate(110px, -10px);
  background: linear-gradient(135deg, #f7f9fb 0%, #e6e8ea 100%);
}
.rp-mock-card.center {
  z-index: 2;
  background: linear-gradient(180deg, rgba(37, 99, 235, 0.05) 0%, rgba(37, 99, 235, 0.6) 100%),
              linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%);
  color: #ffffff;
}
.rp-mock-card .mock-eyebrow {
  font-size: 11px;
  font-weight: 600;
  opacity: 0.85;
  margin-bottom: 0.5rem;
}
.rp-mock-card .mock-title {
  font-size: 18px;
  font-weight: 700;
  line-height: 1.25;
}
.rp-mock-card .mock-bars {
  display: flex;
  gap: 6px;
  align-items: flex-end;
  height: 60px;
  margin-top: auto;
}
.rp-mock-card .mock-bars span {
  display: block;
  width: 14px;
  background: var(--rp-primary);
  border-radius: 4px 4px 0 0;
  opacity: 0.7;
}

/* --- Feature card (bento) --- */
.rp-feature {
  background: var(--rp-surface-container-lowest);
  border: 1px solid var(--rp-outline-variant);
  border-radius: var(--rp-radius-xl);
  padding: 1.75rem;
  box-shadow: var(--rp-shadow-1);
  height: 100%;
  transition: box-shadow 0.18s ease, transform 0.18s ease;
}
.rp-feature:hover {
  box-shadow: var(--rp-shadow-2);
  transform: translateY(-2px);
}
.rp-feature__icon {
  width: 48px;
  height: 48px;
  border-radius: var(--rp-radius-md);
  background: rgba(37, 99, 235, 0.08);
  color: var(--rp-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 1.25rem;
}
.rp-feature__icon .material-symbols-outlined {
  font-size: 26px;
  font-variation-settings: 'FILL' 1, 'wght' 500;
}
.rp-feature__title {
  font-size: 18px;
  font-weight: 600;
  color: var(--rp-on-surface);
  margin-bottom: 0.5rem;
}
.rp-feature__body {
  font-size: 14px;
  line-height: 1.55;
  color: var(--rp-on-surface-variant);
}

/* --- Step nav --- */
.rp-stepnav {
  background: var(--rp-surface-container-lowest);
  border: 1px solid var(--rp-outline-variant);
  border-radius: var(--rp-radius-xl);
  padding: 1.25rem 1rem;
  box-shadow: var(--rp-shadow-1);
  position: sticky;
  top: 5rem;
}
.rp-stepnav__title {
  font-size: 14px;
  font-weight: 700;
  color: var(--rp-on-surface);
  padding: 0 0.5rem 0.75rem 0.5rem;
  border-bottom: 1px solid var(--rp-outline-variant);
  margin-bottom: 0.75rem;
}
.rp-stepnav__sub {
  font-size: 12px;
  color: var(--rp-on-surface-variant);
  padding: 0 0.5rem 0.75rem 0.5rem;
}
.rp-step {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.65rem 0.75rem;
  margin: 0.15rem 0;
  border-radius: var(--rp-radius-md);
  font-size: 14px;
  font-weight: 600;
  color: var(--rp-on-surface-variant);
  cursor: default;
}
.rp-step.done { color: var(--rp-tertiary); }
.rp-step.active {
  background: rgba(37, 99, 235, 0.08);
  color: var(--rp-primary);
}
.rp-step .material-symbols-outlined { font-size: 20px; }

/* --- Panels --- */
.rp-panel {
  background: var(--rp-surface-container-lowest);
  border: 1px solid var(--rp-outline-variant);
  border-radius: var(--rp-radius-xl);
  padding: 1.25rem 1.25rem 0.5rem 1.25rem;
  box-shadow: var(--rp-shadow-1);
  margin-bottom: 1rem;
}
.rp-panel__title {
  font-size: 14px;
  font-weight: 700;
  color: var(--rp-on-surface);
  margin-bottom: 0.75rem;
}

/* --- Pill / chip --- */
.rp-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.25rem 0.7rem;
  border-radius: var(--rp-radius-full);
  font-size: 12px;
  font-weight: 600;
}
.rp-pill.tone-info  { background: rgba(37, 99, 235, 0.10); color: var(--rp-primary); }
.rp-pill.tone-ok    { background: rgba(0, 98, 66, 0.10);   color: var(--rp-tertiary); }
.rp-pill.tone-warn  { background: var(--rp-secondary-container); color: var(--rp-on-secondary-container); }
.rp-pill.tone-error { background: var(--rp-error-container); color: var(--rp-error); }

/* --- Footer --- */
.rp-footer {
  margin-top: 3rem;
  padding: 1.5rem 2rem;
  background: var(--rp-surface-container-low);
  border-top: 1px solid var(--rp-outline-variant);
  border-radius: var(--rp-radius-lg);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
  color: var(--rp-on-surface-variant);
  font-size: 12px;
}

/* --- Preview canvas wrap --- */
.rp-preview {
  background: linear-gradient(180deg, var(--rp-surface-container-low) 0%, var(--rp-surface-container) 100%);
  border: 1px solid var(--rp-outline-variant);
  border-radius: var(--rp-radius-xl);
  padding: 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 480px;
  box-shadow: var(--rp-shadow-1);
}

/* --- Step section header --- */
.rp-section {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin-bottom: 0.5rem;
}
.rp-section__num {
  width: 28px; height: 28px;
  border-radius: var(--rp-radius-full);
  background: var(--rp-primary);
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
}
.rp-section__title {
  font-size: 20px;
  font-weight: 700;
  color: var(--rp-on-surface);
}

/* Hide streamlit deploy + menu */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }

/* =========================================================
   ANIMATIONS — keyframes
   ========================================================= */
@keyframes rp-fade-in-up {
  from { opacity: 0; transform: translateY(16px); }
  to   { opacity: 1; transform: translateY(0); }
}
@keyframes rp-fade-in {
  from { opacity: 0; }
  to   { opacity: 1; }
}
@keyframes rp-float-a {
  0%, 100% { transform: rotate(-7deg) translate(-110px, 10px); }
  50%      { transform: rotate(-9deg) translate(-118px, -2px); }
}
@keyframes rp-float-b {
  0%, 100% { transform: rotate(5deg) translate(110px, -10px); }
  50%      { transform: rotate(7deg) translate(118px, 4px); }
}
@keyframes rp-float-c {
  0%, 100% { transform: translateY(0); }
  50%      { transform: translateY(-10px); }
}
@keyframes rp-pulse-glow {
  0%, 100% { box-shadow: 0 12px 28px rgba(37, 99, 235, 0.30); }
  50%      { box-shadow: 0 16px 40px rgba(37, 99, 235, 0.55), 0 0 0 6px rgba(37, 99, 235, 0.08); }
}
@keyframes rp-gradient-shift {
  0%, 100% { filter: hue-rotate(0deg); }
  50%      { filter: hue-rotate(15deg); }
}
@keyframes rp-shimmer {
  0%   { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
@keyframes rp-step-glow {
  0%, 100% { box-shadow: 0 0 0 0 rgba(37, 99, 235, 0.35); }
  50%      { box-shadow: 0 0 0 6px rgba(37, 99, 235, 0); }
}
@keyframes rp-icon-spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}

/* =========================================================
   HERO — animations (bg orbs handled on stHorizontalBlock above)
   ========================================================= */
.rp-hero-left {
  animation: rp-fade-in-up 0.7s ease both;
}
.rp-hero__mockwrap {
  animation: rp-fade-in 1.1s ease both;
  animation-delay: 0.15s;
}
.rp-hero__badge {
  background: transparent;
  color: var(--rp-primary);
  padding-left: 0;
  padding-right: 0;
  animation: none;
}
.rp-hero__title {
  background: linear-gradient(
      120deg,
      #0f172a 0%,
      #2563eb 25%,
      #1e3a8a 50%,
      #2563eb 75%,
      #0f172a 100%
  );
  background-size: 300% 100%;
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  color: transparent;
  animation: rp-title-shine 6s linear infinite;
}

@keyframes rp-orb-drift {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33%      { transform: translate(3%, -2%) scale(1.05); }
  66%      { transform: translate(-2%, 3%) scale(0.95); }
}
@keyframes rp-title-shine {
  0%   { background-position: 0% 50%; }
  100% { background-position: 300% 50%; }
}

/* Mock cards float — bigger amplitude */
@keyframes rp-float-a-strong {
  0%, 100% { transform: rotate(-7deg) translate(-110px, 10px); }
  50%      { transform: rotate(-11deg) translate(-122px, -14px); }
}
@keyframes rp-float-b-strong {
  0%, 100% { transform: rotate(5deg) translate(110px, -10px); }
  50%      { transform: rotate(9deg) translate(122px, 14px); }
}
@keyframes rp-float-c-strong {
  0%, 100% { transform: translateY(0) scale(1); }
  50%      { transform: translateY(-18px) scale(1.02); }
}
.rp-mock-card.left   { animation: rp-float-a-strong 7s ease-in-out infinite; }
.rp-mock-card.right  { animation: rp-float-b-strong 8s ease-in-out infinite; }
.rp-mock-card.center { animation: rp-float-c-strong 5.5s ease-in-out infinite; }

.rp-mock-card {
  transition: box-shadow 0.4s ease;
}
.rp-hero__mockwrap:hover .rp-mock-card.center {
  box-shadow: 0 32px 60px rgba(37, 99, 235, 0.45);
}

/* =========================================================
   HERO CTA — sits inside hero left column
   ========================================================= */
.st-key-hero_upload_btn {
  margin-top: 1.5rem;
  animation: rp-fade-in-up 0.7s ease both;
  animation-delay: 0.35s;
}
.st-key-hero_upload_btn div.stButton > button,
.st-key-hero_upload_btn div.stButton > button[kind="primary"] {
  animation: rp-pulse-glow 2.4s ease-in-out infinite;
  background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%) !important;
  border: 1px solid transparent !important;
  font-size: 18px !important;
  font-weight: 700 !important;
  padding: 1.15rem 2.5rem !important;
  border-radius: 16px !important;
  letter-spacing: -0.01em;
  color: #ffffff !important;
  transition: transform 0.18s ease, box-shadow 0.25s ease, background 0.25s ease !important;
}
.st-key-hero_upload_btn div.stButton > button::before,
.st-key-hero_upload_btn div.stButton > button[kind="primary"]::before {
  display: none !important;
}
.st-key-hero_upload_btn div.stButton > button:hover,
.st-key-hero_upload_btn div.stButton > button[kind="primary"]:hover {
  animation: none;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
  transform: translateY(-3px);
  box-shadow: 0 18px 40px rgba(37, 99, 235, 0.45) !important;
}
.st-key-hero_upload_btn div.stButton > button:active,
.st-key-hero_upload_btn div.stButton > button[kind="primary"]:active {
  transform: translateY(-1px);
  box-shadow: 0 10px 24px rgba(37, 99, 235, 0.35) !important;
}

/* =========================================================
   FEATURE CARDS — stagger entrance + hover lift
   ========================================================= */
.rp-feature {
  opacity: 0;
  animation: rp-fade-in-up 0.6s ease forwards;
  transition: box-shadow 0.25s ease, transform 0.25s ease, border-color 0.25s ease;
  cursor: default;
}
[data-testid="stHorizontalBlock"] > div:nth-child(1) .rp-feature { animation-delay: 0.10s; }
[data-testid="stHorizontalBlock"] > div:nth-child(2) .rp-feature { animation-delay: 0.22s; }
[data-testid="stHorizontalBlock"] > div:nth-child(3) .rp-feature { animation-delay: 0.34s; }

.rp-feature:hover {
  transform: translateY(-6px);
  box-shadow: 0 24px 48px rgba(15, 23, 42, 0.10);
  border-color: rgba(37, 99, 235, 0.40);
}
.rp-feature__icon {
  transition: transform 0.35s cubic-bezier(.34,1.56,.64,1), background 0.3s ease;
}
.rp-feature:hover .rp-feature__icon {
  transform: scale(1.12) rotate(-6deg);
  background: rgba(37, 99, 235, 0.16);
}

/* =========================================================
   STEP NAV — active pulse + smooth transition
   ========================================================= */
.rp-step {
  transition: background 0.18s ease, color 0.18s ease, transform 0.18s ease;
}
.rp-step:hover { transform: translateX(2px); }
.rp-step.active {
  animation: rp-step-glow 2s ease-in-out infinite;
}
.rp-step.done .material-symbols-outlined {
  animation: rp-fade-in 0.4s ease;
}

/* =========================================================
   TOP APP BAR — smooth nav underline
   ========================================================= */
.rp-topbar__nav a {
  position: relative;
}
.rp-topbar__nav a::after {
  content: '';
  position: absolute;
  left: 50%; right: 50%;
  bottom: -4px;
  height: 2px;
  background: var(--rp-primary);
  transition: left 0.25s ease, right 0.25s ease;
}
.rp-topbar__nav a:hover::after,
.rp-topbar__nav a.rp-active::after {
  left: 0; right: 0;
}
.rp-topbar__nav a.rp-active { border-bottom-color: transparent; }

/* =========================================================
   PANELS — subtle entrance
   ========================================================= */
.rp-panel, .rp-stepnav {
  animation: rp-fade-in-up 0.5s ease both;
}

/* =========================================================
   BUTTONS — smooth color transitions only
   ========================================================= */
div.stButton > button, div.stDownloadButton > button {
  transition: background 0.18s ease, border-color 0.18s ease, color 0.18s ease !important;
}

/* Step nav prev/next — compact */
[class*="st-key-prev_"] div.stButton > button,
[class*="st-key-next_"] div.stButton > button {
  font-size: 13px !important;
  font-weight: 600 !important;
  padding: 0.5rem 0.85rem !important;
  border-radius: var(--rp-radius-md) !important;
  white-space: nowrap;
}

/* Session reset under step_nav — subtle ghost */
.st-key-reset_session_btn {
  margin-top: 0.75rem;
}
.st-key-reset_session_btn div.stButton > button {
  font-size: 12px !important;
  font-weight: 500 !important;
  padding: 0.5rem 0.85rem !important;
  border-radius: var(--rp-radius-md) !important;
  background: transparent !important;
  border: 1px solid var(--rp-outline-variant) !important;
  color: var(--rp-on-surface-variant) !important;
}
.st-key-reset_session_btn div.stButton > button:hover {
  background: var(--rp-surface-container) !important;
  color: var(--rp-on-surface) !important;
}

/* =========================================================
   FILE UPLOADER — animated dashed pulse on hover
   ========================================================= */
[data-testid="stFileUploaderDropzone"] {
  background-image:
    repeating-linear-gradient(0deg,  transparent 0 12px, transparent 12px 24px),
    radial-gradient(circle at 50% 50%, rgba(37, 99, 235, 0.04) 0%, transparent 70%);
  transition: transform 0.25s ease, border-color 0.25s ease, background 0.25s ease;
}
[data-testid="stFileUploaderDropzone"]:hover {
  transform: translateY(-2px);
}

/* =========================================================
   IMAGE PREVIEW — subtle reveal
   ========================================================= */
[data-testid="stImage"] img {
  border-radius: var(--rp-radius-lg);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}
[data-testid="stImage"]:hover img {
  transform: translateY(-2px);
  box-shadow: var(--rp-shadow-2);
}

/* =========================================================
   DESIGN-TOKEN GROUP HEAD + SECTION TONE SWATCH
   ========================================================= */

/* Equal-height cards inside a marked row */
[data-testid="stHorizontalBlock"]:has(.rp-design-row-marker) {
  align-items: stretch !important;
}
[data-testid="stHorizontalBlock"]:has(.rp-design-row-marker)
  > [data-testid="column"] {
  display: flex !important;
  flex-direction: column !important;
}
[data-testid="stHorizontalBlock"]:has(.rp-design-row-marker)
  > [data-testid="column"] > div {
  flex: 1 1 auto !important;
  display: flex !important;
  flex-direction: column !important;
}
[data-testid="stHorizontalBlock"]:has(.rp-design-row-marker)
  > [data-testid="column"]
  [data-testid="stVerticalBlockBorderWrapper"] {
  flex: 1 1 auto !important;
  height: 100% !important;
}

.rp-group-head {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 14px;
  font-weight: 700;
  color: var(--rp-on-surface);
  padding: 0.25rem 0 0.85rem 0;
  border-bottom: 1px solid var(--rp-outline-variant);
  margin-bottom: 1rem;
}
.rp-group-head .material-symbols-outlined {
  font-size: 18px;
  color: var(--rp-primary);
}
.rp-tone-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--rp-on-surface);
  margin: 0.85rem 0 0.4rem 0;
}
.rp-tone-name {
  font-size: 11px;
  font-weight: 600;
  color: var(--rp-on-surface-variant);
  text-align: center;
  margin-top: 6px;
}
.rp-tone-name.sel {
  color: var(--rp-primary);
  font-weight: 700;
}

/* Tone button = the swatch itself. Per-key bg color, primary state = selected. */
[class*="st-key-tone_btn_"] div.stButton > button {
  width: 100% !important;
  aspect-ratio: 1 / 1 !important;
  height: auto !important;
  padding: 0 !important;
  border-radius: var(--rp-radius-md) !important;
  border: 2px solid transparent !important;
  box-shadow: var(--rp-shadow-1) !important;
  color: #ffffff !important;
  font-size: 22px !important;
  font-weight: 800 !important;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.35);
  transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease !important;
}
[class*="st-key-tone_btn_"] div.stButton > button *,
[class*="st-key-tone_btn_"] div.stButton > button[kind="primary"] * {
  color: #ffffff !important;
}
[class*="st-key-tone_btn_neutral"] div.stButton > button,
[class*="st-key-tone_btn_neutral"] div.stButton > button[kind="primary"] {
  background: #94a3b8 !important;
}
[class*="st-key-tone_btn_green"] div.stButton > button,
[class*="st-key-tone_btn_green"] div.stButton > button[kind="primary"] {
  background: #16a34a !important;
}
[class*="st-key-tone_btn_blue"] div.stButton > button,
[class*="st-key-tone_btn_blue"] div.stButton > button[kind="primary"] {
  background: #2563eb !important;
}
[class*="st-key-tone_btn_purple"] div.stButton > button,
[class*="st-key-tone_btn_purple"] div.stButton > button[kind="primary"] {
  background: #7c3aed !important;
}
[class*="st-key-tone_btn_orange"] div.stButton > button,
[class*="st-key-tone_btn_orange"] div.stButton > button[kind="primary"] {
  background: #ea580c !important;
}
[class*="st-key-tone_btn_"] div.stButton > button[kind="primary"] {
  border: 3px solid var(--rp-primary) !important;
  transform: scale(1.06);
  box-shadow: 0 0 0 5px rgba(37, 99, 235, 0.18),
              0 8px 18px rgba(37, 99, 235, 0.25) !important;
}
[class*="st-key-tone_btn_"] div.stButton > button:hover {
  transform: translateY(-2px);
}
[class*="st-key-tone_btn_"] div.stButton > button[kind="primary"]:hover {
  transform: scale(1.06) translateY(-2px);
}

/* =========================================================
   SECTION BAND (between hero and features)
   ========================================================= */
.rp-section-band {
  margin: 1.5rem 0 2rem 0;
  text-align: center;
  animation: rp-fade-in-up 0.6s ease both;
}
.rp-section-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.3rem 0.85rem;
  border-radius: var(--rp-radius-full);
  background: var(--rp-primary-container);
  color: var(--rp-on-primary-container);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  margin-bottom: 0.85rem;
}
.rp-section-h {
  font-size: 30px;
  font-weight: 800;
  color: var(--rp-on-surface);
  letter-spacing: -0.02em;
  margin-bottom: 0.5rem;
  background: linear-gradient(120deg, #0f172a 0%, #2563eb 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  color: transparent;
}
.rp-section-sub {
  font-size: 15px;
  color: var(--rp-on-surface-variant);
  max-width: 36rem;
  margin: 0 auto;
}

/* Respect reduced motion */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.001ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.001ms !important;
  }
}
</style>
"""


def inject_global_css() -> None:
    """Render font links + global CSS once per script run."""
    st.markdown(_FONT_LINKS + _CSS, unsafe_allow_html=True)
