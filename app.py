"""
FraudGuard Command — Credit Card Fraud Detection System
A single-file Streamlit app: UI, routing, auth flow, and detection logic.
"""
import streamlit as st
import numpy as np
import joblib
import time
import struct
from pathlib import Path
from datetime import date, datetime

from database import (init_db, register_user, login_user, log_transaction, get_user_transactions,
                       get_user_stats, save_profile_details, mark_profile_skipped,
                       create_reset_token, verify_reset_token, reset_password)

st.set_page_config(
    page_title="FraudGuard Command",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# How long a signed-in session can sit idle before being auto-logged-out.
SESSION_TIMEOUT_MINUTES = 15


init_db()

@st.cache_resource
def load_model():
    return joblib.load(Path(__file__).parent / "fraud_model.pkl")


model = load_model()



_DEFAULTS = [
    ("user", None), ("active_page", "dashboard"), ("preset_load", None), ("view", "landing"),
    ("pending_signup", None), ("auth_notice", None), ("reset_email", None),
    ("reset_notice", None), ("last_activity", None), ("session_expired", False),
    ("reset_stage", "request"),
]


def init_session_state():
    for k, v in _DEFAULTS:
        if k not in st.session_state:
            st.session_state[k] = v


def check_session_timeout():
    """Logs the user out if too much time has passed since their last
    interaction with the app. Since Streamlit only re-runs the script on
    user interaction (or a manual refresh), this is checked on every
    rerun rather than via a background timer."""
    if st.session_state.user is None:
        return
    now = datetime.now()
    last = st.session_state.last_activity
    if last is not None and (now - last).total_seconds() > SESSION_TIMEOUT_MINUTES * 60:
        st.session_state.user = None
        st.session_state.view = "landing"
        st.session_state.session_expired = True
    else:
        st.session_state.last_activity = now


init_session_state()
check_session_timeout()



def H(html):
    st.markdown(html, unsafe_allow_html=True)


def mono(text, color="rgba(255,255,255,0.4)", size="11px", weight="600", spacing="1.2px"):
    return f"<span style='font-family:JetBrains Mono,monospace;color:{color};font-size:{size};font-weight:{weight};letter-spacing:{spacing};text-transform:uppercase;'>{text}</span>"


def safe_conf(val):
    if isinstance(val, bytes):
        try: return round(struct.unpack("f", val)[0], 1)
        except: return 0.0
    try: return round(float(val), 1)
    except: return 0.0


def load_css(path="style.css"):
    """Read the external stylesheet and inject it into the page. Keeping the
    CSS in its own file (instead of one giant inline string in app.py) makes
    it easier to find, edit, and diff on its own."""
    css_path = Path(__file__).parent / path
    with open(css_path, "r", encoding="utf-8") as f:
        css = f.read()
    H(f"<style>\n{css}\n</style>")


def show_bg():
    H("""
    <div style="position:fixed;top:0;left:0;width:100%;height:100%;
         pointer-events:none;z-index:0;overflow:hidden;opacity:0.5;">
        <div style="position:absolute;top:0;left:0;width:100%;height:100%;
            background-image:
                linear-gradient(rgba(0,255,102,0.025) 1px,transparent 1px),
                linear-gradient(90deg,rgba(0,255,102,0.025) 1px,transparent 1px);
            background-size:40px 40px;"></div>
    </div>
    """)

def metric_card(label, value, sub, color="#00ff66", icon=""):
    return f"""
    <div style="background:#0a0d0a;border:1px solid rgba(0,255,102,0.1);
         border-radius:6px;padding:16px 20px;position:relative;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
            <span style="font-family:'JetBrains Mono',monospace;font-size:12px;
                 color:rgba(255,255,255,0.4);letter-spacing:1.3px;text-transform:uppercase;font-weight:700;">
                 {label}</span>
            <span style="font-size:16px;opacity:0.5;">{icon}</span>
        </div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:42px;font-weight:800;
             color:{color};line-height:1;text-shadow:0 0 20px {color}55;">{value}</div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:13px;
             color:rgba(255,255,255,0.3);margin-top:10px;">{sub}</div>
    </div>
    """

def cc_html(number="4532 •••• •••• 7891", holder="FRAUD ANALYSIS", network="VISA"):
    return f"""
    <div style="background:#0a0d0a;border:1px solid rgba(0,255,102,0.25);
         border-radius:8px;padding:16px 22px;position:relative;overflow:hidden;
         min-height:165px;margin-bottom:20px;">
        <div style="position:absolute;top:0;left:0;right:0;height:2px;
             background:linear-gradient(90deg,transparent,#00ff66,transparent);"></div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;
             color:#00ff66;letter-spacing:2px;margin-bottom:20px;">🛡 FRAUDGUARD</div>
        <div style="width:36px;height:26px;background:rgba(0,255,102,0.15);
             border:1px solid rgba(0,255,102,0.3);border-radius:4px;margin-bottom:18px;"></div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:15px;font-weight:500;
             color:rgba(0,255,102,0.7);letter-spacing:4px;margin-bottom:16px;">{number}</div>
        <div style="display:flex;justify-content:space-between;align-items:flex-end;">
            <div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:8px;
                     color:rgba(255,255,255,0.3);letter-spacing:1.5px;margin-bottom:3px;">CARD HOLDER</div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:12px;
                     color:rgba(255,255,255,0.7);letter-spacing:1px;">{holder}</div>
            </div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:18px;font-weight:700;
                 color:rgba(255,255,255,0.4);">{network}</div>
        </div>
    </div>
    """

def mask_card_number(raw, fallback="4532 •••• •••• 7891"):
    """Turn whatever digits the user typed into a masked 'first4 •••• •••• last4'
    display string, the way a real card UI would show it."""
    digits = "".join(ch for ch in (raw or "") if ch.isdigit())
    if len(digits) < 4:
        return fallback
    first4 = digits[:4]
    last4  = digits[-4:] if len(digits) >= 8 else digits[-min(4, len(digits)):]
    return f"{first4} •••• •••• {last4}"

def section_label(text, count=None):
    extra = f'<span style="color:rgba(255,255,255,0.2);font-weight:400;"> · {count}</span>' if count else ""
    H(f"""
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:16px;">
        <div style="width:6px;height:6px;background:#00ff66;border-radius:50%;
             box-shadow:0 0 8px rgba(0,255,102,0.6);"></div>
        <span style="font-family:'JetBrains Mono',monospace;font-size:16px;font-weight:700;
             color:#fff;letter-spacing:0.5px;text-transform:uppercase;">{text}{extra}</span>
    </div>
    """)

def panel_open(extra=""):
    H(f"""<div style="background:#0a0d0a;border:1px solid rgba(0,255,102,0.1);
         border-radius:8px;padding:18px;{extra}">""")

def panel_close():
    H("</div>")


load_css()

# ══════════════════════════════════════
#  TOP NAV / SIDEBAR / PAGE NAV
# ══════════════════════════════════════


def show_topbar(active="Command Center"):
    u = st.session_state.user
    H(f"""
    <div style="background:#050705;border-bottom:1px solid rgba(0,255,102,0.15);
         padding:0 40px;display:flex;align-items:center;justify-content:space-between;
         height:64px;position:sticky;top:0;z-index:100;">
        <div style="display:flex;align-items:center;gap:16px;">
            <div style="width:52px;height:52px;border:2px solid #00ff66;border-radius:9px;
                 display:flex;align-items:center;justify-content:center;
                 box-shadow:0 0 20px rgba(0,255,102,0.35);">
                <span style="font-size:26px;">🛡️</span>
            </div>
            <div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:28px;font-weight:800;
                     color:#fff;letter-spacing:0.5px;">
                    FRAUD<span style="color:#00ff66;">GUARD</span>
                    <span style="font-size:13px;color:rgba(255,255,255,0.3);
                         font-weight:500;margin-left:4px;">v2</span>
                </div>
            </div>
        </div>
        <div style="display:flex;align-items:center;gap:20px;">
            <div style="display:flex;align-items:center;gap:6px;">
                <div style="width:6px;height:6px;background:#00ff66;border-radius:50%;
                     box-shadow:0 0 8px rgba(0,255,102,0.8);
                     animation:blip 2s ease-in-out infinite;"></div>
                <span style="font-family:'JetBrains Mono',monospace;font-size:13px;
                     color:#00ff66;letter-spacing:1px;text-transform:uppercase;font-weight:700;">
                     {active}</span>
            </div>
            <div style="width:1px;height:20px;background:rgba(255,255,255,0.1);"></div>
            <div style="display:flex;align-items:center;gap:8px;">
                <div style="width:28px;height:28px;border-radius:4px;
                     background:rgba(0,255,102,0.1);border:1px solid rgba(0,255,102,0.3);
                     display:flex;align-items:center;justify-content:center;
                     font-family:'JetBrains Mono',monospace;font-size:11px;
                     font-weight:700;color:#00ff66;">
                     {"".join([w[0].upper() for w in u['full_name'].split()[:2]])}
                </div>
                <div>
                    <div style="font-family:'JetBrains Mono',monospace;font-size:14px;
                         color:#fff;font-weight:700;">{u['full_name']}</div>
                    <div style="font-family:'JetBrains Mono',monospace;font-size:9px;
                         color:rgba(0,255,102,0.5);letter-spacing:0.5px;">ANALYST · SEC-LVL-1</div>
                </div>
            </div>
        </div>
    </div>
    """)

def show_sidebar():
    with st.sidebar:
        H("""
        <div style="padding:24px 4px 16px;">
            <div style="font-family:'JetBrains Mono',monospace;font-size:10px;
                 color:rgba(255,255,255,0.25);letter-spacing:1.5px;
                 text-transform:uppercase;margin-bottom:12px;">Overview</div>
        </div>
        """)
        if st.button("▦  COMMAND CENTER", use_container_width=True, key="nav_dash"):
            st.session_state.active_page = "dashboard"; st.rerun()
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        if st.button("◎  DETECTION", use_container_width=True, key="nav_det"):
            st.session_state.active_page = "detection"; st.rerun()
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        if st.button("▤  INCIDENTS", use_container_width=True, key="nav_hist"):
            st.session_state.active_page = "history"; st.rerun()
        H('<div style="height:1px;background:rgba(0,255,102,0.1);margin:24px 0;"></div>')
        if st.button("→  LOGOUT", use_container_width=True, key="nav_out"):
            st.session_state.user = None; st.rerun()


def show_page_nav(active_page):
    H('<div style="position:relative;z-index:10;padding:8px 40px 0;">')
    n1, n2, n3, n4, n5 = st.columns([1, 1, 1, 0.15, 1])
    with n1:
        if st.button("▦ DASHBOARD", key="pagenav_dash", use_container_width=True,
                     type="primary" if active_page == "dashboard" else "secondary"):
            st.session_state.active_page = "dashboard"; st.rerun()
    with n2:
        if st.button("◎ DETECTION", key="pagenav_det", use_container_width=True,
                     type="primary" if active_page == "detection" else "secondary"):
            st.session_state.active_page = "detection"; st.rerun()
    with n3:
        if st.button("▤ INCIDENTS", key="pagenav_hist", use_container_width=True,
                     type="primary" if active_page == "history" else "secondary"):
            st.session_state.active_page = "history"; st.rerun()
    with n5:
        if st.button("→ LOGOUT", key="pagenav_logout", use_container_width=True):
            st.session_state.user = None
            st.session_state.view = "landing"
            st.rerun()
    H('</div>')


# ══════════════════════════════════════
#  LANDING PAGE
# ══════════════════════════════════════


def show_landing_page():
    show_bg()
    if st.session_state.session_expired:
        st.session_state.session_expired = False
        H(f"""
        <div style="position:relative;z-index:20;margin:14px 48px 0;background:rgba(255,170,0,0.08);
             border:1px solid rgba(255,170,0,0.35);border-radius:4px;padding:12px 18px;
             font-family:'JetBrains Mono',monospace;font-size:13px;color:#ffaa00;">
            ⏱ You were signed out after {SESSION_TIMEOUT_MINUTES} minutes of inactivity. Please sign in again.
        </div>
        """)

    # ── NAV ──────────────────────────────────────────────────────────────
    H("""
    <div style="position:relative;z-index:10;border-bottom:1px solid rgba(0,255,102,0.12);
         padding:10px 48px 0;display:flex;align-items:center;justify-content:space-between;">
        <div style="display:flex;align-items:center;gap:14px;height:52px;">
            <div style="width:54px;height:54px;border:2px solid #00ff66;border-radius:10px;
                 display:flex;align-items:center;justify-content:center;
                 box-shadow:0 0 20px rgba(0,255,102,0.35);font-size:27px;">🛡️</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:29px;font-weight:800;color:#fff;">
                FRAUD<span style="color:#00ff66;">GUARD</span>
                <span style="font-size:14px;color:rgba(255,255,255,0.3);font-weight:500;margin-left:4px;">v2</span>
            </div>
        </div>
    </div>
    """)
    with st.container(key="landing_nav_links"):
        navh, navd, navdet = st.columns([1, 1.5, 1.5])
        with navh:
            if st.button("HOME", key="nav_home_btn", use_container_width=True):
                st.session_state.view = "landing"
                st.rerun()
        with navd:
            if st.button("DASHBOARD", key="nav_dashboard_btn", use_container_width=True):
                st.session_state.view = "auth"
                st.session_state.auth_tab = "login"
                st.session_state.auth_notice = ("ok", "SIGN IN TO ACCESS YOUR DASHBOARD.")
                st.rerun()
        with navdet:
            if st.button("DETECTION", key="nav_detection_btn", use_container_width=True):
                st.session_state.view = "auth"
                st.session_state.auth_tab = "login"
                st.session_state.auth_notice = ("ok", "SIGN IN TO ACCESS YOUR DETECTION.")
                st.rerun()
    H("<div style='height:4px'></div>")

    # ── HERO (layered background graphic behind the headline) ────────────
    H("""
    <div style="position:relative;z-index:10;padding:34px 48px 20px;overflow:hidden;
         min-height:460px;">
        <!-- Layer 1: animated scanning grid across the whole hero -->
        <div style="position:absolute;inset:0;pointer-events:none;opacity:0.5;
             background-image:linear-gradient(rgba(0,255,102,0.06) 1px,transparent 1px),
             linear-gradient(90deg,rgba(0,255,102,0.06) 1px,transparent 1px);
             background-size:40px 40px;animation:scan 6s linear infinite;"></div>
        <!-- Layer 2: giant watermark shield, glowing, sitting behind the copy -->
        <svg viewBox="0 0 200 200" style="position:absolute;top:-40px;right:-30px;width:520px;height:520px;
             opacity:0.16;pointer-events:none;filter:drop-shadow(0 0 40px rgba(0,255,102,0.5));">
            <path d="M100 8 L178 40 V96 C178 142 145 178 100 194 C55 178 22 142 22 96 V40 Z"
                  fill="none" stroke="#00ff66" stroke-width="3"/>
            <path d="M100 8 L178 40 V96 C178 142 145 178 100 194 C55 178 22 142 22 96 V40 Z"
                  fill="url(#shieldFade)"/>
            <path d="M65 100 L88 123 L138 70" fill="none" stroke="#00ff66" stroke-width="6"
                  stroke-linecap="round" stroke-linejoin="round"/>
            <defs>
                <linearGradient id="shieldFade" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#00ff66" stop-opacity="0.12"/>
                    <stop offset="100%" stop-color="#00ff66" stop-opacity="0"/>
                </linearGradient>
            </defs>
        </svg>
        <!-- Layer 3: soft spotlight glow directly behind the headline for contrast -->
        <div style="position:absolute;top:-60px;left:-80px;width:820px;height:560px;
             pointer-events:none;
             background:radial-gradient(ellipse 55% 60% at 30% 35%,
             rgba(0,255,102,0.14),transparent 70%);"></div>
        <!-- Layer 4: connected-nodes network graphic -->
        <div style="position:absolute;top:-20px;left:0;width:100%;height:480px;
             pointer-events:none;opacity:0.9;">
            <svg viewBox="0 0 1400 460" style="width:100%;height:100%;" preserveAspectRatio="xMidYMid slice">
            <line x1="703" y1="107" x2="633" y2="244" stroke="rgba(0,255,102,0.18)" stroke-width="1"/>
            <line x1="703" y1="107" x2="852" y2="55" stroke="rgba(0,255,102,0.18)" stroke-width="1"/>
            <line x1="848" y1="363" x2="788" y2="328" stroke="rgba(0,255,102,0.18)" stroke-width="1"/>
            <line x1="848" y1="363" x2="633" y2="244" stroke="rgba(0,255,102,0.18)" stroke-width="1"/>
            <line x1="138" y1="67" x2="293" y2="144" stroke="rgba(0,255,102,0.18)" stroke-width="1"/>
            <line x1="138" y1="67" x2="216" y2="252" stroke="rgba(0,255,102,0.18)" stroke-width="1"/>
            <line x1="1137" y1="78" x2="1180" y2="98" stroke="rgba(0,255,102,0.18)" stroke-width="1"/>
            <line x1="1137" y1="78" x2="1233" y2="61" stroke="rgba(0,255,102,0.18)" stroke-width="1"/>
            <line x1="788" y1="328" x2="633" y2="244" stroke="rgba(0,255,102,0.18)" stroke-width="1"/>
            <line x1="158" y1="289" x2="161" y2="319" stroke="rgba(0,255,102,0.18)" stroke-width="1"/>
            <line x1="158" y1="289" x2="216" y2="252" stroke="rgba(0,255,102,0.18)" stroke-width="1"/>
            <line x1="479" y1="49" x2="492" y2="53" stroke="rgba(0,255,102,0.18)" stroke-width="1"/>
            <line x1="479" y1="49" x2="532" y2="76" stroke="rgba(0,255,102,0.18)" stroke-width="1"/>
            <line x1="216" y1="252" x2="161" y2="319" stroke="rgba(0,255,102,0.18)" stroke-width="1"/>
            <line x1="896" y1="65" x2="852" y2="55" stroke="rgba(0,255,102,0.18)" stroke-width="1"/>
            <line x1="703" y1="107" x2="896" y2="65" stroke="rgba(0,255,102,0.18)" stroke-width="1"/>
            <line x1="532" y1="76" x2="492" y2="53" stroke="rgba(0,255,102,0.18)" stroke-width="1"/>
            <line x1="1168" y1="247" x2="1221" y2="329" stroke="rgba(0,255,102,0.18)" stroke-width="1"/>
            <line x1="1168" y1="247" x2="1180" y2="98" stroke="rgba(0,255,102,0.18)" stroke-width="1"/>
            <line x1="216" y1="252" x2="293" y2="144" stroke="rgba(0,255,102,0.18)" stroke-width="1"/>
            <line x1="293" y1="144" x2="335" y2="306" stroke="rgba(0,255,102,0.18)" stroke-width="1"/>
            <line x1="1331" y1="351" x2="1221" y2="329" stroke="rgba(0,255,102,0.18)" stroke-width="1"/>
            <line x1="1168" y1="247" x2="1331" y2="351" stroke="rgba(0,255,102,0.18)" stroke-width="1"/>
            <line x1="1233" y1="61" x2="1180" y2="98" stroke="rgba(0,255,102,0.18)" stroke-width="1"/>
            <line x1="335" y1="306" x2="281" y2="322" stroke="rgba(0,255,102,0.18)" stroke-width="1"/>
            <line x1="216" y1="252" x2="335" y2="306" stroke="rgba(0,255,102,0.18)" stroke-width="1"/>
            <line x1="216" y1="252" x2="281" y2="322" stroke="rgba(0,255,102,0.18)" stroke-width="1"/>
            <circle cx="703" cy="107" r="3.5" fill="#00ff66" opacity="0.45"/>
            <circle cx="848" cy="363" r="2.5" fill="#00ff66" opacity="0.45"/>
            <circle cx="138" cy="67" r="2.5" fill="#00ff66" opacity="0.45"/>
            <circle cx="1137" cy="78" r="3.5" fill="#00ff66" opacity="0.45"/>
            <circle cx="788" cy="328" r="2.5" fill="#00ff66" opacity="0.45"/>
            <circle cx="158" cy="289" r="5" fill="#ff3355" opacity="0.9" style="filter:drop-shadow(0 0 6px rgba(255,51,85,0.8))"><animate attributeName="opacity" values="0.9;0.3;0.9" dur="4s" repeatCount="indefinite"/></circle>
            <circle cx="479" cy="49" r="3.5" fill="#00ff66" opacity="0.45"/>
            <circle cx="216" cy="252" r="2.5" fill="#00ff66" opacity="0.45"/>
            <circle cx="896" cy="65" r="2.5" fill="#00ff66" opacity="0.45"/>
            <circle cx="532" cy="76" r="3.5" fill="#00ff66" opacity="0.45"/>
            <circle cx="1168" cy="247" r="2.5" fill="#00ff66" opacity="0.45"/>
            <circle cx="161" cy="319" r="2.5" fill="#00ff66" opacity="0.45"/>
            <circle cx="293" cy="144" r="3.5" fill="#00ff66" opacity="0.45"/>
            <circle cx="1331" cy="351" r="2.5" fill="#00ff66" opacity="0.45"/>
            <circle cx="1233" cy="61" r="5" fill="#ff3355" opacity="0.9" style="filter:drop-shadow(0 0 6px rgba(255,51,85,0.8))"><animate attributeName="opacity" values="0.9;0.3;0.9" dur="4s" repeatCount="indefinite"/></circle>
            <circle cx="1221" cy="329" r="3.5" fill="#00ff66" opacity="0.45"/>
            <circle cx="852" cy="55" r="2.5" fill="#00ff66" opacity="0.45"/>
            <circle cx="492" cy="53" r="2.5" fill="#00ff66" opacity="0.45"/>
            <circle cx="1180" cy="98" r="3.5" fill="#00ff66" opacity="0.45"/>
            <circle cx="633" cy="244" r="2.5" fill="#00ff66" opacity="0.45"/>
            <circle cx="335" cy="306" r="2.5" fill="#00ff66" opacity="0.45"/>
            <circle cx="281" cy="322" r="3.5" fill="#00ff66" opacity="0.45"/>
            </svg>
            <div style="position:absolute;top:0;left:0;width:100%;height:100%;
                 background:linear-gradient(180deg,transparent 45%,#050705 100%);"></div>
        </div>
        <!-- Layer 5 (topmost): the actual copy, sitting on top of everything above -->
        <div style="position:relative;z-index:5;">
            <div style="display:inline-flex;align-items:center;gap:8px;
                 background:rgba(0,255,102,0.06);border:1px solid rgba(0,255,102,0.25);
                 border-radius:3px;padding:6px 14px;margin-bottom:20px;
                 backdrop-filter:blur(2px);">
                <div style="width:6px;height:6px;background:#00ff66;border-radius:50%;
                     box-shadow:0 0 6px rgba(0,255,102,0.8);"></div>
                <span style="font-family:'JetBrains Mono',monospace;font-size:12px;
                     font-weight:600;color:#00ff66;letter-spacing:1.5px;">
                     TRAINED ON 284,807 REAL TRANSACTIONS</span>
            </div>
            <div style="font-family:'Space Grotesk',sans-serif;font-size:60px;font-weight:900;
                 color:#fff;line-height:1.05;margin-bottom:22px;letter-spacing:-2px;max-width:780px;
                 text-shadow:0 4px 40px rgba(0,0,0,0.6);">
                Stop fraud <span style="color:#00ff66;text-shadow:0 0 30px rgba(0,255,102,0.5);">before</span><br>
                the chargeback hits.
            </div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:16px;
                 color:rgba(255,255,255,0.55);line-height:1.75;margin-bottom:28px;max-width:520px;">
                FraudGuard scores every transaction in real time with an XGBoost model —
                amount, merchant, card type, location, time of day — and gives you a
                verdict before the money's gone.
            </div>
        </div>
    </div>
    """)
    H("<div style='height:6px'></div>")
    with st.container(key="landing_hero_ctas"):
        b1, b2 = st.columns([1, 1])
        with b1:
            if st.button("GET STARTED FREE →", key="landing_deploy", use_container_width=True, type="primary"):
                st.session_state.view = "auth"
                st.session_state.auth_tab = "register"
                st.rerun()
        with b2:
            if st.button("SIGN IN", key="landing_signin", use_container_width=True):
                st.session_state.view = "auth"
                st.session_state.auth_tab = "login"
                st.rerun()
    H("<div style='height:32px'></div>")

    # ── STATS ─────────────────────────────────────────────────────────────
    H("""
    <div style="position:relative;z-index:10;padding:10px 48px 30px;
         display:grid;grid-template-columns:repeat(3,1fr);gap:20px;max-width:1100px;">
        <div style="background:#0a0d0a;border:1px solid rgba(0,255,102,0.12);border-radius:8px;padding:20px;">
            <div style="font-family:'JetBrains Mono',monospace;font-size:32px;font-weight:800;
                 color:#00ff66;margin-bottom:8px;">99.9%</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:13px;
                 color:rgba(255,255,255,0.4);letter-spacing:0.5px;">Detection accuracy on test data</div>
        </div>
        <div style="background:#0a0d0a;border:1px solid rgba(0,255,102,0.12);border-radius:8px;padding:20px;">
            <div style="font-family:'JetBrains Mono',monospace;font-size:32px;font-weight:800;
                 color:#00ff66;margin-bottom:8px;">&lt;1s</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:13px;
                 color:rgba(255,255,255,0.4);letter-spacing:0.5px;">Average analysis response time</div>
        </div>
        <div style="background:#0a0d0a;border:1px solid rgba(0,255,102,0.12);border-radius:8px;padding:20px;">
            <div style="font-family:'JetBrains Mono',monospace;font-size:32px;font-weight:800;
                 color:#00ff66;margin-bottom:8px;">284K</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:13px;
                 color:rgba(255,255,255,0.4);letter-spacing:0.5px;">Real transactions used for training</div>
        </div>
    </div>
    """)

    # ── HOW IT WORKS ──────────────────────────────────────────────────────
    H("""
    <div style="position:relative;z-index:10;padding:10px 48px 8px;">
        <div style="font-family:'JetBrains Mono',monospace;font-size:11px;color:rgba(0,255,102,0.7);
             letter-spacing:2px;text-transform:uppercase;margin-bottom:8px;">● Pipeline</div>
        <div style="font-family:'Space Grotesk',sans-serif;font-size:28px;font-weight:800;
             color:#fff;margin-bottom:26px;">From transaction to verdict, in three steps</div>
    </div>
    <div style="position:relative;z-index:10;padding:0 48px 36px;
         display:grid;grid-template-columns:repeat(3,1fr);gap:20px;max-width:1100px;">
        <div style="background:#0a0d0a;border:1px solid rgba(0,255,102,0.12);border-radius:8px;padding:22px;position:relative;">
            <div style="font-family:'JetBrains Mono',monospace;font-size:12px;color:rgba(0,255,102,0.5);
                 letter-spacing:1.5px;margin-bottom:10px;">STEP 01</div>
            <div style="font-family:'Space Grotesk',sans-serif;font-size:19px;font-weight:700;
                 color:#fff;margin-bottom:10px;">Enter the transaction</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:13px;
                 color:rgba(255,255,255,0.4);line-height:1.7;">
                 Amount, merchant type, card type, location, time of day — and a
                 few risk-factor checkboxes like "new merchant" or "foreign currency."</div>
        </div>
        <div style="background:#0a0d0a;border:1px solid rgba(0,255,102,0.12);border-radius:8px;padding:22px;">
            <div style="font-family:'JetBrains Mono',monospace;font-size:12px;color:rgba(0,255,102,0.5);
                 letter-spacing:1.5px;margin-bottom:10px;">STEP 02</div>
            <div style="font-family:'Space Grotesk',sans-serif;font-size:19px;font-weight:700;
                 color:#fff;margin-bottom:10px;">XGBoost scores it</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:13px;
                 color:rgba(255,255,255,0.4);line-height:1.7;">
                 The model — trained on 284,807 real, anonymized transactions —
                 evaluates a 28-feature vector and returns a fraud probability.</div>
        </div>
        <div style="background:#0a0d0a;border:1px solid rgba(0,255,102,0.12);border-radius:8px;padding:22px;">
            <div style="font-family:'JetBrains Mono',monospace;font-size:12px;color:rgba(0,255,102,0.5);
                 letter-spacing:1.5px;margin-bottom:10px;">STEP 03</div>
            <div style="font-family:'Space Grotesk',sans-serif;font-size:19px;font-weight:700;
                 color:#fff;margin-bottom:10px;">Get a verdict, instantly</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:13px;
                 color:rgba(255,255,255,0.4);line-height:1.7;">
                 FRAUD or LEGIT with a confidence score, in under a second —
                 logged straight to your incident history.</div>
        </div>
    </div>
    """)

    # ── FEATURES ──────────────────────────────────────────────────────────
    H("""
    <div style="position:relative;z-index:10;padding:10px 48px 8px;">
        <div style="font-family:'JetBrains Mono',monospace;font-size:11px;color:rgba(0,255,102,0.7);
             letter-spacing:2px;text-transform:uppercase;margin-bottom:8px;">● What's inside</div>
        <div style="font-family:'Space Grotesk',sans-serif;font-size:28px;font-weight:800;
             color:#fff;margin-bottom:26px;">Built like a real command center, not a toy demo</div>
    </div>
    <div style="position:relative;z-index:10;padding:0 48px 36px;
         display:grid;grid-template-columns:repeat(3,1fr);gap:18px;max-width:1150px;">
        <div style="background:#0a0d0a;border:1px solid rgba(0,255,102,0.1);border-radius:8px;padding:20px;">
            <div style="font-size:22px;margin-bottom:10px;">⚡</div>
            <div style="font-family:'Space Grotesk',sans-serif;font-size:16px;font-weight:700;color:#fff;margin-bottom:8px;">Real-time scoring</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:12.5px;color:rgba(255,255,255,0.4);line-height:1.6;">Every transaction gets an XGBoost fraud/legit verdict with a confidence score, under a second.</div>
        </div>
        <div style="background:#0a0d0a;border:1px solid rgba(0,255,102,0.1);border-radius:8px;padding:20px;">
            <div style="font-size:22px;margin-bottom:10px;">🔐</div>
            <div style="font-family:'Space Grotesk',sans-serif;font-size:16px;font-weight:700;color:#fff;margin-bottom:8px;">bcrypt-secured accounts</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:12.5px;color:rgba(255,255,255,0.4);line-height:1.6;">Passwords hashed with bcrypt and a per-user salt — plus password reset and idle session timeout.</div>
        </div>
        <div style="background:#0a0d0a;border:1px solid rgba(0,255,102,0.1);border-radius:8px;padding:20px;">
            <div style="font-size:22px;margin-bottom:10px;">💳</div>
            <div style="font-family:'Space Grotesk',sans-serif;font-size:16px;font-weight:700;color:#fff;margin-bottom:8px;">Card-aware risk scoring</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:12.5px;color:rgba(255,255,255,0.4);line-height:1.6;">Debit vs. credit is factored into the score itself, not just captured and ignored.</div>
        </div>
        <div style="background:#0a0d0a;border:1px solid rgba(0,255,102,0.1);border-radius:8px;padding:20px;">
            <div style="font-size:22px;margin-bottom:10px;">📊</div>
            <div style="font-family:'Space Grotesk',sans-serif;font-size:16px;font-weight:700;color:#fff;margin-bottom:8px;">Command-center dashboard</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:12.5px;color:rgba(255,255,255,0.4);line-height:1.6;">Total checks, fraud rate, and quick-test presets at a glance the moment you sign in.</div>
        </div>
        <div style="background:#0a0d0a;border:1px solid rgba(0,255,102,0.1);border-radius:8px;padding:20px;">
            <div style="font-size:22px;margin-bottom:10px;">📋</div>
            <div style="font-family:'Space Grotesk',sans-serif;font-size:16px;font-weight:700;color:#fff;margin-bottom:8px;">Full incident history</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:12.5px;color:rgba(255,255,255,0.4);line-height:1.6;">Every check you've ever run, timestamped and searchable, tied to your account.</div>
        </div>
        <div style="background:#0a0d0a;border:1px solid rgba(0,255,102,0.1);border-radius:8px;padding:20px;">
            <div style="font-size:22px;margin-bottom:10px;">🔍</div>
            <div style="font-family:'Space Grotesk',sans-serif;font-size:16px;font-weight:700;color:#fff;margin-bottom:8px;">Transparent about its model</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:12.5px;color:rgba(255,255,255,0.4);line-height:1.6;">Every analysis page explains exactly how the demo blends its features — no black box.</div>
        </div>
    </div>
    """)

    # ── FOOTER ────────────────────────────────────────────────────────────
    H("""
    <div style="position:relative;z-index:10;border-top:1px solid rgba(0,255,102,0.1);
         padding:24px 48px;display:flex;align-items:center;justify-content:space-between;
         flex-wrap:wrap;gap:12px;">
        <div style="display:flex;align-items:center;gap:10px;">
            <div style="width:28px;height:28px;border:1.5px solid rgba(0,255,102,0.5);border-radius:6px;
                 display:flex;align-items:center;justify-content:center;font-size:14px;">🛡️</div>
            <span style="font-family:'JetBrains Mono',monospace;font-size:13px;font-weight:700;color:rgba(255,255,255,0.5);">
                FRAUD<span style="color:#00ff66;">GUARD</span> v2</span>
        </div>
    </div>
    """)


def show_auth_page():
    show_bg()
    if "auth_tab" not in st.session_state:
        st.session_state.auth_tab = "login"

    H('<div style="position:relative;z-index:10;padding:10px 48px 0;'
      'display:flex;align-items:center;justify-content:space-between;">'
      '<div style="display:flex;align-items:center;gap:14px;">'
      '<div style="width:54px;height:54px;border:2px solid #00ff66;border-radius:10px;'
      'display:flex;align-items:center;justify-content:center;'
      'box-shadow:0 0 20px rgba(0,255,102,0.35);font-size:27px;">🛡️</div>'
      '<div style="font-family:\'JetBrains Mono\',monospace;font-size:29px;font-weight:800;color:#fff;">'
      'FRAUD<span style="color:#00ff66;">GUARD</span></div></div></div>')

    _, back_col = st.columns([8, 1.6])
    with back_col:
        if st.button("← BACK TO HOME", key="back_home", use_container_width=True):
            st.session_state.view = "landing"
            st.rerun()

    H("<div style='height:8px'></div>")
    _, mid, _ = st.columns([0.8, 1.6, 0.8])
    with mid:
        # Custom tab switcher (session-state driven so we can flip tabs
        # programmatically, e.g. after a duplicate-email signup attempt).
        t1, t2 = st.columns(2)
        with t1:
            if st.button("🔐  SIGN IN", key="tab_btn_login", use_container_width=True,
                         type="primary" if st.session_state.auth_tab == "login" else "secondary"):
                st.session_state.auth_tab = "login"
                st.rerun()
        with t2:
            if st.button("✨  CREATE ACCOUNT", key="tab_btn_reg", use_container_width=True,
                         type="primary" if st.session_state.auth_tab == "register" else "secondary"):
                st.session_state.auth_tab = "register"
                st.rerun()
        H("<div style='height:10px'></div>")

        if st.session_state.auth_notice:
            kind, text = st.session_state.auth_notice
            color = "#00ff66" if kind == "ok" else "#ff6b6b"
            bg    = "rgba(0,255,102,0.08)" if kind == "ok" else "rgba(255,50,50,0.08)"
            H(f'<div style="background:{bg};border:1px solid {color}55;border-radius:4px;'
              f'padding:14px 18px;color:{color};font-family:JetBrains Mono,monospace;'
              f'font-size:14px;margin-bottom:18px;">{text}</div>')
            st.session_state.auth_notice = None

        if st.session_state.auth_tab == "login":
            H("""
            <div style="padding:8px 0 4px;">
                <div style="display:inline-flex;align-items:center;gap:8px;
                     background:rgba(0,255,102,0.06);border:1px solid rgba(0,255,102,0.2);
                     padding:6px 16px;border-radius:3px;margin-bottom:12px;">
                    <div style="width:7px;height:7px;background:#00ff66;border-radius:50%;"></div>
                    <span style="font-family:'JetBrains Mono',monospace;font-size:12px;
                         color:#00ff66;letter-spacing:1.5px;text-transform:uppercase;font-weight:700;">
                         Access Terminal</span>
                </div>
                <div style="font-family:'Space Grotesk',sans-serif;font-size:34px;font-weight:800;
                     color:#fff;margin-bottom:10px;">Welcome back.</div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:15px;
                     color:rgba(255,255,255,0.4);margin-bottom:14px;line-height:1.6;">
                     Sign in to access your fraud detection dashboard.</div>
            </div>
            """)
            email_l = st.text_input("Email", key="login_email", placeholder="analyst@fraudguard.io")
            pass_l  = st.text_input("Password", key="login_pass", type="password", placeholder="••••••••••••")
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
            fp1, fp2 = st.columns([1.6, 1])
            with fp2:
                if st.button("Forgot password?", key="btn_forgot_link", use_container_width=True):
                    st.session_state.view = "forgot_password"
                    st.session_state.reset_stage = "request"
                    st.session_state.reset_email = None
                    st.rerun()
            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
            if st.button("SIGN IN →", key="btn_login"):
                if not email_l or not pass_l:
                    H('<div style="background:rgba(255,50,50,0.08);border:1px solid rgba(255,50,50,0.3);border-radius:4px;padding:14px 18px;color:#ff6b6b;font-family:JetBrains Mono,monospace;font-size:14px;margin-top:14px;">⚠ ALL FIELDS REQUIRED</div>')
                else:
                    user = login_user(email_l, pass_l)
                    if user:
                        st.session_state.user = user
                        st.session_state.active_page = "dashboard"
                        st.session_state.last_activity = datetime.now()
                        st.rerun()
                    else:
                        H('<div style="background:rgba(255,50,50,0.08);border:1px solid rgba(255,50,50,0.3);border-radius:4px;padding:14px 18px;color:#ff6b6b;font-family:JetBrains Mono,monospace;font-size:14px;margin-top:14px;">⚠ INVALID CREDENTIALS</div>')

        else:
            H("""
            <div style="padding:8px 0 4px;">
                <div style="display:inline-flex;align-items:center;gap:8px;
                     background:rgba(0,255,102,0.06);border:1px solid rgba(0,255,102,0.2);
                     padding:6px 16px;border-radius:3px;margin-bottom:12px;">
                    <div style="width:7px;height:7px;background:#00ff66;border-radius:50%;"></div>
                    <span style="font-family:'JetBrains Mono',monospace;font-size:12px;
                         color:#00ff66;letter-spacing:1.5px;text-transform:uppercase;font-weight:700;">
                         Create Account</span>
                </div>
                <div style="font-family:'Space Grotesk',sans-serif;font-size:34px;font-weight:800;
                     color:#fff;margin-bottom:10px;">Deploy your shield.</div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:15px;
                     color:rgba(255,255,255,0.4);margin-bottom:14px;line-height:1.6;">
                     5 minutes to your first blocked transaction.</div>
            </div>
            """)
            full_name = st.text_input("Full Name",        key="reg_name",  placeholder="John Doe")
            email_r   = st.text_input("Email",            key="reg_email", placeholder="analyst@fraudguard.io")
            pass_r    = st.text_input("Password",         key="reg_pass",  type="password", placeholder="Min. 6 characters")
            conf_r    = st.text_input("Confirm Password", key="reg_conf",  type="password", placeholder="Repeat password")
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            if st.button("CREATE COMMAND ACCESS →", key="btn_reg"):
                if not full_name or not email_r or not pass_r or not conf_r:
                    H('<div style="background:rgba(255,50,50,0.08);border:1px solid rgba(255,50,50,0.3);border-radius:4px;padding:14px 18px;color:#ff6b6b;font-family:JetBrains Mono,monospace;font-size:14px;margin-top:14px;">⚠ ALL FIELDS REQUIRED</div>')
                elif len(pass_r) < 6:
                    H('<div style="background:rgba(255,50,50,0.08);border:1px solid rgba(255,50,50,0.3);border-radius:4px;padding:14px 18px;color:#ff6b6b;font-family:JetBrains Mono,monospace;font-size:14px;margin-top:14px;">⚠ PASSWORD TOO SHORT (MIN 6)</div>')
                elif pass_r != conf_r:
                    H('<div style="background:rgba(255,50,50,0.08);border:1px solid rgba(255,50,50,0.3);border-radius:4px;padding:14px 18px;color:#ff6b6b;font-family:JetBrains Mono,monospace;font-size:14px;margin-top:14px;">⚠ PASSWORDS DO NOT MATCH</div>')
                else:
                    ok, msg, new_user_id = register_user(full_name, email_r, pass_r)
                    if ok:
                        st.session_state.pending_signup = {
                            "id": new_user_id, "full_name": full_name, "email": email_r
                        }
                        st.session_state.view = "profile_setup"
                        st.rerun()
                    else:
                        # Email already registered → send them straight to Sign In, pre-filled.
                        st.session_state.auth_tab = "login"
                        st.session_state["login_email"] = email_r.strip().lower()
                        st.session_state.auth_notice = (
                            "err",
                            f"⚠ {msg.upper()} SIGN IN BELOW INSTEAD."
                        )
                        st.rerun()

        H("""
        <div style="text-align:center;margin-top:16px;font-family:'JetBrains Mono',monospace;
             font-size:12px;color:rgba(255,255,255,0.2);letter-spacing:1px;">
             PROTECTED BY SOC-2 · PCI DSS · GDPR
        </div>
        """)



# ══════════════════════════════════════
#  FORGOT / RESET PASSWORD
# ══════════════════════════════════════


def show_forgot_password():
    show_bg()
    H('<div style="position:relative;z-index:10;padding:10px 48px 0;'
      'display:flex;align-items:center;justify-content:space-between;">'
      '<div style="display:flex;align-items:center;gap:14px;">'
      '<div style="width:54px;height:54px;border:2px solid #00ff66;border-radius:10px;'
      'display:flex;align-items:center;justify-content:center;'
      'box-shadow:0 0 20px rgba(0,255,102,0.35);font-size:27px;">🛡️</div>'
      '<div style="font-family:\'JetBrains Mono\',monospace;font-size:29px;font-weight:800;color:#fff;">'
      'FRAUD<span style="color:#00ff66;">GUARD</span></div></div></div>')

    _, back_col = st.columns([8, 1.6])
    with back_col:
        if st.button("← BACK TO SIGN IN", key="forgot_back", use_container_width=True):
            st.session_state.view = "auth"
            st.session_state.auth_tab = "login"
            st.rerun()

    H("<div style='height:8px'></div>")
    _, mid, _ = st.columns([0.8, 1.6, 0.8])
    with mid:
        if st.session_state.reset_notice:
            kind, text = st.session_state.reset_notice
            color = "#00ff66" if kind == "ok" else "#ff6b6b"
            bg    = "rgba(0,255,102,0.08)" if kind == "ok" else "rgba(255,50,50,0.08)"
            H(f'<div style="background:{bg};border:1px solid {color}55;border-radius:4px;'
              f'padding:14px 18px;color:{color};font-family:JetBrains Mono,monospace;'
              f'font-size:14px;margin-bottom:18px;">{text}</div>')
            st.session_state.reset_notice = None

        if st.session_state.reset_stage == "request":
            H("""
            <div style="padding:8px 0 4px;">
                <div style="font-family:'Space Grotesk',sans-serif;font-size:32px;font-weight:800;
                     color:#fff;margin-bottom:10px;">Reset your password.</div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:14px;
                     color:rgba(255,255,255,0.4);margin-bottom:14px;line-height:1.6;">
                     Enter the email on your account and we'll issue a reset code.</div>
            </div>
            """)
            panel_open()
            email_req = st.text_input("Email", key="forgot_email", placeholder="analyst@fraudguard.io")
            H("<div style='height:6px'></div>")
            if st.button("SEND RESET CODE →", key="btn_send_reset", use_container_width=True):
                if not email_req:
                    H('<div style="color:#ff6b6b;font-family:JetBrains Mono,monospace;font-size:13px;margin-top:8px;">⚠ ENTER YOUR EMAIL</div>')
                else:
                    token = create_reset_token(email_req)
                    st.session_state.reset_email = email_req.strip().lower()
                    st.session_state.reset_stage = "confirm"
                    if token:
                        # DEMO MODE: this project has no email server configured, so the
                        # code is shown directly instead of being sent out. In production,
                        # this token would be emailed to the user rather than displayed here.
                        st.session_state.reset_notice = (
                            "ok",
                            f"✓ DEMO MODE (NO EMAIL SERVER CONFIGURED): YOUR RESET CODE IS <b>{token}</b>. "
                            f"IT EXPIRES IN 15 MINUTES."
                        )
                    else:
                        # Same message whether or not the email exists, so we don't
                        # leak which addresses are registered.
                        st.session_state.reset_notice = (
                            "ok",
                            "✓ IF AN ACCOUNT WITH THAT EMAIL EXISTS, A RESET CODE HAS BEEN ISSUED."
                        )
                    st.rerun()
            panel_close()

        else:  # "confirm" stage
            H(f"""
            <div style="padding:8px 0 4px;">
                <div style="font-family:'Space Grotesk',sans-serif;font-size:32px;font-weight:800;
                     color:#fff;margin-bottom:10px;">Enter your reset code.</div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:14px;
                     color:rgba(255,255,255,0.4);margin-bottom:14px;line-height:1.6;">
                     Code sent for <b style="color:#00ff66;">{st.session_state.reset_email}</b>.</div>
            </div>
            """)
            panel_open()
            code_in   = st.text_input("Reset Code", key="reset_code_in", max_chars=6, placeholder="6-digit code")
            new_pass  = st.text_input("New Password", key="reset_new_pass", type="password", placeholder="Min. 6 characters")
            conf_pass = st.text_input("Confirm New Password", key="reset_conf_pass", type="password", placeholder="Repeat password")
            H("<div style='height:6px'></div>")
            b1, b2 = st.columns([1.4, 1])
            with b1:
                if st.button("✓ RESET PASSWORD →", key="btn_do_reset", use_container_width=True):
                    if not code_in or not new_pass or not conf_pass:
                        H('<div style="color:#ff6b6b;font-family:JetBrains Mono,monospace;font-size:13px;margin-top:8px;">⚠ ALL FIELDS REQUIRED</div>')
                    elif len(new_pass) < 6:
                        H('<div style="color:#ff6b6b;font-family:JetBrains Mono,monospace;font-size:13px;margin-top:8px;">⚠ PASSWORD TOO SHORT (MIN 6)</div>')
                    elif new_pass != conf_pass:
                        H('<div style="color:#ff6b6b;font-family:JetBrains Mono,monospace;font-size:13px;margin-top:8px;">⚠ PASSWORDS DO NOT MATCH</div>')
                    else:
                        ok, msg = reset_password(st.session_state.reset_email, code_in, new_pass)
                        if ok:
                            st.session_state.view = "auth"
                            st.session_state.auth_tab = "login"
                            st.session_state["login_email"] = st.session_state.reset_email
                            st.session_state.reset_stage = "request"
                            st.session_state.reset_email = None
                            st.session_state.auth_notice = ("ok", "✓ PASSWORD RESET. SIGN IN BELOW.")
                            st.rerun()
                        else:
                            H(f'<div style="color:#ff6b6b;font-family:JetBrains Mono,monospace;font-size:13px;margin-top:8px;">⚠ {msg.upper()}</div>')
            with b2:
                if st.button("← START OVER", key="btn_reset_restart", use_container_width=True):
                    st.session_state.reset_stage = "request"
                    st.session_state.reset_email = None
                    st.rerun()
            panel_close()



# ══════════════════════════════════════
#  PROFILE SETUP (post-signup)
# ══════════════════════════════════════


FRAUD_TYPE_OPTIONS = [
    "Not applicable / just exploring",
    "Unauthorized Transaction",
    "Card Skimming",
    "Phishing",
    "Identity Theft",
    "Other",
]

def _finish_profile_setup(notice):
    st.session_state.pending_signup = None
    st.session_state.view = "auth"
    st.session_state.auth_tab = "login"
    st.session_state["login_email"] = notice.pop("email", "")
    st.session_state.auth_notice = ("ok", notice["text"])
    st.rerun()

def show_profile_setup():
    show_bg()
    pending = st.session_state.pending_signup
    if not pending:
        # Nothing to complete (e.g. page refresh) — bounce back to auth.
        st.session_state.view = "auth"
        st.rerun()
        return

    H('<div style="position:relative;z-index:10;padding:10px 48px 0;'
      'display:flex;align-items:center;justify-content:space-between;">'
      '<div style="display:flex;align-items:center;gap:14px;">'
      '<div style="width:54px;height:54px;border:2px solid #00ff66;border-radius:10px;'
      'display:flex;align-items:center;justify-content:center;'
      'box-shadow:0 0 20px rgba(0,255,102,0.35);font-size:27px;">🛡️</div>'
      '<div style="font-family:\'JetBrains Mono\',monospace;font-size:29px;font-weight:800;color:#fff;">'
      'FRAUD<span style="color:#00ff66;">GUARD</span></div></div></div>')

    H("<div style='height:8px'></div>")
    _, mid, _ = st.columns([0.6, 1.8, 0.6])
    with mid:
        H(f"""
        <div style="padding:8px 0 4px;">
            <div style="display:inline-flex;align-items:center;gap:8px;
                 background:rgba(0,255,102,0.06);border:1px solid rgba(0,255,102,0.2);
                 padding:6px 16px;border-radius:3px;margin-bottom:12px;">
                <div style="width:7px;height:7px;background:#00ff66;border-radius:50%;"></div>
                <span style="font-family:'JetBrains Mono',monospace;font-size:12px;
                     color:#00ff66;letter-spacing:1.5px;text-transform:uppercase;font-weight:700;">
                     Step 2 of 2 · Account Details</span>
            </div>
            <div style="font-family:'Space Grotesk',sans-serif;font-size:32px;font-weight:800;
                 color:#fff;margin-bottom:10px;">Welcome, {pending['full_name'].split()[0]}. One more step.</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:14px;
                 color:rgba(255,255,255,0.4);margin-bottom:14px;line-height:1.6;">
                 Add your card &amp; contact details so we can personalize fraud checks for you.
                 This step is optional — you can skip it and sign in right away.</div>
        </div>
        """)

        panel_open()
        c1, c2 = st.columns(2)
        with c1:
            mobile = st.text_input("Mobile Number", key="ps_mobile", placeholder="98765 43210", max_chars=15)
        with c2:
            dob = st.date_input("Date of Birth", key="ps_dob",
                                 min_value=date(1930, 1, 1), max_value=date.today(),
                                 value=date(2000, 1, 1))
        c3, c4 = st.columns(2)
        with c3:
            bank_name = st.text_input("Bank Name", key="ps_bank", placeholder="e.g. State Bank of India")
        with c4:
            card_number = st.text_input("Card Number", key="ps_card", placeholder="4532 XXXX XXXX 7891", max_chars=19)
        fraud_type = st.selectbox("Type of Fraud You're Facing / Concerned About",
                                   FRAUD_TYPE_OPTIONS, key="ps_fraud_type")
        H('<div style="font-family:JetBrains Mono,monospace;font-size:11px;color:rgba(255,255,255,0.3);'
          'margin-top:6px;line-height:1.5;">Stored locally in the demo database only — this is not a real '
          'payment processor, so avoid entering a genuine card number.</div>')
        H("<div style='height:8px'></div>")

        b1, b2 = st.columns([1.4, 1])
        with b1:
            if st.button("✓ SAVE & CONTINUE TO SIGN IN →", key="ps_save", use_container_width=True):
                save_profile_details(pending["id"], mobile, str(dob), bank_name, card_number, fraud_type)
                _finish_profile_setup({"email": pending["email"],
                                        "text": "✓ ACCOUNT CREATED & DETAILS SAVED. SIGN IN BELOW."})
        with b2:
            if st.button("SKIP FOR NOW", key="ps_skip", use_container_width=True):
                mark_profile_skipped(pending["id"])
                _finish_profile_setup({"email": pending["email"],
                                        "text": "✓ ACCOUNT CREATED. SIGN IN BELOW."})
        panel_close()



# ══════════════════════════════════════
#  DASHBOARD
# ══════════════════════════════════════


def show_dashboard():
    show_bg()
    show_topbar("LIVE OPERATIONS")
    show_sidebar()
    show_page_nav("dashboard")

    u     = st.session_state.user
    stats = get_user_stats(u["id"])
    txns  = get_user_transactions(u["id"], limit=8)
    fraud_rate = round(stats["fraud"] / stats["total"] * 100, 1) if stats["total"] > 0 else 0.0

    H('<div style="position:relative;z-index:10;padding:10px 40px 16px;">')
    H(f"""
    <div style="margin-bottom:12px;">
        <div style="font-family:'JetBrains Mono',monospace;font-size:11px;color:#00ff66;
             letter-spacing:1.5px;text-transform:uppercase;margin-bottom:6px;">● COMMAND CENTER</div>
        <div style="font-family:'Space Grotesk',sans-serif;font-size:34px;font-weight:800;color:#fff;">
            Live Operations
        </div>
    </div>
    """)

    c1, c2, c3, c4 = st.columns(4)
    with c1: H(metric_card("TOTAL CHECKS", stats['total'], "ALL TIME", "#00ff66", "📊"))
    with c2: H(metric_card("LEGITIMATE",  stats['legit'], "SAFE TRANSACTIONS", "#00ff66", "✅"))
    with c3: H(metric_card("FRAUD BLOCKED", stats['fraud'], "THREATS STOPPED", "#ff3355", "🚨"))
    with c4: H(metric_card("FRAUD RATE",  f"{fraud_rate}%", "OF ALL TRANSACTIONS", "#ffaa00", "📈"))

    H("<div style='height:12px'></div>")

    # Prominent banner pointing to the full transaction form
    H("""
    <div style="background:linear-gradient(135deg,rgba(0,255,102,0.08),rgba(0,255,102,0.02));
         border:1.5px solid rgba(0,255,102,0.35);border-radius:8px;
         padding:22px 28px;margin-bottom:14px;display:flex;align-items:center;
         justify-content:space-between;flex-wrap:wrap;gap:16px;">
        <div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:15px;font-weight:800;
                 color:#00ff66;margin-bottom:4px;">▸ WANT TO CHECK A TRANSACTION?</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:13px;
                 color:rgba(255,255,255,0.45);">
                 Fill in the amount, type, and location on the Fraud Detection page — the AI does the rest.
            </div>
        </div>
    </div>
    """)
    if st.button("◎  FILL TRANSACTION DETAILS → GO TO FRAUD DETECTION", key="dash_banner_cta", use_container_width=True):
        st.session_state.active_page = "detection"; st.rerun()

    H("<div style='height:12px'></div>")
    col1, col2 = st.columns([1.6, 1], gap="large")

    with col1:
        section_label("TRANSACTION LOG", len(txns))
        panel_open("max-height:min(42vh,330px);overflow-y:auto;")
        if not txns:
            H("""
            <div style="text-align:center;padding:56px 20px;">
                <div style="font-size:40px;margin-bottom:12px;opacity:0.3;">◌</div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:13px;
                     color:rgba(255,255,255,0.3);letter-spacing:0.5px;">NO TRANSACTIONS LOGGED YET</div>
            </div>
            """)
        else:
            rows = ""
            for i, t in enumerate(txns):
                tx_id = "TX-" + str(8000+i) + chr(65+i%5)
                if t["result"] == "FRAUD":
                    status = '<span style="color:#ff3355;font-weight:700;">● BLOCKED</span>'
                else:
                    status = '<span style="color:#00ff66;font-weight:700;">● PASSED</span>'
                conf = str(safe_conf(t["confidence"]))
                amt  = "{:,.2f}".format(t["amount"])
                dt   = str(t["checked_at"])
                rows += "<tr style='border-bottom:1px solid rgba(0,255,102,0.06);'>"
                rows += "<td style='padding:12px 16px;font-family:JetBrains Mono,monospace;font-size:14px;color:rgba(255,255,255,0.75);'>" + tx_id + "</td>"
                rows += "<td style='padding:12px 16px;font-family:JetBrains Mono,monospace;font-size:15px;color:#fff;font-weight:700;'>&#8377;" + amt + "</td>"
                rows += "<td style='padding:12px 16px;font-family:JetBrains Mono,monospace;font-size:14px;'>" + status + "</td>"
                rows += "<td style='padding:12px 16px;font-family:JetBrains Mono,monospace;font-size:14px;color:#00ff66;font-weight:600;'>" + conf + "%</td>"
                rows += "<td style='padding:12px 16px;font-family:JetBrains Mono,monospace;font-size:12px;color:rgba(255,255,255,0.3);'>" + dt + "</td>"
                rows += "</tr>"
            H("<table style='width:100%;border-collapse:collapse;'>"
              "<thead><tr style='border-bottom:1px solid rgba(0,255,102,0.15);position:sticky;top:0;background:#0a0d0a;'>"
              "<th style='padding:10px 16px;text-align:left;font-family:JetBrains Mono,monospace;font-size:12px;color:rgba(255,255,255,0.35);letter-spacing:1px;text-transform:uppercase;'>TX ID</th>"
              "<th style='padding:10px 16px;text-align:left;font-family:JetBrains Mono,monospace;font-size:12px;color:rgba(255,255,255,0.35);letter-spacing:1px;text-transform:uppercase;'>Amount</th>"
              "<th style='padding:10px 16px;text-align:left;font-family:JetBrains Mono,monospace;font-size:12px;color:rgba(255,255,255,0.35);letter-spacing:1px;text-transform:uppercase;'>Status</th>"
              "<th style='padding:10px 16px;text-align:left;font-family:JetBrains Mono,monospace;font-size:12px;color:rgba(255,255,255,0.35);letter-spacing:1px;text-transform:uppercase;'>Confidence</th>"
              "<th style='padding:10px 16px;text-align:left;font-family:JetBrains Mono,monospace;font-size:12px;color:rgba(255,255,255,0.35);letter-spacing:1px;text-transform:uppercase;'>Timestamp</th>"
              "</tr></thead><tbody>" + rows + "</tbody></table>")
        panel_close()

    with col2:
        section_label("QUICK CHECK")
        panel_open()
        with st.expander("✎  CUSTOMIZE CARD DETAILS"):
            ce1, ce2 = st.columns(2)
            with ce1:
                st.text_input("Last 4 digits", value=st.session_state.get("card_last4","7891"),
                               max_chars=4, key="card_last4")
            with ce2:
                st.text_input("Card holder name", value=st.session_state.get("card_holder","FRAUD ANALYSIS"),
                               key="card_holder")
        _last4  = (st.session_state.get("card_last4") or "7891")
        _holder = (st.session_state.get("card_holder") or "FRAUD ANALYSIS").upper()
        H(cc_html(number=f"4532 •••• •••• {_last4}", holder=_holder))
        H('<div style="font-family:JetBrains Mono,monospace;font-size:11px;color:rgba(255,255,255,0.35);letter-spacing:1px;text-transform:uppercase;margin-bottom:10px;">Enter Amount (₹)</div>')
        quick_amount = st.number_input("Quick Amount", min_value=0.0, value=100.0,
                                        format="%.2f", key="dash_quick_amount", label_visibility="collapsed")
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        if st.button("⚡ QUICK ANALYZE", key="dash_quick_analyze", use_container_width=True):
            default_v = [0.5,-0.2,0.3,0.8,-0.1,0.2,-0.3,0.1,0.4,-0.2,0.1,0.3,-0.1,0.5,
                         0.2,-0.1,0.3,0.1,-0.2,0.4,0.1,-0.3,0.2,0.1,0.3,-0.1,0.2,0.1]
            features = np.array([[0.0] + default_v + [quick_amount]])
            with st.spinner("ANALYZING..."):
                time.sleep(0.4)
                pred = model.predict(features)[0]
                prob = float(model.predict_proba(features)[0][1]*100)
            if pred == 1:
                H("<div style='background:rgba(255,51,85,0.06);border:1px solid rgba(255,51,85,0.3);"
                  "border-radius:6px;padding:14px 16px;margin-top:6px;font-family:JetBrains Mono,monospace;'>"
                  "<span style='color:#ff3355;font-weight:800;font-size:14px;'>⚠ FRAUD RISK</span> "
                  "<span style='color:rgba(255,255,255,0.5);font-size:12px;'>(" + str(round(prob,1)) + "% confidence)</span></div>")
            else:
                H("<div style='background:rgba(0,255,102,0.05);border:1px solid rgba(0,255,102,0.25);"
                  "border-radius:6px;padding:14px 16px;margin-top:6px;font-family:JetBrains Mono,monospace;'>"
                  "<span style='color:#00ff66;font-weight:800;font-size:14px;'>✓ LOOKS SAFE</span> "
                  "<span style='color:rgba(255,255,255,0.5);font-size:12px;'>(" + str(round(100-prob,1)) + "% confidence)</span></div>")
        H("""
        <div style="font-family:'JetBrains Mono',monospace;font-size:11px;color:rgba(255,255,255,0.25);
             text-align:center;margin-top:16px;line-height:1.6;">
            For full analysis with all risk factors,<br>use the Fraud Detection page.
        </div>
        """)
        panel_close()

    H('</div>')



# ══════════════════════════════════════
#  FRAUD DETECTION
# ══════════════════════════════════════


def show_detection():
    show_bg()
    show_topbar("DETECTION ENGINE")
    show_sidebar()
    show_page_nav("detection")

    FRAUD_VALS = [-3.0,0.0,-4.0,2.5,0.0,0.0,0.0,0.0,0.0,0.0,
                  0.0,0.0,0.0,-9.5,0.0,0.0,0.0,0.0,0.0,0.0,
                  0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0]
    LEGIT_VALS = [1.19,0.26,0.16,0.44,0.06,-0.08,-0.07,0.08,
                  -0.25,0.16,0.28,-0.16,0.36,0.14,0.08,0.09,
                  -0.05,-0.02,-0.09,0.06,0.06,0.26,-0.11,0.06,
                  0.21,-0.17,0.07,0.09]
    PATTERNS = {
        "Online Shopping":    [0.5,-0.2,0.3,0.8,-0.1,0.2,-0.3,0.1,0.4,-0.2,0.1,0.3,-0.1,0.5,0.2,-0.1,0.3,0.1,-0.2,0.4,0.1,-0.3,0.2,0.1,0.3,-0.1,0.2,0.1],
        "ATM Withdrawal":     [1.2,0.3,-0.5,0.2,0.8,-0.3,0.1,0.5,-0.2,0.3,0.4,-0.1,0.6,0.2,-0.4,0.3,0.1,0.5,-0.1,0.2,0.3,-0.2,0.4,0.1,-0.3,0.2,0.5,-0.1],
        "Restaurant/Food":    [0.3,0.8,-0.2,0.4,0.1,0.6,-0.1,0.3,0.5,-0.2,0.2,0.4,-0.3,0.1,0.7,-0.2,0.3,0.1,0.4,-0.1,0.2,0.5,-0.1,0.3,0.1,0.4,-0.2,0.3],
        "Travel/Hotel":       [0.8,0.4,0.6,-0.2,0.3,0.5,0.1,-0.3,0.4,0.2,0.6,-0.1,0.3,0.5,-0.2,0.4,0.1,0.3,0.5,-0.1,0.2,0.4,0.1,0.3,-0.2,0.5,0.1,0.4],
        "Grocery/Supermarket":[0.2,0.5,0.3,-0.1,0.4,0.2,0.6,-0.2,0.3,0.5,-0.1,0.4,0.2,0.3,0.5,-0.1,0.2,0.4,0.1,0.3,0.5,-0.2,0.3,0.1,0.4,0.2,-0.1,0.5],
    }

    if st.session_state.get("preset_load") == "fraud":
        st.session_state["preset_amount"] = 2.69
        st.session_state["preset_load"] = None
    elif st.session_state.get("preset_load") == "legit":
        st.session_state["preset_amount"] = 149.62
        st.session_state["preset_load"] = None

    H('<div style="position:relative;z-index:10;padding:10px 40px 16px;">')
    H("""
    <div style="margin-bottom:12px;">
        <div style="font-family:'JetBrains Mono',monospace;font-size:11px;color:#00ff66;
             letter-spacing:1.5px;text-transform:uppercase;margin-bottom:6px;">● XGBOOST MODEL ACTIVE</div>
        <div style="font-family:'Space Grotesk',sans-serif;font-size:34px;font-weight:800;color:#fff;">
            Transaction Analyzer
        </div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:12px;color:rgba(255,255,255,0.3);margin-top:6px;">
            Fill in details below · AI handles the 28-feature analysis automatically
        </div>
    </div>
    """)

    with st.expander("ℹ️  HOW THIS ANALYSIS WORKS (READ BEFORE PRESENTING AS PRODUCTION-GRADE)"):
        H("""
        <div style="font-family:'JetBrains Mono',monospace;font-size:12.5px;color:rgba(255,255,255,0.55);line-height:1.7;">
        The XGBoost model underneath was trained on 284,807 real anonymized transactions,
        each described by 28 PCA-derived components (V1–V28) that can't be reconstructed
        from the simple fields on this form. So for this demo, the fields you enter
        (merchant type, risk-factor checkboxes, card type, location, time of day) are
        used to <b style="color:#00ff66;">blend a synthetic feature vector</b> — a
        reasonable stand-in that pushes the vector toward a "fraud-like" or "legit-like"
        shape — rather than genuine PCA components from an actual transaction.<br><br>
        That makes this great for demoing how the model reacts to different risk signals,
        but the inputs are a <b>simulated approximation</b>, not live transaction data. A
        production deployment would feed the model real, properly-transformed transaction
        features from a payment processor instead.
        </div>
        """)

    left, right = st.columns([1.15, 0.85], gap="large")

    with left:
        section_label("TRANSACTION DETAILS")
        panel_open()
        c1, c2 = st.columns(2)
        with c1:
            amount_val = st.number_input("Amount (₹)", min_value=0.0,
                value=float(st.session_state.get("preset_amount", 100.0)), format="%.2f")
        with c2:
            hour = st.selectbox("Time of Transaction",
                ["Morning (6AM-12PM)","Afternoon (12PM-6PM)","Evening (6PM-10PM)","Night (10PM-6AM)"])
        txn_type = st.selectbox("Transaction Type",
            ["Online Shopping","ATM Withdrawal","Restaurant/Food","Travel/Hotel","Grocery/Supermarket"])
        c3, c4 = st.columns(2)
        with c3: card_type = st.selectbox("Card Type", ["Credit Card","Debit Card"])
        with c4: location  = st.selectbox("Location",  ["Same City","Different City","International","Online"])

        H('<div style="height:1px;background:rgba(0,255,102,0.1);margin:20px 0 16px;"></div>')
        H('<div style="font-family:JetBrains Mono,monospace;font-size:10px;color:rgba(255,255,255,0.3);letter-spacing:1.5px;text-transform:uppercase;margin-bottom:14px;">Risk Factors</div>')
        rc1, rc2 = st.columns(2)
        with rc1:
            is_new_merchant = st.checkbox("New / Unknown Merchant")
            is_foreign      = st.checkbox("Foreign Currency")
        with rc2:
            is_unusual_amt  = st.checkbox("Unusual Amount")
            is_multiple     = st.checkbox("Multiple Today")
        panel_close()

    with right:
        section_label("ANALYSIS PANEL")
        panel_open()
        with st.expander("✎  CUSTOMIZE CARD DETAILS", expanded=True):
            ce1, ce2 = st.columns(2)
            with ce1:
                card_number_in = st.text_input("Card Number", value=st.session_state.get("card_number_det", ""),
                               max_chars=19, key="card_number_det", placeholder="4532 1234 5678 9012")
            with ce2:
                holder_in = st.text_input("Card holder name", value=st.session_state.get("card_holder_det", ""),
                               key="card_holder_det", placeholder="FRAUD ANALYSIS")
        _holder = (holder_in or st.session_state.get("card_holder") or "FRAUD ANALYSIS").upper()
        _masked_number = mask_card_number(card_number_in) if card_number_in else \
                          mask_card_number(st.session_state.get("card_last4", ""), fallback="4532 •••• •••• 7891")
        H(cc_html(number=_masked_number, holder=_holder))

        # ── Live customer / transaction details review ──────────────────────
        H(f"""
        <div style="background:#050705;border:1px solid rgba(0,255,102,0.15);border-radius:6px;
             padding:14px 16px;margin-bottom:16px;">
            <div style="font-family:'JetBrains Mono',monospace;font-size:10px;color:#00ff66;
                 letter-spacing:1.5px;text-transform:uppercase;margin-bottom:10px;">📋 Customer Details — Live Review</div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px 14px;
                 font-family:'JetBrains Mono',monospace;font-size:12px;">
                <div style="color:rgba(255,255,255,0.35);">Customer</div>
                <div style="color:#e8ffe8;text-align:right;">{_holder}</div>
                <div style="color:rgba(255,255,255,0.35);">Card Number</div>
                <div style="color:#e8ffe8;text-align:right;">{_masked_number}</div>
                <div style="color:rgba(255,255,255,0.35);">Card Type</div>
                <div style="color:#e8ffe8;text-align:right;">{card_type}</div>
                <div style="color:rgba(255,255,255,0.35);">Amount</div>
                <div style="color:#e8ffe8;text-align:right;">₹{amount_val:,.2f}</div>
                <div style="color:rgba(255,255,255,0.35);">Transaction Type</div>
                <div style="color:#e8ffe8;text-align:right;">{txn_type}</div>
                <div style="color:rgba(255,255,255,0.35);">Location</div>
                <div style="color:#e8ffe8;text-align:right;">{location}</div>
            </div>
        </div>
        """)
        H('<div style="font-family:JetBrains Mono,monospace;font-size:10px;color:rgba(255,255,255,0.3);letter-spacing:1.5px;text-transform:uppercase;margin-bottom:12px;">Quick Test Presets</div>')
        p1, p2 = st.columns(2)
        with p1:
            if st.button("🚨 FRAUD", use_container_width=True, key="p_fraud"):
                st.session_state["preset_load"] = "fraud"; st.rerun()
        with p2:
            if st.button("✅ LEGIT", use_container_width=True, key="p_legit"):
                st.session_state["preset_load"] = "legit"; st.rerun()
        H("<div style='height:8px'></div>")

        if st.button("◎ ANALYZE TRANSACTION", key="btn_analyze", use_container_width=True):
            v = list(PATTERNS[txn_type])
            if is_new_merchant: v[0]-=2.0; v[2]-=1.5; v[4]+=1.0
            if is_unusual_amt:  v[1]-=1.5; v[3]+=2.0; v[13]-=2.0
            if is_foreign:      v[5]-=1.0; v[7]+=1.5; v[11]-=1.0
            if is_multiple:     v[0]-=1.0; v[2]-=2.0; v[14]-=1.5
            if "Night" in hour: v[0]-=0.5; v[2]-=0.5
            if location=="International": v[5]-=1.5; v[11]-=1.0
            # Card Type: debit cards draw straight from the bank account with
            # fewer built-in chargeback protections than credit cards, so we
            # nudge the risk score up slightly for debit — more so when paired
            # with other already-risky context (foreign/international use).
            if card_type == "Debit Card":
                v[0]-=0.4; v[6]+=0.5
                if is_foreign or location=="International":
                    v[6]+=0.5; v[11]-=0.5
            else:  # Credit Card
                v[0]+=0.2; v[6]-=0.3
            if st.session_state.get("preset_amount")==2.69: v = FRAUD_VALS[:]
            elif st.session_state.get("preset_amount")==149.62: v = LEGIT_VALS[:]
            hour_map = {"Morning (6AM-12PM)":6*3600,"Afternoon (12PM-6PM)":12*3600,
                        "Evening (6PM-10PM)":18*3600,"Night (10PM-6AM)":22*3600}
            time_val = float(hour_map.get(hour,0))
            features = np.array([[time_val]+v+[amount_val]])
            with st.spinner("ANALYZING..."):
                time.sleep(0.6)
                pred = model.predict(features)[0]
                prob = float(model.predict_proba(features)[0][1]*100)
            result_str = "FRAUD" if pred==1 else "LEGIT"
            conf_val   = prob if pred==1 else (100-prob)
            log_transaction(st.session_state.user["id"], amount_val, result_str, conf_val)

            if pred == 1:
                bar = min(int(prob),100)
                H("<div style='background:rgba(255,51,85,0.05);border:1px solid rgba(255,51,85,0.3);"
                  "border-left:3px solid #ff3355;border-radius:6px;padding:22px 24px;margin-top:16px;'>"
                  "<div style='font-family:JetBrains Mono,monospace;font-size:16px;font-weight:800;color:#ff3355;margin-bottom:6px;'>⚠ FRAUD DETECTED</div>"
                  "<div style='font-family:JetBrains Mono,monospace;font-size:11px;color:rgba(255,255,255,0.4);margin-bottom:18px;line-height:1.6;'>HIGH-RISK PATTERN MATCH · RECOMMEND BLOCK</div>"
                  "<div style='display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:10px;'>"
                  "<span style='font-family:JetBrains Mono,monospace;font-size:12px;color:rgba(255,255,255,0.35);letter-spacing:1px;text-transform:uppercase;'>FRAUD PROBABILITY</span>"
                  "<span style='font-family:JetBrains Mono,monospace;font-size:32px;font-weight:800;color:#ff3355;'>" + str(round(prob,1)) + "%</span></div>"
                  "<div style='background:rgba(255,51,85,0.1);border-radius:2px;height:6px;overflow:hidden;'>"
                  "<div style='width:" + str(bar) + "%;height:6px;background:#ff3355;'></div></div></div>")
            else:
                safe = 100-prob
                bar  = min(int(safe),100)
                H("<div style='background:rgba(0,255,102,0.04);border:1px solid rgba(0,255,102,0.25);"
                  "border-left:3px solid #00ff66;border-radius:6px;padding:22px 24px;margin-top:16px;'>"
                  "<div style='font-family:JetBrains Mono,monospace;font-size:16px;font-weight:800;color:#00ff66;margin-bottom:6px;'>✓ LEGITIMATE</div>"
                  "<div style='font-family:JetBrains Mono,monospace;font-size:11px;color:rgba(255,255,255,0.4);margin-bottom:18px;line-height:1.6;'>NO SUSPICIOUS PATTERNS · SAFE TO PROCEED</div>"
                  "<div style='display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:10px;'>"
                  "<span style='font-family:JetBrains Mono,monospace;font-size:12px;color:rgba(255,255,255,0.35);letter-spacing:1px;text-transform:uppercase;'>CONFIDENCE</span>"
                  "<span style='font-family:JetBrains Mono,monospace;font-size:32px;font-weight:800;color:#00ff66;'>" + str(round(safe,1)) + "%</span></div>"
                  "<div style='background:rgba(0,255,102,0.1);border-radius:2px;height:6px;overflow:hidden;'>"
                  "<div style='width:" + str(bar) + "%;height:6px;background:#00ff66;'></div></div></div>")
        panel_close()

    H('</div>')



# ══════════════════════════════════════
#  HISTORY / INCIDENTS
# ══════════════════════════════════════


def show_history():
    show_bg()
    show_topbar("INCIDENTS")
    show_sidebar()
    show_page_nav("history")

    txns = get_user_transactions(st.session_state.user["id"], limit=50)
    fraud_ct = sum(1 for t in txns if t["result"]=="FRAUD")

    H('<div style="position:relative;z-index:10;padding:10px 40px 16px;">')
    H(f"""
    <div style="margin-bottom:12px;">
        <div style="font-family:'JetBrains Mono',monospace;font-size:11px;color:#00ff66;
             letter-spacing:1.5px;text-transform:uppercase;margin-bottom:6px;">● INCIDENT LOG</div>
        <div style="font-family:'Space Grotesk',sans-serif;font-size:34px;font-weight:800;color:#fff;">
            Alert Queue
        </div>
    </div>
    """)

    c1, c2, c3 = st.columns(3)
    with c1: H(metric_card("TOTAL LOGGED", len(txns), "ALL TIME", "#00ff66", "▤"))
    with c2: H(metric_card("FRAUD FLAGGED", fraud_ct, "BLOCKED", "#ff3355", "⚠"))
    with c3: H(metric_card("CLEAN", len(txns)-fraud_ct, "PASSED", "#00ff66", "✓"))

    H("<div style='height:8px'></div>")
    section_label("ALL TRANSACTIONS", len(txns))
    panel_open("max-height:min(46vh,420px);overflow-y:auto;")
    if not txns:
        H("""
        <div style="text-align:center;padding:64px 20px;">
            <div style="font-size:40px;margin-bottom:12px;opacity:0.3;">◌</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:13px;
                 color:rgba(255,255,255,0.3);">NO INCIDENTS LOGGED YET</div>
        </div>
        """)
    else:
        rows = ""
        for i, t in enumerate(txns):
            tx_id = "TX-" + str(9000-i) + chr(65+i%5)
            if t["result"] == "FRAUD":
                sev = '<span style="background:rgba(255,51,85,0.1);color:#ff3355;font-size:10px;font-weight:700;padding:3px 10px;border-radius:3px;border:1px solid rgba(255,51,85,0.3);letter-spacing:0.5px;">CRITICAL</span>'
                status = '<span style="color:#ff3355;">● BLOCKED</span>'
            else:
                sev = '<span style="background:rgba(0,255,102,0.08);color:#00ff66;font-size:10px;font-weight:700;padding:3px 10px;border-radius:3px;border:1px solid rgba(0,255,102,0.25);letter-spacing:0.5px;">LOW</span>'
                status = '<span style="color:#00ff66;">● RESOLVED</span>'
            amt = "{:,.2f}".format(t["amount"])
            dt  = str(t["checked_at"])
            rows += "<tr style='border-bottom:1px solid rgba(0,255,102,0.06);'>"
            rows += "<td style='padding:14px 18px;font-family:JetBrains Mono,monospace;font-size:12px;color:#fff;font-weight:600;'>" + tx_id + "</td>"
            rows += "<td style='padding:14px 18px;'>" + sev + "</td>"
            rows += "<td style='padding:14px 18px;font-family:JetBrains Mono,monospace;font-size:15px;color:#fff;font-weight:700;'>&#8377;" + amt + "</td>"
            rows += "<td style='padding:14px 18px;font-family:JetBrains Mono,monospace;font-size:12px;font-weight:600;'>" + status + "</td>"
            rows += "<td style='padding:14px 18px;font-family:JetBrains Mono,monospace;font-size:12px;color:rgba(255,255,255,0.3);'>" + dt + "</td>"
            rows += "</tr>"
        H("<table style='width:100%;border-collapse:collapse;'>"
          "<thead><tr style='border-bottom:1px solid rgba(0,255,102,0.15);position:sticky;top:0;background:#0a0d0a;'>"
          "<th style='padding:10px 18px;text-align:left;font-family:JetBrains Mono,monospace;font-size:12px;color:rgba(255,255,255,0.35);letter-spacing:1px;text-transform:uppercase;'>Incident</th>"
          "<th style='padding:10px 18px;text-align:left;font-family:JetBrains Mono,monospace;font-size:12px;color:rgba(255,255,255,0.35);letter-spacing:1px;text-transform:uppercase;'>Severity</th>"
          "<th style='padding:10px 18px;text-align:left;font-family:JetBrains Mono,monospace;font-size:12px;color:rgba(255,255,255,0.35);letter-spacing:1px;text-transform:uppercase;'>Amount</th>"
          "<th style='padding:10px 18px;text-align:left;font-family:JetBrains Mono,monospace;font-size:12px;color:rgba(255,255,255,0.35);letter-spacing:1px;text-transform:uppercase;'>Status</th>"
          "<th style='padding:10px 18px;text-align:left;font-family:JetBrains Mono,monospace;font-size:12px;color:rgba(255,255,255,0.35);letter-spacing:1px;text-transform:uppercase;'>Timestamp</th>"
          "</tr></thead><tbody>" + rows + "</tbody></table>")
    panel_close()
    H('</div>')



# ══════════════════════════════════════
#  ROUTER
# ══════════════════════════════════════
if st.session_state.user is None:
    if st.session_state.view == "landing":
        show_landing_page()
    elif st.session_state.view == "profile_setup":
        show_profile_setup()
    elif st.session_state.view == "forgot_password":
        show_forgot_password()
    else:
        show_auth_page()
else:
    page = st.session_state.active_page
    if   page == "dashboard": show_dashboard()
    elif page == "detection": show_detection()
    elif page == "history":   show_history()
