import streamlit as st
import numpy as np
import json
import os
from datetime import datetime

# =========================================================
# CONFIG
# =========================================================
st.set_page_config("STP SCADA HMI v5", layout="wide")

DATA_FILE = "scada_v5_hmi.json"

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
    return (sv30 * 1000) / mlss if mlss else 0

def calc_srt(mlss, volume, was_flow, was_mlss):
    return (mlss * volume) / (was_flow * was_mlss) if was_flow and was_mlss else 0

def calc_fm(flow, bod, mlss, volume):
    return (flow * bod) / (mlss * volume) if mlss and volume else 0

# =========================================================
# ALARM CLASSIFICATION (HMI STYLE)
# =========================================================
def alarm_system(do, nh3, svi, srt, mlss):

    alarms = []

    # DO
    if do <= 0.5:
        alarms.append(("🔴 CRITICAL", "No oxygen in system"))
    elif do < 1.5:
        alarms.append(("🟠 WARNING", "Low dissolved oxygen"))
    else:
        alarms.append(("🟢 OK", "DO stable"))

    # NH3
    if nh3 > 20:
        alarms.append(("🔴 CRITICAL", "Ammonia overload"))
    elif nh3 > 10:
        alarms.append(("🟠 WARNING", "Elevated ammonia"))
    else:
        alarms.append(("🟢 OK", "Nitrogen stable"))

    # SVI
    if svi > 180:
        alarms.append(("🔴 CRITICAL", "Severe sludge bulking"))
    elif svi > 150:
        alarms.append(("🟠 WARNING", "Bulking tendency"))
    else:
        alarms.append(("🟢 OK", "Good settling"))

    # MLSS
    if mlss < 1500:
        alarms.append(("🔴 CRITICAL", "Low biomass concentration"))

    return alarms

# =========================================================
# CONTROL RECOMMENDATION ENGINE (HMI SIMPLE)
# =========================================================
def control_panel(do, nh3, svi, srt):

    actions = []

    if do < 1:
        actions.append("🔥 Increase aeration (blower +40%)")

    if nh3 > 15:
        actions.append("⚠️ Reduce influent load or equalize flow")

    if svi > 180:
        actions.append("⚙️ Adjust sludge wasting (reduce WAS)")

    if srt < 5:
        actions.append("🧪 Stop sludge wasting immediately")

    if not actions:
        actions.append("🟢 Maintain current operation")

    return actions

# =========================================================
# HEALTH INDEX (SIMPLE HMI KPI)
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
# UI
# =========================================================
st.title("🏭 STP SCADA HMI CONTROL PANEL v5")

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

alarms = alarm_system(do, nh3, svi, srt, mlss)

actions = control_panel(do, nh3, svi, srt)

# =========================================================
# HMI DASHBOARD
# =========================================================
st.subheader("📊 Live Plant Overview")

c1, c2, c3, c4 = st.columns(4)

c1.metric("Plant Health", f"{health}/100")
c2.metric("DO", f"{do:.2f}")
c3.metric("NH3", f"{nh3:.2f}")
c4.metric("SVI", f"{svi:.2f}")

# =========================================================
# ALARMS PANEL
# =========================================================
st.subheader("🚨 Alarm Panel")

for level, msg in alarms:
    if "CRITICAL" in level:
        st.error(f"{level} → {msg}")
    elif "WARNING" in level:
        st.warning(f"{level} → {msg}")
    else:
        st.success(f"{level} → {msg}")

# =========================================================
# CONTROL PANEL
# =========================================================
st.subheader("⚙️ Operator Action Panel")

for a in actions:
    st.write("👉", a)

# =========================================================
# NEXT STEP (VERY IMPORTANT FOR OPERATORS)
# =========================================================
st.subheader("🧭 Recommended Next Step")

if health < 40:
    st.error("Immediate operator intervention required")
elif health < 70:
    st.warning("Adjust aeration and monitor influent load")
else:
    st.success("Continue normal operation")

# =========================================================
# SYSTEM STATUS
# =========================================================
st.subheader("🟢 System Status")

if health < 40:
    st.error("CRITICAL OPERATION STATE")
elif health < 70:
    st.warning("DEGRADED PERFORMANCE")
else:
    st.success("STABLE OPERATION")

st.progress(health)

# =========================================================
# RAW DATA (OPTIONAL ENGINEER VIEW)
# =========================================================
with st.expander("🔍 Engineering Data"):
    st.write("SVI:", svi)
    st.write("SRT:", srt)
    st.write("F/M:", fm)