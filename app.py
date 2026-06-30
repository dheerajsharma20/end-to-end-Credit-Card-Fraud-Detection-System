import streamlit as st
import numpy as np
import joblib
import time
import struct
from pathlib import Path
from database import init_db, register_user, login_user, log_transaction, get_user_transactions, get_user_stats

st.set_page_config(
    page_title="FraudGuard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()

@st.cache_resource
def load_model():
    return joblib.load(Path(__file__).parent / "fraud_model.pkl")
model = load_model()

for k, v in [("user", None), ("active_page", "dashboard"), ("preset_load", None)]:
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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600;700&display=swap');

*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
    line-height: 1.5 !important;
    color: #111827 !important;
}
#MainMenu, footer { visibility: hidden; }

/* ── Keep header visible so sidebar toggle (>>) always works ── */
header[data-testid="stHeader"] {
    background: transparent !important;
    height: 2.5rem !important;
}
/* Style the sidebar collapse/expand control so it's visible on white bg */
button[data-testid="stSidebarCollapseButton"],
button[data-testid="baseButton-headerNoPadding"],
[data-testid="collapsedControl"] {
    color: #528ff0 !important;
    visibility: visible !important;
    opacity: 1 !important;
}

/* ── Streamlit layout reset ── */
.block-container {
    padding-top: 1rem !important;
    padding-left: 1.5rem !important;
    padding-right: 1.5rem !important;
    padding-bottom: 1rem !important;
    max-width: 100% !important;
}

