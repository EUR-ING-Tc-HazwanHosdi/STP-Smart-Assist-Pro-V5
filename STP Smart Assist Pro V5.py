import streamlit as st
import numpy as np
import json
import os
from datetime import datetime
from sklearn.linear_model import LogisticRegression

# =========================================================
# CONFIG
# =========================================================
st.set_page_config("STP SCADA Autonomous AI v4", layout="wide")

DATA_FILE = "scada_v4_history.json"

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
# MEMORY (SCADA HISTORIAN)
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
# ENGINEERING CALC
# =========================================================
def calc_svi(sv30, mlss):
    return (sv30 * 1000) / mlss if mlss else 0

def calc_srt(mlss, volume, was_flow, was_mlss):
    return (mlss * volume) / (was_flow * was_mlss) if was_flow and was_mlss else 0

def calc_fm(flow, bod, mlss, volume):
    return (flow * bod) / (mlss * volume) if mlss and volume else 0

# =========================================================
# ANOMALY ENGINE
# =========================================================
def anomaly(do, nh3, svi, mlss, srt):
    score = 0

    if do < 1: score += 0.35
    elif do < 2: score += 0.20

    if nh3 > 20: score += 0.35
    elif nh3 > 10: score += 0.20

    if svi > 180: score += 0.30

    if mlss < 1500: score += 0.25

    if srt < 5: score += 0.30

    return min(score, 1.0)

# =========================================================
# DIGITAL TWIN FORECAST (48H SIMULATION)
# =========================================================
def forecast(do, nh3, svi):

    return {
        "DO_48h": max(do - np.random.uniform(0.5, 1.2), 0),
        "NH3_48h": nh3 + np.random.uniform(2, 8),
        "SVI_48h": svi + np.random.uniform(10, 40)
    }

# =========================================================
# AUTONOMOUS CONTROL ENGINE (KEY UPGRADE)
# =========================================================
def autonomous_control(do, nh3, svi, mlss, srt):

    actions = []

    # =====================================================
    # ENERGY OPTIMIZATION (AERATION CONTROL)
    # =====================================================
    if do > 4:
        actions.append({
            "priority": "LOW",
            "action": "Reduce blower speed (-10% to -20%)",
            "reason": "Excess dissolved oxygen = energy waste"
        })

    elif do < 1:
        actions.append({
            "priority": "HIGH",
            "action": "Increase blower capacity (+30–50%)",
            "reason": "Critical oxygen deficit affecting biology"
        })

    # =====================================================
    # LOAD CONTROL
    # =====================================================
    if nh3 > 20:
        actions.append({
            "priority": "HIGH",
            "action": "Reduce influent load / equalization needed",
            "reason": "Nitrification failure risk"
        })

    # =====================================================
    # SLUDGE CONTROL
    # =====================================================
    if svi > 180:
        actions.append({
            "priority": "HIGH",
            "action": "Adjust RAS/WAS balance (reduce WAS)",
            "reason": "Sludge bulking detected"
        })

    # =====================================================
    # SRT CONTROL
    # =====================================================
    if srt < 5:
        actions.append({
            "priority": "CRITICAL",
            "action": "Stop sludge wasting immediately",
            "reason": "Biomass washout risk"
        })

    return sorted(actions, key=lambda x: x["priority"], reverse=True)

# =========================================================
# CONTROL IMPACT SIMULATION
# =========================================================
def simulate_action(do, nh3, svi, action):

    if "blower" in action.lower():
        do_new = min(do + 1.5, 8)
        nh3_new = max(nh3 - 2, 0)
    else:
        do_new = do
        nh3_new = nh3

    if "sludge" in action.lower() or "wasting" in action.lower():
        svi_new = max(svi - 20, 80)
    else:
        svi_new = svi

    return do_new, nh3_new, svi_new

