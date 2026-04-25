import streamlit as st
import numpy as np
import json
import os

# =========================================================
# CONFIG
# =========================================================
st.set_page_config("STP SCADA HMI v5 + Training Mode", layout="wide")

# =========================================================
# PLANT CONFIG
# =========================================================
PLANT_CONFIG = {
    "Extended Aeration": {"fm_range": (0.05, 0.3), "srt_min": 8},
    "SBR": {"fm_range": (0.08, 0.4), "srt_min": 10},
    "MBBR": {"fm_range": (0.1, 0.5), "srt_min": 5},
    "Oxidation Ditch": {"fm_range": (0.05, 0.25), "srt_min": 12},
}

# =========================================================
# CALCULATIONS
# =========================================================
def calc_svi(sv30, mlss):
    return (sv30 * 1000) / mlss if mlss > 0 else 0

def calc_srt(mlss, volume, was_flow, was_mlss):
    return (mlss * volume) / (was_flow * was_mlss) if was_flow > 0 and was_mlss > 0 else 0

def calc_fm(flow, bod, mlss, volume):
    return (flow * bod) / (mlss * volume) if mlss > 0 and volume > 0 else 0

# =========================================================
# TRAINING EXPLANATION ENGINE
# =========================================================
def explain_parameter(param, value):

    if param == "DO":
        if value < 1:
            return "🔴 Critical: No oxygen → biological system failing"
        elif value < 2:
            return "🟠 Low oxygen → nitrification stress"
        else:
            return "🟢 Healthy oxygen level"

    if param == "SRT":
        if value < 3:
            return "🔴 Very low SRT → sludge washout risk"
        elif value < 5:
            return "🟠 Low SRT → unstable biomass"
        elif value <= 15:
            return "🟢 Optimal sludge age"
        else:
            return "🟠 High SRT → old sludge accumulation"

    if param == "NH3":
        if value > 20:
            return "🔴 Ammonia overload → nitrification failure"
        elif value > 10:
            return "🟠 Elevated ammonia"
        else:
            return "🟢 Stable nitrogen removal"

    if param == "SVI":
        if value > 180:
            return "🔴 Severe bulking"
        elif value > 150:
            return "🟠 Bulking risk"
        else:
            return "🟢 Good settling"

    return "No interpretation available"

# =========================================================
# CONTROL ENGINE (HMI STYLE)
# =========================================================
def control_actions(do, nh3, svi, srt):

    actions = []

    if do < 1:
        actions.append("🔥 Increase blower output (+40–50%)")

    elif do < 2:
        actions.append("⚙️ Slight increase aeration (+10–20%)")

    if nh3 > 15:
        actions.append("⚠️ Reduce influent load / equalization needed")

    if svi > 180:
        actions.append("⚙️ Reduce sludge wasting (control bulking)")

    if srt < 5:
        actions.append("🧪 Stop sludge wasting immediately")

    if not actions:
        actions.append("🟢 Maintain current operation")

    return actions

# =========================================================
# PLANT HEALTH INDEX
# =========================================================
def plant_health(do, nh3, svi, srt):

    score = 100

    if do < 1: score -= 40
    elif do < 2: score -= 20

    if nh3 > 20: score -= 30
    elif nh3 > 10: score -= 15

    if svi > 180: score -= 25

    if srt < 5: score -= 25

    return max(score, 0)

# =========================================================
# TRAINING MODE UI
# =========================================================
st.sidebar.title("🎓 Training Mode")

training_mode = st.sidebar.toggle("Enable Training Overlay", value=True)

level = st.sidebar.selectbox(
    "Operator Level",
    ["Beginner", "Technician", "Engineer"]
)

# =========================================================
# INPUTS
# =========================================================
st.title("🏭 STP SCADA HMI CONTROL v5 + Training System")

plant = st.selectbox("Plant Type", list(PLANT_CONFIG.keys()))

col1, col2 = st.columns(2)

with col1:
    sv30 = st.number_input("SV30", value=250.0)
    mlss = st.number_input("MLSS", value=3000.0)
    do = st.number_input("DO", value=2.0)

with col2:
    nh3 = st.number_input("NH3", value=5.0)
    volume = st.number_input("Volume", value=500.0)
    was_flow = st.number_input("WAS Flow", value=50.0)
    was_mlss = st.number_input("WAS MLSS", value=8000.0)
    flow = st.number_input("Flow", value=1000.0)
    bod = st.number_input("BOD", value=250.0)

# =========================================================
# CALCULATIONS
# =========================================================
svi = calc_svi(sv30, mlss)
srt = calc_srt(mlss, volume, was_flow, was_mlss)
fm = calc_fm(flow, bod, mlss, volume)

health = plant_health(do, nh3, svi, srt)
actions = control_actions(do, nh3, svi, srt)

# =========================================================
# DASHBOARD
# =========================================================
st.subheader("📊 Live Process Overview")

c1, c2, c3, c4 = st.columns(4)

c1.metric("Plant Health", f"{health}/100")
c2.metric("DO", f"{do:.2f}")
c3.metric("NH3", f"{nh3:.2f}")
c4.metric("SRT (days)", f"{srt:.2f}")

# =========================================================
# ALARMS (HMI STYLE)
# =========================================================
st.subheader("🚨 System Status")

if health < 40:
    st.error("🔴 CRITICAL OPERATION STATE")
elif health < 70:
    st.warning("🟠 DEGRADED PERFORMANCE")
else:
    st.success("🟢 STABLE OPERATION")

st.progress(health)

# =========================================================
# CONTROL ACTIONS
# =========================================================
st.subheader("⚙️ Operator Action Panel")

for a in actions:
    st.write("👉", a)

# =========================================================
# TRAINING OVERLAY MODE
# =========================================================
if training_mode:

    st.subheader("🎓 Training Overlay")

    st.info("Operator guidance system for process understanding")

    st.write("### 🧪 DO (Dissolved Oxygen)")
    st.write(explain_parameter("DO", do))

    st.write("### 🧪 SRT (Sludge Retention Time)")
    st.write(explain_parameter("SRT", srt))

    st.write("### 🧪 NH3 (Ammonia)")
    st.write(explain_parameter("NH3", nh3))

    st.write("### 🧪 SVI (Sludge Volume Index)")
    st.write(explain_parameter("SVI", svi))

# =========================================================
# WHAT IF SIMULATION (TRAINING TOOL)
# =========================================================
if training_mode:

    st.subheader("🧭 What-If Simulation")

    sim_do = st.slider("Simulate DO", 0.0, 8.0, float(do))
    st.write("DO Impact:", explain_parameter("DO", sim_do))

    sim_srt = st.slider("Simulate SRT", 0.0, 20.0, float(srt))
    st.write("SRT Impact:", explain_parameter("SRT", sim_srt))

# =========================================================
# ENGINEERING DATA (ADVANCED VIEW)
# =========================================================
with st.expander("🔍 Engineering View"):
    st.write("SVI:", svi)
    st.write("SRT:", srt)
    st.write("F/M:", fm)