/* ── App + sidebar background ── */
.stApp { background: #f3f4f6 !important; }
section[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid #e5e7eb !important;
}
section[data-testid="stSidebar"] > div:first-child { padding-top: 0 !important; }

/* ── Labels ── */
.stTextInput label, .stNumberInput label, .stSelectbox label {
    font-size: 13px !important; font-weight: 600 !important;
    color: #374151 !important; margin-bottom: 4px !important;
}
.stCheckbox label { font-size: 13px !important; font-weight: 500 !important; color: #374151 !important; }

/* ── Inputs ── */
.stTextInput input, .stNumberInput input {
    background: #ffffff !important; border: 1.5px solid #e5e7eb !important;
    border-radius: 8px !important; color: #111827 !important;
    font-size: 14px !important; padding: 9px 12px !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
}
.stTextInput input:focus, .stNumberInput input:focus {
    border-color: #528ff0 !important;
    box-shadow: 0 0 0 3px rgba(82,143,240,0.1) !important;
}
.stTextInput input::placeholder, .stNumberInput input::placeholder { color: #9ca3af !important; }

/* ── Selects ── */
div[data-baseweb="select"] > div {
    background: #ffffff !important; border: 1.5px solid #e5e7eb !important;
    border-radius: 8px !important; color: #111827 !important;
    font-size: 14px !important; min-height: 42px !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
}
div[data-baseweb="select"] * { color: #111827 !important; }

/* ── All buttons default blue ── */
.stButton > button {
    background: #528ff0 !important; color: #fff !important;
    border: none !important; border-radius: 8px !important;
    padding: 10px 20px !important; font-size: 14px !important;
    font-weight: 700 !important; width: 100% !important;
    transition: all 0.18s ease !important;
    box-shadow: 0 2px 6px rgba(82,143,240,0.28) !important;
}
.stButton > button:hover {
    background: #3b5fc0 !important;
    box-shadow: 0 4px 14px rgba(82,143,240,0.38) !important;
    transform: translateY(-1px) !important;
}

/* ── Back button override ── */
[data-testid="stButton"].back-btn > button {
    background: #ffffff !important; color: #374151 !important;
    border: 1.5px solid #d1d5db !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
    font-size: 13px !important; padding: 7px 16px !important;
    font-weight: 600 !important; width: auto !important;
}
[data-testid="stButton"].back-btn > button:hover {
    border-color: #528ff0 !important; color: #528ff0 !important;
    background: #f0f7ff !important; transform: none !important;
    box-shadow: none !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: #f3f4f6; border-radius: 10px; padding: 3px;
    border: 1px solid #e5e7eb; gap: 3px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 7px; font-size: 14px; font-weight: 600;
    color: #6b7280; padding: 9px 22px;
}
.stTabs [aria-selected="true"] {
    background: #ffffff !important; color: #528ff0 !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.09) !important;
}
.stTabs [data-baseweb="tab-border"] { display: none !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 100px; }

.stSpinner p { font-size: 14px !important; color: #6b7280 !important; }
.stCheckbox { margin-bottom: 0; }
</style>
""")

# ══════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════
def hero(page_label, title, subtitle):
    H(f"""
    <div style="background:linear-gradient(135deg,#528ff0,#3b5fc0);
         border-radius:12px;padding:20px 24px 18px;
         margin-bottom:16px;position:relative;overflow:hidden;">
        <div style="position:absolute;top:-30px;right:-30px;width:140px;height:140px;
             background:rgba(255,255,255,0.07);border-radius:50%;"></div>
        <div style="font-size:10px;font-weight:700;color:rgba(255,255,255,0.55);
             letter-spacing:1.5px;text-transform:uppercase;margin-bottom:6px;">{page_label}</div>
        <div style="font-size:22px;font-weight:800;color:#fff;letter-spacing:-0.4px;margin-bottom:3px;">
            {title}</div>
        <div style="font-size:13px;color:rgba(255,255,255,0.65);">{subtitle}</div>
    </div>
    """)

def stat_card(label, value, color, top_color):
    return f"""
    <div style="background:#fff;border:1px solid #e5e7eb;border-radius:10px;
         padding:14px 16px;border-top:3px solid {top_color};
         box-shadow:0 1px 3px rgba(0,0,0,0.04);">
        <div style="font-size:10px;font-weight:600;color:#9ca3af;
             letter-spacing:0.6px;text-transform:uppercase;margin-bottom:6px;">{label}</div>
        <div style="font-size:28px;font-weight:800;color:{color};
             font-family:'JetBrains Mono',monospace;line-height:1;">{value}</div>
    </div>"""

def card_open(extra=""):
    H(f'<div style="background:#fff;border:1px solid #e5e7eb;border-radius:10px;'
      f'padding:16px;box-shadow:0 1px 3px rgba(0,0,0,0.04);{extra}">')

def card_close():
    H("</div>")

def section_header(title):
    H(f'<div style="font-size:14px;font-weight:700;color:#111827;margin-bottom:10px;'
      f'display:flex;align-items:center;gap:8px;">'
      f'<div style="width:3px;height:16px;background:#528ff0;border-radius:2px;"></div>'
      f'{title}</div>')

def badge(result):
    if result == "FRAUD":
        return '<span style="background:#fef2f2;color:#ef4444;font-size:11px;font-weight:700;padding:3px 10px;border-radius:100px;border:1px solid #fecaca;">🚨 FRAUD</span>'
    return '<span style="background:#f0fdf4;color:#10b981;font-size:11px;font-weight:700;padding:3px 10px;border-radius:100px;border:1px solid #bbf7d0;">✅ LEGIT</span>'

def show_back_button(key="back_btn"):
    col_back, _ = st.columns([0.12, 0.88])
    with col_back:
        st.markdown('<span class="back-btn">', unsafe_allow_html=True)
        if st.button("← Back", key=key):
            st.session_state.active_page = "dashboard"; st.rerun()
        st.markdown('</span>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════
def show_sidebar():
    with st.sidebar:
        H("""
        <div style="padding:18px 14px 10px;">
            <div style="display:flex;align-items:center;gap:9px;margin-bottom:16px;">
                <div style="width:30px;height:30px;background:#528ff0;border-radius:7px;
                     display:flex;align-items:center;justify-content:center;font-size:15px;flex-shrink:0;">🛡️</div>
                <div>
                    <div style="font-size:14px;font-weight:700;color:#111827;">FraudGuard</div>
                    <div style="font-size:10px;color:#9ca3af;">Detection System</div>
                </div>
            </div>
            <div style="height:1px;background:#f0f0f0;margin-bottom:12px;"></div>
            <div style="font-size:10px;font-weight:700;color:#9ca3af;letter-spacing:1px;
                 text-transform:uppercase;margin-bottom:8px;">Menu</div>
        </div>
        """)
        if st.button("📊  Dashboard",       use_container_width=True, key="nav_dash"):
            st.session_state.active_page = "dashboard"; st.rerun()
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        if st.button("🔍  Fraud Detection", use_container_width=True, key="nav_det"):
            st.session_state.active_page = "detection"; st.rerun()
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        if st.button("📋  History",         use_container_width=True, key="nav_hist"):
            st.session_state.active_page = "history";   st.rerun()
        H('<div style="padding:0 14px;"><div style="height:1px;background:#f0f0f0;margin:12px 0;"></div></div>')
        if st.button("🚪  Logout",          use_container_width=True, key="nav_logout"):
            st.session_state.user = None; st.rerun()
        u = st.session_state.user
        if u:
            initials = "".join([w[0].upper() for w in u["full_name"].split()[:2]])
            H(f"""
            <div style="padding:12px 14px;margin-top:8px;">
                <div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:9px;
                     padding:9px 11px;display:flex;align-items:center;gap:8px;">
                    <div style="width:26px;height:26px;background:#528ff0;border-radius:50%;
                         display:flex;align-items:center;justify-content:center;
                         font-size:10px;font-weight:700;color:#fff;flex-shrink:0;">{initials}</div>
                    <div style="overflow:hidden;">
                        <div style="font-size:12px;font-weight:600;color:#111827;
                             white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{u['full_name']}</div>
                        <div style="font-size:10px;color:#9ca3af;
                             white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{u['email']}</div>
                    </div>
                </div>
            </div>
            """)

# ══════════════════════════════════════════════════════
#  AUTH
# ══════════════════════════════════════════════════════
def show_auth_page():
    _, mid, _ = st.columns([1, 1.1, 1])
    with mid:
        H("""<div style="padding:32px 0 20px;text-align:center;">
            <div style="display:inline-flex;align-items:center;justify-content:center;
                 width:44px;height:44px;background:#528ff0;border-radius:11px;
                 font-size:22px;margin-bottom:10px;box-shadow:0 4px 12px rgba(82,143,240,0.35);">🛡️</div>
            <div style="font-size:22px;font-weight:800;color:#111827;letter-spacing:-0.4px;margin-bottom:3px;">FraudGuard</div>
            <div style="font-size:13px;color:#9ca3af;">AI-powered credit card fraud detection</div>
        </div>""")
        card_open()
        tab_login, tab_reg = st.tabs(["🔐  Sign In", "✨  Create Account"])
        with tab_login:
            H('<div style="padding:10px 0 4px;"><div style="font-size:17px;font-weight:800;color:#111827;margin-bottom:2px;">Welcome back 👋</div><div style="font-size:13px;color:#9ca3af;margin-bottom:12px;">Sign in to your account</div></div>')
            email_l = st.text_input("Email", key="login_email", placeholder="you@example.com")
            pass_l  = st.text_input("Password", key="login_pass", type="password", placeholder="Enter your password")
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
            if st.button("Sign In →", key="btn_login"):
                if not email_l or not pass_l:
                    H('<div style="background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:10px 14px;color:#dc2626;font-size:13px;font-weight:600;margin-top:10px;">⚠️ Please fill in all fields.</div>')
                else:
                    user = login_user(email_l, pass_l)
                    if user:
                        st.session_state.user = user
                        st.session_state.active_page = "dashboard"
                        st.rerun()
                    else:
                        H('<div style="background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:10px 14px;color:#dc2626;font-size:13px;font-weight:600;margin-top:10px;">⚠️ Invalid email or password.</div>')
        with tab_reg:
            H('<div style="padding:10px 0 4px;"><div style="font-size:17px;font-weight:800;color:#111827;margin-bottom:2px;">Create Account ✨</div><div style="font-size:13px;color:#9ca3af;margin-bottom:12px;">Get started with FraudGuard</div></div>')
            full_name = st.text_input("Full Name",        key="reg_name",  placeholder="John Doe")
            email_r   = st.text_input("Email",            key="reg_email", placeholder="you@example.com")
            pass_r    = st.text_input("Password",         key="reg_pass",  type="password", placeholder="Min. 6 characters")
            conf_r    = st.text_input("Confirm Password", key="reg_conf",  type="password", placeholder="Repeat password")
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
            if st.button("Create Account →", key="btn_reg"):
                if not full_name or not email_r or not pass_r or not conf_r:
                    H('<div style="background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:10px 14px;color:#dc2626;font-size:13px;font-weight:600;margin-top:10px;">⚠️ Please fill in all fields.</div>')
                elif len(pass_r) < 6:
                    H('<div style="background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:10px 14px;color:#dc2626;font-size:13px;font-weight:600;margin-top:10px;">⚠️ Password must be at least 6 characters.</div>')
                elif pass_r != conf_r:
                    H('<div style="background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:10px 14px;color:#dc2626;font-size:13px;font-weight:600;margin-top:10px;">⚠️ Passwords do not match.</div>')
                else:
                    ok, msg = register_user(full_name, email_r, pass_r)
                    if ok:
                        H(f'<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:10px 14px;color:#15803d;font-size:13px;font-weight:600;margin-top:10px;">✅ {msg} Please sign in.</div>')
                    else:
                        H(f'<div style="background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:10px 14px;color:#dc2626;font-size:13px;font-weight:600;margin-top:10px;">⚠️ {msg}</div>')
        card_close()

# ══════════════════════════════════════════════════════
#  DASHBOARD
# ══════════════════════════════════════════════════════
def show_dashboard():
    u          = st.session_state.user
    stats      = get_user_stats(u["id"])
    txns       = get_user_transactions(u["id"], limit=6)
    fraud_rate = round(stats["fraud"] / stats["total"] * 100, 1) if stats["total"] > 0 else 0
    first      = u["full_name"].split()[0]

    hero("DASHBOARD",
         f"Welcome back, {first}! 🙏",
         "Real-time fraud protection · 284K rows trained")

    # ── Stats row ──
    s1, s2, s3, s4 = st.columns(4, gap="small")
    s1.markdown(stat_card("Total Checks",  stats['total'],  "#528ff0", "#528ff0"), unsafe_allow_html=True)
    s2.markdown(stat_card("Legitimate",    stats['legit'],  "#10b981", "#10b981"), unsafe_allow_html=True)
    s3.markdown(stat_card("Fraud Found",   stats['fraud'],  "#ef4444", "#ef4444"), unsafe_allow_html=True)
    s4.markdown(stat_card("Fraud Rate",    f"{fraud_rate}%","#f59e0b", "#f59e0b"), unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    col1, col2 = st.columns([1.6, 1], gap="medium")

    with col1:
        section_header("Recent Transactions")
        card_open()
        if not txns:
            H('<div style="text-align:center;padding:36px 0;"><div style="font-size:36px;margin-bottom:10px;">📭</div><div style="font-size:16px;font-weight:700;color:#111827;margin-bottom:4px;">No transactions yet</div><div style="font-size:13px;color:#9ca3af;">Go to Fraud Detection to start!</div></div>')
        else:
            rows = ""
            for t in txns:
                amt = "{:,.2f}".format(t["amount"])
                dt  = str(t["checked_at"])[:16]
                rows += ("<tr>"
                    "<td style='padding:10px 14px;color:#111827;font-weight:600;font-size:13px;"
                    "border-bottom:1px solid #f3f4f6;font-family:JetBrains Mono,monospace;'>₹" + amt + "</td>"
                    "<td style='padding:10px 14px;border-bottom:1px solid #f3f4f6;'>" + badge(t["result"]) + "</td>"
                    "<td style='padding:10px 14px;color:#528ff0;font-weight:700;font-family:JetBrains Mono,"
                    "monospace;font-size:13px;border-bottom:1px solid #f3f4f6;'>" + str(safe_conf(t["confidence"])) + "%</td>"
                    "<td style='padding:10px 14px;color:#9ca3af;font-size:12px;border-bottom:1px solid #f3f4f6;'>" + dt + "</td>"
                    "</tr>")
            H("<table style='width:100%;border-collapse:collapse;'>"
              "<thead><tr style='background:#f9fafb;'>"
              "<th style='padding:8px 14px;text-align:left;font-size:10px;font-weight:700;color:#6b7280;"
              "text-transform:uppercase;letter-spacing:0.6px;border-bottom:1px solid #e5e7eb;'>Amount</th>"
              "<th style='padding:8px 14px;text-align:left;font-size:10px;font-weight:700;color:#6b7280;"
              "text-transform:uppercase;letter-spacing:0.6px;border-bottom:1px solid #e5e7eb;'>Result</th>"
              "<th style='padding:8px 14px;text-align:left;font-size:10px;font-weight:700;color:#6b7280;"
              "text-transform:uppercase;letter-spacing:0.6px;border-bottom:1px solid #e5e7eb;'>Confidence</th>"
              "<th style='padding:8px 14px;text-align:left;font-size:10px;font-weight:700;color:#6b7280;"
              "text-transform:uppercase;letter-spacing:0.6px;border-bottom:1px solid #e5e7eb;'>Time</th>"
              "</tr></thead><tbody>" + rows + "</tbody></table>")
        card_close()

    with col2:
        section_header("Quick Action")
        card_open()
        H("""
        <div style="background:linear-gradient(135deg,#528ff0,#3b5fc0);border-radius:10px;
             padding:14px 16px;margin-bottom:12px;position:relative;overflow:hidden;min-height:80px;">
            <div style="position:absolute;top:-20px;right:-20px;width:80px;height:80px;
                 background:rgba(255,255,255,0.08);border-radius:50%;"></div>
            <div style="font-size:10px;font-weight:700;color:rgba(255,255,255,0.65);
                 letter-spacing:1.5px;text-transform:uppercase;margin-bottom:10px;">🛡️ FRAUDGUARD</div>
            <div style="width:22px;height:15px;background:rgba(255,255,255,0.22);
                 border-radius:3px;margin-bottom:8px;"></div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:600;
                 color:rgba(255,255,255,0.75);letter-spacing:3px;">4532 •••• •••• 7891</div>
        </div>
        <div style="font-size:13px;color:#6b7280;text-align:center;margin-bottom:12px;line-height:1.5;">
            Run fraud analysis on the Detection page</div>
        """)
        if st.button("🔍  Analyze Transaction", key="dash_detect"):
            st.session_state.active_page = "detection"; st.rerun()
        card_close()

# ══════════════════════════════════════════════════════
#  FRAUD DETECTION
# ══════════════════════════════════════════════════════
def show_detection():
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
        for i,val in enumerate(FRAUD_VALS,1): st.session_state[f"pv{i}"] = float(val)
        st.session_state["preset_amount"] = 2.69
        st.session_state["preset_load"] = None
    elif st.session_state.get("preset_load") == "legit":
        for i,val in enumerate(LEGIT_VALS,1): st.session_state[f"pv{i}"] = float(val)
        st.session_state["preset_amount"] = 149.62
        st.session_state["preset_load"] = None

    hero("FRAUD DETECTION ENGINE",
         "Transaction Analyzer 🔍",
         "Fill in details —  Model processes all 28 PCA features automatically.")

    show_back_button(key="back_det")
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    left, right = st.columns([1.3, 1], gap="medium")

    with left:
        section_header("Transaction Details")
        card_open()
        H("""<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;
             padding:10px 13px;margin-bottom:14px;display:flex;gap:10px;align-items:flex-start;">
            <span style="font-size:14px;flex-shrink:0;">ℹ️</span>
            <div style="font-size:12px;color:#1e40af;line-height:1.5;">
                Fill the fields below. XGBoost AI auto-processes all PCA features for real-time fraud verdict.
            </div></div>""")
        c1, c2 = st.columns(2)
        with c1:
            amount_val = st.number_input("💰 Amount (₹)", min_value=0.0,
                value=float(st.session_state.get("preset_amount", 100.0)), format="%.2f")
        with c2:
            hour = st.selectbox("🕐 Time of Day",
                ["Morning (6AM–12PM)","Afternoon (12PM–6PM)","Evening (6PM–10PM)","Night (10PM–6AM)"])
        txn_type = st.selectbox("🏪 Transaction Type",
            ["Online Shopping","ATM Withdrawal","Restaurant/Food","Travel/Hotel","Grocery/Supermarket"])
        c3, c4 = st.columns(2)
        with c3: st.selectbox("💳 Card Type", ["Credit Card","Debit Card"])
        with c4: location = st.selectbox("📍 Location",["Same City","Different City","International","Online"])
        H("""<div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;
             padding:12px 14px;margin-top:12px;">
            <div style="font-size:10px;font-weight:700;color:#6b7280;
                 letter-spacing:0.6px;text-transform:uppercase;margin-bottom:10px;">⚠️ Risk Factors</div>""")
        rc1, rc2 = st.columns(2)
        with rc1:
            is_new_merchant = st.checkbox("🆕 New Merchant")
            is_foreign      = st.checkbox("🌍 Foreign Currency")
        with rc2:
            is_unusual_amt  = st.checkbox("⚠️ Unusual Amount")
            is_multiple     = st.checkbox("🔁 Multiple Txns")
        H("</div>")
        card_close()

    with right:
        section_header("Analysis Panel")
        card_open()
        H("""
        <div style="background:linear-gradient(135deg,#528ff0,#3b5fc0);border-radius:10px;
             padding:14px 16px;margin-bottom:12px;position:relative;overflow:hidden;min-height:80px;">
            <div style="position:absolute;top:-20px;right:-20px;width:80px;height:80px;
                 background:rgba(255,255,255,0.08);border-radius:50%;"></div>
            <div style="font-size:10px;font-weight:700;color:rgba(255,255,255,0.65);
                 letter-spacing:1.5px;text-transform:uppercase;margin-bottom:10px;">🛡️ FRAUDGUARD</div>
            <div style="width:22px;height:15px;background:rgba(255,255,255,0.22);
                 border-radius:3px;margin-bottom:8px;"></div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:600;
                 color:rgba(255,255,255,0.75);letter-spacing:3px;">4532 •••• •••• 7891</div>
        </div>
        <div style="font-size:11px;font-weight:700;color:#9ca3af;
             letter-spacing:0.6px;text-transform:uppercase;margin-bottom:9px;">Quick Test Presets</div>
        """)
        p1, p2 = st.columns(2)
        with p1:
            if st.button("🚨 Test Fraud", use_container_width=True, key="p_fraud"):
                st.session_state["preset_load"] = "fraud"; st.rerun()
        with p2:
            if st.button("✅ Test Legit", use_container_width=True, key="p_legit"):
                st.session_state["preset_load"] = "legit"; st.rerun()
        H("""<div style="display:flex;flex-wrap:wrap;gap:6px;margin:12px 0;">
            <span style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:6px;
                 padding:3px 9px;font-size:11px;color:#3b82f6;font-weight:600;">🤖 XGBoost</span>
            <span style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:6px;
                 padding:3px 9px;font-size:11px;color:#3b82f6;font-weight:600;">⚡ Real-time</span>
            <span style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:6px;
                 padding:3px 9px;font-size:11px;color:#3b82f6;font-weight:600;">📊 284K rows</span>
        </div>""")
        card_close()

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        if st.button("🔍  Analyze Transaction Now", key="btn_analyze", use_container_width=True):
            risk_score = 0.0
            if is_new_merchant: risk_score += 0.28
            if is_unusual_amt:  risk_score += 0.25
            if is_foreign:      risk_score += 0.18
            if is_multiple:     risk_score += 0.20
            if "Night" in hour:              risk_score += 0.10
            if location == "International":  risk_score += 0.15
            if amount_val > 50000:           risk_score += 0.20
            elif amount_val > 10000:         risk_score += 0.10
            risk_score = min(risk_score, 1.0)

            base     = np.array(PATTERNS[txn_type])
            fvec     = np.array(FRAUD_VALS)
            v        = list(base * (1.0 - risk_score) + fvec * risk_score)
            hour_map = {"Morning (6AM–12PM)":6*3600,"Afternoon (12PM–6PM)":12*3600,
                        "Evening (6PM–10PM)":18*3600,"Night (10PM–6AM)":22*3600}
            features = np.array([[float(hour_map.get(hour,0))] + v + [amount_val]])

            with st.spinner("Analyzing..."):
                time.sleep(0.5)
                pred = model.predict(features)[0]
                prob = float(model.predict_proba(features)[0][1] * 100)

            result_str = "FRAUD" if pred==1 else "LEGIT"
            conf_val   = prob if pred==1 else (100-prob)
            log_transaction(st.session_state.user["id"], amount_val, result_str, conf_val)

            if pred == 1:
                bar = min(int(prob), 100)
                H("<div style='background:#fef2f2;border:1px solid #fecaca;border-left:4px solid #ef4444;"
                  "border-radius:10px;padding:16px 18px;margin-top:10px;'>"
                  "<div style='font-size:17px;font-weight:800;color:#dc2626;margin-bottom:4px;'>🚨 Fraudulent!</div>"
                  "<div style='font-size:12px;color:#6b7280;margin-bottom:4px;line-height:1.5;'>High-risk patterns detected. Matches known fraud signatures.</div>"
                  "<div style='font-size:12px;color:#ef4444;font-weight:600;margin-bottom:14px;'>⚠️ Recommend blocking this transaction.</div>"
                  "<div style='display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:8px;'>"
                  "<div style='font-size:10px;font-weight:700;color:#9ca3af;letter-spacing:0.6px;text-transform:uppercase;'>Fraud Probability</div>"
                  "<div style='font-size:34px;font-weight:800;color:#dc2626;font-family:JetBrains Mono,monospace;line-height:1;'>" + str(round(prob,1)) + "%</div></div>"
                  "<div style='background:#fee2e2;border-radius:100px;height:8px;overflow:hidden;'>"
                  "<div style='width:" + str(bar) + "%;height:8px;border-radius:100px;background:linear-gradient(90deg,#dc2626,#f87171);'></div></div></div>")
            else:
                safe = 100 - prob
                bar  = min(int(safe), 100)
                H("<div style='background:#f0fdf4;border:1px solid #bbf7d0;border-left:4px solid #10b981;"
                  "border-radius:10px;padding:16px 18px;margin-top:10px;'>"
                  "<div style='font-size:17px;font-weight:800;color:#15803d;margin-bottom:4px;'>✅ Legitimate!</div>"
                  "<div style='font-size:12px;color:#6b7280;margin-bottom:4px;line-height:1.5;'>No suspicious patterns. Transaction appears genuine and safe.</div>"
                  "<div style='font-size:12px;color:#10b981;font-weight:600;margin-bottom:14px;'>✓ Safe to proceed.</div>"
                  "<div style='display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:8px;'>"
                  "<div style='font-size:10px;font-weight:700;color:#9ca3af;letter-spacing:0.6px;text-transform:uppercase;'>Confidence</div>"
                  "<div style='font-size:34px;font-weight:800;color:#15803d;font-family:JetBrains Mono,monospace;line-height:1;'>" + str(round(safe,1)) + "%</div></div>"
                  "<div style='background:#dcfce7;border-radius:100px;height:8px;overflow:hidden;'>"
                  "<div style='width:" + str(bar) + "%;height:8px;border-radius:100px;background:linear-gradient(90deg,#15803d,#4ade80);'></div></div></div>")

# ══════════════════════════════════════════════════════
#  HISTORY
# ══════════════════════════════════════════════════════
def show_history():
    hero("TRANSACTION LOG", "Transaction History 📋",
         "Full log of all fraud checks on your account.")

    show_back_button(key="back_hist")
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    section_header("All Transactions")
    card_open()
    txns = get_user_transactions(st.session_state.user["id"], limit=50)
    if not txns:
        H('<div style="text-align:center;padding:48px 0;"><div style="font-size:48px;margin-bottom:10px;">📭</div>'
          '<div style="font-size:18px;font-weight:700;color:#111827;margin-bottom:4px;">No transactions yet</div>'
          '<div style="font-size:13px;color:#9ca3af;">Start analyzing transactions to see history here.</div></div>')
    else:
        rows = ""
        for t in txns:
            amt = "{:,.2f}".format(t["amount"])
            dt  = str(t["checked_at"])[:16]
            rows += ("<tr>"
                "<td style='padding:11px 14px;color:#111827;font-weight:600;font-size:13px;"
                "border-bottom:1px solid #f3f4f6;font-family:JetBrains Mono,monospace;'>₹" + amt + "</td>"
                "<td style='padding:11px 14px;border-bottom:1px solid #f3f4f6;'>" + badge(t["result"]) + "</td>"
                "<td style='padding:11px 14px;color:#528ff0;font-weight:700;font-family:JetBrains Mono,"
                "monospace;font-size:13px;border-bottom:1px solid #f3f4f6;'>" + str(safe_conf(t["confidence"])) + "%</td>"
                "<td style='padding:11px 14px;color:#9ca3af;font-size:12px;border-bottom:1px solid #f3f4f6;'>" + dt + "</td>"
                "</tr>")
        H("<table style='width:100%;border-collapse:collapse;'>"
          "<thead><tr style='background:#f9fafb;'>"
          "<th style='padding:9px 14px;text-align:left;font-size:10px;font-weight:700;color:#6b7280;"
          "text-transform:uppercase;letter-spacing:0.6px;border-bottom:1px solid #e5e7eb;'>Amount</th>"
          "<th style='padding:9px 14px;text-align:left;font-size:10px;font-weight:700;color:#6b7280;"
          "text-transform:uppercase;letter-spacing:0.6px;border-bottom:1px solid #e5e7eb;'>Result</th>"
          "<th style='padding:9px 14px;text-align:left;font-size:10px;font-weight:700;color:#6b7280;"
          "text-transform:uppercase;letter-spacing:0.6px;border-bottom:1px solid #e5e7eb;'>Confidence</th>"
          "<th style='padding:9px 14px;text-align:left;font-size:10px;font-weight:700;color:#6b7280;"
          "text-transform:uppercase;letter-spacing:0.6px;border-bottom:1px solid #e5e7eb;'>Date & Time</th>"
          "</tr></thead><tbody>" + rows + "</tbody></table>")
    card_close()

# ══════════════════════════════════════════════════════
#  ROUTER
# ══════════════════════════════════════════════════════
if st.session_state.user is None:
    show_auth_page()
else:
    show_sidebar()
    page = st.session_state.active_page
    if   page == "dashboard": show_dashboard()
    elif page == "detection": show_detection()
    elif page == "history":   show_history()
    H('<div style="text-align:center;padding:16px 0 10px;border-top:1px solid #e5e7eb;margin-top:16px;'
      'color:#d1d5db;font-size:12px;">🛡️ FraudGuard ·Fraud Detection · XGBoost + Streamlit</div>')
