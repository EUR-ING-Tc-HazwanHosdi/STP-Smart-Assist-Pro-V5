import streamlit as st
import numpy as np
import json
import os
import time
from sklearn.linear_model import LogisticRegression

# =========================================================
# CONFIG
# =========================================================
st.set_page_config("STP SCADA Industrial AI v2", layout="wide")

DATA_FILE = "scada_stp_memory.json"

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
# MEMORY
# =========================================================
def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

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
# SCADA ANOMALY ENGINE
# =========================================================
def anomaly_score(do, nh3, svi, mlss, srt):

    score = 0

    # DO trend stress
    if do < 0.5:
        score += 0.35
    elif do < 1:
        score += 0.25
    elif do < 2:
        score += 0.10

    # Ammonia loading
    if nh3 > 25:
        score += 0.35
    elif nh3 > 15:
        score += 0.20

    # Sludge settleability
    if svi > 200:
        score += 0.30
    elif svi > 150:
        score += 0.15

    # Biomass health
    if mlss < 1500:
        score += 0.25

    # SRT instability
    if srt < 3:
        score += 0.30
    elif srt < 5:
        score += 0.15

    return min(score, 1.0)

# =========================================================
# ENGINE LOGIC
# =========================================================
def decision_engine(do, mlss, nh3, svi, srt, fm, plant):

    cfg = PLANT_CONFIG[plant]

    result = {
        "status": "🟢 STABLE",
        "process": "Normal Operation",
        "issues": [],
        "actions": []
    }

    if mlss < 500 or srt < cfg["srt_min"]:
        return {
            "status": "🔴 CRITICAL",
            "process": "Biomass Failure Risk",
            "issues": ["Low MLSS / SRT"],
            "actions": ["Stop wasting sludge", "Increase SRT immediately"]
        }

    if do < 2:
        result["issues"].append("Low DO")
        result["actions"].append("Increase aeration")

    if nh3 > 10:
        result["issues"].append("High NH3 load")
        result["actions"].append("Improve nitrification")

    if svi > 150:
        result["issues"].append("Bulking risk")
        result["actions"].append("Check sludge settleability")

    if not result["issues"]:
        result["issues"] = ["System Stable"]
        result["actions"] = ["Maintain operation"]

    return result

# =========================================================
# ML MODEL
# =========================================================
def train_model():
    data = load_data()

    if len(data) < 20:
        return None

    X = []
    y = []

    for d in data:
        X.append([d["do"], d["mlss"], d["nh3"], d["svi"], d["srt"], d["fm"]])
        y.append(d["failure"])

    model = LogisticRegression()
    model.fit(X, y)

    return model

# =========================================================
# HYBRID SCADA RISK ENGINE
# =========================================================
def scada_risk(model, x, do, nh3, svi, mlss, srt):

    rule = anomaly_score(do, nh3, svi, mlss, srt)

    if model is None:
        ml = None
        final = rule
        confidence = 0.60
    else:
        ml = model.predict_proba([x])[0][1]
        final = (0.7 * rule) + (0.3 * ml)
        confidence = 0.85

    return final, confidence, rule, ml

# =========================================================
# DIGITAL TWIN (SIMULATION)
# =========================================================
def simulate_future(do, nh3, svi):

    return {
        "DO_24h": max(do - np.random.uniform(0.2, 0.8), 0),
        "NH3_24h": nh3 + np.random.uniform(1, 5),
        "SVI_24h": svi + np.random.uniform(5, 20)
    }

# =========================================================
# UI
# =========================================================
st.title("🏭 STP SCADA Industrial AI v2 - Digital Twin System")

plant = st.selectbox("Plant Type", list(PLANT_CONFIG.keys()))

col1, col2 = st.columns(2)

with col1:
    sv30 = st.number_input("SV30", value=250.0)
    mlss = st.number_input("MLSS", value=3000.0)
    do = st.number_input("DO", value=2.0)
    nh3 = st.number_input("NH3", value=5.0)

with col2:
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

# =========================================================
# ENGINE
# =========================================================
result = decision_engine(do, mlss, nh3, svi, srt, fm, plant)

# =========================================================
# ML + SCADA RISK
# =========================================================
model = train_model()

risk, confidence, rule_risk, ml_risk = scada_risk(
    model,
    [do, mlss, nh3, svi, srt, fm],
    do, nh3, svi, mlss, srt
)

# =========================================================
# DIGITAL TWIN FORECAST
# =========================================================
forecast = simulate_future(do, nh3, svi)

# =========================================================
# KPI DASHBOARD (SCADA STYLE)
# =========================================================
st.subheader("📊 SCADA Live KPIs")

k1, k2, k3, k4 = st.columns(4)

k1.metric("DO", f"{do:.2f}")
k2.metric("NH3", f"{nh3:.2f}")
k3.metric("SVI", f"{svi:.2f}")
k4.metric("SRT", f"{srt:.2f}")

st.subheader("⚠️ Alarm System")

if risk > 0.7:
    st.error("🔴 CRITICAL ALARM")
elif risk > 0.4:
    st.warning("🟠 WARNING ALERT")
else:
    st.success("🟢 NORMAL OPERATION")

st.progress(int(risk * 100))

# =========================================================
# DIGITAL TWIN VIEW
# =========================================================
st.subheader("🧬 24H Digital Twin Forecast")

st.write(f"DO → {forecast['DO_24h']:.2f}")
st.write(f"NH3 → {forecast['NH3_24h']:.2f}")
st.write(f"SVI → {forecast['SVI_24h']:.2f}")

# =========================================================
# ENGINE OUTPUT
# =========================================================
st.subheader("🧠 Engineering Decision Engine")
st.json(result)

# =========================================================
# RISK BREAKDOWN
# =========================================================
with st.expander("🔍 SCADA Risk Breakdown"):
    st.write(f"Rule Risk: {rule_risk:.2%}")
    st.write(f"ML Risk: {ml_risk if ml_risk is not None else 'Not trained'}")
    st.write(f"Confidence: {confidence:.2%}")

st.metric("Plant Stability Index", f"{100*(1-risk):.1f}%")

# =========================================================
# SAVE DATA
# =========================================================
if st.button("Save SCADA Case"):
    data = load_data()

    data.append({
        "do": do,
        "mlss": mlss,
        "nh3": nh3,
        "svi": svi,
        "srt": srt,
        "fm": fm,
        "failure": 1 if risk > 0.6 else 0
    })

    save_data(data)
    st.success("Saved to SCADA memory system")