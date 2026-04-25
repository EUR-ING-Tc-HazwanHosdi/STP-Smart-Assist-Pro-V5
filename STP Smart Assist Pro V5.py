import streamlit as st
import numpy as np
import json
import os
from sklearn.linear_model import LogisticRegression

# =========================================================
# CONFIG
# =========================================================
st.set_page_config("STP Industrial AI v1", layout="wide")

DATA_FILE = "stp_industrial_memory.json"

# =========================================================
# PLANT CONFIG (ENGINEERING BASELINE)
# =========================================================
PLANT_CONFIG = {
    "Extended Aeration": {"fm_range": (0.05, 0.3), "srt_min": 8},
    "SBR": {"fm_range": (0.08, 0.4), "srt_min": 10},
    "MBBR": {"fm_range": (0.1, 0.5), "srt_min": 5},
    "Oxidation Ditch": {"fm_range": (0.05, 0.25), "srt_min": 12},
}

# =========================================================
# MEMORY SYSTEM
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
# ENGINEERING CALCS
# =========================================================
def calc_svi(sv30, mlss):
    return (sv30 * 1000) / mlss if mlss else 0

def calc_srt(mlss, volume, was_flow, was_mlss):
    return (mlss * volume) / (was_flow * was_mlss) if was_flow and was_mlss else 0

def calc_fm(flow, bod, mlss, volume):
    return (flow * bod) / (mlss * volume) if mlss and volume else 0

# =========================================================
# INDUSTRIAL ANOMALY ENGINE (NO ML REQUIRED)
# =========================================================
def anomaly_score(do, nh3, svi, mlss, srt):
    score = 0.0

    # Oxygen stress
    if do < 0.5:
        score += 0.35
    elif do < 1:
        score += 0.25
    elif do < 2:
        score += 0.15

    # Ammonia stress
    if nh3 > 25:
        score += 0.35
    elif nh3 > 15:
        score += 0.25
    elif nh3 > 10:
        score += 0.15

    # Sludge condition
    if svi > 200:
        score += 0.30
    elif svi > 150:
        score += 0.20

    # Biomass loss
    if mlss < 1500:
        score += 0.25

    # SRT instability
    if srt < 3:
        score += 0.30
    elif srt < 5:
        score += 0.20

    return min(score, 1.0)

# =========================================================
# ENGINEERING RULE ENGINE
# =========================================================
def decision_engine(do, mlss, nh3, svi, srt, fm, plant):

    cfg = PLANT_CONFIG[plant]

    result = {
        "status": "🟢 NORMAL",
        "process": "Stable Operation",
        "issues": [],
        "actions": []
    }

    if mlss < 500 or srt < cfg["srt_min"]:
        return {
            "status": "🔴 CRITICAL",
            "process": "Biomass Washout Risk",
            "issues": ["Low MLSS / SRT"],
            "actions": ["Stop wasting sludge", "Increase SRT immediately"]
        }

    if do < 2:
        result["issues"].append("Low DO")
        result["actions"].append("Increase aeration")

    if nh3 > 10:
        result["issues"].append("High Ammonia")
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

    if len(data) < 15:
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
# HYBRID RISK ENGINE (INDUSTRIAL VERSION)
# =========================================================
def hybrid_risk(model, x, do, nh3, svi, mlss, srt):

    rule_risk = anomaly_score(do, nh3, svi, mlss, srt)

    if model is None:
        ml_risk = None
        final = rule_risk
        confidence = 0.60
    else:
        ml_risk = model.predict_proba([x])[0][1]
        final = (0.7 * rule_risk) + (0.3 * ml_risk)
        confidence = 0.85

    return final, confidence, rule_risk, ml_risk

# =========================================================
# AUTO LABELING (INDUSTRIAL GRADE)
# =========================================================
def auto_label(do, nh3, svi, srt):
    if do < 1 or nh3 > 20 or svi > 180 or srt < 3:
        return 1
    return 0

# =========================================================
# UI
# =========================================================
st.title("🏭 STP Industrial AI v1 - Smart Wastewater Engine")

plant = st.selectbox("Plant Type", list(PLANT_CONFIG.keys()))

sv30 = st.number_input("SV30", value=250.0)
mlss = st.number_input("MLSS", value=3000.0)
do = st.number_input("DO", value=2.0)
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

# =========================================================
# ENGINE
# =========================================================
result = decision_engine(do, mlss, nh3, svi, srt, fm, plant)

# =========================================================
# ML
# =========================================================
model = train_model()

risk, confidence, rule_risk, ml_risk = hybrid_risk(
    model,
    [do, mlss, nh3, svi, srt, fm],
    do, nh3, svi, mlss, srt
)

# =========================================================
# SCORE (INDUSTRIAL KPI)
# =========================================================
stability_index = 100 * (1 - risk)

# =========================================================
# OUTPUT
# =========================================================
st.subheader("🧠 Engineering Result")
st.json(result)

st.subheader("📊 Industrial AI Risk Engine")

st.write(f"⚠️ Risk Score: {risk:.2%}")
st.write(f"🎯 Confidence: {confidence:.2%}")
st.progress(int(risk * 100))

if risk > 0.7:
    st.error("🔴 CRITICAL SYSTEM INSTABILITY")
elif risk > 0.4:
    st.warning("🟠 PROCESS DEVIATION DETECTED")
else:
    st.success("🟢 STABLE OPERATION")

with st.expander("🔍 Diagnostic Breakdown"):
    st.write(f"Rule Risk: {rule_risk:.2%}")
    st.write(f"ML Risk: {ml_risk if ml_risk is not None else 'Not trained yet'}")

st.metric("Stability Index", f"{stability_index:.1f}")

# =========================================================
# MEMORY
# =========================================================
if st.button("Save Case"):
    data = load_data()

    data.append({
        "do": do,
        "mlss": mlss,
        "nh3": nh3,
        "svi": svi,
        "srt": srt,
        "fm": fm,
        "failure": auto_label(do, nh3, svi, srt)
    })

    save_data(data)
    st.success("Saved to industrial dataset")