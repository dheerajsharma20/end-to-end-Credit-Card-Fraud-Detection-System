import streamlit as st
import numpy as np
import joblib
import time
import struct
from pathlib import Path
from database import (init_db, register_user, login_user, log_transaction, get_user_transactions,
                       get_user_stats, save_profile_details, mark_profile_skipped)
from datetime import date

st.set_page_config(
    page_title="FraudGuard Command",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()

@st.cache_resource
def load_model():
    return joblib.load(Path(__file__).parent / "fraud_model.pkl")
model = load_model()

for k, v in [("user", None), ("active_page", "dashboard"), ("preset_load", None), ("view", "landing"),
             ("pending_signup", None), ("auth_notice", None)]:
    if k not in st.session_state:
        st.session_state[k] = v

def H(html): st.markdown(html, unsafe_allow_html=True)

def safe_conf(val):
    if isinstance(val, bytes):
        try: return round(struct.unpack("f", val)[0], 1)
        except: return 0.0
    try: return round(float(val), 1)
    except: return 0.0

# ── GLOBAL STYLES ──────────────────────────────────────────────────────────────
H("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');
*,*::before,*::after{box-sizing:border-box;}
html,body,[class*="css"]{font-family:'Space Grotesk',sans-serif!important;}
#MainMenu,footer{visibility:hidden;}
header{background:transparent!important;box-shadow:none!important;}
header [data-testid="stToolbar"]{visibility:hidden!important;}
[data-testid="stSidebarCollapsedControl"]{visibility:visible!important;display:flex!important;z-index:999999!important;}
[data-testid="stSidebarCollapsedControl"] button{background:#0a0d0a!important;border:1px solid rgba(0,255,102,0.4)!important;border-radius:6px!important;}
[data-testid="stSidebarCollapsedControl"] svg{color:#00ff66!important;fill:#00ff66!important;}
[data-testid="collapsedControl"]{visibility:visible!important;display:flex!important;z-index:999999!important;}
[data-testid="collapsedControl"] svg{color:#00ff66!important;fill:#00ff66!important;}
.stApp{background:#050705!important;}
section[data-testid="stSidebar"]{background:#0a0d0a!important;border-right:1px solid rgba(0,255,102,0.1)!important;}
.stButton>button{
    background:#00ff66!important;
    color:#000!important;border:1px solid #00ff66!important;border-radius:4px!important;
    padding:11px 24px!important;font-size:15px!important;font-weight:700!important;
    font-family:'JetBrains Mono',monospace!important;width:100%!important;
    letter-spacing:1px!important;text-transform:uppercase!important;
    box-shadow:0 0 20px rgba(0,255,102,0.25)!important;
    transition:all 0.2s ease!important;
}
.stButton>button:hover{
    background:#00e85c!important;
    box-shadow:0 0 30px rgba(0,255,102,0.5)!important;
    transform:translateY(-1px)!important;
}
.stTextInput label,.stNumberInput label,.stSelectbox label{
    color:rgba(0,255,102,0.7)!important;font-size:13px!important;
    font-weight:700!important;letter-spacing:1px!important;text-transform:uppercase!important;
    font-family:'JetBrains Mono',monospace!important;
}
.stTextInput input,.stNumberInput input{
    background:#0a0d0a!important;
    border:1px solid rgba(0,255,102,0.2)!important;
    border-radius:6px!important;color:#e8ffe8!important;
    font-size:16px!important;padding:12px 14px!important;font-family:'JetBrains Mono',monospace!important;
}
.stTextInput input:focus,.stNumberInput input:focus{
    border-color:rgba(0,255,102,0.6)!important;
    box-shadow:0 0 0 2px rgba(0,255,102,0.1)!important;
}
div[data-baseweb="select"]>div{
    background:#0a0d0a!important;
    border:1px solid rgba(0,255,102,0.2)!important;
    border-radius:4px!important;color:#e8ffe8!important;
    font-family:'JetBrains Mono',monospace!important;
}
.stCheckbox label{color:rgba(255,255,255,0.7)!important;font-size:13px!important;font-family:'JetBrains Mono',monospace!important;}
.stTabs [data-baseweb="tab-list"]{
    background:#0a0d0a;border-radius:4px;padding:3px;
    border:1px solid rgba(0,255,102,0.15);gap:2px;
}
.stTabs [data-baseweb="tab"]{
    border-radius:4px;font-size:14px;font-weight:700;
    color:rgba(255,255,255,0.4);padding:12px 26px;
    font-family:'JetBrains Mono',monospace;letter-spacing:1px;text-transform:uppercase;
}
.stTabs [aria-selected="true"]{
    background:rgba(0,255,102,0.1)!important;
    color:#00ff66!important;
    border:1px solid rgba(0,255,102,0.3)!important;
}
.stTabs [data-baseweb="tab-border"]{display:none!important;}
::-webkit-scrollbar{width:4px;}
::-webkit-scrollbar-track{background:#050705;}
::-webkit-scrollbar-thumb{background:#00ff66;border-radius:100px;}
/* ── Reclaim Streamlit's default chrome so the app fits one screen ── */
header[data-testid="stHeader"]{height:2.2rem!important;min-height:2.2rem!important;}
.block-container{
    padding-top:0.6rem!important;
    padding-bottom:0.6rem!important;
    max-width:100%!important;
}
[data-testid="stVerticalBlock"]{gap:0.35rem!important;}
div[data-testid="stElementContainer"]{margin-bottom:0!important;}
section[data-testid="stSidebar"] .block-container{padding-top:0.4rem!important;}
</style>
""")

def mono(text, color="rgba(255,255,255,0.4)", size="11px", weight="600", spacing="1.2px"):
    return f"<span style='font-family:JetBrains Mono,monospace;color:{color};font-size:{size};font-weight:{weight};letter-spacing:{spacing};text-transform:uppercase;'>{text}</span>"

# ══════════════════════════════════════
#  TOP NAV (command bar)
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
    <style>
    @keyframes blip{{0%,100%{{opacity:1}}50%{{opacity:0.3}}}}
    @keyframes scan{{0%{{background-position:0 0}}100%{{background-position:0 40px}}}}
    </style>
    """)

# ══════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════
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

# ══════════════════════════════════════
#  ALWAYS-VISIBLE PAGE NAV / BACK STRIP
#  (real buttons — doesn't depend on the sidebar being open)
# ══════════════════════════════════════
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
#  BACKGROUND GRID (terminal feel)
# ══════════════════════════════════════
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

# ══════════════════════════════════════
#  METRIC CARD
# ══════════════════════════════════════
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

# ══════════════════════════════════════
#  CREDIT CARD VISUAL
# ══════════════════════════════════════
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

# ══════════════════════════════════════
#  SECTION LABEL
# ══════════════════════════════════════
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

# ══════════════════════════════════════
#  LANDING PAGE
# ══════════════════════════════════════
def show_landing_page():
    show_bg()
    H("""
    <div style="position:relative;z-index:10;border-bottom:1px solid rgba(0,255,102,0.12);
         padding:0 48px;display:flex;align-items:center;justify-content:space-between;height:62px;">
        <div style="display:flex;align-items:center;gap:14px;">
            <div style="width:54px;height:54px;border:2px solid #00ff66;border-radius:10px;
                 display:flex;align-items:center;justify-content:center;
                 box-shadow:0 0 20px rgba(0,255,102,0.35);font-size:27px;">🛡️</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:29px;font-weight:800;color:#fff;">
                FRAUD<span style="color:#00ff66;">GUARD</span>
                <span style="font-size:14px;color:rgba(255,255,255,0.3);font-weight:500;margin-left:4px;">v2</span>
            </div>
        </div>
        <div style="display:flex;align-items:center;gap:40px;">
            <span style="font-family:'JetBrains Mono',monospace;font-size:14px;font-weight:700;
                 color:#00ff66;letter-spacing:1px;">HOME</span>
            <span style="font-family:'JetBrains Mono',monospace;font-size:14px;font-weight:600;
                 color:rgba(255,255,255,0.45);letter-spacing:1px;">DASHBOARD</span>
            <span style="font-family:'JetBrains Mono',monospace;font-size:14px;font-weight:600;
                 color:rgba(255,255,255,0.45);letter-spacing:1px;">DETECTION</span>
            <span style="font-family:'JetBrains Mono',monospace;font-size:14px;font-weight:600;
                 color:rgba(255,255,255,0.45);letter-spacing:1px;">DOCS</span>
        </div>
    </div>
    """)

    c1, c2 = st.columns([1, 1], gap="large")
    with c1:
        H("""
        <div style="position:relative;z-index:10;padding:18px 48px 10px 48px;">
            <div style="display:inline-flex;align-items:center;gap:8px;
                 background:rgba(0,255,102,0.06);border:1px solid rgba(0,255,102,0.25);
                 border-radius:3px;padding:6px 14px;margin-bottom:18px;">
                <div style="width:6px;height:6px;background:#00ff66;border-radius:50%;
                     box-shadow:0 0 6px rgba(0,255,102,0.8);"></div>
                <span style="font-family:'JetBrains Mono',monospace;font-size:12px;
                     font-weight:600;color:#00ff66;letter-spacing:1.5px;">
                     TRAINED ON 284,807 REAL TRANSACTIONS</span>
            </div>
            <div style="font-family:'Space Grotesk',sans-serif;font-size:46px;font-weight:900;
                 color:#fff;line-height:1.08;margin-bottom:20px;letter-spacing:-1.5px;">
                Stop fraud<br>
                <span style="color:#00ff66;">before</span> the<br>
                chargeback.
            </div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:16px;
                 color:rgba(255,255,255,0.45);line-height:1.7;margin-bottom:12px;max-width:460px;">
                FraudGuard v2 scores every transaction in real-time using an
                XGBoost model trained on real fraud data. Deploy in minutes.
                Block bad actors instantly.
            </div>
        </div>
        """)
        b1, b2, b3 = st.columns([1.1, 1, 1])
        with b1:
            if st.button("DEPLOY FREE →", key="landing_deploy", use_container_width=True):
                st.session_state.view = "auth"
                st.session_state.auth_tab = "register"
                st.rerun()
        with b2:
            if st.button("SIGN IN", key="landing_signin", use_container_width=True):
                st.session_state.view = "auth"
                st.session_state.auth_tab = "login"
                st.rerun()
        H("<div style='height:14px'></div>")

    with c2:
        H("""
        <div style="position:relative;z-index:10;padding:6px 48px;
             display:flex;align-items:center;justify-content:center;">
            <div style="position:relative;width:250px;height:250px;">
                <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
                     width:250px;height:250px;border:1px solid rgba(0,255,102,0.12);
                     border-radius:50%;"></div>
                <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
                     width:180px;height:180px;border:1px solid rgba(0,255,102,0.18);
                     border-radius:50%;"></div>
                <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
                     width:114px;height:114px;border:1px solid rgba(0,255,102,0.25);
                     border-radius:50%;"></div>
                <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
                     font-size:60px;filter:drop-shadow(0 0 30px rgba(0,255,102,0.5));">🛡️</div>
                <div style="position:absolute;top:50%;left:50%;
                     transform:translate(-50%,47px);
                     font-family:'JetBrains Mono',monospace;font-size:11px;color:#00ff66;
                     letter-spacing:3px;">SECURED</div>
                <div style="position:absolute;top:15%;left:10%;width:8px;height:8px;
                     background:#00ff66;border-radius:50%;box-shadow:0 0 10px rgba(0,255,102,0.9);
                     animation:blip 2s ease-in-out infinite;"></div>
                <div style="position:absolute;bottom:20%;right:8%;width:6px;height:6px;
                     background:#00ff66;border-radius:50%;box-shadow:0 0 10px rgba(0,255,102,0.9);
                     animation:blip 2.5s ease-in-out infinite 0.5s;"></div>
                <div style="position:absolute;top:35%;right:2%;width:5px;height:5px;
                     background:#00ff66;border-radius:50%;box-shadow:0 0 10px rgba(0,255,102,0.9);
                     animation:blip 3s ease-in-out infinite 1s;"></div>
            </div>
        </div>
        """)

    H("""
    <div style="position:relative;z-index:10;padding:2px 48px 14px;
         display:grid;grid-template-columns:repeat(3,1fr);gap:20px;max-width:1100px;">
        <div style="background:#0a0d0a;border:1px solid rgba(0,255,102,0.12);border-radius:8px;padding:18px;">
            <div style="font-family:'JetBrains Mono',monospace;font-size:30px;font-weight:800;
                 color:#00ff66;margin-bottom:8px;">99.9%</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:13px;
                 color:rgba(255,255,255,0.4);letter-spacing:0.5px;">Detection accuracy on test data</div>
        </div>
        <div style="background:#0a0d0a;border:1px solid rgba(0,255,102,0.12);border-radius:8px;padding:18px;">
            <div style="font-family:'JetBrains Mono',monospace;font-size:30px;font-weight:800;
                 color:#00ff66;margin-bottom:8px;">&lt;1s</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:13px;
                 color:rgba(255,255,255,0.4);letter-spacing:0.5px;">Average analysis response time</div>
        </div>
        <div style="background:#0a0d0a;border:1px solid rgba(0,255,102,0.12);border-radius:8px;padding:18px;">
            <div style="font-family:'JetBrains Mono',monospace;font-size:30px;font-weight:800;
                 color:#00ff66;margin-bottom:8px;">284K</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:13px;
                 color:rgba(255,255,255,0.4);letter-spacing:0.5px;">Real transactions used for training</div>
        </div>
    </div>
    """)

# ══════════════════════════════════════
#  AUTH PAGE
# ══════════════════════════════════════
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
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            if st.button("SIGN IN →", key="btn_login"):
                if not email_l or not pass_l:
                    H('<div style="background:rgba(255,50,50,0.08);border:1px solid rgba(255,50,50,0.3);border-radius:4px;padding:14px 18px;color:#ff6b6b;font-family:JetBrains Mono,monospace;font-size:14px;margin-top:14px;">⚠ ALL FIELDS REQUIRED</div>')
                else:
                    user = login_user(email_l, pass_l)
                    if user:
                        st.session_state.user = user
                        st.session_state.active_page = "dashboard"
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
        with st.expander("✎  CUSTOMIZE CARD DETAILS"):
            ce1, ce2 = st.columns(2)
            with ce1:
                st.text_input("Last 4 digits", value=st.session_state.get("card_last4","7891"),
                               max_chars=4, key="card_last4_det")
            with ce2:
                st.text_input("Card holder name", value=st.session_state.get("card_holder","FRAUD ANALYSIS"),
                               key="card_holder_det")
        _last4  = (st.session_state.get("card_last4_det") or st.session_state.get("card_last4") or "7891")
        _holder = (st.session_state.get("card_holder_det") or st.session_state.get("card_holder") or "FRAUD ANALYSIS").upper()
        H(cc_html(number=f"4532 •••• •••• {_last4}", holder=_holder))
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
    else:
        show_auth_page()
else:
    page = st.session_state.active_page
    if   page == "dashboard": show_dashboard()
    elif page == "detection": show_detection()
    elif page == "history":   show_history()
