import streamlit as st
import numpy as np
import json
import os
from sklearn.linear_model import LogisticRegression
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# =========================================================
# CONFIG
# =========================================================
st.set_page_config("STP Smart Assist Pro V8.3 HYBRID AI", layout="wide")

DATA_FILE = "plant_memory.json"

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
# ENGINEERING CALCULATIONS
# =========================================================
def calc_svi(sv30, mlss):
    return (sv30 * 1000) / mlss if mlss else 0

def calc_srt(mlss, volume, was_flow, was_mlss):
    return (mlss * volume) / (was_flow * was_mlss) if was_flow and was_mlss else 0

def calc_fm(flow, bod, mlss, volume):
    return (flow * bod) / (mlss * volume) if mlss and volume else 0

# =========================================================
# INPUT VALIDATION
# =========================================================
def input_validator(do, mlss, nh3, svi, srt, fm):
    warnings = []
    critical = []

    if do < 0:
        critical.append("DO impossible (negative value)")
    elif do < 1:
        warnings.append("Very low DO - process failure likely")
    elif do > 10:
        warnings.append("Unusually high DO - sensor check recommended")

    if mlss < 500:
        critical.append("Severe biomass loss risk")
    elif mlss < 1500:
        warnings.append("Low biomass concentration")

    if nh3 > 50:
        critical.append("Extreme ammonia loading")
    elif nh3 > 20:
        warnings.append("High ammonia load")

    if svi > 200:
        warnings.append("Severe bulking condition")
    elif svi > 150:
        warnings.append("Bulking risk")

    if srt < 2:
        critical.append("System collapse risk (very low SRT)")
    elif srt < 5:
        warnings.append("Low SRT - unstable biomass")

    if fm > 1:
        warnings.append("Very high organic loading")
    elif fm < 0.05:
        warnings.append("Starvation condition")

    return warnings, critical

# =========================================================
# ENGINE LOGIC
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

    fm_low, fm_high = cfg["fm_range"]

    if fm < fm_low:
        result["process"] = "Underloaded"
    elif fm > fm_high:
        result["process"] = "Overloaded"

    if do < 2 and nh3 > 10:
        result["process"] = "Nitrification Failure"

    if not result["issues"]:
        result["issues"] = ["System Stable"]
        result["actions"] = ["Maintain operation"]

    return result

# =========================================================
# ML MODEL
# =========================================================
def train_model():
    data = load_data()

    if len(data) < 10:
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
# HYBRID AI ENGINE (NEW)
# =========================================================
def hybrid_risk(model, x, svi, nh3, do, mlss, srt):

    # -------------------------------
    # RULE-BASED RISK (ENGINEERING)
    # -------------------------------
    risk_rule = 0.0

    if do < 1:
        risk_rule += 0.35
    elif do < 2:
        risk_rule += 0.20

    if nh3 > 20:
        risk_rule += 0.35
    elif nh3 > 10:
        risk_rule += 0.20

    if svi > 200:
        risk_rule += 0.30
    elif svi > 150:
        risk_rule += 0.15

    if mlss < 1500:
        risk_rule += 0.25

    if srt < 5:
        risk_rule += 0.25

    risk_rule = min(risk_rule, 1.0)

    # -------------------------------
    # ML RISK
    # -------------------------------
    if model is None:
        risk_ml = None
    else:
        risk_ml = model.predict_proba([x])[0][1]

    # -------------------------------
    # FINAL HYBRID SCORE
    # -------------------------------
    if risk_ml is None:
        final_risk = risk_rule
        confidence = 0.55
    else:
        final_risk = (0.6 * risk_rule) + (0.4 * risk_ml)
        confidence = 0.85

    return final_risk, confidence, risk_rule, risk_ml

# =========================================================
# PDF GENERATOR
# =========================================================
def generate_pdf(result, score):
    filename = "STP_Report_V8_3.pdf"

    doc = SimpleDocTemplate(filename)
    styles = getSampleStyleSheet()
    content = []

    content.append(Paragraph("🌊 STP SMART ASSIST PRO V8.3 HYBRID AI", styles["Title"]))
    content.append(Spacer(1, 12))

    content.append(Paragraph(f"STATUS: {result['status']}", styles["Heading2"]))
    content.append(Paragraph(f"PROCESS: {result['process']}", styles["Normal"]))
    content.append(Spacer(1, 10))

    content.append(Paragraph("ISSUES:", styles["Heading2"]))
    content.append(Paragraph(", ".join(result["issues"]), styles["Normal"]))
    content.append(Spacer(1, 10))

    content.append(Paragraph("ACTIONS:", styles["Heading2"]))
    content.append(Paragraph(", ".join(result["actions"]), styles["Normal"]))
    content.append(Spacer(1, 10))

    content.append(Paragraph(f"STABILITY SCORE: {score}/100", styles["Heading2"]))

    doc.build(content)
    return filename

# =========================================================
# UI
# =========================================================
st.title("🌊 STP Smart Assist Pro V8.3 - HYBRID AI ENGINE")

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
# VALIDATION
# =========================================================
warnings, critical = input_validator(do, mlss, nh3, svi, srt, fm)

st.subheader("⚠️ Input Health Check")

for c in critical:
    st.error(c)

for w in warnings:
    st.warning(w)

if not warnings and not critical:
    st.success("🟢 Inputs within safe engineering range")

# =========================================================
# ENGINE
# =========================================================
result = decision_engine(do, mlss, nh3, svi, srt, fm, plant)

# =========================================================
# ML + HYBRID AI
# =========================================================
model = train_model()

risk, confidence, risk_rule, risk_ml = hybrid_risk(
    model,
    [do, mlss, nh3, svi, srt, fm],
    svi, nh3, do, mlss, srt
)

# =========================================================
# SCORE
# =========================================================
score = 100

if do < 1:
    score -= 30
elif do < 2:
    score -= 20

if svi > 200:
    score -= 30
elif svi > 150:
    score -= 20

if nh3 > 20:
    score -= 30
elif nh3 > 10:
    score -= 20

if mlss < 1500:
    score -= 20

if srt < 5:
    score -= 20

# =========================================================
# OUTPUT
# =========================================================
st.subheader("🧠 Engineering Result")
st.json(result)

st.subheader("📊 HYBRID AI RISK ENGINE")

st.write(f"🧠 Final Risk: {risk:.2%}")
st.write(f"🎯 Confidence: {confidence:.2%}")

st.progress(min(int(risk * 100), 100))

if risk > 0.7:
    st.error("🔴 HIGH RISK")
elif risk > 0.4:
    st.warning("🟠 MEDIUM RISK")
else:
    st.success("🟢 LOW RISK")

with st.expander("🔍 Breakdown"):
    st.write(f"Rule-based risk: {risk_rule:.2%}")
    st.write(f"ML risk: {risk_ml if risk_ml is not None else 'Not trained yet'}")

st.metric("Stability Score", score)

# =========================================================
# SAVE MEMORY
# =========================================================
if st.button("Save Case to AI Memory"):
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
    st.success("Case saved")

# =========================================================
# PDF EXPORT
# =========================================================
if st.button("Generate PDF Report"):
    file = generate_pdf(result, score)

    with open(file, "rb") as f:
        st.download_button(
            "Download Report",
            f,
            file_name=file,
            mime="application/pdf"
        )