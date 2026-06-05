import streamlit as st
import numpy as np
import pandas as pd
import json
import os
from datetime import datetime

# =========================================================
# CONFIG & LOGO LINKING
# =========================================================
LOGO_URL = "ChatGPT Image Jun 4, 2026, 07_18_35 AM.png"

st.set_page_config(
    page_title="STP SMART ASSIST PRO V.5.0", 
    page_icon=LOGO_URL, 
    layout="wide"
)

# =========================================================
# ADVANCED COMMERCIAL DARK THEME CSS
# =========================================================
st.markdown("""
<style>
    /* Base App Styling */
    .stApp {
        background-color: #0B0E14;
    }
    h1, h2, h3, h4 {
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
        font-weight: 600;
        letter-spacing: -0.5px;
    }
    /* Input border polish */
    div[data-testid="stMetricValue"] {
        font-family: 'Courier New', monospace;
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
# HIGH-ATTRACTION KPI CARD
# =========================================================
def kpi_card(title, value, color, unit=""):
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #161B25 0%, #0F121A 100%);
        border-left: 4px solid {color};
        border-top: 1px solid #232B3A;
        border-right: 1px solid #232B3A;
        border-bottom: 1px solid #232B3A;
        padding: 16px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        margin-bottom: 12px;">
        <div style="color: #8A96A8; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">
            {title}
        </div>
        <div style="display: flex; align-items: baseline; margin-top: 4px;">
            <span style="color: white; font-size: 26px; font-weight: 700; font-family: monospace;">{value}</span>
            <span style="color: #4B5666; font-size: 13px; margin-left: 4px;">{unit}</span>
        </div>
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
# SIDEBAR (LOGO INTEGRATED)
# =========================================================
st.sidebar.image(LOGO_URL, use_container_width=True)
st.sidebar.markdown("<div style='margin-top: -15px;'></div>", unsafe_allow_html=True)
st.sidebar.title("⚙️ System Control")

training_mode = st.sidebar.toggle("Training Mode", True)

level = st.sidebar.selectbox(
    "User Level",
    ["Operator", "Technician", "Engineer"]
)

plant = st.sidebar.selectbox("Plant Type", list(PLANT_CONFIG.keys()))

# =========================================================
# MAIN APP HEADER
# =========================================================
st.markdown("<h1 style='margin-bottom: 0px;'>🏭 STP SMART ASSIST PRO</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #53637A; font-size: 14px; margin-top: 0px;'>HMI Core Terminal Enterprise V5.0</p>", unsafe_allow_html=True)

# =========================================================
# INPUT PANEL (WITH COLLAPSIBLE CONTAINER SHIELD)
# =========================================================
with st.container(border=True):
    st.markdown("<p style='font-size: 12px; font-weight:600; text-transform:uppercase; color:#8A96A8; letter-spacing:0.5px; margin-bottom: 15px;'>📡 Telemetry Ingestion Desk</p>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    with col1:
        sv30 = st.number_input("SV30 (mL/L)", value=250.0)
        mlss = st.number_input("MLSS (mg/L)", value=3000.0)
        do = st.number_input("DO (mg/L)", value=2.0)

    with col2:
        nh3 = st.number_input("NH3 (mg/L)", value=5.0)
        volume = st.number_input("Reactor Volume (m³)", value=500.0)
        was_flow = st.number_input("WAS Flow (m³/d)", value=50.0)
        was_mlss = st.number_input("WAS MLSS (mg/L)", value=8000.0)
        flow = st.number_input("Influent Flow (m³/d)", value=1000.0)
        bod = st.number_input("BOD (mg/L)", value=250.0)

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
st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
k1, k2, k3, k4 = st.columns(4)

health_color = "#2ecc71" if health > 70 else ("#f1c40f" if health >= 40 else "#e74c3c")

with k1:
    kpi_card("System Health", f"{health}/100", health_color, unit="%")
with k2:
    kpi_card("Dissolved Oxygen", f"{do:.2f}", "#3498db", unit="mg/L")
with k3:
    kpi_card("Ammonia Nitrogen", f"{nh3:.2f}", "#f39c12", unit="mg/L")
with k4:
    kpi_card("Sludge Age (SRT)", f"{srt:.2f}", "#9b59b6", unit="Days")

# =========================================================
# STATUS ALERT LINE
# =========================================================
if health < 40:
    st.error("🚨 **CRITICAL STATE** — Biological parameters require emergency adjustment.")
elif health < 70:
    st.warning("⚠️ **DEGRADED PERFORMANCE** — Sub-optimal process variables detected.")
else:
    st.success("✨ **STABLE OPERATION** — Plant balance operating within standard parameters.")

st.progress(int(health))

# =========================================================
# MAIN PANELS (CLEAN BLOCK CONTAINER LAYOUT)
# =========================================================
st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
colA, colB = st.columns(2)

# CONTROL PANEL
with colA:
    with st.container(border=True):
        st.subheader("⚙️ Control Automation Protocol")
        for a in actions:
            st.markdown(f"<span style='color: #E2E8F0;'>👉 {a}</span>", unsafe_allow_html=True)

# AI PANEL
with colB:
    with st.container(border=True):
        st.subheader("🧠 Operational Core Insights")
        for i in insights:
            st.markdown(f"<span style='color: #E2E8F0;'>• {i}</span>", unsafe_allow_html=True)

# =========================================================
# TREND SIMULATION
# =========================================================
st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
st.subheader("📈 Process Trend Real-Time Simulation")

trend = pd.DataFrame({
    "Time Tick": range(20),
    "DO Sensor Probe": np.random.normal(do, 0.15, 20),
    "NH3 Analytical Loop": np.random.normal(nh3, 0.5, 20)
})

st.line_chart(trend.set_index("Time Tick"))

# =========================================================
# TRAINING MODE
# =========================================================
if training_mode:
    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
    with st.container(border=True):
        st.subheader("🎓 Active Simulation Overlay")

        if level == "Operator":
            st.info("💡 Basic configuration assistance active. Monitor DO levels closely during peak inflow hours.")
        elif level == "Engineer":
            ec1, ec2 = st.columns(2)
            ec1.metric("Calculated Kinetic F/M Ratio", f"{fm:.3f}")
            ec2.metric("Sludge Volume Index (SVI)", f"{svi:.1f} mL/g")

        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        st.markdown("**What-If Matrix Calibration**")
        sim_do = st.slider("Simulate DO Variance", 0.0, 8.0, float(do), label_visibility="collapsed")
        st.write("Dynamic Evaluation:", "🚨 Critical low DO risk" if sim_do < 2 else "✅ Kinetic balance protected")

# =========================================================
# ENGINEERING VIEW
# =========================================================
with st.expander("🔍 Advanced Process Registers"):
    st.write("Calculated SVI:", svi)
    st.write("Calculated SRT:", srt)
    st.write("Calculated F/M:", fm)

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
