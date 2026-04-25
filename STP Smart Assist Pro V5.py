import streamlit as st
import numpy as np
import pandas as pd
import json
import os
from datetime import datetime

# =========================================================
# CONFIG
# =========================================================
st.set_page_config("STP SCADA HMI V6", layout="wide")

# =========================================================
# DARK THEME (COMMERCIAL LOOK)
# =========================================================
st.markdown("""
<style>
body {
    background-color: #0e1117;
}
h1, h2, h3, h4 {
    color: #ffffff;
}
</style>
""", unsafe_allow_html=True)

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
# KPI CARD
# =========================================================
def kpi_card(title, value, color):
    st.markdown(f"""
    <div style="
        background-color:{color};
        padding:18px;
        border-radius:12px;
        text-align:center;
        color:white;">
        <h4>{title}</h4>
        <h2>{value}</h2>
    </div>
    """, unsafe_allow_html=True)

# =========================================================
# AI INSIGHT ENGINE
# =========================================================
def ai_insight(do, nh3, svi, srt, fm, plant):

    insight = []

    if do < 1:
        insight.append("Critical oxygen depletion → biomass respiration collapsing.")

    if nh3 > 20:
        insight.append("Nitrification failure → check aeration & sludge age.")

    if svi > 180:
        insight.append("Severe sludge bulking → filament dominance suspected.")

    if srt < 5:
        insight.append("Low sludge age → biomass washout risk.")

    config = PLANT_CONFIG[plant]
    fm_min, fm_max = config["fm_range"]

    if fm > fm_max:
        insight.append("Organic overloading detected (High F/M).")

    elif fm < fm_min:
        insight.append("Underloading condition (Low F/M).")

    if not insight:
        insight.append("Process stable with balanced kinetics.")

    return insight

# =========================================================
# CONTROL ENGINE
# =========================================================
def control_actions(do, nh3, svi, srt):

    actions = []

    if do < 1:
        actions.append("Increase blower output (+50%)")

    elif do < 2:
        actions.append("Increase aeration (+20%)")

    if nh3 > 15:
        actions.append("Reduce influent load / equalization")

    if svi > 180:
        actions.append("Adjust sludge wasting strategy")

    if srt < 5:
        actions.append("Stop sludge wasting immediately")

    if not actions:
        actions.append("Maintain current operation")

    return actions

# =========================================================
# HEALTH SCORE
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
# LOGGING
# =========================================================
def log_data(data):
    with open("plant_log.json", "a") as f:
        f.write(json.dumps(data) + "\n")

# =========================================================
# SIDEBAR
# =========================================================
st.sidebar.title("⚙️ System Control")

training_mode = st.sidebar.toggle("Training Mode", True)

level = st.sidebar.selectbox(
    "User Level",
    ["Operator", "Technician", "Engineer"]
)

plant = st.sidebar.selectbox("Plant Type", list(PLANT_CONFIG.keys()))

# =========================================================
# INPUT PANEL
# =========================================================
st.title("🏭 STP SCADA HMI V6")

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
# CALC
# =========================================================
svi = calc_svi(sv30, mlss)
srt = calc_srt(mlss, volume, was_flow, was_mlss)
fm = calc_fm(flow, bod, mlss, volume)
health = plant_health(do, nh3, svi, srt)

actions = control_actions(do, nh3, svi, srt)
insights = ai_insight(do, nh3, svi, srt, fm, plant)

# =========================================================
# KPI DASHBOARD
# =========================================================
k1, k2, k3, k4 = st.columns(4)

kpi_card("Health", f"{health}/100",
         "#2ecc71" if health > 70 else "#e74c3c")

kpi_card("DO", f"{do:.2f}", "#3498db")
kpi_card("NH3", f"{nh3:.2f}", "#f39c12")
kpi_card("SRT", f"{srt:.2f}", "#9b59b6")

# =========================================================
# STATUS
# =========================================================
st.subheader("🚨 System Status")

if health < 40:
    st.error("CRITICAL STATE")
elif health < 70:
    st.warning("DEGRADED PERFORMANCE")
else:
    st.success("STABLE OPERATION")

st.progress(health)

# =========================================================
# MAIN PANELS
# =========================================================
colA, colB = st.columns(2)

# CONTROL PANEL
with colA:
    st.subheader("⚙️ Control Actions")

    for a in actions:
        st.write("👉", a)

# AI PANEL
with colB:
    st.subheader("🧠 AI Insights")

    for i in insights:
        st.write("•", i)

# =========================================================
# TREND SIMULATION
# =========================================================
st.subheader("📈 Process Trend (Simulated)")

trend = pd.DataFrame({
    "Time": range(20),
    "DO": np.random.normal(do, 0.3, 20),
    "NH3": np.random.normal(nh3, 1, 20)
})

st.line_chart(trend.set_index("Time"))

# =========================================================
# TRAINING MODE
# =========================================================
if training_mode:
    st.subheader("🎓 Training Overlay")

    if level == "Operator":
        st.info("Basic operation guidance enabled")

    elif level == "Engineer":
        st.write("F/M Ratio:", fm)
        st.write("SVI:", svi)

    st.subheader("🧭 What-If Simulation")

    sim_do = st.slider("Simulate DO", 0.0, 8.0, float(do))
    st.write("Impact:", "Low DO risk" if sim_do < 2 else "Healthy")

# =========================================================
# ENGINEERING VIEW
# =========================================================
with st.expander("🔍 Advanced Engineering Data"):
    st.write("SVI:", svi)
    st.write("SRT:", srt)
    st.write("F/M:", fm)

# =========================================================
# LOGGING
# =========================================================
log_data({
    "time": str(datetime.now()),
    "DO": do,
    "NH3": nh3,
    "SRT": srt,
    "SVI": svi,
    "Health": health
})