# fix3.py - Replace complex V1-V28 inputs with simple user-friendly detection page

import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace entire show_detection function
old_func_start = 'def show_detection():'
old_func_end   = 'def show_history():'

start_idx = content.index(old_func_start)
end_idx   = content.index(old_func_end)

new_detection = '''def show_detection():
    import numpy as np
    import random

    # Preset patterns
    FRAUD_VALS = [-3.0, 0.0, -4.0, 2.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                  0.0, 0.0, 0.0, -9.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                  0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    LEGIT_VALS = [1.19, 0.26, 0.16, 0.44, 0.06, -0.08, -0.07, 0.08,
                  -0.25, 0.16, 0.28, -0.16, 0.36, 0.14, 0.08, 0.09,
                  -0.05, -0.02, -0.09, 0.06, 0.06, 0.26, -0.11, 0.06,
                  0.21, -0.17, 0.07, 0.09]

    # Transaction type patterns (realistic PCA-like values)
    PATTERNS = {
        "Online Shopping":    [0.5,-0.2,0.3,0.8,-0.1,0.2,-0.3,0.1,0.4,-0.2,
                               0.1,0.3,-0.1,0.5,0.2,-0.1,0.3,0.1,-0.2,0.4,
                               0.1,-0.3,0.2,0.1,0.3,-0.1,0.2,0.1],
        "ATM Withdrawal":     [1.2,0.3,-0.5,0.2,0.8,-0.3,0.1,0.5,-0.2,0.3,
                               0.4,-0.1,0.6,0.2,-0.4,0.3,0.1,0.5,-0.1,0.2,
                               0.3,-0.2,0.4,0.1,-0.3,0.2,0.5,-0.1],
        "Restaurant/Food":    [0.3,0.8,-0.2,0.4,0.1,0.6,-0.1,0.3,0.5,-0.2,
                               0.2,0.4,-0.3,0.1,0.7,-0.2,0.3,0.1,0.4,-0.1,
                               0.2,0.5,-0.1,0.3,0.1,0.4,-0.2,0.3],
        "Travel/Hotel":       [0.8,0.4,0.6,-0.2,0.3,0.5,0.1,-0.3,0.4,0.2,
                               0.6,-0.1,0.3,0.5,-0.2,0.4,0.1,0.3,0.5,-0.1,
                               0.2,0.4,0.1,0.3,-0.2,0.5,0.1,0.4],
        "Grocery/Supermarket":[0.2,0.5,0.3,-0.1,0.4,0.2,0.6,-0.2,0.3,0.5,
                               -0.1,0.4,0.2,0.3,0.5,-0.1,0.2,0.4,0.1,0.3,
                               0.5,-0.2,0.3,0.1,0.4,0.2,-0.1,0.5],
    }

    H("""
    <div style="background:linear-gradient(135deg,#1a237e 0%,#283593 40%,#c5185a 100%);
         padding:48px 52px 56px;position:relative;overflow:hidden;">
        <div style="position:absolute;top:-80px;right:-80px;width:320px;height:320px;
             background:rgba(255,255,255,0.05);border-radius:50%;"></div>
        <div style="position:absolute;top:20px;right:52px;font-size:100px;opacity:0.06;">🔍</div>
        <div style="display:inline-flex;align-items:center;gap:10px;
             background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.25);
             color:#fff;font-size:12px;font-weight:700;letter-spacing:1.5px;
             text-transform:uppercase;padding:7px 18px;border-radius:100px;margin-bottom:22px;">
            <div style="width:8px;height:8px;background:#22c55e;border-radius:50%;
                 box-shadow:0 0 10px rgba(34,197,94,0.9);"></div>
            XGBoost Model Active
        </div>
        <div style="font-size:40px;font-weight:800;color:#fff;line-height:1.1;
             letter-spacing:-1px;margin-bottom:14px;">
            Transaction Fraud Analyzer 🔍
        </div>
        <div style="font-size:16px;color:rgba(255,255,255,0.65);max-width:500px;line-height:1.7;">
            Fill in simple transaction details — our AI handles the rest automatically.
        </div>
    </div>
    <div style="padding:36px;">
    """)

    left, right = st.columns([1.1, 0.9], gap="large")

    with left:
        H("""
        <div style="font-size:20px;font-weight:800;color:#0f172a;margin-bottom:20px;
             display:flex;align-items:center;gap:12px;">
            <div style="width:5px;height:24px;background:linear-gradient(to bottom,#1a237e,#c5185a);
                 border-radius:3px;"></div>
            Enter Transaction Details
        </div>
        <div style="background:#fff;border:1px solid #e2e8f0;border-radius:20px;
             padding:32px;box-shadow:0 4px 20px rgba(0,0,0,0.06);">
        """)

        H("""
        <div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:12px;
             padding:14px 18px;margin-bottom:24px;display:flex;align-items:flex-start;gap:10px;">
            <div style="font-size:20px;">ℹ️</div>
            <div>
                <div style="font-size:13px;font-weight:700;color:#1e40af;margin-bottom:2px;">
                    How it works
                </div>
                <div style="font-size:13px;color:#3b82f6;line-height:1.5;">
                    Just enter the basic transaction details below.
                    Our AI automatically processes the data and checks for fraud instantly.
                </div>
            </div>
        </div>
        """)

        c1, c2 = st.columns(2)
        with c1:
            amount_val = st.number_input(
                "💰 Transaction Amount (₹)",
                min_value=0.0, value=100.0, format="%.2f",
                key="det_amount"
            )
        with c2:
            hour = st.selectbox(
                "🕐 Time of Transaction",
                ["Morning (6AM-12PM)", "Afternoon (12PM-6PM)",
                 "Evening (6PM-10PM)", "Night (10PM-6AM)"],
                key="det_hour"
            )

        txn_type = st.selectbox(
            "🏪 Transaction Type",
            ["Online Shopping", "ATM Withdrawal", "Restaurant/Food",
             "Travel/Hotel", "Grocery/Supermarket"],
            key="det_type"
        )

        card_type = st.selectbox(
            "💳 Card Type",
            ["Credit Card", "Debit Card"],
            key="det_card"
        )

        location = st.selectbox(
            "📍 Transaction Location",
            ["Same City", "Different City", "International", "Online"],
            key="det_loc"
        )

        H("""
        <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;
             padding:16px 20px;margin-top:20px;">
            <div style="font-size:12px;font-weight:700;color:#64748b;letter-spacing:0.8px;
                 text-transform:uppercase;margin-bottom:12px;">Risk Factors</div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
        """)

        is_new_merchant  = st.checkbox("🆕 New / Unknown Merchant")
        is_unusual_amt   = st.checkbox("⚠️ Unusual Amount for me")
        is_foreign       = st.checkbox("🌍 Foreign Currency")
        is_multiple      = st.checkbox("🔁 Multiple transactions today")

        H("</div></div></div>")

    with right:
        H("""
        <div style="font-size:20px;font-weight:800;color:#0f172a;margin-bottom:20px;
             display:flex;align-items:center;gap:12px;">
            <div style="width:5px;height:24px;background:linear-gradient(to bottom,#1a237e,#c5185a);
                 border-radius:3px;"></div>
            Analysis Panel
        </div>
        <div style="background:#fff;border:1px solid #e2e8f0;border-radius:20px;
             padding:28px;box-shadow:0 4px 20px rgba(0,0,0,0.06);">
        """)

        # Credit card visual
        H("""
        <div style="background:linear-gradient(135deg,#1a237e 0%,#283593 40%,#c5185a 100%);
             border-radius:18px;padding:26px 30px;position:relative;overflow:hidden;
             min-height:185px;margin-bottom:24px;
             box-shadow:0 12px 40px rgba(26,35,126,0.35);">
            <div style="position:absolute;top:-60px;right:-60px;width:200px;height:200px;
                 background:rgba(255,255,255,0.07);border-radius:50%;"></div>
            <div style="position:absolute;bottom:-40px;left:10px;width:150px;height:150px;
                 background:rgba(255,255,255,0.04);border-radius:50%;"></div>
            <div style="font-size:13px;font-weight:800;color:rgba(255,255,255,0.9);
                 letter-spacing:2px;text-transform:uppercase;margin-bottom:18px;
                 position:relative;z-index:2;">🛡️ FraudGuard</div>
            <div style="width:42px;height:32px;
                 background:linear-gradient(135deg,#d97706,#fde68a);
                 border-radius:6px;margin-bottom:18px;position:relative;z-index:2;
                 box-shadow:0 2px 8px rgba(0,0,0,0.3);"></div>
            <div style="font-family:monospace;font-size:16px;font-weight:600;
                 color:rgba(255,255,255,0.85);letter-spacing:4px;margin-bottom:16px;
                 position:relative;z-index:2;">4532 .... .... 7891</div>
            <div style="display:flex;justify-content:space-between;align-items:flex-end;
                 position:relative;z-index:2;">
                <div>
                    <div style="font-size:9px;color:rgba(255,255,255,0.35);
                         letter-spacing:1.5px;text-transform:uppercase;margin-bottom:4px;">
                         Card Holder</div>
                    <div style="font-size:13px;font-weight:700;
                         color:rgba(255,255,255,0.85);letter-spacing:1.5px;">
                         FRAUD ANALYSIS</div>
                </div>
                <div style="font-size:24px;font-weight:800;color:rgba(255,255,255,0.6);">VISA</div>
            </div>
        </div>
        """)

        # Quick test presets
        H("""
        <div style="font-size:13px;font-weight:700;color:#374151;letter-spacing:0.5px;
             text-transform:uppercase;margin-bottom:12px;">Quick Test Presets</div>
        """)
        p1, p2 = st.columns(2)
        with p1:
            if st.button("🚨 Test Fraud", use_container_width=True, key="p_fraud"):
                st.session_state["preset_load"] = "fraud"
                st.rerun()
        with p2:
            if st.button("✅ Test Legit", use_container_width=True, key="p_legit"):
                st.session_state["preset_load"] = "legit"
                st.rerun()

        H("""
        <div style="display:flex;flex-wrap:wrap;gap:8px;margin:16px 0 20px;">
            <span style="background:#f1f5f9;border:1px solid #e2e8f0;border-radius:8px;
                 padding:5px 12px;font-size:12px;color:#64748b;font-weight:600;">
                🤖 XGBoost AI</span>
            <span style="background:#f1f5f9;border:1px solid #e2e8f0;border-radius:8px;
                 padding:5px 12px;font-size:12px;color:#64748b;font-weight:600;">
                ⚡ Real-time</span>
            <span style="background:#f1f5f9;border:1px solid #e2e8f0;border-radius:8px;
                 padding:5px 12px;font-size:12px;color:#64748b;font-weight:600;">
                🔐 Secure</span>
            <span style="background:#f1f5f9;border:1px solid #e2e8f0;border-radius:8px;
                 padding:5px 12px;font-size:12px;color:#64748b;font-weight:600;">
                📊 284K trained</span>
        </div>
        </div>
        """)

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        if st.button("🔍  Analyze Transaction Now", key="btn_analyze", use_container_width=True):

            # Build feature vector from user inputs
            v = list(PATTERNS[txn_type])

            # Adjust based on risk factors
            if is_new_merchant:
                v[0] -= 2.0; v[2] -= 1.5; v[4] += 1.0
            if is_unusual_amt:
                v[1] -= 1.5; v[3] += 2.0; v[13] -= 2.0
            if is_foreign:
                v[5] -= 1.0; v[7] += 1.5; v[11] -= 1.0
            if is_multiple:
                v[0] -= 1.0; v[2] -= 2.0; v[14] -= 1.5

            # Adjust for night transactions
            if "Night" in hour:
                v[0] -= 0.5; v[2] -= 0.5
            if location == "International":
                v[5] -= 1.5; v[11] -= 1.0

            # Handle presets
            if st.session_state.get("preset_load") == "fraud":
                v = FRAUD_VALS[:]
                time_val = 406.0
                st.session_state["preset_load"] = None
            elif st.session_state.get("preset_load") == "legit":
                v = LEGIT_VALS[:]
                time_val = 1.0
                st.session_state["preset_load"] = None
            else:
                hour_map = {
                    "Morning (6AM-12PM)":   6*3600,
                    "Afternoon (12PM-6PM)": 12*3600,
                    "Evening (6PM-10PM)":   18*3600,
                    "Night (10PM-6AM)":     22*3600,
                }
                time_val = float(hour_map.get(hour, 0))

            features = np.array([[time_val] + v + [amount_val]])

            with st.spinner("Running AI fraud analysis..."):
                import time
                time.sleep(0.6)
                pred = model.predict(features)[0]
                prob = float(model.predict_proba(features)[0][1] * 100)

            result_str = "FRAUD" if pred == 1 else "LEGIT"
            conf_val   = prob if pred == 1 else (100 - prob)
            log_transaction(st.session_state.user["id"], amount_val, result_str, conf_val)

            if pred == 1:
                bar = min(int(prob), 100)
                amt_str = "{:,.2f}".format(amount_val)
                H("""
                <div style="background:linear-gradient(135deg,#fff5f5,#fef2f2);
                     border:2px solid #fecaca;border-left:6px solid #dc2626;
                     border-radius:16px;padding:28px 32px;margin-top:20px;
                     box-shadow:0 8px 32px rgba(220,38,38,0.12);">
                    <div style="font-size:22px;font-weight:800;color:#dc2626;margin-bottom:8px;">
                        &#128680; Fraudulent Transaction Detected!
                    </div>
                    <div style="font-size:14px;color:#6b7280;margin-bottom:8px;line-height:1.6;">
                        High-risk patterns detected. This transaction matches known fraud signatures.
                    </div>
                    <div style="font-size:13px;color:#ef4444;font-weight:600;margin-bottom:20px;">
                        &#9888; We recommend blocking this transaction immediately.
                    </div>
                    <div style="display:flex;justify-content:space-between;
                         align-items:flex-end;margin-bottom:12px;">
                        <div style="font-size:12px;font-weight:700;color:#94a3b8;
                             letter-spacing:1px;text-transform:uppercase;">
                             Fraud Probability</div>
                        <div style="font-size:40px;font-weight:800;color:#dc2626;
                             font-family:monospace;line-height:1;">""" +
                str(round(prob, 1)) + """%</div>
                    </div>
                    <div style="background:#fee2e2;border-radius:100px;height:10px;overflow:hidden;">
                        <div style="width:""" + str(bar) + """%;height:10px;border-radius:100px;
                             background:linear-gradient(90deg,#991b1b,#dc2626,#f87171);
                             box-shadow:0 0 12px rgba(220,38,38,0.5);"></div>
                    </div>
                </div>
                """)
            else:
                safe = 100 - prob
                bar  = min(int(safe), 100)
                H("""
                <div style="background:linear-gradient(135deg,#f0fdf4,#dcfce7);
                     border:2px solid #bbf7d0;border-left:6px solid #059669;
                     border-radius:16px;padding:28px 32px;margin-top:20px;
                     box-shadow:0 8px 32px rgba(5,150,105,0.12);">
                    <div style="font-size:22px;font-weight:800;color:#059669;margin-bottom:8px;">
                        &#9989; Legitimate Transaction
                    </div>
                    <div style="font-size:14px;color:#6b7280;margin-bottom:8px;line-height:1.6;">
                        No suspicious patterns detected. Transaction appears genuine and safe.
                    </div>
                    <div style="font-size:13px;color:#059669;font-weight:600;margin-bottom:20px;">
                        &#10003; This transaction is safe to proceed.
                    </div>
                    <div style="display:flex;justify-content:space-between;
                         align-items:flex-end;margin-bottom:12px;">
                        <div style="font-size:12px;font-weight:700;color:#94a3b8;
                             letter-spacing:1px;text-transform:uppercase;">
                             Legitimacy Confidence</div>
                        <div style="font-size:40px;font-weight:800;color:#059669;
                             font-family:monospace;line-height:1;">""" +
                str(round(safe, 1)) + """%</div>
                    </div>
                    <div style="background:#dcfce7;border-radius:100px;height:10px;overflow:hidden;">
                        <div style="width:""" + str(bar) + """%;height:10px;border-radius:100px;
                             background:linear-gradient(90deg,#065f46,#059669,#34d399);
                             box-shadow:0 0 12px rgba(5,150,105,0.5);"></div>
                    </div>
                </div>
                """)

    H('</div>')

'''

# Replace the old function
content = content[:start_idx] + new_detection + content[end_idx:]

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

import py_compile
try:
    py_compile.compile('app.py', doraise=True)
    print("Done! Syntax OK. Run: streamlit run app.py")
except py_compile.PyCompileError as e:
    print(f"Syntax error: {e}")
