
# fix2.py - fixes preset button session state conflict

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove the rerun inside preset buttons - set a flag instead
old = '''        FRAUD_VALS = [-3.0, 0.0, -4.0, 2.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                      0.0, 0.0, 0.0, -9.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                      0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        LEGIT_VALS = [1.19, 0.26, 0.16, 0.44, 0.06, -0.08, -0.07, 0.08,
                      -0.25, 0.16, 0.28, -0.16, 0.36, 0.14, 0.08, 0.09,
                      -0.05, -0.02, -0.09, 0.06, 0.06, 0.26, -0.11, 0.06,
                      0.21, -0.17, 0.07, 0.09]

        with p1:
            if st.button("🚨 Fraud Sample", use_container_width=True, key="p_fraud"):
                for i, val in enumerate(FRAUD_VALS, 1):
                    st.session_state[f"v{i}"] = val
                st.session_state["det_time"]   = 406.0
                st.session_state["det_amount"] = 2.69
                st.rerun()
        with p2:
            if st.button("✅ Legit Sample", use_container_width=True, key="p_legit"):
                for i, val in enumerate(LEGIT_VALS, 1):
                    st.session_state[f"v{i}"] = val
                st.session_state["det_time"]   = 1.0
                st.session_state["det_amount"] = 149.62
                st.rerun()'''

new = '''        with p1:
            if st.button("🚨 Fraud Sample", use_container_width=True, key="p_fraud"):
                st.session_state["preset_load"] = "fraud"
                st.rerun()
        with p2:
            if st.button("✅ Legit Sample", use_container_width=True, key="p_legit"):
                st.session_state["preset_load"] = "legit"
                st.rerun()'''

if old in content:
    content = content.replace(old, new)
    print("Preset buttons fixed!")
else:
    print("Pattern not found - trying partial fix")
    # Try to find and replace just the button part
    content = content.replace(
        'if st.button("🚨 Fraud Sample", use_container_width=True, key="p_fraud"):\n                for i, val in enumerate(FRAUD_VALS, 1):\n                    st.session_state[f"v{i}"] = val\n                st.session_state["det_time"]   = 406.0\n                st.session_state["det_amount"] = 2.69\n                st.rerun()',
        'if st.button("🚨 Fraud Sample", use_container_width=True, key="p_fraud"):\n                st.session_state["preset_load"] = "fraud"\n                st.rerun()'
    )
    content = content.replace(
        'if st.button("✅ Legit Sample", use_container_width=True, key="p_legit"):\n                for i, val in enumerate(LEGIT_VALS, 1):\n                    st.session_state[f"v{i}"] = val\n                st.session_state["det_time"]   = 1.0\n                st.session_state["det_amount"] = 149.62\n                st.rerun()',
        'if st.button("✅ Legit Sample", use_container_width=True, key="p_legit"):\n                st.session_state["preset_load"] = "legit"\n                st.rerun()'
    )
    print("Partial fix applied")

# Now add preset loading at the TOP of show_detection function
old_det_start = 'def show_detection():'
new_det_start = '''def show_detection():
    FRAUD_VALS = [-3.0, 0.0, -4.0, 2.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                  0.0, 0.0, 0.0, -9.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                  0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    LEGIT_VALS = [1.19, 0.26, 0.16, 0.44, 0.06, -0.08, -0.07, 0.08,
                  -0.25, 0.16, 0.28, -0.16, 0.36, 0.14, 0.08, 0.09,
                  -0.05, -0.02, -0.09, 0.06, 0.06, 0.26, -0.11, 0.06,
                  0.21, -0.17, 0.07, 0.09]
    if st.session_state.get("preset_load") == "fraud":
        for i, val in enumerate(FRAUD_VALS, 1):
            st.session_state[f"v{i}"] = float(val)
        st.session_state["det_time"]   = 406.0
        st.session_state["det_amount"] = 2.69
        st.session_state["preset_load"] = None
    elif st.session_state.get("preset_load") == "legit":
        for i, val in enumerate(LEGIT_VALS, 1):
            st.session_state[f"v{i}"] = float(val)
        st.session_state["det_time"]   = 1.0
        st.session_state["det_amount"] = 149.62
        st.session_state["preset_load"] = None'''

content = content.replace(old_det_start, new_det_start, 1)
print("Preset loader added to top of show_detection!")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

import py_compile
try:
    py_compile.compile('app.py', doraise=True)
    print("Syntax OK! Run: streamlit run app.py")
except py_compile.PyCompileError as e:
    print(f"Syntax error: {e}")
