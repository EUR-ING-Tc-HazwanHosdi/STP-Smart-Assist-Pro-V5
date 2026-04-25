import streamlit as st
import numpy as np
import cv2
from PIL import Image
import json
import os
import hashlib
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# =========================================================
# CONFIG
# =========================================================
st.set_page_config("STP Smart Assist Pro - Master", layout="wide")
USER_DB_FILE = "users.json"

# =========================================================
# USER SYSTEM
# =========================================================
def load_users():
    if not os.path.exists(USER_DB_FILE):
        return {}
    with open(USER_DB_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USER_DB_FILE, "w") as f:
        json.dump(users, f)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_user(username):
    return load_users().get(username)

def create_user(username, password, name):
    users = load_users()
    if username in users:
        return False
    users[username] = {
        "username": username,
        "password": hash_password(password),
        "name": name
    }
    save_users(users)
    return True

def authenticate(username, password):
    user = get_user(username)
    return user and user["password"] == hash_password(password)

# =========================================================
# PLANT CONFIG
# =========================================================
PLANT_CONFIG = {
    "Extended Aeration": {"srt_min": 10, "fm_range": (0.05, 0.15)},
    "Conventional ASP": {"srt_min": 5, "fm_range": (0.2, 0.5)},
    "Package STP": {"srt_min": 8, "fm_range": (0.1, 0.3)}
}

# =========================================================
# PRESETS
# =========================================================
def apply_preset(p):
    return {
        "Residential": {"flow": 800, "bod": 250, "mlss": 3000},
        "Commercial": {"flow": 1200, "bod": 300, "mlss": 3500},
        "Industrial": {"flow": 1500, "bod": 400, "mlss": 4000}
    }.get(p, {})

# =========================================================
# CALCULATIONS
# =========================================================
def calculate_svi(sv30, mlss):
    return (sv30 * 1000) / mlss if mlss else 0

def calculate_srt(mlss, volume, was_flow, was_mlss):
    return (mlss * volume) / (was_flow * was_mlss) if was_flow and was_mlss else 0

def calculate_fm(flow, bod, mlss, volume):
    return (flow * bod) / (mlss * volume) if mlss and volume else 0

# =========================================================
# DECISION ENGINE
# =========================================================
def decision_engine(data, plant_type):
    cfg = PLANT_CONFIG[plant_type]
    do, mlss, nh3, svi, srt, fm = data.values()

    result = {
        "status": "🟢 NORMAL",
        "issue": "Stable Operation",
        "root": [],
        "impact": [],
        "actions": [],
        "confidence": "MEDIUM"
    }

    if mlss < 500 or srt < 3:
        return {
            "status": "🔴 CRITICAL",
            "issue": "Biomass Washout",
            "root": ["Low MLSS / SRT"],
            "impact": ["Process failure"],
            "actions": ["Stop wasting", "Increase SRT"],
            "confidence": "HIGH"
        }

    if do < 2:
        result["status"] = "🔴 CRITICAL"
        result["issue"] = "Low DO"
        result["root"].append("Insufficient aeration")
        result["actions"].append("Increase aeration")

    if nh3 > 10:
        result["issue"] = "Nitrification Failure"
        result["root"].append("Low SRT or DO")

    if svi > 150:
        result["issue"] = "Bulking Risk"
        result["root"].append("Filamentous bacteria")

    fm_low, fm_high = cfg["fm_range"]
    if fm < fm_low:
        result["issue"] = "Underloading"
    elif fm > fm_high:
        result["issue"] = "Overloading"

    if not result["root"]:
        result["root"] = ["System stable"]
    if not result["actions"]:
        result["actions"] = ["Maintain operation"]

    return result

# =========================================================
# COMPLIANCE
# =========================================================
def compliance_check(svi, do, nh3, srt):
    c = []
    if do < 2: c.append("DO < 2 mg/L")
    if svi > 150: c.append("SVI high")
    if nh3 > 10: c.append("NH3 high")
    if srt < 5: c.append("SRT low")
    return c or ["Within acceptable range"]