# =========================================================
# DECISION ENGINE
# =========================================================
def decision_engine(do, mlss, nh3, svi, srt, fm, plant):

    cfg = PLANT_CONFIG[plant]

    if mlss < 500 or srt < cfg["srt_min"]:
        return {
            "status": "🔴 CRITICAL",
            "summary": "Biomass collapse risk detected",
            "reason": ["Low MLSS or SRT failure"],
            "actions": ["Emergency sludge retention required"]
        }

    return {
        "status": "🟠 CONTROL MODE ACTIVE",
        "summary": "System requires optimization",
        "reason": ["Operational stress detected"],
        "actions": []
    }

# =========================================================
# ML MODEL
# =========================================================
def train_model():
    data = load_data()

    if len(data) < 25:
        return None

    X, y = [], []

    for d in data:
        X.append([d["do"], d["mlss"], d["nh3"], d["svi"], d["srt"], d["fm"]])
        y.append(d["failure"])

    model = LogisticRegression()
    model.fit(X, y)

    return model

# =========================================================
# HYBRID RISK
# =========================================================
def hybrid_risk(model, x, do, nh3, svi, mlss, srt):

    rule = anomaly(do, nh3, svi, mlss, srt)

    if model is None:
        ml = None
        final = rule
        confidence = 0.65
    else:
        ml = model.predict_proba([x])[0][1]
        final = (0.7 * rule) + (0.3 * ml)
        confidence = 0.88

    return final, confidence, rule, ml

# =========================================================
# UI
# =========================================================
st.title("🏭 STP SCADA Autonomous Control AI v4")

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
# CALC
# =========================================================
svi = calc_svi(sv30, mlss)
srt = calc_srt(mlss, volume, was_flow, was_mlss)
fm = calc_fm(flow, bod, mlss, volume)

# =========================================================
# ENGINE
# =========================================================
result = decision_engine(do, mlss, nh3, svi, srt, fm, plant)

model = train_model()

risk, confidence, rule_risk, ml_risk = hybrid_risk(
    model,
    [do, mlss, nh3, svi, srt, fm],
    do, nh3, svi, mlss, srt
)

forecast_data = forecast(do, nh3, svi)

actions = autonomous_control(do, nh3, svi, mlss, srt)

# =========================================================
# DASHBOARD
# =========================================================
st.subheader("📊 SCADA Control Dashboard")

c1, c2, c3, c4 = st.columns(4)
c1.metric("DO", f"{do:.2f}")
c2.metric("NH3", f"{nh3:.2f}")
c3.metric("SVI", f"{svi:.2f}")
c4.metric("SRT", f"{srt:.2f}")

# =========================================================
# CONTROL ACTIONS (AUTOPILOT)
# =========================================================
st.subheader("🤖 Autonomous Control Recommendations")

for a in actions:
    st.write(f"⚙️ {a['action']}")
    st.caption(f"Reason: {a['reason']} | Priority: {a['priority']}")

# =========================================================
# SIMULATION MODE
# =========================================================
st.subheader("🧪 What-if Simulation (First Action)")

if actions:
    do_new, nh3_new, svi_new = simulate_action(do, nh3, svi, actions[0]["action"])

    st.write("After applying top action:")
    st.write(f"DO → {do_new:.2f}")
    st.write(f"NH3 → {nh3_new:.2f}")
    st.write(f"SVI → {svi_new:.2f}")

# =========================================================
# FORECAST
# =========================================================
st.subheader("📉 48H Digital Twin Forecast")

st.write(f"DO → {forecast_data['DO_48h']:.2f}")
st.write(f"NH3 → {forecast_data['NH3_48h']:.2f}")
st.write(f"SVI → {forecast_data['SVI_48h']:.2f}")

# =========================================================
# STATUS
# =========================================================
st.subheader("🚨 System Status")

if risk > 0.7:
    st.error("🔴 AUTONOMOUS SYSTEM HIGH RISK")
elif risk > 0.4:
    st.warning("🟠 CONTROL OPTIMIZATION REQUIRED")
else:
    st.success("🟢 STABLE")

st.progress(int(risk * 100))

# =========================================================
# SAVE
# =========================================================
if st.button("Save Autonomous Snapshot"):
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

    st.success("Saved to autonomous SCADA memory")