# =========================================================
# PDF
# =========================================================

def generate_pdf(data, result, filename="stp_report.pdf"):
    doc = SimpleDocTemplate(filename)
    styles = getSampleStyleSheet()
    content = []

    def add(title, value):
        content.append(Paragraph(title, styles["Heading2"]))
        content.append(Paragraph(str(value), styles["Normal"]))
        content.append(Spacer(1, 10))

    # TITLE
    content.append(Paragraph("STP SMART ASSIST REPORT", styles["Title"]))
    content.append(Spacer(1, 15))

    # INPUT DATA
    add("INPUT DATA", "")
    for k, v in data.items():
        content.append(Paragraph(f"{k}: {v}", styles["Normal"]))

    content.append(Spacer(1, 10))

    # STATUS
    add("STATUS", result.get("status", "N/A"))
    add("ISSUE", result.get("issue", "N/A"))

    # ROOT CAUSE
    add("ROOT CAUSE", "")
    for r in result.get("root_cause", []):
        content.append(Paragraph(f"• {r}", styles["Normal"]))

    content.append(Spacer(1, 10))

    # IMPACT
    add("IMPACT", "")
    for i in result.get("impact", []):
        content.append(Paragraph(f"• {i}", styles["Normal"]))

    content.append(Spacer(1, 10))

    # ACTIONS
    add("ACTIONS", "")
    for a in result.get("actions", []):
        content.append(Paragraph(f"• {a}", styles["Normal"]))

    content.append(Spacer(1, 10))

    # CONFIDENCE
    add("CONFIDENCE", result.get("confidence", "N/A"))

    doc.build(content)
    return filename

# =========================================================
# UI
# =========================================================
st.title("🌊 STP Smart Assist Pro - Master")

# LOGIN
tab1, tab2 = st.tabs(["Login", "Register"])

with tab1:
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        if authenticate(u, p):
            st.session_state["user"] = get_user(u)
            st.rerun()

with tab2:
    ru = st.text_input("Username", key="ru")
    rp = st.text_input("Password", type="password", key="rp")
    rn = st.text_input("Name")
    if st.button("Register"):
        create_user(ru, rp, rn)

if not st.session_state.get("user"):
    st.stop()

# CONFIG
plant_type = st.selectbox("Plant Type", list(PLANT_CONFIG.keys()))
preset = st.selectbox("Preset", ["None", "Residential", "Commercial", "Industrial"])
preset_data = apply_preset(preset)

# INPUT
sv30 = st.number_input("SV30", 250.0)
mlss = st.number_input("MLSS", preset_data.get("mlss", 3000.0))
do = st.number_input("DO", 2.0)
nh3 = st.number_input("NH3", 5.0)

volume = st.number_input("Volume", 500.0)
was_flow = st.number_input("WAS Flow", 50.0)
was_mlss = st.number_input("WAS MLSS", 8000.0)
flow = st.number_input("Flow", preset_data.get("flow", 1000.0))
bod = st.number_input("BOD", preset_data.get("bod", 250.0))

# CALC
svi = calculate_svi(sv30, mlss)
srt = calculate_srt(mlss, volume, was_flow, was_mlss)
fm = calculate_fm(flow, bod, mlss, volume)

data = {"do": do, "mlss": mlss, "nh3": nh3, "svi": svi, "srt": srt, "fm": fm}
result = decision_engine(data, plant_type)

# OUTPUT
st.subheader("Decision")
st.write(result)

# COMPLIANCE
st.subheader("Compliance")
for c in compliance_check(svi, do, nh3, srt):
    st.write("•", c)

# PDF
if st.button("Generate PDF"):
    f = generate_pdf(data, result)
    with open(f, "rb") as file:
        st.download_button("Download", file)

# IMAGE
img = st.file_uploader("Upload Image")
if img:
    st.image(Image.open(img))